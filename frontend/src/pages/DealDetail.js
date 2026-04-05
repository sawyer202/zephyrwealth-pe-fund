import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, FileText, Download, Loader2, CheckCircle2, RefreshCw,
  Shield, Building2, Globe, TrendingUp, DollarSign, AlertTriangle,
  ChevronRight, Check,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

const STAGE_LABELS = { leads: 'Leads', due_diligence: 'Due Diligence', ic_review: 'IC Review', closing: 'Closing' };
const STAGE_ORDER = ['leads', 'due_diligence', 'ic_review', 'closing'];

const MANDATE_STYLE = {
  'In Mandate': 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20',
  'Exception': 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/20',
  'Exception Cleared': 'bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/20',
  'Blocked': 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/20',
};

const HEALTH_COLORS = { Low: '#22C55E', Medium: '#F59E0B', High: '#EF4444', Aligned: '#22C55E', Misaligned: '#EF4444', Complete: '#22C55E', Partial: '#F59E0B', Missing: '#EF4444' };
const OVERALL_COLORS = { 'Recommend Approve': '#22C55E', 'Review': '#F59E0B', 'Block': '#EF4444' };

const DOC_LABELS = { financials: 'Financial Statements', cap_table: 'Cap Table', im: 'Information Memorandum', passport: 'ID Document', proof_of_address: 'Proof of Address' };

function formatCurrency(v) { if (!v && v !== 0) return '—'; return `$${Number(v).toLocaleString()}`; }
function formatDate(d) { if (!d) return '—'; return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); }
function formatSize(b) { if (b < 1024) return `${b} B`; if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`; return `${(b / 1048576).toFixed(1)} MB`; }

function InfoRow({ label, value }) {
  return (
    <div className="flex items-start justify-between py-2.5 border-b border-[#F3F4F6] last:border-0">
      <span className="text-xs text-[#6B7280] uppercase tracking-wider font-semibold w-36 flex-shrink-0">{label}</span>
      <span className="text-sm text-[#1F2937] text-right font-mono">{value || '—'}</span>
    </div>
  );
}

function HealthIndicator({ label, value }) {
  const color = HEALTH_COLORS[value] || '#6B7280';
  return (
    <div className="flex items-center justify-between py-2 border-b border-[#333333] last:border-0">
      <span className="text-xs text-[#9CA3AF] uppercase tracking-wider">{label}</span>
      <div className="flex items-center gap-2">
        <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
        <span className="text-xs font-mono font-semibold" style={{ color }}>{value}</span>
      </div>
    </div>
  );
}

export default function DealDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [deal, setDeal] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [healthScore, setHealthScore] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generatingHealth, setGeneratingHealth] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [movingStage, setMovingStage] = useState('');
  const [overrideNote, setOverrideNote] = useState('');
  const [showOverride, setShowOverride] = useState(null); // stage name needing override
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const canDecide = ['compliance', 'risk'].includes(user?.role);
  const isRisk = user?.role === 'risk';
  const canExportPDF = ['compliance', 'risk'].includes(user?.role);

  const handleExportPDF = async () => {
    try {
      const res = await fetch(`${API}/api/deals/${id}/export-pdf`, { credentials: 'include' });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `IC_Pack_${deal?.company_name?.replace(/ /g, '_') || id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    }
  };

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [dealRes, docsRes] = await Promise.all([
        fetch(`${API}/api/deals/${id}`, { credentials: 'include' }),
        fetch(`${API}/api/deals/${id}/documents`, { credentials: 'include' }),
      ]);
      if (!dealRes.ok) throw new Error('Deal not found');
      setDeal(await dealRes.json());
      if (docsRes.ok) setDocuments(await docsRes.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const fetchHealthScore = async () => {
    setGeneratingHealth(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/deals/${id}/health-score`, { credentials: 'include' });
      if (!res.ok) throw new Error('Failed to load health score');
      setHealthScore(await res.json());
    } catch (e) {
      setError(e.message);
    } finally {
      setGeneratingHealth(false);
    }
  };

  const handleMoveStage = async (targetStage, override = null) => {
    const deal_ = deal;
    if (deal_?.mandate_status === 'Exception' && STAGE_ORDER.indexOf(targetStage) > STAGE_ORDER.indexOf(deal_?.pipeline_stage) && !override) {
      if (!isRisk) {
        setError('Mandate Exception: Risk Officer override required to advance this deal.');
        return;
      }
      setShowOverride(targetStage);
      return;
    }
    setMovingStage(targetStage);
    setError('');
    try {
      const body = { stage: targetStage };
      if (override) body.override_note = override;
      const res = await fetch(`${API}/api/deals/${id}/stage`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json();
        if (err.detail === 'mandate_exception_block') {
          setError('Mandate Exception: Risk Officer override required.');
        } else {
          throw new Error(err.detail || 'Failed to move stage');
        }
        return;
      }
      const data = await res.json();
      setDeal(d => d ? { ...d, pipeline_stage: data.pipeline_stage, mandate_status: data.mandate_status } : d);
      setSuccess(`Deal advanced to ${STAGE_LABELS[targetStage]}`);
      setShowOverride(null);
      setOverrideNote('');
    } catch (e) {
      setError(e.message);
    } finally {
      setMovingStage('');
    }
  };

  const handleExecute = async () => {
    setExecuting(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/deals/${id}/execute`, { method: 'POST', credentials: 'include' });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Execution failed');
      }
      const blob = await res.blob();
      const cd = res.headers.get('Content-Disposition') || '';
      const fnMatch = cd.match(/filename="?([^"]+)"?/);
      const filename = fnMatch ? fnMatch[1] : `Agreement_${id}.txt`;
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setSuccess('Transaction executed. Agreement downloaded. Deal moved to Closing.');
      setDeal(d => d ? { ...d, pipeline_stage: 'closing' } : d);
    } catch (e) {
      setError(e.message);
    } finally {
      setExecuting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={28} className="animate-spin text-[#1B3A6B]" />
          <p className="text-sm text-[#6B7280]">Loading deal...</p>
        </div>
      </div>
    );
  }

  if (error && !deal) {
    return (
      <div className="p-8">
        <button onClick={() => navigate('/deals')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] mb-6">
          <ArrowLeft size={15} /> Back to Deals
        </button>
        <div className="bg-white border border-[#EF4444]/20 rounded-sm p-6 text-center">
          <p className="text-[#EF4444]">{error}</p>
        </div>
      </div>
    );
  }

  if (!deal) return null;

  const currentStageIdx = STAGE_ORDER.indexOf(deal.pipeline_stage || 'leads');
  const nextStage = STAGE_ORDER[currentStageIdx + 1];

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <button onClick={() => navigate('/deals')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] transition-colors mb-3" data-testid="back-to-deals">
            <ArrowLeft size={15} /> Back to Deals
          </button>
          <p className="text-overline mb-1">Deal Pipeline</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading flex items-center gap-3">
            <Building2 size={28} strokeWidth={1.5} color="#1B3A6B" />
            {deal.company_name}
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <span className={`px-2.5 py-0.5 rounded-sm text-xs font-mono uppercase tracking-wide border ${MANDATE_STYLE[deal.mandate_status] || 'bg-gray-100 text-gray-500 border-gray-200'}`} data-testid="mandate-badge">
              {deal.mandate_status === 'Exception' ? '⚠ Mandate Exception' : deal.mandate_status}
            </span>
            <span className={`px-2.5 py-0.5 rounded-sm text-xs font-mono border ${deal.entity_type === 'ICON' ? 'bg-[#7C3AED]/5 text-[#7C3AED] border-[#7C3AED]/20' : 'bg-[#00A8C6]/5 text-[#00A8C6] border-[#00A8C6]/20'}`}>
              {deal.entity_type}
            </span>
            <span className="text-xs text-[#6B7280] font-semibold">{STAGE_LABELS[deal.pipeline_stage] || deal.pipeline_stage}</span>
          </div>
        </div>
        <div className="flex items-center gap-3 mt-1">
          {canExportPDF && (
            <button
              onClick={handleExportPDF}
              data-testid="export-ic-pack-btn"
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-[#252523] text-white rounded-sm hover:bg-[#333333] transition-colors border border-[#444444]"
            >
              <Download size={14} /> Export IC Pack
            </button>
          )}
          <button onClick={fetchAll} className="text-sm text-[#6B7280] hover:text-[#1B3A6B] flex items-center gap-1.5 transition-colors">
            <RefreshCw size={14} /> Refresh
          </button>
        </div>
      </div>

      {/* Pipeline Progress */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-4 mb-6">
        <div className="flex items-center gap-2">
          {STAGE_ORDER.map((stage, i) => {
            const done = i < currentStageIdx;
            const active = i === currentStageIdx;
            return (
              <React.Fragment key={stage}>
                <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-semibold transition-all ${done ? 'bg-[#10B981]/10 text-[#10B981]' : active ? 'bg-[#1B3A6B] text-white' : 'bg-[#F8F9FA] text-[#9CA3AF]'}`}>
                  {done ? <Check size={12} /> : <span className="font-mono">{i + 1}</span>}
                  {STAGE_LABELS[stage]}
                </div>
                {i < STAGE_ORDER.length - 1 && <ChevronRight size={14} className="text-[#D1D5DB] flex-shrink-0" />}
              </React.Fragment>
            );
          })}
        </div>
      </div>

      {/* Banners */}
      {error && <div className="mb-4 p-3 bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-sm text-sm text-[#EF4444]" data-testid="error-banner">{error}</div>}
      {success && <div className="mb-4 p-3 bg-[#10B981]/10 border border-[#10B981]/20 rounded-sm text-sm text-[#10B981] flex items-center gap-2" data-testid="success-banner"><CheckCircle2 size={16} />{success}</div>}

      {/* ICON Notice */}
      {deal.entity_type === 'ICON' && (
        <div className="mb-6 p-4 bg-[#F59E0B]/5 border border-[#F59E0B]/30 rounded-sm">
          <div className="flex items-start gap-2">
            <AlertTriangle size={16} className="text-[#F59E0B] mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-semibold text-[#92400E]">Investment Condominium Notice</p>
              <p className="text-xs text-[#92400E] mt-0.5">Upon execution, the Fund Administrator must update the Register of Participants per the Investment Condominium Act 2014 and notify the Securities Commission of The Bahamas.</p>
            </div>
          </div>
        </div>
      )}

      {/* 3-Column Info Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
          <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
            <Building2 size={15} color="#1B3A6B" />
            <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Company</span>
          </div>
          <div className="px-4 py-2">
            <InfoRow label="Company" value={deal.company_name} />
            <InfoRow label="Sector" value={deal.sector} />
            <InfoRow label="Geography" value={deal.geography} />
            <InfoRow label="Asset Class" value={deal.asset_class} />
            <InfoRow label="Entity Type" value={deal.entity_type} />
            <InfoRow label="Submitted" value={formatDate(deal.submitted_date)} />
          </div>
        </div>
        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
          <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
            <TrendingUp size={15} color="#1B3A6B" />
            <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Financials</span>
          </div>
          <div className="px-4 py-2">
            <InfoRow label="Entry Valuation" value={formatCurrency(deal.entry_valuation)} />
            <InfoRow label="Expected IRR" value={`${deal.expected_irr}%`} />
            <InfoRow label="Stamp Duty Est." value={formatCurrency(deal.stamp_duty_estimate)} />
            <InfoRow label="Mandate" value={deal.mandate_status} />
          </div>
        </div>
        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
          <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
            <Globe size={15} color="#1B3A6B" />
            <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Pipeline Stage</span>
          </div>
          <div className="px-4 py-3">
            <p className="text-2xl font-bold font-mono text-[#1B3A6B] mb-1">{STAGE_LABELS[deal.pipeline_stage] || deal.pipeline_stage}</p>
            {deal.mandate_override_note && (
              <div className="mt-2 p-2 bg-[#F59E0B]/5 border border-[#F59E0B]/20 rounded-sm">
                <p className="text-xs text-[#6B7280] uppercase tracking-wider mb-0.5">Override Note</p>
                <p className="text-xs text-[#374151]">{deal.mandate_override_note}</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Documents */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm mb-6">
        <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
          <FileText size={15} color="#1B3A6B" />
          <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Documents</span>
          <span className="ml-auto text-xs font-mono bg-[#F8F9FA] px-2 py-0.5 rounded-sm border border-[#E5E7EB] text-[#6B7280]">{documents.length} file{documents.length !== 1 ? 's' : ''}</span>
        </div>
        {documents.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-[#9CA3AF]">No documents uploaded</div>
        ) : (
          <div className="divide-y divide-[#F3F4F6]">
            {documents.map(doc => (
              <div key={doc.id} className="flex items-center justify-between px-4 py-3" data-testid={`doc-row-${doc.id}`}>
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-[#1B3A6B]/5 rounded-sm flex items-center justify-center">
                    <FileText size={16} color="#1B3A6B" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-[#1F2937]">{doc.file_name}</p>
                    <p className="text-xs text-[#9CA3AF]">{DOC_LABELS[doc.document_type] || doc.document_type} · {formatSize(doc.file_size)} · {formatDate(doc.uploaded_at)}</p>
                  </div>
                </div>
                <a href={`${API}/api/deals/${id}/documents/${doc.id}/download`} target="_blank" rel="noopener noreferrer" data-testid={`download-${doc.id}`} className="flex items-center gap-1.5 text-xs text-[#1B3A6B] hover:text-[#122A50] border border-[#1B3A6B]/20 px-3 py-1.5 rounded-sm hover:bg-[#1B3A6B]/5 transition-colors">
                  <Download size={13} /> Download
                </a>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Deal Health Score Panel */}
      <div className="bg-[#252523] rounded-sm shadow-lg mb-6" data-testid="health-score-panel">
        <div className="px-5 py-4 border-b border-[#333333] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Shield size={16} color="#00A8C6" />
            <span className="text-sm font-semibold text-white">Deal Health Score</span>
          </div>
          {!healthScore && !generatingHealth && (
            <button onClick={fetchHealthScore} data-testid="load-health-score-btn" className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-[#00A8C6] text-white rounded-sm hover:bg-[#0096B3] transition-colors">
              Load Health Score
            </button>
          )}
          {generatingHealth && <div className="flex items-center gap-2 text-xs text-[#9CA3AF]"><Loader2 size={14} className="animate-spin text-[#00A8C6]" />Loading...</div>}
          {healthScore && <button onClick={fetchHealthScore} disabled={generatingHealth} className="text-xs text-[#9CA3AF] hover:text-white flex items-center gap-1.5 transition-colors"><RefreshCw size={12} />Refresh</button>}
        </div>

        {!healthScore && !generatingHealth && (
          <div className="px-5 py-8 text-center">
            <Shield size={32} className="mx-auto mb-3 text-[#444444]" />
            <p className="text-sm text-[#6B7280]">Click "Load Health Score" to evaluate deal readiness</p>
          </div>
        )}

        {generatingHealth && (
          <div className="px-5 py-8 text-center">
            <Loader2 size={28} className="mx-auto mb-3 text-[#00A8C6] animate-spin" />
            <p className="text-sm text-[#9CA3AF]">Computing deal health score...</p>
          </div>
        )}

        {healthScore && (
          <div className="p-5">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-3">Health Indicators</p>
                <HealthIndicator label="Compliance Risk" value={healthScore.compliance_risk} />
                <HealthIndicator label="Financial Alignment" value={healthScore.financial_alignment} />
                <HealthIndicator label="Document Status" value={healthScore.document_status} />
                <HealthIndicator label="Mandate Status" value={healthScore.mandate_status} />
                <div className="flex items-center justify-between pt-3 mt-2 border-t border-[#333333]">
                  <span className="text-xs text-[#9CA3AF] uppercase tracking-wider">Documents on File</span>
                  <span className="text-xs font-mono text-white">{healthScore.doc_count} file{healthScore.doc_count !== 1 ? 's' : ''}</span>
                </div>
              </div>
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-3">Stamp Duty Estimate</p>
                <div className="border border-[#333333] rounded-sm p-3 mb-3">
                  <p className="text-2xl font-bold font-mono text-white" data-testid="stamp-duty-estimate">{formatCurrency(healthScore.stamp_duty_estimate)}</p>
                  <p className="text-xs text-[#9CA3AF] mt-1">{healthScore.stamp_duty_pct} of entry valuation ({formatCurrency(healthScore.entry_valuation)})</p>
                  <p className="text-xs text-[#F59E0B] mt-2">Estimate only — confirm with Bahamian counsel</p>
                </div>
                <div className="border border-[#333333] rounded-sm p-3">
                  <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-1">Overall Assessment</p>
                  <p className="text-xl font-bold font-mono" style={{ color: OVERALL_COLORS[healthScore.overall] || '#FFC72C' }} data-testid="health-overall">{healthScore.overall}</p>
                </div>
              </div>
            </div>
            <p className="text-center text-xs text-[#444444] mt-5 pt-4 border-t border-[#333333]">
              Rule-based assessment · human review required · ZephyrWealth Compliance Framework
            </p>
          </div>
        )}
      </div>

      {/* Override Modal */}
      {showOverride && isRisk && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-sm shadow-xl p-6 w-full max-w-md mx-4">
            <h3 className="text-base font-semibold text-[#1F2937] mb-2">Mandate Override — Risk Officer</h3>
            <p className="text-sm text-[#6B7280] mb-4">This deal has a Mandate Exception. Provide an override rationale to advance to <strong>{STAGE_LABELS[showOverride]}</strong>.</p>
            <textarea
              value={overrideNote}
              onChange={e => setOverrideNote(e.target.value)}
              placeholder="State reason for override (required)..."
              data-testid="override-note-input"
              className="w-full border border-[#D1D5DB] rounded-sm p-3 text-sm text-[#1F2937] focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] h-24 resize-none mb-4"
            />
            <div className="flex gap-3">
              <button onClick={() => { setShowOverride(null); setOverrideNote(''); }} className="flex-1 px-4 py-2 text-sm border border-[#D1D5DB] rounded-sm text-[#374151] hover:bg-[#F8F9FA]">Cancel</button>
              <button
                onClick={() => handleMoveStage(showOverride, overrideNote || 'Risk Officer override')}
                disabled={!overrideNote.trim()}
                data-testid="btn-confirm-override"
                className="flex-1 px-4 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Confirm Override
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5">
        <div className="flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="text-sm font-semibold text-[#1F2937]">Pipeline Actions</p>
            <p className="text-xs text-[#6B7280] mt-0.5">
              {!healthScore ? 'Load Health Score first to enable Execute Transaction' : canDecide ? 'All actions available' : 'View only — your role does not have execution permissions'}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            {nextStage && (
              <button
                onClick={() => handleMoveStage(nextStage)}
                disabled={!!movingStage}
                data-testid={`btn-advance-${nextStage}`}
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors disabled:opacity-50"
              >
                {movingStage === nextStage ? <Loader2 size={14} className="animate-spin" /> : <ChevronRight size={14} />}
                Advance to {STAGE_LABELS[nextStage]}
              </button>
            )}
            {canDecide && (
              <button
                disabled={!healthScore || executing}
                onClick={handleExecute}
                data-testid="btn-execute"
                className="flex items-center gap-2 px-5 py-2 text-sm font-semibold bg-[#15803D] text-white rounded-sm hover:bg-[#166534] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {executing ? <Loader2 size={14} className="animate-spin" /> : <DollarSign size={14} />}
                Execute Transaction
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft, FileText, Download, Loader2, CheckCircle2,
  AlertTriangle, XCircle, RefreshCw, Shield, User, Building2,
  Phone, Mail, MapPin, DollarSign, Briefcase, Clock,
} from 'lucide-react';
import RiskBadge from '../components/RiskBadge';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

// ─── Color helpers ─────────────────────────────────────────────────────────
const INDICATOR_COLORS = {
  Clear: '#22C55E', Verified: '#22C55E', Complete: '#22C55E',
  No: '#22C55E', 'In Mandate': '#22C55E', 'Low Risk': '#22C55E',
  Pending: '#F59E0B', Partial: '#F59E0B', 'Requires Clarification': '#F59E0B',
  Possible: '#F59E0B', Exception: '#F59E0B', 'Medium Risk': '#F59E0B',
  Flagged: '#EF4444', Unverified: '#EF4444', Missing: '#EF4444',
  Unexplained: '#EF4444', Confirmed: '#EF4444', Blocked: '#EF4444', 'High Risk': '#EF4444',
};
const getColor = (v) => INDICATOR_COLORS[v] || '#6B7280';

const REC_COLORS = { Approve: '#22C55E', Review: '#F59E0B', Reject: '#EF4444' };

const STATUS_STYLE = {
  pending: 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/20',
  approved: 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20',
  flagged: 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20',
  rejected: 'bg-gray-100 text-gray-500 border border-gray-200',
};

const DOC_LABELS = {
  passport: 'Passport / National ID',
  proof_of_address: 'Proof of Address',
  source_of_wealth_doc: 'Source of Wealth',
  corporate_documents: 'Corporate Documents',
};

const CLASS_LABELS = {
  individual_accredited: 'Individual Accredited',
  institutional: 'Institutional',
  retail: 'Retail',
};

function formatCurrency(v) {
  if (!v && v !== 0) return '—';
  return `$${Number(v).toLocaleString()}`;
}
function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function formatSize(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-start justify-between py-2.5 border-b border-[#F3F4F6] last:border-0">
      <span className="text-xs text-[#6B7280] uppercase tracking-wider font-semibold w-36 flex-shrink-0">{label}</span>
      <span className="text-sm text-[#1F2937] text-right font-mono">{value || '—'}</span>
    </div>
  );
}

function ScoreBar({ label, value, max, color }) {
  const pct = Math.round((value / max) * 100);
  return (
    <div className="mb-3">
      <div className="flex justify-between text-xs text-[#9CA3AF] mb-1">
        <span>{label}</span>
        <span className="font-mono">{value}/{max}</span>
      </div>
      <div className="h-1.5 bg-[#333333] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
    </div>
  );
}

function IndicatorRow({ label, value }) {
  const color = getColor(value);
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

export default function InvestorDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const canDecide = user?.role === 'compliance';
  const [investor, setInvestor] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [scorecard, setScorecard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [deciding, setDeciding] = useState('');
  const [error, setError] = useState('');
  const [decisionSuccess, setDecisionSuccess] = useState('');

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [invRes, docsRes, scRes] = await Promise.all([
        fetch(`${API}/api/investors/${id}`, { credentials: 'include' }),
        fetch(`${API}/api/investors/${id}/documents`, { credentials: 'include' }),
        fetch(`${API}/api/investors/${id}/scorecard`, { credentials: 'include' }),
      ]);
      if (!invRes.ok) throw new Error('Investor not found');
      setInvestor(await invRes.json());
      if (docsRes.ok) setDocuments(await docsRes.json());
      if (scRes.ok) {
        const sc = await scRes.json();
        setScorecard(sc);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchAll(); }, [fetchAll]);

  const handleGenerateScorecard = async () => {
    setGenerating(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/investors/${id}/scorecard`, {
        method: 'POST', credentials: 'include',
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to generate scorecard');
      }
      const sc = await res.json();
      setScorecard(sc);
      setInvestor(inv => inv ? { ...inv, scorecard_completed: true } : inv);
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  const handleDecision = async (decision) => {
    setDeciding(decision);
    setError('');
    setDecisionSuccess('');
    try {
      const res = await fetch(`${API}/api/investors/${id}/decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ decision }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Decision failed');
      }
      const data = await res.json();
      setDecisionSuccess(data.message);
      setInvestor(inv => inv ? { ...inv, kyc_status: data.status } : inv);
    } catch (e) {
      setError(e.message);
    } finally {
      setDeciding('');
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[50vh]">
        <div className="flex flex-col items-center gap-3">
          <Loader2 size={28} className="animate-spin text-[#1B3A6B]" />
          <p className="text-sm text-[#6B7280]">Loading investor profile...</p>
        </div>
      </div>
    );
  }

  if (error && !investor) {
    return (
      <div className="p-8">
        <button onClick={() => navigate('/investors')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] mb-6">
          <ArrowLeft size={15} /> Back to Investors
        </button>
        <div className="bg-white border border-[#EF4444]/20 rounded-sm p-6 text-center">
          <XCircle size={32} className="mx-auto mb-3 text-[#EF4444]" />
          <p className="text-[#1F2937] font-medium">{error}</p>
        </div>
      </div>
    );
  }

  if (!investor) return null;

  const sc = scorecard?.scorecard_data;
  const isCorporate = investor.entity_type === 'corporate' || investor.type === 'Corporate Entity';

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <button onClick={() => navigate('/investors')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] transition-colors mb-3" data-testid="back-btn">
            <ArrowLeft size={15} /> Back to Investors
          </button>
          <p className="text-overline mb-1">Investor Profile</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading flex items-center gap-3">
            {isCorporate ? <Building2 size={28} strokeWidth={1.5} color="#1B3A6B" /> : <User size={28} strokeWidth={1.5} color="#1B3A6B" />}
            {investor.legal_name || investor.name}
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <span className={`px-2.5 py-0.5 rounded-sm text-xs font-mono uppercase tracking-wide ${STATUS_STYLE[investor.kyc_status] || 'bg-gray-100 text-gray-500 border border-gray-200'}`} data-testid="kyc-status-badge">
              {investor.kyc_status}
            </span>
            <RiskBadge rating={investor.risk_rating} />
            <span className="text-xs text-[#6B7280] font-mono">{investor.type}</span>
          </div>
        </div>
        <button onClick={fetchAll} className="text-sm text-[#6B7280] hover:text-[#1B3A6B] flex items-center gap-1.5 transition-colors mt-1" data-testid="refresh-btn">
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Error / Success banners */}
      {error && (
        <div className="mb-4 p-3 bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-sm text-sm text-[#EF4444]" data-testid="error-banner">
          {error}
        </div>
      )}
      {decisionSuccess && (
        <div className="mb-4 p-3 bg-[#10B981]/10 border border-[#10B981]/20 rounded-sm text-sm text-[#10B981] flex items-center gap-2" data-testid="decision-success">
          <CheckCircle2 size={16} /> {decisionSuccess}
        </div>
      )}

      {/* 3-column grid: Entity Info | Contact | Financial */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Entity Info */}
        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
          <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
            {isCorporate ? <Building2 size={15} color="#1B3A6B" /> : <User size={15} color="#1B3A6B" />}
            <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Entity Information</span>
          </div>
          <div className="px-4 py-2">
            <InfoRow label="Full Name" value={investor.legal_name || investor.name} />
            <InfoRow label="Entity Type" value={isCorporate ? 'Corporate' : 'Individual'} />
            <InfoRow label={isCorporate ? 'Incorporation' : 'Date of Birth'} value={investor.dob ? formatDate(investor.dob) : '—'} />
            <InfoRow label="Nationality" value={investor.nationality} />
            <InfoRow label="Residence" value={investor.residence_country || investor.country} />
            <InfoRow label="Submitted" value={formatDate(investor.submitted_date || investor.submitted_at)} />
          </div>
        </div>

        {/* Contact */}
        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
          <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
            <Mail size={15} color="#1B3A6B" />
            <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Contact Information</span>
          </div>
          <div className="px-4 py-2">
            <InfoRow label="Email" value={investor.email} />
            <InfoRow label="Phone" value={investor.phone} />
            {investor.address && (
              <>
                <InfoRow label="Street" value={investor.address.street} />
                <InfoRow label="City" value={investor.address.city} />
                <InfoRow label="Postal" value={investor.address.postal_code} />
                <InfoRow label="Country" value={investor.address.country} />
              </>
            )}
            {!investor.address && <InfoRow label="Country" value={investor.country} />}
          </div>
        </div>

        {/* Financial */}
        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
          <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
            <DollarSign size={15} color="#1B3A6B" />
            <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Financial Profile</span>
          </div>
          <div className="px-4 py-2">
            <InfoRow label="Classification" value={CLASS_LABELS[investor.classification] || investor.classification} />
            <InfoRow label="Net Worth" value={investor.net_worth ? formatCurrency(investor.net_worth) : '—'} />
            <InfoRow label="Annual Income" value={investor.annual_income ? formatCurrency(investor.annual_income) : '—'} />
            <InfoRow label="Investment" value={investor.investment_amount ? formatCurrency(investor.investment_amount) : '—'} />
            <InfoRow label="Src of Wealth" value={investor.source_of_wealth} />
            <InfoRow label="Experience" value={investor.investment_experience} />
          </div>
        </div>
      </div>

      {/* UBO Declarations (corporate only) */}
      {isCorporate && investor.ubo_declarations && investor.ubo_declarations.length > 0 && (
        <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm mb-6">
          <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
            <Shield size={15} color="#1B3A6B" />
            <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">UBO Declarations</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs uppercase bg-[#F8F9FA] text-[#6B7280] font-semibold border-b border-[#E5E7EB] tracking-wider">
                  <th className="px-4 py-2.5 text-left">Beneficial Owner</th>
                  <th className="px-4 py-2.5 text-left">Nationality</th>
                  <th className="px-4 py-2.5 text-right">Ownership %</th>
                </tr>
              </thead>
              <tbody>
                {investor.ubo_declarations.map((ubo, i) => (
                  <tr key={i} className="border-b border-[#E5E7EB] last:border-0">
                    <td className="px-4 py-2.5 font-medium text-[#1F2937]">{ubo.name}</td>
                    <td className="px-4 py-2.5 text-[#6B7280] text-xs">{ubo.nationality}</td>
                    <td className="px-4 py-2.5 text-right font-mono text-sm font-semibold text-[#1B3A6B]">{ubo.ownership_percentage}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Documents Section */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm mb-6">
        <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center gap-2">
          <FileText size={15} color="#1B3A6B" />
          <span className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Documents</span>
          <span className="ml-auto text-xs font-mono text-[#6B7280] bg-[#F8F9FA] px-2 py-0.5 rounded-sm border border-[#E5E7EB]">{documents.length} file{documents.length !== 1 ? 's' : ''}</span>
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
                    <p className="text-xs text-[#9CA3AF]">
                      {DOC_LABELS[doc.document_type] || doc.document_type} · {formatSize(doc.file_size)} · {formatDate(doc.uploaded_at)}
                    </p>
                  </div>
                </div>
                <a
                  href={`${API}/api/investors/${id}/documents/${doc.id}/download`}
                  target="_blank"
                  rel="noopener noreferrer"
                  data-testid={`download-${doc.id}`}
                  className="flex items-center gap-1.5 text-xs text-[#1B3A6B] hover:text-[#122A50] border border-[#1B3A6B]/20 px-3 py-1.5 rounded-sm hover:bg-[#1B3A6B]/5 transition-colors"
                >
                  <Download size={13} /> Download
                </a>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* AI Scorecard Panel */}
      <div className="bg-[#252523] rounded-sm shadow-lg mb-6 overflow-hidden" data-testid="scorecard-panel">
        <div className="px-5 py-4 border-b border-[#333333] flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <Shield size={16} color="#00A8C6" />
            <span className="text-sm font-semibold text-white">AI Compliance Scorecard</span>
          </div>
          {!sc && !generating && (
            <button
              onClick={handleGenerateScorecard}
              data-testid="generate-scorecard-btn"
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-[#00A8C6] text-white rounded-sm hover:bg-[#0096B3] transition-colors"
            >
              Generate AI Review
            </button>
          )}
          {generating && (
            <div className="flex items-center gap-2 text-xs text-[#9CA3AF]">
              <Loader2 size={14} className="animate-spin text-[#00A8C6]" />
              <span>Analysing profile with Claude...</span>
            </div>
          )}
          {sc && (
            <button
              onClick={handleGenerateScorecard}
              disabled={generating}
              data-testid="regenerate-scorecard-btn"
              className="flex items-center gap-1.5 text-xs text-[#9CA3AF] hover:text-white transition-colors disabled:opacity-50"
            >
              <RefreshCw size={12} /> Regenerate
            </button>
          )}
        </div>

        {!sc && !generating && (
          <div className="px-5 py-10 text-center">
            <Shield size={32} className="mx-auto mb-3 text-[#444444]" />
            <p className="text-sm text-[#6B7280]">No scorecard generated yet</p>
            <p className="text-xs text-[#555555] mt-1">Click "Generate AI Review" to run a Claude-powered KYC analysis</p>
          </div>
        )}

        {generating && (
          <div className="px-5 py-10 text-center">
            <Loader2 size={32} className="mx-auto mb-3 text-[#00A8C6] animate-spin" />
            <p className="text-sm text-[#9CA3AF]">Claude is reviewing the investor profile...</p>
            <p className="text-xs text-[#555555] mt-1">This may take 10–20 seconds</p>
          </div>
        )}

        {sc && (
          <div className="p-5">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left: Indicators */}
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-3">Compliance Indicators</p>
                <IndicatorRow label="Sanctions Status" value={sc.sanctions_status} />
                <IndicatorRow label="Identity / UBO" value={sc.identity_status} />
                <IndicatorRow label="Document Status" value={sc.document_status} />
                <IndicatorRow label="Source of Funds" value={sc.source_of_funds} />
                <IndicatorRow label="PEP Status" value={sc.pep_status} />
                <IndicatorRow label="Fund Mandate" value={sc.mandate_status} />
                <div className="flex items-center justify-between pt-3 mt-2 border-t border-[#333333]">
                  <span className="text-xs text-[#9CA3AF] uppercase tracking-wider">EDD Required</span>
                  <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded-sm ${sc.edd_required ? 'bg-[#EF4444]/20 text-[#EF4444]' : 'bg-[#22C55E]/10 text-[#22C55E]'}`}>
                    {sc.edd_required ? 'YES' : 'NO'}
                  </span>
                </div>
              </div>

              {/* Right: Score + Summary */}
              <div>
                <p className="text-xs font-semibold text-[#9CA3AF] uppercase tracking-wider mb-3">Identity Confidence Score</p>
                <div className="mb-4">
                  <div className="flex items-end gap-2 mb-1">
                    <span
                      className="text-5xl font-bold font-mono leading-none"
                      style={{ color: sc.identity_confidence_score >= 70 ? '#22C55E' : sc.identity_confidence_score >= 40 ? '#F59E0B' : '#EF4444' }}
                      data-testid="confidence-score"
                    >
                      {sc.identity_confidence_score}
                    </span>
                    <span className="text-lg text-[#6B7280] font-mono mb-1">/100</span>
                  </div>
                  {sc.score_breakdown && (
                    <div className="mt-3">
                      <ScoreBar label="Documents" value={sc.score_breakdown.documents} max={30} color={getColor(sc.document_status)} />
                      <ScoreBar label="Source of Wealth" value={sc.score_breakdown.source_of_wealth} max={25} color={getColor(sc.source_of_funds)} />
                      <ScoreBar label="Sanctions" value={sc.score_breakdown.sanctions} max={25} color={getColor(sc.sanctions_status)} />
                      <ScoreBar label="Nationality Risk" value={sc.score_breakdown.nationality_risk} max={20} color="#6B7280" />
                    </div>
                  )}
                </div>

                {/* Recommendation */}
                <div className="border border-[#333333] rounded-sm p-3 mb-3">
                  <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-1">Recommendation</p>
                  <p className="text-xl font-bold font-mono" style={{ color: REC_COLORS[sc.recommendation] || '#FFC72C' }} data-testid="scorecard-recommendation">
                    {sc.recommendation}
                  </p>
                  <p className="text-xs text-[#9CA3AF] mt-1">{sc.overall_rating} · Risk: {sc.risk_rating}</p>
                </div>

                {/* Summary */}
                <div className="border border-[#333333] rounded-sm p-3">
                  <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-2">Analysis Summary</p>
                  <p className="text-xs text-[#C0C0C0] leading-relaxed" data-testid="scorecard-summary">{sc.summary}</p>
                </div>
              </div>
            </div>

            <p className="text-center text-xs text-[#444444] mt-5 pt-4 border-t border-[#333333]">
              AI recommendation · human approval required · generated {formatDate(scorecard?.generated_at)}
            </p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold text-[#1F2937]">Compliance Decision</p>
            <p className="text-xs text-[#6B7280] mt-0.5">
              {!canDecide
                ? 'View only — compliance decisions are restricted to Compliance Officers'
                : investor.scorecard_completed
                ? 'Scorecard complete — action buttons are enabled'
                : 'Generate AI scorecard first to enable action buttons'}
            </p>
          </div>
          {canDecide && (
            <div className="flex items-center gap-3">
              <button
                disabled={!investor.scorecard_completed || !!deciding}
                onClick={() => handleDecision('more_info')}
                data-testid="btn-more-info"
                className="px-4 py-2 text-sm font-semibold text-white bg-[#252523] border border-[#444444] rounded-sm hover:bg-[#333333] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {deciding === 'more_info' ? <Loader2 size={14} className="animate-spin inline" /> : 'Request More Info'}
              </button>
              <button
                disabled={!investor.scorecard_completed || !!deciding}
                onClick={() => handleDecision('reject')}
                data-testid="btn-reject"
                className="px-4 py-2 text-sm font-semibold text-[#EF4444] bg-transparent border border-[#EF4444] rounded-sm hover:bg-[#EF4444]/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {deciding === 'reject' ? <Loader2 size={14} className="animate-spin inline" /> : 'Reject'}
              </button>
              <button
                disabled={!investor.scorecard_completed || !!deciding}
                onClick={() => handleDecision('approve')}
                data-testid="btn-approve"
                className="px-5 py-2 text-sm font-semibold text-white bg-[#15803D] rounded-sm hover:bg-[#166534] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {deciding === 'approve' ? <Loader2 size={14} className="animate-spin inline" /> : 'Approve'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

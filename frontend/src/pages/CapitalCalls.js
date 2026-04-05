import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, RefreshCw, ChevronRight, Landmark, ChevronLeft } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

function formatUSD(v) {
  if (!v && v !== 0) return '—';
  if (v >= 1000000) return `$${(v / 1000000).toFixed(2)}M`;
  if (v >= 1000) return `$${(v / 1000).toFixed(0)}K`;
  return `$${Number(v).toLocaleString()}`;
}
function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const STATUS_BADGE = {
  draft: { color: '#6B7280', label: 'Draft' },
  issued: { color: '#00A8C6', label: 'Issued' },
  closed: { color: '#10B981', label: 'Closed' },
};

const CLASS_LABELS = { A: 'Class A', B: 'Class B', C: 'Class C' };

const EMPTY_FORM = {
  call_name: '', call_type: 'fund_level', target_classes: ['A', 'B'],
  call_percentage: 20, due_date: '', deal_id: null,
};

export default function CapitalCalls() {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState(EMPTY_FORM);
  const [preview, setPreview] = useState(null);
  const [draftId, setDraftId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [deals, setDeals] = useState([]);
  const navigate = useNavigate();
  const { user } = useAuth();
  const isCompliance = user?.role === 'compliance';

  const fetchCalls = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/capital-calls`, { credentials: 'include' });
      if (res.ok) setCalls(await res.json());
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  const fetchDeals = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/deals`, { credentials: 'include' });
      if (res.ok) setDeals(await res.json());
    } catch (e) { console.error(e); }
  }, []);

  useEffect(() => { fetchCalls(); fetchDeals(); }, [fetchCalls, fetchDeals]);

  const resetModal = () => {
    setShowModal(false); setStep(1); setForm(EMPTY_FORM); setPreview(null); setDraftId(null);
  };

  const toggleClass = (cls) => {
    setForm(f => ({
      ...f,
      target_classes: f.target_classes.includes(cls)
        ? f.target_classes.filter(c => c !== cls)
        : [...f.target_classes, cls],
    }));
  };

  const handlePreview = async () => {
    if (!form.call_name.trim()) { toast.error('Call name is required'); return; }
    if (form.call_type === 'fund_level' && form.target_classes.length === 0) { toast.error('Select at least one share class'); return; }
    if (form.call_type === 'deal_specific' && !form.deal_id) { toast.error('Select a deal'); return; }
    if (!form.due_date) { toast.error('Due date is required'); return; }
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/capital-calls`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          call_name: form.call_name,
          call_type: form.call_type,
          target_classes: form.call_type === 'deal_specific' ? ['C'] : form.target_classes,
          call_percentage: Number(form.call_percentage),
          due_date: form.due_date,
          deal_id: form.call_type === 'deal_specific' ? form.deal_id : null,
        }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed to create draft');
      const data = await res.json();
      setPreview(data);
      setDraftId(data.id);
      setStep(2);
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleIssue = async () => {
    if (!draftId) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/capital-calls/${draftId}/issue`, {
        method: 'POST', credentials: 'include',
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed to issue call');
      toast.success('Capital call issued successfully!');
      resetModal();
      fetchCalls();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const defaultDate = () => {
    const d = new Date(); d.setDate(d.getDate() + 30);
    return d.toISOString().split('T')[0];
  };

  return (
    <div className="p-6 md:p-8 animate-fade-in" data-testid="capital-calls-page">
      <div className="flex items-start justify-between mb-8">
        <div>
          <p className="text-overline mb-1">Fund Operations</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading">Capital Calls</h1>
          <p className="text-sm text-gray-500 mt-1">Manage capital drawdowns and investor funding notices</p>
        </div>
        <div className="flex items-center gap-3 mt-1">
          <button onClick={fetchCalls} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#1B3A6B] transition-colors">
            <RefreshCw size={15} strokeWidth={1.5} /> Refresh
          </button>
          {isCompliance && (
            <button
              onClick={() => { setShowModal(true); setStep(1); setForm({ ...EMPTY_FORM, due_date: defaultDate() }); }}
              data-testid="new-capital-call-btn"
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors"
            >
              <Plus size={14} /> New Capital Call
            </button>
          )}
        </div>
      </div>

      {/* Calls Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm" data-testid="capital-calls-table">
        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Loading capital calls…</div>
        ) : calls.length === 0 ? (
          <div className="p-12 text-center">
            <Landmark size={32} className="mx-auto mb-3 text-gray-300" />
            <p className="text-sm text-gray-400">No capital calls found</p>
            {isCompliance && <p className="text-xs text-gray-400 mt-1">Click "New Capital Call" to issue your first drawdown</p>}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#FAFAF8]">
                  {['Call Name', 'Call Date', 'Due Date', 'Classes', 'Total Amount', 'Status', '% Received', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {calls.map((call, idx) => {
                  const s = STATUS_BADGE[call.status] || STATUS_BADGE.draft;
                  return (
                    <tr
                      key={call.id}
                      onClick={() => navigate(`/capital-calls/${call.id}`)}
                      className="border-b border-[#F3F4F6] hover:bg-[#FAFAF8] cursor-pointer transition-colors"
                      data-testid={`call-row-${idx}`}
                    >
                      <td className="px-4 py-3 font-medium text-[#1F2937]">{call.call_name}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(call.call_date)}</td>
                      <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(call.due_date)}</td>
                      <td className="px-4 py-3">
                        <div className="flex gap-1 flex-wrap">
                          {(call.target_classes || []).map(c => (
                            <span key={c} className="text-xs font-mono px-1.5 py-0.5 rounded-sm bg-[#1B3A6B]/10 text-[#1B3A6B]">{c}</span>
                          ))}
                        </div>
                      </td>
                      <td className="px-4 py-3 font-mono text-[#1F2937]">{formatUSD(call.total_amount)}</td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-mono px-1.5 py-0.5 rounded-sm" style={{ color: s.color, backgroundColor: `${s.color}15` }}>{s.label}</span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="flex-1 h-1.5 bg-[#E5E7EB] rounded-full overflow-hidden w-16">
                            <div className="h-full rounded-full bg-[#10B981]" style={{ width: `${call.pct_received || 0}%` }} />
                          </div>
                          <span className="text-xs font-mono text-gray-500">{call.pct_received ?? 0}%</span>
                        </div>
                      </td>
                      <td className="px-4 py-3"><ChevronRight size={14} className="text-gray-300" /></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* New Capital Call Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-sm shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="new-call-modal">
            {/* Modal Header */}
            <div className="border-b border-[#E5E7EB] px-6 py-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-0.5">
                  Step {step} of 3 — {step === 1 ? 'Call Setup' : step === 2 ? 'Preview' : 'Confirm'}
                </p>
                <p className="text-sm font-bold text-[#1F2937]">
                  {step === 1 ? 'Configure Capital Call' : step === 2 ? 'Review Call Details' : 'Issue Capital Call'}
                </p>
              </div>
              <button onClick={resetModal} className="text-gray-400 hover:text-gray-600 text-xl font-light">&times;</button>
            </div>

            {/* Step 1: Setup */}
            {step === 1 && (
              <div className="p-6 space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Call Name *</label>
                  <input
                    type="text"
                    value={form.call_name}
                    onChange={e => setForm(f => ({ ...f, call_name: e.target.value }))}
                    placeholder="e.g. Q2 2026 — Harbour House Acquisition"
                    className="w-full px-3 py-2 text-sm border border-[#E5E7EB] rounded-sm bg-white text-[#1F2937] outline-none focus:ring-1 focus:ring-[#00A8C6]"
                    data-testid="call-name-input"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-2">Call Type *</label>
                  <div className="grid grid-cols-2 gap-3">
                    {[['fund_level', 'Fund Level', 'Class A + B investors, pro-rata'], ['deal_specific', 'Deal Specific', 'Class C investors linked to a deal']].map(([val, label, desc]) => (
                      <button
                        key={val}
                        onClick={() => setForm(f => ({ ...f, call_type: val, target_classes: val === 'fund_level' ? ['A', 'B'] : ['C'], deal_id: null }))}
                        data-testid={`call-type-${val}`}
                        className={`p-3 text-left border rounded-sm transition-colors ${form.call_type === val ? 'border-[#1B3A6B] bg-[#1B3A6B]/5' : 'border-[#E5E7EB] hover:border-[#1B3A6B]/30'}`}
                      >
                        <p className={`text-sm font-semibold ${form.call_type === val ? 'text-[#1B3A6B]' : 'text-[#1F2937]'}`}>{label}</p>
                        <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
                      </button>
                    ))}
                  </div>
                </div>
                {form.call_type === 'fund_level' && (
                  <div>
                    <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-2">Target Classes *</label>
                    <div className="flex gap-3">
                      {['A', 'B'].map(cls => (
                        <button
                          key={cls}
                          onClick={() => toggleClass(cls)}
                          className={`px-4 py-2 text-sm font-mono border rounded-sm transition-colors ${form.target_classes.includes(cls) ? 'border-[#1B3A6B] bg-[#1B3A6B] text-white' : 'border-[#E5E7EB] text-[#6B7280] hover:border-[#1B3A6B]/50'}`}
                        >
                          Class {cls}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {form.call_type === 'deal_specific' && (
                  <div>
                    <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Select Deal *</label>
                    <select
                      value={form.deal_id || ''}
                      onChange={e => setForm(f => ({ ...f, deal_id: e.target.value || null }))}
                      className="w-full px-3 py-2 text-sm border border-[#E5E7EB] rounded-sm bg-white text-[#1F2937] outline-none focus:ring-1 focus:ring-[#00A8C6]"
                      data-testid="deal-select"
                    >
                      <option value="">Select a deal…</option>
                      {deals.map(d => (
                        <option key={d.id} value={d.id}>{d.company_name || d.name}</option>
                      ))}
                    </select>
                  </div>
                )}
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Call Percentage (%) *</label>
                    <input
                      type="number"
                      min="0.1" max="100" step="0.1"
                      value={form.call_percentage}
                      onChange={e => setForm(f => ({ ...f, call_percentage: e.target.value }))}
                      className="w-full px-3 py-2 text-sm border border-[#E5E7EB] rounded-sm bg-white text-[#1F2937] outline-none focus:ring-1 focus:ring-[#00A8C6]"
                      data-testid="call-percentage-input"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Due Date *</label>
                    <input
                      type="date"
                      value={form.due_date}
                      onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))}
                      className="w-full px-3 py-2 text-sm border border-[#E5E7EB] rounded-sm bg-white text-[#1F2937] outline-none focus:ring-1 focus:ring-[#00A8C6]"
                      data-testid="due-date-input"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Preview */}
            {step === 2 && preview && (
              <div className="p-6">
                <div className="bg-[#FAFAF8] border border-[#E5E7EB] rounded-sm p-4 mb-4">
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div>
                      <p className="text-xs text-[#6B7280] uppercase tracking-wider">Call %</p>
                      <p className="text-xl font-bold font-mono text-[#1B3A6B] mt-1">{preview.call_percentage}%</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#6B7280] uppercase tracking-wider">Total Amount</p>
                      <p className="text-xl font-bold font-mono text-[#1B3A6B] mt-1">{formatUSD(preview.total_amount)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#6B7280] uppercase tracking-wider">Investors</p>
                      <p className="text-xl font-bold font-mono text-[#1B3A6B] mt-1">{(preview.line_items || []).length}</p>
                    </div>
                  </div>
                </div>
                <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-3">Investor Line Items</p>
                {(preview.line_items || []).length === 0 ? (
                  <div className="bg-[#F59E0B]/10 border border-[#F59E0B]/20 rounded-sm p-4 text-center">
                    <p className="text-sm text-[#F59E0B]">No eligible investors found for this call configuration.</p>
                    <p className="text-xs text-[#6B7280] mt-1">Ensure investors have the correct share class, are KYC approved, and have committed capital &gt; 0.</p>
                  </div>
                ) : (
                  <table className="w-full text-sm border border-[#E5E7EB] rounded-sm overflow-hidden">
                    <thead>
                      <tr className="bg-[#1B3A6B] text-white">
                        {['Investor Name', 'Class', 'Committed', 'Call Amount'].map(h => (
                          <th key={h} className="px-3 py-2 text-left text-xs font-semibold">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {(preview.line_items || []).map((li, i) => (
                        <tr key={i} className={`border-b border-[#E5E7EB] ${i % 2 === 0 ? 'bg-white' : 'bg-[#F8F9FA]'}`}>
                          <td className="px-3 py-2 font-medium text-[#1F2937] text-xs">{li.investor_name}</td>
                          <td className="px-3 py-2 font-mono text-xs text-[#1B3A6B]">Class {li.share_class}</td>
                          <td className="px-3 py-2 font-mono text-xs text-[#1F2937]">{formatUSD(li.committed_capital)}</td>
                          <td className="px-3 py-2 font-mono text-xs font-semibold text-[#1B3A6B]">{formatUSD(li.call_amount)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}

            {/* Step 3: Confirm */}
            {step === 3 && preview && (
              <div className="p-6">
                <div className="bg-[#1B3A6B]/5 border border-[#1B3A6B]/20 rounded-sm p-5 mb-4">
                  <p className="text-sm font-bold text-[#1B3A6B] mb-3">Ready to Issue</p>
                  <p className="text-sm text-[#374151]">You are about to issue <strong>"{preview.call_name}"</strong> to <strong>{(preview.line_items || []).length} investor{(preview.line_items || []).length !== 1 ? 's' : ''}</strong> for a total of <strong>{formatUSD(preview.total_amount)}</strong>.</p>
                  <p className="text-xs text-[#6B7280] mt-3">This will update <strong>Capital Called</strong> on each investor record and set the call status to <strong>Issued</strong>. This action cannot be undone.</p>
                </div>
              </div>
            )}

            {/* Footer */}
            <div className="border-t border-[#E5E7EB] px-6 py-4 flex items-center justify-between">
              <div>
                {step > 1 && (
                  <button onClick={() => setStep(s => s - 1)} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1F2937] transition-colors">
                    <ChevronLeft size={14} /> Back
                  </button>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button onClick={resetModal} className="px-4 py-2 text-sm text-[#6B7280] hover:text-[#1F2937] transition-colors">Cancel</button>
                {step === 1 && (
                  <button onClick={handlePreview} disabled={saving} data-testid="preview-call-btn" className="px-5 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors disabled:opacity-50">
                    {saving ? 'Calculating…' : 'Preview Call'}
                  </button>
                )}
                {step === 2 && (
                  <button onClick={() => setStep(3)} data-testid="confirm-step-btn" className="px-5 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors">
                    Review & Issue
                  </button>
                )}
                {step === 3 && (
                  <button onClick={handleIssue} disabled={saving || (preview?.line_items || []).length === 0} data-testid="issue-call-btn" className="px-5 py-2 text-sm font-semibold bg-[#15803D] text-white rounded-sm hover:bg-[#166534] transition-colors disabled:opacity-50">
                    {saving ? 'Issuing…' : 'Issue Capital Call'}
                  </button>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

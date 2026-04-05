import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Plus, RefreshCw, CheckCircle2, XCircle, ChevronRight, Handshake, Receipt } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

function formatUSD(v) {
  if (!v && v !== 0) return '—';
  if (v >= 1000000) return `$${(v / 1000000).toFixed(2)}M`;
  if (v >= 1000) return `$${(v / 1000).toFixed(0)}K`;
  return `$${Number(v).toLocaleString()}`;
}

const EMPTY_FORM = {
  agent_name: '', company_name: '', email: '', phone: '',
  bank_name: '', bank_account_number: '', swift_code: '',
  vat_registered: false, vat_number: '',
};

export default function Agents() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [showTFModal, setShowTFModal] = useState(false);
  const [tfYear, setTfYear] = useState(new Date().getFullYear() - 1);
  const [tfSelectedIds, setTfSelectedIds] = useState([]);
  const [tfGenerating, setTfGenerating] = useState(false);
  const [tfResult, setTfResult] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState({});
  const navigate = useNavigate();
  const { user } = useAuth();
  const isCompliance = user?.role === 'compliance';

  const fetchAgents = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/agents`, { credentials: 'include' });
      if (res.ok) setAgents(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchAgents(); }, [fetchAgents]);

  const validate = () => {
    const e = {};
    if (!form.agent_name.trim()) e.agent_name = 'Required';
    if (!form.company_name.trim()) e.company_name = 'Required';
    if (!form.email.trim()) e.email = 'Required';
    if (!form.bank_name.trim()) e.bank_name = 'Required';
    if (!form.bank_account_number.trim()) e.bank_account_number = 'Required';
    if (!form.swift_code.trim()) e.swift_code = 'Required';
    setErrors(e);
    return Object.keys(e).length === 0;
  };

  const handleSave = async () => {
    if (!validate()) return;
    setSaving(true);
    try {
      const res = await fetch(`${API}/api/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ ...form, vat_number: form.vat_number || null }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Failed to create agent');
      toast.success('Placement agent added successfully');
      setShowModal(false);
      setForm(EMPTY_FORM);
      setErrors({});
      fetchAgents();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleGenerateTF = async () => {
    setTfGenerating(true);
    setTfResult(null);
    try {
      const body = { year: tfYear, agent_ids: tfSelectedIds.length > 0 ? tfSelectedIds : null };
      const res = await fetch(`${API}/api/trailer-fees/generate`, {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Generation failed');
      const data = await res.json();
      setTfResult(data);
      if (data.count > 0) {
        toast.success(`Generated ${data.count} trailer fee invoice${data.count !== 1 ? 's' : ''}`);
      } else {
        toast.warning('No invoices generated — no eligible Class C investors found for selected agents');
      }
      fetchAgents();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setTfGenerating(false);
    }
  };

  const Field = ({ label, name, type = 'text', placeholder }) => (
    <div>
      <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">{label}</label>
      <input
        type={type}
        value={form[name]}
        onChange={e => { setForm(f => ({ ...f, [name]: e.target.value })); setErrors(er => ({ ...er, [name]: '' })); }}
        placeholder={placeholder}
        className={`w-full px-3 py-2 text-sm border rounded-sm bg-white text-[#1F2937] outline-none focus:ring-1 focus:ring-[#00A8C6] ${errors[name] ? 'border-[#EF4444]' : 'border-[#E5E7EB]'}`}
      />
      {errors[name] && <p className="text-xs text-[#EF4444] mt-0.5">{errors[name]}</p>}
    </div>
  );

  return (
    <div className="p-6 md:p-8 animate-fade-in" data-testid="agents-page">
      <div className="flex items-start justify-between mb-8">
        <div>
          <p className="text-overline mb-1">Fee Management</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading">Placement Agents</h1>
          <p className="text-sm text-gray-500 mt-1">Manage Class C placement agents and trailer fee relationships</p>
        </div>
        <div className="flex items-center gap-3 mt-1">
          <button onClick={fetchAgents} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#1B3A6B] transition-colors">
            <RefreshCw size={15} strokeWidth={1.5} /> Refresh
          </button>
          {isCompliance && (
            <>
              <button
                onClick={() => { setShowTFModal(true); setTfResult(null); setTfSelectedIds([]); }}
                data-testid="generate-tf-btn"
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-[#1B3A6B] border border-[#1B3A6B]/30 rounded-sm hover:bg-[#1B3A6B]/5 transition-colors"
              >
                <Receipt size={14} /> Generate Trailer Fees
              </button>
              <button
                onClick={() => setShowModal(true)}
                data-testid="add-agent-btn"
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors"
              >
                <Plus size={14} /> Add Agent
              </button>
            </>
          )}
        </div>
      </div>

      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm" data-testid="agents-table">
        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Loading agents…</div>
        ) : agents.length === 0 ? (
          <div className="p-12 text-center">
            <Handshake size={32} className="mx-auto mb-3 text-gray-300" />
            <p className="text-sm text-gray-400">No placement agents found</p>
            {isCompliance && <p className="text-xs text-gray-400 mt-1">Click "Add Agent" to register your first placement agent</p>}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#FAFAF8]">
                  {['Agent Name', 'Company', 'Email', 'VAT Status', 'Linked Investors', 'Total Fees', ''].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wider whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {agents.map((ag, idx) => (
                  <tr
                    key={ag.id}
                    onClick={() => navigate(`/agents/${ag.id}`)}
                    className="border-b border-[#F3F4F6] hover:bg-[#FAFAF8] cursor-pointer transition-colors"
                    data-testid={`agent-row-${idx}`}
                  >
                    <td className="px-4 py-3 font-medium text-[#1F2937]">{ag.agent_name}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{ag.company_name}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{ag.email}</td>
                    <td className="px-4 py-3">
                      {ag.vat_registered
                        ? <span className="flex items-center gap-1 text-xs text-[#10B981]"><CheckCircle2 size={12} /> VAT Registered</span>
                        : <span className="flex items-center gap-1 text-xs text-[#6B7280]"><XCircle size={12} /> Not Registered</span>
                      }
                    </td>
                    <td className="px-4 py-3 font-mono text-[#1F2937] text-xs">{ag.linked_investors ?? 0}</td>
                    <td className="px-4 py-3 font-mono text-[#1F2937] text-xs">{formatUSD(ag.total_fees_invoiced)}</td>
                    <td className="px-4 py-3"><ChevronRight size={14} className="text-gray-300" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Generate Trailer Fee Modal */}
      {showTFModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={e => { if (e.target === e.currentTarget) { setShowTFModal(false); setTfResult(null); } }}>
          <div className="bg-white rounded-sm shadow-xl w-full max-w-lg" data-testid="generate-tf-modal">
            <div className="border-b border-[#E5E7EB] px-6 py-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-0.5">Trailer Fee Invoices</p>
                <p className="text-sm font-bold text-[#1F2937]">Generate Annual Fee Invoices</p>
              </div>
              <button onClick={() => { setShowTFModal(false); setTfResult(null); }} className="text-gray-400 hover:text-gray-600 text-xl font-light">&times;</button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Period Year</label>
                <input
                  type="number"
                  value={tfYear}
                  onChange={e => setTfYear(parseInt(e.target.value) || new Date().getFullYear() - 1)}
                  className="w-full px-3 py-2 text-sm border border-[#E5E7EB] rounded-sm bg-white text-[#1F2937] outline-none focus:ring-1 focus:ring-[#00A8C6]"
                  data-testid="tf-year-input"
                  min={2020} max={new Date().getFullYear()}
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-2">Select Agents</label>
                <p className="text-xs text-gray-400 mb-2">Leave all unselected to generate for all eligible agents</p>
                <div className="space-y-2 max-h-40 overflow-y-auto border border-[#E5E7EB] rounded-sm p-3">
                  {agents.map(ag => (
                    <label key={ag.id} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={tfSelectedIds.includes(ag.id)}
                        onChange={e => {
                          setTfSelectedIds(ids => e.target.checked ? [...ids, ag.id] : ids.filter(i => i !== ag.id));
                        }}
                        className="w-3.5 h-3.5 accent-[#1B3A6B]"
                      />
                      <span className="text-sm text-[#1F2937]">{ag.agent_name}</span>
                      {ag.vat_registered && <span className="text-xs text-[#10B981] ml-auto">+10% VAT</span>}
                    </label>
                  ))}
                </div>
              </div>
              {tfResult && (
                <div className="bg-[#FAFAF8] border border-[#E5E7EB] rounded-sm p-4">
                  <p className="text-sm font-semibold text-[#1B3A6B] mb-2">
                    {tfResult.count > 0 ? `${tfResult.count} draft invoice${tfResult.count !== 1 ? 's' : ''} created` : 'No invoices generated'}
                  </p>
                  {(tfResult.invoices || []).map((inv, i) => (
                    <div key={i} className="text-xs text-gray-600 flex items-center justify-between py-1 border-b border-[#E5E7EB] last:border-0">
                      <span>{inv.agent_name}</span>
                      <span className="font-mono">
                        ${Number(inv.total_due).toFixed(2)} {inv.vat_applicable ? '(incl. VAT)' : ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="border-t border-[#E5E7EB] px-6 py-4 flex items-center justify-end gap-3">
              <button onClick={() => { setShowTFModal(false); setTfResult(null); }} className="px-4 py-2 text-sm text-[#6B7280] hover:text-[#1F2937] transition-colors">
                {tfResult ? 'Close' : 'Cancel'}
              </button>
              {!tfResult && (
                <button
                  onClick={handleGenerateTF}
                  disabled={tfGenerating}
                  data-testid="confirm-generate-tf-btn"
                  className="px-5 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors disabled:opacity-50"
                >
                  {tfGenerating ? 'Generating…' : 'Generate Invoices'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Add Agent Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={e => { if (e.target === e.currentTarget) { setShowModal(false); setErrors({}); } }}>
          <div className="bg-white rounded-sm shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="add-agent-modal">
            <div className="border-b border-[#E5E7EB] px-6 py-4 flex items-center justify-between">
              <div>
                <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-0.5">New Placement Agent</p>
                <p className="text-sm font-bold text-[#1F2937]">Register Agent Details</p>
              </div>
              <button onClick={() => { setShowModal(false); setErrors({}); }} className="text-gray-400 hover:text-gray-600 transition-colors text-xl font-light">&times;</button>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <Field label="Agent Name *" name="agent_name" placeholder="e.g. Island Capital Advisors" />
                <Field label="Company Name *" name="company_name" placeholder="e.g. Island Capital Advisors Ltd" />
                <Field label="Email *" name="email" type="email" placeholder="fees@agent.com" />
                <Field label="Phone" name="phone" placeholder="+1 242-555-0001" />
              </div>
              <div className="border-t border-[#E5E7EB] pt-4">
                <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-3">Banking Details</p>
                <div className="grid grid-cols-2 gap-4">
                  <Field label="Bank Name *" name="bank_name" placeholder="RBC Royal Bank" />
                  <Field label="Account Number *" name="bank_account_number" placeholder="0123456789" />
                  <Field label="SWIFT / BIC *" name="swift_code" placeholder="ROYCBSNA" />
                </div>
              </div>
              <div className="border-t border-[#E5E7EB] pt-4">
                <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-3">VAT Details</p>
                <div className="flex items-center gap-3 mb-3">
                  <input
                    type="checkbox"
                    id="vat-reg"
                    checked={form.vat_registered}
                    onChange={e => setForm(f => ({ ...f, vat_registered: e.target.checked }))}
                    className="w-4 h-4 accent-[#1B3A6B]"
                    data-testid="vat-registered-checkbox"
                  />
                  <label htmlFor="vat-reg" className="text-sm text-[#1F2937]">VAT Registered (10% VAT applies to trailer fees)</label>
                </div>
                {form.vat_registered && (
                  <Field label="VAT Number" name="vat_number" placeholder="VAT-BS-20240001" />
                )}
              </div>
            </div>
            <div className="border-t border-[#E5E7EB] px-6 py-4 flex items-center justify-end gap-3">
              <button onClick={() => { setShowModal(false); setErrors({}); }} className="px-4 py-2 text-sm text-[#6B7280] hover:text-[#1F2937] transition-colors">Cancel</button>
              <button
                onClick={handleSave}
                disabled={saving}
                data-testid="save-agent-btn"
                className="px-5 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors disabled:opacity-50"
              >
                {saving ? 'Saving…' : 'Add Agent'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

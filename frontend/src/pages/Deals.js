import React, { useState, useEffect, useCallback } from 'react';
import { TrendingUp, Plus, X, Loader2, ChevronRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const API = process.env.REACT_APP_BACKEND_URL;

const COLUMNS = [
  { key: 'leads', label: 'Leads', color: '#6B7280' },
  { key: 'due_diligence', label: 'Due Diligence', color: '#F59E0B' },
  { key: 'ic_review', label: 'IC Review', color: '#1B3A6B' },
  { key: 'closing', label: 'Closing', color: '#10B981' },
];

const MANDATE_BADGE = {
  'In Mandate': 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20',
  'Exception': 'bg-[#EF4444]/10 text-[#EF4444] border-[#EF4444]/20',
  'Exception Cleared': 'bg-[#F59E0B]/10 text-[#F59E0B] border-[#F59E0B]/20',
};

const SECTORS = ['Technology', 'Financial Services', 'Fintech', 'Real Estate', 'Healthcare', 'Energy', 'Infrastructure'];
const GEOGRAPHIES = ['Caribbean', 'Africa', 'Latin America', 'North America', 'Europe', 'Asia'];
const ASSET_CLASSES = ['Private Equity', 'Venture', 'Real Estate', 'Infrastructure', 'Credit'];

function getMandateShortLabel(status) {
  if (status === 'Exception') return '⚠ Exception';
  if (status === 'Exception Cleared') return 'Cleared';
  return 'In Mandate';
}

export default function Deals() {
  const navigate = useNavigate();
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [mandateFilter, setMandateFilter] = useState('all');
  const [showModal, setShowModal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [form, setForm] = useState({
    company_name: '', sector: '', geography: '', asset_class: '',
    expected_irr: '', entry_valuation: '', entity_type: 'IBC',
  });

  const fetchDeals = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/deals`, { credentials: 'include' });
      const data = await res.json();
      setDeals(Array.isArray(data) ? data : data.deals || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchDeals(); }, [fetchDeals]);

  const filtered = deals.filter(d =>
    mandateFilter === 'all' || d.mandate_status === mandateFilter
  );

  const grouped = COLUMNS.reduce((acc, col) => {
    acc[col.key] = filtered.filter(d => d.pipeline_stage === col.key);
    return acc;
  }, {});

  const resetForm = () => setForm({
    company_name: '', sector: '', geography: '', asset_class: '',
    expected_irr: '', entry_valuation: '', entity_type: 'IBC',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError('');
    const { company_name, sector, geography, asset_class, expected_irr, entry_valuation, entity_type } = form;
    if (!company_name || !sector || !geography || !asset_class || !expected_irr || !entry_valuation) {
      setFormError('All fields are required.');
      return;
    }
    setSubmitting(true);
    try {
      const res = await fetch(`${API}/api/deals`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          company_name,
          sector,
          geography,
          asset_class,
          expected_irr: parseFloat(expected_irr),
          entry_valuation: parseFloat(entry_valuation),
          entity_type,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to create deal');
      }
      const newDeal = await res.json();
      setDeals(prev => [newDeal, ...prev]);
      setShowModal(false);
      resetForm();
    } catch (e) {
      setFormError(e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <p className="text-overline mb-1">Deal Pipeline</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading flex items-center gap-3">
            <TrendingUp size={28} strokeWidth={1.5} color="#1B3A6B" />
            Deal Pipeline
          </h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-sm font-mono text-[#6B7280]">
            <span className="text-2xl font-bold text-[#00A8C6]">{filtered.length}</span>
            <span>in pipeline</span>
          </div>
          <select
            value={mandateFilter}
            onChange={e => setMandateFilter(e.target.value)}
            data-testid="mandate-filter"
            className="text-sm border border-[#D1D5DB] rounded-sm px-3 py-2 bg-white focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] text-[#374151]"
          >
            <option value="all">All Mandates</option>
            <option value="In Mandate">In Mandate</option>
            <option value="Exception">Exception</option>
          </select>
          <button
            onClick={() => setShowModal(true)}
            data-testid="add-deal-btn"
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] transition-colors"
          >
            <Plus size={15} /> Add New Deal
          </button>
        </div>
      </div>

      {/* Kanban Board */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={28} className="animate-spin text-[#1B3A6B]" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
          {COLUMNS.map(col => (
            <div
              key={col.key}
              className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm flex flex-col"
              data-testid={`column-${col.key}`}
            >
              {/* Column Header */}
              <div className="px-4 py-3 border-b border-[#E5E7EB] flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full" style={{ backgroundColor: col.color }} />
                  <span className="text-xs font-semibold uppercase tracking-wider text-[#374151]">{col.label}</span>
                </div>
                <span className="text-xs font-mono bg-[#F8F9FA] border border-[#E5E7EB] px-2 py-0.5 rounded-sm text-[#6B7280]">
                  {grouped[col.key].length}
                </span>
              </div>

              {/* Cards */}
              <div className="p-3 flex flex-col gap-3 flex-1 min-h-[180px]">
                {grouped[col.key].length === 0 ? (
                  <div className="flex-1 flex items-center justify-center py-8">
                    <p className="text-xs text-[#D1D5DB] font-mono">No deals</p>
                  </div>
                ) : (
                  grouped[col.key].map(deal => (
                    <div
                      key={deal.id}
                      onClick={() => navigate(`/deals/${deal.id}`)}
                      data-testid={`deal-card-${deal.id}`}
                      className="bg-[#FAFAF8] border border-[#E5E7EB] rounded-sm p-3 cursor-pointer hover:border-[#1B3A6B]/40 hover:shadow-sm transition-all group"
                    >
                      <div className="flex items-start justify-between gap-2 mb-2">
                        <p className="text-sm font-semibold text-[#1F2937] leading-tight group-hover:text-[#1B3A6B] transition-colors">
                          {deal.company_name}
                        </p>
                        <span className={`flex-shrink-0 text-[10px] font-mono px-1.5 py-0.5 rounded-sm border ${MANDATE_BADGE[deal.mandate_status] || 'bg-gray-100 text-gray-400 border-gray-200'}`}>
                          {getMandateShortLabel(deal.mandate_status)}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5 mb-2">
                        <span className="text-[10px] font-mono text-[#6B7280] bg-[#F3F4F6] px-1.5 py-0.5 rounded-sm">{deal.sector}</span>
                        <span className="text-[10px] text-[#9CA3AF]">{deal.geography}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="text-[11px] font-mono font-bold text-[#10B981]">{deal.expected_irr}% IRR</span>
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded-sm ${deal.entity_type === 'ICON' ? 'bg-[#7C3AED]/5 text-[#7C3AED]' : 'bg-[#00A8C6]/5 text-[#00A8C6]'}`}>
                            {deal.entity_type}
                          </span>
                        </div>
                        <ChevronRight size={12} className="text-[#D1D5DB] group-hover:text-[#1B3A6B] transition-colors" />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Add Deal Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-sm shadow-xl w-full max-w-lg">
            <div className="px-6 py-4 border-b border-[#E5E7EB] flex items-center justify-between">
              <h2 className="text-base font-bold text-[#1F2937] font-heading">Add New Deal</h2>
              <button
                onClick={() => { setShowModal(false); setFormError(''); resetForm(); }}
                className="text-[#9CA3AF] hover:text-[#374151] transition-colors"
                data-testid="close-modal-btn"
              >
                <X size={18} />
              </button>
            </div>
            <form onSubmit={handleSubmit} className="p-6">
              {formError && (
                <div className="mb-4 p-3 bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-sm text-sm text-[#EF4444]" data-testid="form-error">
                  {formError}
                </div>
              )}
              <div className="grid grid-cols-2 gap-4">
                <div className="col-span-2">
                  <label className="block text-xs font-semibold text-[#374151] mb-1 uppercase tracking-wider">Company Name</label>
                  <input
                    type="text"
                    value={form.company_name}
                    onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
                    data-testid="deal-company-name"
                    placeholder="e.g. NexaTech Caribbean Ltd"
                    className="w-full border border-[#D1D5DB] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1 uppercase tracking-wider">Sector</label>
                  <select
                    value={form.sector}
                    onChange={e => setForm(f => ({ ...f, sector: e.target.value }))}
                    data-testid="deal-sector"
                    className="w-full border border-[#D1D5DB] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] bg-white"
                  >
                    <option value="">Select sector</option>
                    {SECTORS.map(s => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1 uppercase tracking-wider">Geography</label>
                  <select
                    value={form.geography}
                    onChange={e => setForm(f => ({ ...f, geography: e.target.value }))}
                    data-testid="deal-geography"
                    className="w-full border border-[#D1D5DB] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] bg-white"
                  >
                    <option value="">Select geography</option>
                    {GEOGRAPHIES.map(g => <option key={g} value={g}>{g}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1 uppercase tracking-wider">Asset Class</label>
                  <select
                    value={form.asset_class}
                    onChange={e => setForm(f => ({ ...f, asset_class: e.target.value }))}
                    data-testid="deal-asset-class"
                    className="w-full border border-[#D1D5DB] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] bg-white"
                  >
                    <option value="">Select class</option>
                    {ASSET_CLASSES.map(a => <option key={a} value={a}>{a}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1 uppercase tracking-wider">Entity Type</label>
                  <select
                    value={form.entity_type}
                    onChange={e => setForm(f => ({ ...f, entity_type: e.target.value }))}
                    data-testid="deal-entity-type"
                    className="w-full border border-[#D1D5DB] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] bg-white"
                  >
                    <option value="IBC">IBC</option>
                    <option value="ICON">ICON</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1 uppercase tracking-wider">Expected IRR (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    min="0"
                    value={form.expected_irr}
                    onChange={e => setForm(f => ({ ...f, expected_irr: e.target.value }))}
                    data-testid="deal-irr"
                    placeholder="e.g. 18.5"
                    className="w-full border border-[#D1D5DB] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1 uppercase tracking-wider">Entry Valuation (USD)</label>
                  <input
                    type="number"
                    min="0"
                    value={form.entry_valuation}
                    onChange={e => setForm(f => ({ ...f, entry_valuation: e.target.value }))}
                    data-testid="deal-valuation"
                    placeholder="e.g. 5000000"
                    className="w-full border border-[#D1D5DB] rounded-sm px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B]"
                  />
                </div>
              </div>
              <div className="flex gap-3 mt-6">
                <button
                  type="button"
                  onClick={() => { setShowModal(false); setFormError(''); resetForm(); }}
                  className="flex-1 px-4 py-2 text-sm border border-[#D1D5DB] rounded-sm text-[#374151] hover:bg-[#F8F9FA]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  data-testid="submit-deal-btn"
                  className="flex-1 px-4 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#122A50] disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {submitting && <Loader2 size={14} className="animate-spin" />}
                  {submitting ? 'Creating...' : 'Add Deal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

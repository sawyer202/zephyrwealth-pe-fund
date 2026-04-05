import React, { useState, useEffect } from 'react';
import { TrendingUp, Search } from 'lucide-react';
import RiskBadge from '../components/RiskBadge';

const API = process.env.REACT_APP_BACKEND_URL;

const STAGE_CONFIG = {
  due_diligence: { label: 'Due Diligence', style: 'bg-[#1B3A6B]/10 text-[#1B3A6B] border border-[#1B3A6B]/20' },
  term_sheet: { label: 'Term Sheet', style: 'bg-[#C9A84C]/10 text-[#C9A84C] border border-[#C9A84C]/20' },
  closed: { label: 'Closed', style: 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20' },
  prospecting: { label: 'Prospecting', style: 'bg-gray-100 text-gray-500 border border-gray-200' },
};

function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function formatCurrency(v) {
  if (!v) return '—';
  return `$${(v / 1000000).toFixed(1)}M`;
}

export default function Deals() {
  const [deals, setDeals] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');

  useEffect(() => {
    fetch(`${API}/api/deals`, { credentials: 'include' })
      .then((r) => r.json())
      .then(setDeals)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = deals.filter(
    (d) =>
      !search ||
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.type?.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      <div className="flex items-start justify-between mb-6">
        <div>
          <p className="text-overline mb-1">Deal Pipeline</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading flex items-center gap-3">
            <TrendingUp size={28} strokeWidth={1.5} color="#1B3A6B" />
            Deals
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm font-mono text-[#6B7280]">
          <span className="text-2xl font-bold text-[#00A8C6]">{deals.length}</span>
          <span>in pipeline</span>
        </div>
      </div>

      {/* Search */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search deals..."
            data-testid="deal-search"
            className="w-full pl-9 pr-3 py-2 text-sm border border-[#D1D5DB] rounded-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] bg-white"
          />
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left" data-testid="deals-table">
            <thead>
              <tr className="text-xs uppercase bg-[#F8F9FA] text-[#6B7280] font-semibold border-b border-[#E5E7EB] tracking-wider">
                <th className="px-4 py-3">Deal Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Deal Size</th>
                <th className="px-4 py-3">Target Return</th>
                <th className="px-4 py-3">Submitted</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">Stage</th>
                <th className="px-4 py-3">Scorecard</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-gray-400">
                    Loading...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-gray-400">
                    No deals found
                  </td>
                </tr>
              ) : (
                filtered.map((deal) => (
                  <tr
                    key={deal.id}
                    className="border-b border-[#E5E7EB] hover:bg-[#F3F4F6] transition-colors"
                    data-testid={`deal-row-${deal.id}`}
                  >
                    <td className="px-4 py-3 font-medium text-[#1F2937]">{deal.name}</td>
                    <td className="px-4 py-3 text-[#6B7280] text-xs">{deal.type}</td>
                    <td className="px-4 py-3 font-mono text-xs text-[#6B7280]">
                      {formatCurrency(deal.deal_size)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#10B981]">
                      {deal.target_return || '—'}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#6B7280]">
                      {formatDate(deal.submitted_date)}
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge rating={deal.risk_rating} />
                    </td>
                    <td className="px-4 py-3">
                      <span className={`${STAGE_CONFIG[deal.stage]?.style || 'bg-gray-100 text-gray-500'} px-2.5 py-0.5 rounded-sm text-xs font-mono uppercase tracking-wide`}>
                        {STAGE_CONFIG[deal.stage]?.label || deal.stage}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-mono px-2 py-0.5 rounded-sm border ${deal.scorecard_completed ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20' : 'bg-gray-100 text-gray-400 border-gray-200'}`}>
                        {deal.scorecard_completed ? 'Complete' : 'Pending'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        disabled={!deal.scorecard_completed}
                        data-testid={`deal-action-${deal.id}`}
                        className={`text-xs px-3 py-1.5 rounded-sm font-semibold transition-colors ${
                          deal.scorecard_completed
                            ? 'bg-[#1B3A6B] text-white hover:bg-[#122A50]'
                            : 'bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed opacity-60 border border-[#D1D5DB]'
                        }`}
                        title={!deal.scorecard_completed ? 'Complete Review Scorecard first' : 'Review deal'}
                      >
                        Review
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

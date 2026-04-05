import React, { useState, useEffect } from 'react';
import { Users, Search, Filter } from 'lucide-react';
import RiskBadge from '../components/RiskBadge';

const API = process.env.REACT_APP_BACKEND_URL;

const STATUS_CONFIG = {
  pending: { label: 'Pending', style: 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/20' },
  approved: { label: 'Approved', style: 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20' },
  flagged: { label: 'Flagged', style: 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20' },
  rejected: { label: 'Rejected', style: 'bg-gray-100 text-gray-500 border border-gray-200' },
};

function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}
function formatCurrency(v) {
  if (!v) return '—';
  return `$${(v / 1000000).toFixed(1)}M`;
}

export default function Investors() {
  const [investors, setInvestors] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    fetch(`${API}/api/investors`, { credentials: 'include' })
      .then((r) => r.json())
      .then(setInvestors)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = investors.filter((inv) => {
    const matchSearch =
      !search ||
      inv.name.toLowerCase().includes(search.toLowerCase()) ||
      inv.country?.toLowerCase().includes(search.toLowerCase());
    const matchFilter =
      filter === 'all' ||
      inv.kyc_status === filter ||
      inv.risk_rating === filter;
    return matchSearch && matchFilter;
  });

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      <div className="flex items-start justify-between mb-6">
        <div>
          <p className="text-overline mb-1">Investor Management</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading flex items-center gap-3">
            <Users size={28} strokeWidth={1.5} color="#1B3A6B" />
            Investors
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm font-mono text-[#6B7280]">
          <span className="text-2xl font-bold text-[#1B3A6B]">{investors.length}</span>
          <span>total</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search investors..."
            data-testid="investor-search"
            className="w-full pl-9 pr-3 py-2 text-sm border border-[#D1D5DB] rounded-sm focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] bg-white"
          />
        </div>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          data-testid="investor-filter"
          className="text-sm border border-[#D1D5DB] rounded-sm px-3 py-2 bg-white focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] text-[#374151]"
        >
          <option value="all">All Status</option>
          <option value="pending">Pending</option>
          <option value="approved">Approved</option>
          <option value="flagged">Flagged</option>
          <option value="high">High Risk</option>
          <option value="medium">Medium Risk</option>
          <option value="low">Low Risk</option>
        </select>
      </div>

      {/* Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
        <div className="border-b border-[#E5E7EB] px-5 py-3 flex items-center gap-2">
          <Filter size={14} color="#6B7280" />
          <span className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider">
            {filtered.length} {filtered.length === 1 ? 'investor' : 'investors'} shown
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left" data-testid="investors-table">
            <thead>
              <tr className="text-xs uppercase bg-[#F8F9FA] text-[#6B7280] font-semibold border-b border-[#E5E7EB] tracking-wider">
                <th className="px-4 py-3">Investor Name</th>
                <th className="px-4 py-3">Type</th>
                <th className="px-4 py-3">Country</th>
                <th className="px-4 py-3">Investment</th>
                <th className="px-4 py-3">Submitted</th>
                <th className="px-4 py-3">Risk</th>
                <th className="px-4 py-3">KYC Status</th>
                <th className="px-4 py-3">Scorecard</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-gray-400 text-sm">
                    Loading...
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-gray-400 text-sm">
                    No investors match the current filter
                  </td>
                </tr>
              ) : (
                filtered.map((inv) => (
                  <tr
                    key={inv.id}
                    className="border-b border-[#E5E7EB] hover:bg-[#F3F4F6] transition-colors"
                    data-testid={`investor-row-${inv.id}`}
                  >
                    <td className="px-4 py-3 font-medium text-[#1F2937]">{inv.name}</td>
                    <td className="px-4 py-3 text-[#6B7280] text-xs">{inv.type}</td>
                    <td className="px-4 py-3 text-[#6B7280] text-xs">{inv.country || '—'}</td>
                    <td className="px-4 py-3 font-mono text-xs text-[#6B7280]">
                      {formatCurrency(inv.investment_amount)}
                    </td>
                    <td className="px-4 py-3 font-mono text-xs text-[#6B7280]">
                      {formatDate(inv.submitted_date)}
                    </td>
                    <td className="px-4 py-3">
                      <RiskBadge rating={inv.risk_rating} />
                    </td>
                    <td className="px-4 py-3">
                      <span className={`${STATUS_CONFIG[inv.kyc_status]?.style || 'bg-gray-100 text-gray-500'} px-2.5 py-0.5 rounded-sm text-xs font-mono uppercase tracking-wide`}>
                        {STATUS_CONFIG[inv.kyc_status]?.label || inv.kyc_status}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`text-xs font-mono px-2 py-0.5 rounded-sm border ${inv.scorecard_completed ? 'bg-[#10B981]/10 text-[#10B981] border-[#10B981]/20' : 'bg-gray-100 text-gray-400 border-gray-200'}`}>
                        {inv.scorecard_completed ? 'Complete' : 'Pending'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        disabled={!inv.scorecard_completed}
                        data-testid={`investor-action-${inv.id}`}
                        className={`text-xs px-3 py-1.5 rounded-sm font-semibold transition-colors ${
                          inv.scorecard_completed
                            ? 'bg-[#1B3A6B] text-white hover:bg-[#122A50]'
                            : 'bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed opacity-60 border border-[#D1D5DB]'
                        }`}
                        title={!inv.scorecard_completed ? 'Complete Review Scorecard first' : 'Review investor'}
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

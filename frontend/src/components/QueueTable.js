import React from 'react';
import RiskBadge from './RiskBadge';

const STATUS_CONFIG = {
  pending: { label: 'Pending', style: 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/20' },
  approved: { label: 'Approved', style: 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20' },
  flagged: { label: 'Flagged', style: 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20' },
  rejected: { label: 'Rejected', style: 'bg-gray-100 text-gray-500 border border-gray-200' },
  due_diligence: { label: 'Due Diligence', style: 'bg-[#1B3A6B]/10 text-[#1B3A6B] border border-[#1B3A6B]/20' },
  term_sheet: { label: 'Term Sheet', style: 'bg-[#C9A84C]/10 text-[#C9A84C] border border-[#C9A84C]/20' },
  closed: { label: 'Closed', style: 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20' },
};

function StatusBadge({ status }) {
  const config = STATUS_CONFIG[status] || { label: status, style: 'bg-gray-100 text-gray-500 border border-gray-200' };
  return (
    <span className={`${config.style} px-2.5 py-0.5 rounded-sm text-xs font-mono uppercase tracking-wide`}>
      {config.label}
    </span>
  );
}

function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatCurrency(amount) {
  if (!amount) return '—';
  if (amount >= 1000000) return `$${(amount / 1000000).toFixed(1)}M`;
  if (amount >= 1000) return `$${(amount / 1000).toFixed(0)}K`;
  return `$${amount}`;
}

export default function QueueTable({ data, type, loading }) {
  const isInvestor = type === 'investor';

  if (loading) {
    return (
      <div className="px-5 py-12 text-center">
        <div className="inline-flex gap-1">
          <div className="w-1.5 h-1.5 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-1.5 h-1.5 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-1.5 h-1.5 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    );
  }

  if (!data || data.length === 0) {
    return (
      <div className="px-5 py-12 text-center text-sm text-gray-400">
        No {type}s found
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table
        className="w-full text-sm text-left border-collapse"
        data-testid={`${type}-queue-table`}
      >
        <thead>
          <tr className="text-xs uppercase bg-[#F8F9FA] text-[#6B7280] font-semibold border-b border-[#E5E7EB] tracking-wider">
            <th className="px-4 py-3">Name</th>
            <th className="px-4 py-3">Type</th>
            {isInvestor && <th className="px-4 py-3">Amount</th>}
            {!isInvestor && <th className="px-4 py-3">Deal Size</th>}
            <th className="px-4 py-3">Submitted</th>
            <th className="px-4 py-3">Risk Rating</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.map((item) => {
            const scorecardDone = item.scorecard_completed;
            return (
              <tr
                key={item.id}
                className="border-b border-[#E5E7EB] hover:bg-[#F3F4F6] transition-colors duration-150"
                data-testid={`${type}-row-${item.id}`}
              >
                <td className="px-4 py-3 font-medium text-[#1F2937]">{item.name}</td>
                <td className="px-4 py-3 text-[#6B7280] text-xs">{item.type}</td>
                <td className="px-4 py-3 font-mono text-xs text-[#6B7280]">
                  {isInvestor
                    ? formatCurrency(item.investment_amount)
                    : formatCurrency(item.deal_size)}
                </td>
                <td className="px-4 py-3 font-mono text-xs text-[#6B7280]">
                  {formatDate(item.submitted_date)}
                </td>
                <td className="px-4 py-3">
                  <RiskBadge rating={item.risk_rating} />
                </td>
                <td className="px-4 py-3">
                  <StatusBadge
                    status={isInvestor ? item.kyc_status : item.stage}
                  />
                </td>
                <td className="px-4 py-3">
                  <button
                    disabled={!scorecardDone}
                    data-testid={`${type}-action-${item.id}`}
                    title={
                      !scorecardDone
                        ? 'Complete Review Scorecard first'
                        : 'Review record'
                    }
                    className={`text-xs px-3 py-1.5 rounded-sm font-semibold transition-colors duration-150 ${
                      scorecardDone
                        ? 'bg-[#1B3A6B] text-white hover:bg-[#122A50] cursor-pointer'
                        : 'bg-[#E5E7EB] text-[#9CA3AF] cursor-not-allowed opacity-60 border border-[#D1D5DB]'
                    }`}
                  >
                    Review
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

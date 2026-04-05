import React from 'react';

const badgeConfig = {
  low: {
    style: 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20',
    dot: '#10B981',
  },
  medium: {
    style: 'bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/20',
    dot: '#F59E0B',
  },
  high: {
    style: 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20',
    dot: '#EF4444',
  },
};

export default function RiskBadge({ rating }) {
  const config = badgeConfig[rating?.toLowerCase()] || badgeConfig.medium;
  return (
    <span
      className={`${config.style} px-2.5 py-0.5 rounded-sm text-xs font-mono uppercase tracking-wide inline-flex items-center gap-1.5`}
      data-testid={`risk-badge-${rating}`}
    >
      <span
        className="w-1.5 h-1.5 rounded-full"
        style={{ backgroundColor: config.dot }}
      />
      {rating}
    </span>
  );
}

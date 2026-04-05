import React from 'react';

export default function KPICard({ title, value, icon: Icon, color = 'primary', testId, subtitle }) {
  const colorMap = {
    primary: { text: '#1B3A6B', bg: 'rgba(27,58,107,0.08)' },
    warning: { text: '#F59E0B', bg: 'rgba(245,158,11,0.08)' },
    danger: { text: '#EF4444', bg: 'rgba(239,68,68,0.08)' },
    success: { text: '#10B981', bg: 'rgba(16,185,129,0.08)' },
    brand: { text: '#00A8C6', bg: 'rgba(0,168,198,0.08)' },
  };

  const colors = colorMap[color] || colorMap.primary;

  return (
    <div
      className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5 hover:shadow-md transition-shadow duration-200"
      data-testid={testId}
    >
      <div className="flex items-center justify-between mb-4">
        <p className="text-overline">{title}</p>
        {Icon && (
          <div
            className="w-8 h-8 rounded-sm flex items-center justify-center"
            style={{ backgroundColor: colors.bg }}
          >
            <Icon size={17} strokeWidth={1.5} color={colors.text} />
          </div>
        )}
      </div>
      <p
        className="text-3xl font-mono font-bold tracking-tight"
        style={{ color: colors.text }}
        data-testid={`${testId}-value`}
      >
        {value}
      </p>
      {subtitle && (
        <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
      )}
    </div>
  );
}

import React from 'react';
import { Briefcase, Construction } from 'lucide-react';

export default function Portfolio() {
  return (
    <div className="p-6 md:p-8 animate-fade-in">
      <div className="mb-8">
        <p className="text-overline mb-1">Portfolio Overview</p>
        <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading flex items-center gap-3">
          <Briefcase size={28} strokeWidth={1.5} color="#1B3A6B" />
          Portfolio
        </h1>
      </div>
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-12 text-center" data-testid="portfolio-page">
        <Construction size={40} strokeWidth={1} color="#D1D5DB" className="mx-auto mb-4" />
        <h2 className="text-xl font-bold font-heading text-[#1F2937] mb-2">Coming in Phase 2</h2>
        <p className="text-sm text-gray-400 max-w-sm mx-auto">
          Portfolio analytics, performance metrics, and asset allocation dashboards will be available in the next release.
        </p>
      </div>
    </div>
  );
}

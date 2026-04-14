import React, { useState, useEffect } from 'react';
import { Loader2, Building2, User, TrendingUp, FileText } from 'lucide-react';
import { portalFetch } from '../../utils/authFetch';

const API = process.env.REACT_APP_BACKEND_URL;

function fmt(v) {
  if (v == null) return '—';
  return `$${Number(v).toLocaleString('en-US', { minimumFractionDigits: 0 })}`;
}
function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function StatusBadge({ status }) {
  const map = {
    approved: { bg: '#F0FDF4', text: '#15803D' },
    pending:  { bg: '#FFFBEB', text: '#92400E' },
    flagged:  { bg: '#FEF2F2', text: '#991B1B' },
    rejected: { bg: '#F3F4F6', text: '#6B7280' },
  };
  const s = map[status] || map.pending;
  return (
    <span className="px-2 py-0.5 rounded-sm text-xs font-semibold capitalize" style={{ backgroundColor: s.bg, color: s.text }}>
      {status}
    </span>
  );
}

function CallStatusBadge({ status }) {
  const map = {
    received:  { bg: '#F0FDF4', text: '#15803D' },
    pending:   { bg: '#FFFBEB', text: '#92400E' },
    defaulted: { bg: '#FEF2F2', text: '#991B1B' },
  };
  const s = map[status] || map.pending;
  return (
    <span className="px-2 py-0.5 rounded-sm text-xs font-semibold capitalize" style={{ backgroundColor: s.bg, color: s.text }}>
      {status}
    </span>
  );
}

function ClassBadge({ cls }) {
  const map = { A: '#00A8C6', B: '#1B3A6B', C: '#92400E' };
  const color = map[cls] || '#888880';
  return (
    <span className="px-2 py-0.5 rounded-sm text-xs font-bold font-mono border" style={{ color, borderColor: `${color}30`, backgroundColor: `${color}10` }}>
      Class {cls}
    </span>
  );
}

const SC_DESCRIPTIONS = {
  A: "As a Founding Anchor investor, you benefit from a 1.5% management fee, 15% carried interest above an 8% preferred return, priority distributions, and voting rights on major fund decisions.",
  B: "As a Professional investor, you benefit from a 2.0% management fee and 20% carried interest above an 8% preferred return, with standard LP participation in fund distributions.",
  C: "As a Co-Investment partner, your investment is deal-specific with a 1.0% management fee on deployed capital and 20% carried interest above a deal-level 8% hurdle.",
};

export default function PortalInvestment() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    portalFetch(`${API}/api/portal/investment`)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load investment data');
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={24} className="animate-spin text-[#00A8C6]" />
        <p className="text-sm text-[#888880]">Loading investment details...</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="p-8 text-center">
      <p className="text-sm text-red-500">{error}</p>
    </div>
  );

  const profile = data?.profile || {};
  const fp = data?.fund_participation || {};
  const distributions = data?.distribution_history || [];
  const capitalCalls = data?.capital_call_history || [];
  const callRate = fp.call_rate || 0;

  return (
    <div className="px-6 md:px-10 py-8 max-w-5xl mx-auto" data-testid="portal-investment">
      {/* Header */}
      <div className="mb-8">
        <p className="text-xs text-[#888880] font-mono uppercase tracking-wider mb-1">Investment Portal</p>
        <h1 className="text-2xl font-semibold text-[#0F0F0E] tracking-tight flex items-center gap-2">
          <TrendingUp size={22} color="#00A8C6" />
          My Investment
        </h1>
      </div>

      {/* Section 1: Investor Profile */}
      <div className="bg-white border border-[#E8E6E0] rounded-sm mb-5" data-testid="investor-profile-section">
        <div className="border-b border-[#E8E6E0] px-5 py-3.5 flex items-center gap-2">
          {profile.entity_type === 'corporate' ? <Building2 size={15} color="#00A8C6" /> : <User size={15} color="#00A8C6" />}
          <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">Investor Profile</span>
        </div>
        <div className="p-5 grid grid-cols-2 md:grid-cols-3 gap-x-6 gap-y-4">
          <div>
            <p className="text-xs text-[#888880] uppercase tracking-wider font-semibold mb-0.5">Legal Name</p>
            <p className="text-sm font-semibold text-[#0F0F0E]">{profile.legal_name || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-[#888880] uppercase tracking-wider font-semibold mb-0.5">Entity Type</p>
            <p className="text-sm font-semibold text-[#0F0F0E] capitalize">{profile.entity_type || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-[#888880] uppercase tracking-wider font-semibold mb-0.5">Share Class</p>
            <ClassBadge cls={profile.share_class} />
          </div>
          <div>
            <p className="text-xs text-[#888880] uppercase tracking-wider font-semibold mb-0.5">Nationality</p>
            <p className="text-sm text-[#0F0F0E]">{profile.nationality || '—'}</p>
          </div>
          <div>
            <p className="text-xs text-[#888880] uppercase tracking-wider font-semibold mb-0.5">KYC Status</p>
            <StatusBadge status={profile.kyc_status} />
          </div>
          <div>
            <p className="text-xs text-[#888880] uppercase tracking-wider font-semibold mb-0.5">Risk Rating</p>
            <span className="text-sm capitalize text-[#0F0F0E]">{profile.risk_rating || '—'}</span>
          </div>
        </div>
      </div>

      {/* Section 2: Fund Participation */}
      <div className="bg-white border border-[#E8E6E0] rounded-sm mb-5" data-testid="fund-participation-section">
        <div className="border-b border-[#E8E6E0] px-5 py-3.5 flex items-center gap-2">
          <TrendingUp size={15} color="#00A8C6" />
          <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">Fund Participation</span>
        </div>
        <div className="p-5">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
            {[
              { label: 'Committed Capital', value: fp.committed_capital },
              { label: 'Capital Called', value: fp.capital_called },
              { label: 'Capital Uncalled', value: fp.capital_uncalled },
              { label: 'Call Rate', value: `${callRate}%` },
            ].map(({ label, value }) => (
              <div key={label}>
                <p className="text-xs text-[#888880] uppercase tracking-wider font-semibold mb-0.5">{label}</p>
                <p className="text-lg font-bold font-mono text-[#0F0F0E]">
                  {typeof value === 'string' ? value : fmt(value)}
                </p>
              </div>
            ))}
          </div>

          {/* Call rate progress bar */}
          <div className="mb-5">
            <div className="flex justify-between text-xs text-[#888880] mb-1">
              <span>Capital Call Rate</span>
              <span className="font-mono">{callRate}%</span>
            </div>
            <div className="h-2 bg-[#F3F4F6] rounded-full overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, callRate)}%`, backgroundColor: '#00A8C6' }}
              />
            </div>
          </div>

          {/* Share class description */}
          <div className="p-4 bg-[#FAFAF8] border border-[#E8E6E0] rounded-sm">
            <div className="flex items-center gap-2 mb-2">
              <ClassBadge cls={profile.share_class} />
              <span className="text-xs font-semibold text-[#888880]">Share Class Terms</span>
            </div>
            <p className="text-sm text-[#888880] leading-relaxed">
              {SC_DESCRIPTIONS[profile.share_class] || SC_DESCRIPTIONS.A}
            </p>
          </div>
        </div>
      </div>

      {/* Section 3: Distribution History */}
      <div className="bg-white border border-[#E8E6E0] rounded-sm mb-5" data-testid="distribution-history">
        <div className="border-b border-[#E8E6E0] px-5 py-3.5 flex items-center gap-2">
          <FileText size={15} color="#00A8C6" />
          <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">Distribution History</span>
        </div>
        {distributions.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-sm text-[#888880]">No distributions recorded yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E8E6E0] bg-[#FAFAF8]">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Date</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Type</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Deal</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Gross</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Net</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F3F4F6]">
                {distributions.map((d, i) => (
                  <tr key={i} className="hover:bg-[#FAFAF8] transition-colors">
                    <td className="px-5 py-3 text-xs font-mono text-[#888880]">{fmtDate(d.date)}</td>
                    <td className="px-5 py-3 text-sm text-[#0F0F0E]">{d.type || '—'}</td>
                    <td className="px-5 py-3 text-sm text-[#888880]">{d.deal || '—'}</td>
                    <td className="px-5 py-3 text-right font-mono text-sm">{fmt(d.gross_amount)}</td>
                    <td className="px-5 py-3 text-right font-mono text-sm font-semibold">{fmt(d.net_amount)}</td>
                    <td className="px-5 py-3 text-right">
                      <StatusBadge status={d.status} />
                    </td>
                  </tr>
                ))}
                <tr className="bg-[#FAFAF8] border-t border-[#E8E6E0]">
                  <td colSpan={4} className="px-5 py-3 text-xs font-semibold text-[#888880] uppercase">Total Received</td>
                  <td className="px-5 py-3 text-right font-mono text-sm font-bold text-[#0F0F0E]">
                    {fmt(distributions.filter(d => d.status === 'paid').reduce((s, d) => s + (d.net_amount || 0), 0))}
                  </td>
                  <td />
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 4: Capital Call History */}
      <div className="bg-white border border-[#E8E6E0] rounded-sm" data-testid="capital-call-history">
        <div className="border-b border-[#E8E6E0] px-5 py-3.5 flex items-center gap-2">
          <FileText size={15} color="#00A8C6" />
          <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">Capital Call History</span>
        </div>
        {capitalCalls.length === 0 ? (
          <div className="py-10 text-center">
            <p className="text-sm text-[#888880]">No capital calls recorded yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E8E6E0] bg-[#FAFAF8]">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Call Name</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Issue Date</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Due Date</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Amount</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F3F4F6]">
                {capitalCalls.map((cc, i) => (
                  <tr key={i} className="hover:bg-[#FAFAF8] transition-colors" data-testid={`call-row-${i}`}>
                    <td className="px-5 py-3 text-sm font-medium text-[#0F0F0E]">{cc.call_name}</td>
                    <td className="px-5 py-3 text-xs font-mono text-[#888880]">{fmtDate(cc.issue_date)}</td>
                    <td className="px-5 py-3 text-xs font-mono text-[#888880]">{fmtDate(cc.due_date)}</td>
                    <td className="px-5 py-3 text-right font-mono text-sm font-semibold text-[#0F0F0E]">{fmt(cc.call_amount)}</td>
                    <td className="px-5 py-3 text-right">
                      <CallStatusBadge status={cc.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

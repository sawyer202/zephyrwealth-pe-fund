import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { DollarSign, TrendingUp, TrendingDown, Layers, Bell, ArrowRight, Loader2, FileText, Activity } from 'lucide-react';
import { useInvestorAuth } from '../../context/InvestorAuthContext';
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
function fmtTs(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function KPICard({ label, value, icon: Icon, accent }) {
  return (
    <div className="bg-white border border-[#E8E6E0] rounded-sm p-5 flex flex-col gap-3" data-testid={`kpi-${label.toLowerCase().replace(/ /g, '-')}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">{label}</span>
        <div className="w-8 h-8 rounded-sm flex items-center justify-center" style={{ backgroundColor: `${accent || '#00A8C6'}15` }}>
          <Icon size={16} color={accent || '#00A8C6'} />
        </div>
      </div>
      <p className="text-2xl font-bold font-mono text-[#0F0F0E] leading-none" style={{ color: accent || '#0F0F0E' }}>
        {fmt(value)}
      </p>
    </div>
  );
}

function daysColor(days) {
  if (days == null) return '#888880';
  if (days > 30) return '#15803D';
  if (days >= 10) return '#92400E';
  return '#991B1B';
}
function daysBg(days) {
  if (days == null) return '#F3F4F6';
  if (days > 30) return '#F0FDF4';
  if (days >= 10) return '#FFFBEB';
  return '#FEF2F2';
}

function ActivityIcon({ type }) {
  if (type === 'capital_call') return <Bell size={14} color="#00A8C6" />;
  if (type === 'distribution') return <TrendingDown size={14} color="#15803D" />;
  return <FileText size={14} color="#888880" />;
}

export default function PortalDashboard() {
  const { investor } = useInvestorAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    portalFetch(`${API}/api/portal/dashboard`)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load dashboard data');
        return r.json();
      })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const today = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric', year: 'numeric' });

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={24} className="animate-spin text-[#00A8C6]" />
        <p className="text-sm text-[#888880]">Loading your dashboard...</p>
      </div>
    </div>
  );

  if (error) return (
    <div className="p-8 text-center">
      <p className="text-sm text-red-500">{error}</p>
    </div>
  );

  const kpi = data?.kpi || {};
  const nextCall = data?.next_capital_call;
  const activity = data?.recent_activity || [];

  return (
    <div className="px-6 md:px-10 py-8 max-w-6xl mx-auto" data-testid="portal-dashboard">
      {/* Welcome header */}
      <div className="mb-8">
        <p className="text-xs text-[#888880] font-mono uppercase tracking-wider mb-1">{today}</p>
        <h1 className="text-2xl font-medium text-[#0F0F0E] tracking-tight">
          Welcome back, <span className="font-semibold">{investor?.name || 'Investor'}</span>
        </h1>
        <p className="text-sm text-[#888880] mt-1">Zephyr Caribbean Growth Fund I — Investor Overview</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6" data-testid="kpi-cards">
        <KPICard label="Committed Capital" value={kpi.committed_capital} icon={Layers} accent="#00A8C6" />
        <KPICard label="Capital Called" value={kpi.capital_called} icon={TrendingUp} accent="#0F0F0E" />
        <KPICard label="Capital Uncalled" value={kpi.capital_uncalled} icon={DollarSign} accent="#15803D" />
        <KPICard label="Total Distributions" value={kpi.total_distributions} icon={TrendingDown} accent="#92400E" />
      </div>

      {/* Bottom row: Next Capital Call + Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Next Capital Call */}
        <div className="bg-white border border-[#E8E6E0] rounded-sm p-5" data-testid="next-capital-call-card">
          <div className="flex items-center gap-2 mb-4">
            <Bell size={15} color="#00A8C6" />
            <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">Next Capital Call</span>
          </div>
          {nextCall ? (
            <div>
              <p className="text-base font-semibold text-[#0F0F0E] mb-3">{nextCall.call_name}</p>
              <div className="grid grid-cols-2 gap-3 mb-4">
                <div>
                  <p className="text-xs text-[#888880] mb-0.5">Amount Due</p>
                  <p className="text-xl font-bold font-mono" style={{ color: '#00A8C6' }}>{fmt(nextCall.amount_due)}</p>
                </div>
                <div>
                  <p className="text-xs text-[#888880] mb-0.5">Due Date</p>
                  <p className="text-sm font-semibold text-[#0F0F0E]">{fmtDate(nextCall.due_date)}</p>
                </div>
              </div>
              {nextCall.days_remaining != null && (
                <div
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-sm text-xs font-semibold mb-4"
                  style={{ backgroundColor: daysBg(nextCall.days_remaining), color: daysColor(nextCall.days_remaining) }}
                  data-testid="days-remaining"
                >
                  <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: daysColor(nextCall.days_remaining) }} />
                  {nextCall.days_remaining > 0
                    ? `${nextCall.days_remaining} days remaining`
                    : nextCall.days_remaining === 0
                    ? 'Due today'
                    : `${Math.abs(nextCall.days_remaining)} days overdue`}
                </div>
              )}
              <button
                onClick={() => navigate('/portal/capital-calls')}
                className="flex items-center gap-1.5 text-xs font-semibold transition-colors"
                style={{ color: '#00A8C6' }}
              >
                View Details <ArrowRight size={13} />
              </button>
            </div>
          ) : (
            <div className="py-8 text-center">
              <Bell size={24} className="mx-auto mb-2 text-[#D1D5DB]" />
              <p className="text-sm text-[#888880]">No pending capital calls</p>
            </div>
          )}
        </div>

        {/* Recent Activity */}
        <div className="bg-white border border-[#E8E6E0] rounded-sm p-5" data-testid="recent-activity">
          <div className="flex items-center gap-2 mb-4">
            <Activity size={15} color="#00A8C6" />
            <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">Recent Activity</span>
          </div>
          {activity.length === 0 ? (
            <div className="py-8 text-center">
              <Activity size={24} className="mx-auto mb-2 text-[#D1D5DB]" />
              <p className="text-sm text-[#888880]">No recent activity</p>
            </div>
          ) : (
            <div className="space-y-0 divide-y divide-[#F3F4F6]">
              {activity.map((item, i) => (
                <div key={i} className="flex items-center gap-3 py-3" data-testid={`activity-row-${i}`}>
                  <div className="w-7 h-7 rounded-sm bg-[#F3F4F6] flex items-center justify-center flex-shrink-0">
                    <ActivityIcon type={item.type} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#0F0F0E] truncate">{item.event}</p>
                    <p className="text-xs text-[#888880]">{item.sub}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-xs text-[#888880] font-mono">{fmtTs(item.date)}</p>
                    {item.amount != null && (
                      <p className="text-xs font-semibold font-mono text-[#0F0F0E]">{fmt(item.amount)}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import {
  Users, Clock, TrendingUp, AlertTriangle, RefreshCw,
  Landmark, DollarSign, ArrowDownToLine, Percent,
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import KPICard from '../components/KPICard';
import QueueTable from '../components/QueueTable';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

function formatUSD(v) {
  if (!v && v !== 0) return '—';
  if (v >= 1000000) return `$${(v / 1000000).toFixed(2)}M`;
  if (v >= 1000) return `$${(v / 1000).toFixed(0)}K`;
  return `$${Number(v).toLocaleString()}`;
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [investors, setInvestors] = useState([]);
  const [deals, setDeals] = useState([]);
  const [chartsData, setChartsData] = useState(null);
  const [activeTab, setActiveTab] = useState('investors');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { user } = useAuth();

  const fetchData = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const [statsRes, investorsRes, dealsRes, chartsRes] = await Promise.all([
        fetch(`${API}/api/dashboard/stats`, { credentials: 'include' }),
        fetch(`${API}/api/investors`, { credentials: 'include' }),
        fetch(`${API}/api/deals`, { credentials: 'include' }),
        fetch(`${API}/api/dashboard/charts`, { credentials: 'include' }),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (investorsRes.ok) {
        const d = await investorsRes.json();
        setInvestors(Array.isArray(d) ? d : d.investors || []);
      }
      if (dealsRes.ok) {
        const d = await dealsRes.json();
        setDeals(Array.isArray(d) ? d : d.deals || []);
      }
      if (chartsRes.ok) setChartsData(await chartsRes.json());
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const today = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <p className="text-overline mb-1">Executive Dashboard</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading">
            {getGreeting()}, {user?.name?.split(' ')[0]}
          </h1>
          <p className="text-sm text-gray-500 mt-1">{today}</p>
        </div>
        <button
          onClick={() => fetchData(true)}
          disabled={refreshing}
          data-testid="refresh-dashboard"
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-[#1B3A6B] transition-colors disabled:opacity-50 mt-1"
        >
          <RefreshCw
            size={15}
            strokeWidth={1.5}
            className={refreshing ? 'animate-spin' : ''}
          />
          Refresh
        </button>
      </div>

      {/* KPI Cards — Investor & Deal Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
        <KPICard
          title="Total Investors"
          value={loading ? '—' : stats?.total_investors ?? 0}
          icon={Users}
          color="primary"
          testId="kpi-total-investors"
        />
        <KPICard
          title="Pending KYC Reviews"
          value={loading ? '—' : stats?.pending_kyc ?? 0}
          icon={Clock}
          color="warning"
          testId="kpi-pending-kyc"
          subtitle="Awaiting review"
        />
        <KPICard
          title="Deals in Pipeline"
          value={loading ? '—' : stats?.deals_in_pipeline ?? 0}
          icon={TrendingUp}
          color="brand"
          testId="kpi-deals-pipeline"
        />
        <KPICard
          title="Flagged Items"
          value={loading ? '—' : stats?.flagged_items ?? 0}
          icon={AlertTriangle}
          color="danger"
          testId="kpi-flagged-items"
          subtitle="High risk"
        />
      </div>

      {/* KPI Cards — Capital */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard
          title="Total Committed Capital"
          value={loading ? '—' : formatUSD(stats?.total_committed_capital)}
          icon={Landmark}
          color="primary"
          testId="kpi-committed-capital"
          subtitle="Approved investors"
        />
        <KPICard
          title="Total Capital Called"
          value={loading ? '—' : formatUSD(stats?.total_capital_called)}
          icon={ArrowDownToLine}
          color="brand"
          testId="kpi-capital-called"
          subtitle="Issued drawdowns"
        />
        <KPICard
          title="Total Uncalled"
          value={loading ? '—' : formatUSD(stats?.total_uncalled)}
          icon={DollarSign}
          color="success"
          testId="kpi-total-uncalled"
          subtitle="Available capital"
        />
        <KPICard
          title="Call Rate"
          value={loading ? '—' : `${stats?.call_rate ?? 0}%`}
          icon={Percent}
          color={(stats?.call_rate || 0) > 80 ? 'danger' : 'warning'}
          testId="kpi-call-rate"
          subtitle="Called / committed"
        />
      </div>

      {/* Charts */}
      {chartsData && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-8" data-testid="charts-section">
          {/* Investor Status Distribution */}
          <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5">
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Investor Queue</p>
            <p className="text-sm font-bold text-[#1F2937] mb-4">Status Distribution</p>
            <ResponsiveContainer width="100%" height={180} style={{ maxHeight: '250px' }}>
              <BarChart data={chartsData.investor_funnel} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="status" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ border: '1px solid #E5E7EB', borderRadius: '2px', fontSize: '12px' }}
                  cursor={{ fill: '#F8F9FA' }}
                />
                <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                  {chartsData.investor_funnel.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Deal Pipeline Distribution */}
          <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5">
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Deal Pipeline</p>
            <p className="text-sm font-bold text-[#1F2937] mb-4">Deals by Stage</p>
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={chartsData.deal_pipeline} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                <XAxis dataKey="stage" tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ border: '1px solid #E5E7EB', borderRadius: '2px', fontSize: '12px' }}
                  cursor={{ fill: '#F8F9FA' }}
                />
                <Bar dataKey="count" radius={[2, 2, 0, 0]}>
                  {chartsData.deal_pipeline.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Queue Tables */}
      <div
        className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm"
        data-testid="queue-container"
      >
        {/* Tab Header */}
        <div className="border-b border-[#E5E7EB] px-5 py-4 flex items-center justify-between">
          <div className="flex gap-6">
            {[
              { key: 'investors', label: 'Investor Queue', count: investors.length },
              { key: 'deals', label: 'Deal Queue', count: deals.length },
            ].map(({ key, label, count }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                data-testid={`tab-${key}`}
                className={`text-sm font-semibold pb-1 border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === key
                    ? 'text-[#1B3A6B] border-[#1B3A6B]'
                    : 'text-gray-400 border-transparent hover:text-gray-600'
                }`}
              >
                {label}
                <span
                  className={`text-xs font-mono px-1.5 py-0.5 rounded-sm ${
                    activeTab === key
                      ? 'bg-[#1B3A6B]/10 text-[#1B3A6B]'
                      : 'bg-gray-100 text-gray-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Table Content */}
        {activeTab === 'investors' ? (
          <QueueTable data={investors} type="investor" loading={loading} />
        ) : (
          <QueueTable data={deals} type="deal" loading={loading} />
        )}
      </div>
    </div>
  );
}

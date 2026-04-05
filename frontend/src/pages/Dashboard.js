import React, { useState, useEffect } from 'react';
import {
  Users,
  Clock,
  TrendingUp,
  AlertTriangle,
  RefreshCw,
} from 'lucide-react';
import KPICard from '../components/KPICard';
import QueueTable from '../components/QueueTable';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

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
  const [activeTab, setActiveTab] = useState('investors');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const { user } = useAuth();

  const fetchData = async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const [statsRes, investorsRes, dealsRes] = await Promise.all([
        fetch(`${API}/api/dashboard/stats`, { credentials: 'include' }),
        fetch(`${API}/api/investors`, { credentials: 'include' }),
        fetch(`${API}/api/deals`, { credentials: 'include' }),
      ]);
      if (statsRes.ok) setStats(await statsRes.json());
      if (investorsRes.ok) setInvestors(await investorsRes.json());
      if (dealsRes.ok) setDeals(await dealsRes.json());
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

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
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

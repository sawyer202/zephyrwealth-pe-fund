import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Briefcase, TrendingUp, BarChart3, AlertTriangle,
  ChevronUp, ChevronDown, ChevronsUpDown, RefreshCw,
} from 'lucide-react';
import {
  PieChart, Pie, Cell, Tooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer,
} from 'recharts';
import KPICard from '../components/KPICard';

const API = process.env.REACT_APP_BACKEND_URL;

const STAGE_LABELS = {
  leads: 'Leads',
  due_diligence: 'Due Diligence',
  ic_review: 'IC Review',
  closing: 'Closing',
};

const STAGE_COLORS = {
  leads: '#6B7280',
  due_diligence: '#F59E0B',
  ic_review: '#1B3A6B',
  closing: '#10B981',
};

const CHART_COLORS = ['#00A8C6', '#1B3A6B', '#C9A84C', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6'];

function formatUSD(val) {
  if (!val && val !== 0) return '—';
  if (val >= 1000000) return `$${(val / 1000000).toFixed(2)}M`;
  if (val >= 1000) return `$${(val / 1000).toFixed(0)}K`;
  return `$${val.toLocaleString()}`;
}

function MandateBadge({ status }) {
  const config = {
    'In Mandate': { color: '#10B981' },
    'Exception': { color: '#F59E0B' },
    'Exception Cleared': { color: '#00A8C6' },
    'Blocked': { color: '#EF4444' },
  };
  const c = config[status] || { color: '#6B7280' };
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded-sm text-xs font-mono"
      style={{ color: c.color, backgroundColor: `${c.color}15`, border: `1px solid ${c.color}30` }}
    >
      {status || '—'}
    </span>
  );
}

function HealthBadge({ score }) {
  const config = {
    'Good': { color: '#10B981' },
    'Review': { color: '#F59E0B' },
    'Poor': { color: '#EF4444' },
  };
  const c = config[score] || { color: '#6B7280' };
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded-sm text-xs font-mono"
      style={{ color: c.color, backgroundColor: `${c.color}15`, border: `1px solid ${c.color}30` }}
    >
      {score || '—'}
    </span>
  );
}

function SortIcon({ field, sortField, sortDir }) {
  if (sortField !== field) return <ChevronsUpDown size={12} className="opacity-30 flex-shrink-0" />;
  return sortDir === 'asc'
    ? <ChevronUp size={12} className="flex-shrink-0" />
    : <ChevronDown size={12} className="flex-shrink-0" />;
}

function PieTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0];
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-2 text-xs">
      <p className="font-semibold text-[#1F2937]">{name}</p>
      <p className="text-[#6B7280]">{formatUSD(value)}</p>
    </div>
  );
}

function StageTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-2 text-xs">
      <p className="font-semibold text-[#1F2937] mb-1">{label}</p>
      <p style={{ color: payload[0]?.fill }}>{formatUSD(payload[0]?.value)}</p>
    </div>
  );
}

function IrrTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-2 text-xs">
      <p className="font-semibold text-[#1F2937] mb-0.5">{d?.name}</p>
      <p style={{ color: payload[0]?.fill }}>IRR: {d?.irr?.toFixed(1)}%</p>
      <p className="text-[#6B7280]">Valuation: {formatUSD(d?.valuation)}</p>
    </div>
  );
}

const TABLE_COLUMNS = [
  { key: 'company_name', label: 'Company' },
  { key: 'sector', label: 'Sector' },
  { key: 'geography', label: 'Geography' },
  { key: 'entity_type', label: 'Entity' },
  { key: 'pipeline_stage', label: 'Stage' },
  { key: 'entry_valuation', label: 'Entry Valuation' },
  { key: 'expected_irr', label: 'IRR %' },
  { key: 'mandate_status', label: 'Mandate' },
  { key: 'health_score', label: 'Health' },
];

export default function Portfolio() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [sortField, setSortField] = useState('entry_valuation');
  const [sortDir, setSortDir] = useState('desc');
  const navigate = useNavigate();

  const fetchData = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    else setRefreshing(true);
    try {
      const res = await fetch(`${API}/api/portfolio/summary`, { credentials: 'include' });
      if (res.ok) setData(await res.json());
    } catch (err) {
      console.error('Portfolio fetch error:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sortedHoldings = [...(data?.holdings || [])].sort((a, b) => {
    const av = a[sortField];
    const bv = b[sortField];
    if (typeof av === 'number') return sortDir === 'asc' ? av - bv : bv - av;
    return sortDir === 'asc'
      ? String(av || '').localeCompare(String(bv || ''))
      : String(bv || '').localeCompare(String(av || ''));
  });

  const kpis = data?.kpis || {};
  const charts = data?.charts || {};

  const irrData = (charts.irr_distribution || []).map(d => ({
    ...d,
    color: d.mandate_status === 'Exception' ? '#F59E0B' : '#00A8C6',
  }));

  const stageData = (charts.pipeline_stage_value || []).map(d => ({
    ...d,
    color: STAGE_COLORS[d.key] || '#6B7280',
  }));

  return (
    <div className="p-6 md:p-8 animate-fade-in" data-testid="portfolio-page">
      {/* Page Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <p className="text-overline mb-1">Fund Analytics</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading">
            Portfolio
          </h1>
          <p className="text-sm text-gray-500 mt-1">Live portfolio composition and performance</p>
        </div>
        <button
          onClick={() => fetchData(true)}
          disabled={refreshing}
          data-testid="refresh-portfolio"
          className="flex items-center gap-2 text-sm text-gray-500 hover:text-[#1B3A6B] transition-colors disabled:opacity-50 mt-1"
        >
          <RefreshCw size={15} strokeWidth={1.5} className={refreshing ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Section 1: KPI Strip */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KPICard
          title="Total Portfolio Value"
          value={loading ? '—' : formatUSD(kpis.total_portfolio_value)}
          icon={TrendingUp}
          color="brand"
          testId="kpi-portfolio-value"
        />
        <KPICard
          title="Active Investments"
          value={loading ? '—' : (kpis.active_investments ?? 0)}
          icon={Briefcase}
          color="primary"
          testId="kpi-active-investments"
          subtitle="IC Review & Closing"
        />
        <KPICard
          title="Weighted Avg. IRR"
          value={loading ? '—' : `${kpis.weighted_avg_irr ?? 0}%`}
          icon={BarChart3}
          color="success"
          testId="kpi-weighted-irr"
          subtitle="By entry valuation"
        />
        <KPICard
          title="Mandate Exception Rate"
          value={loading ? '—' : `${kpis.mandate_exception_rate ?? 0}%`}
          icon={AlertTriangle}
          color={(kpis.mandate_exception_rate || 0) > 30 ? 'danger' : 'warning'}
          testId="kpi-exception-rate"
          subtitle="Of total portfolio"
        />
      </div>

      {/* Section 2: Charts */}
      {!loading && (
        <div className="mb-8" data-testid="portfolio-charts">
          {/* Row 1: Pie Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            {/* Sector Allocation */}
            <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5" data-testid="chart-sector">
              <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Composition</p>
              <p className="text-sm font-bold text-[#1F2937] mb-4">Portfolio Allocation by Sector</p>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={charts.sector_allocation || []}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                    dataKey="value"
                    nameKey="name"
                  >
                    {(charts.sector_allocation || []).map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: '11px', color: '#6B7280' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Geography Allocation */}
            <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5" data-testid="chart-geography">
              <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Geographic Exposure</p>
              <p className="text-sm font-bold text-[#1F2937] mb-4">Portfolio Allocation by Geography</p>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie
                    data={charts.geography_allocation || []}
                    cx="50%"
                    cy="50%"
                    innerRadius={55}
                    outerRadius={85}
                    paddingAngle={3}
                    dataKey="value"
                    nameKey="name"
                  >
                    {(charts.geography_allocation || []).map((_, i) => (
                      <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip content={<PieTooltip />} />
                  <Legend
                    iconType="circle"
                    iconSize={8}
                    wrapperStyle={{ fontSize: '11px', color: '#6B7280' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Row 2: IRR Distribution + Pipeline Stage Value */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* IRR Distribution */}
            <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5" data-testid="chart-irr">
              <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Return Profile</p>
              <p className="text-sm font-bold text-[#1F2937] mb-2">IRR Distribution</p>
              <div className="flex items-center gap-4 mb-4">
                <span className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: '#00A8C6' }} />
                  In Mandate
                </span>
                <span className="flex items-center gap-1.5 text-xs text-gray-500">
                  <span className="inline-block w-2 h-2 rounded-full" style={{ backgroundColor: '#F59E0B' }} />
                  Exception
                </span>
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={irrData}
                  layout="vertical"
                  margin={{ top: 0, right: 30, left: 0, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" horizontal={false} />
                  <XAxis
                    type="number"
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={v => `${v}%`}
                    domain={[0, 'dataMax + 5']}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    tick={{ fontSize: 10, fill: '#6B7280' }}
                    axisLine={false}
                    tickLine={false}
                    width={120}
                  />
                  <Tooltip content={<IrrTooltip />} />
                  <Bar dataKey="irr" radius={[0, 2, 2, 0]}>
                    {irrData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Pipeline Stage Value */}
            <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-5" data-testid="chart-pipeline">
              <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Capital Deployment</p>
              <p className="text-sm font-bold text-[#1F2937] mb-4">Pipeline Stage Value</p>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={stageData}
                  margin={{ top: 0, right: 0, left: 10, bottom: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                  <XAxis
                    dataKey="stage"
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#6B7280' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={v =>
                      v >= 1000000
                        ? `$${(v / 1000000).toFixed(1)}M`
                        : v >= 1000
                        ? `$${(v / 1000).toFixed(0)}K`
                        : `$${v}`
                    }
                  />
                  <Tooltip content={<StageTooltip />} />
                  <Bar dataKey="value" radius={[2, 2, 0, 0]}>
                    {stageData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* Section 3: Holdings Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm" data-testid="holdings-table">
        <div className="border-b border-[#E5E7EB] px-5 py-4">
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-0.5">Portfolio Holdings</p>
          <p className="text-sm font-bold text-[#1F2937]">
            All Deals — {sortedHoldings.length} position{sortedHoldings.length !== 1 ? 's' : ''}
          </p>
        </div>

        {loading ? (
          <div className="p-12 text-center text-gray-400 text-sm">Loading holdings…</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#FAFAF8]">
                  {TABLE_COLUMNS.map(({ key, label }) => (
                    <th
                      key={key}
                      onClick={() => handleSort(key)}
                      data-testid={`sort-${key}`}
                      className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wider cursor-pointer hover:text-[#1F2937] select-none whitespace-nowrap"
                    >
                      <span className="flex items-center gap-1">
                        {label}
                        <SortIcon field={key} sortField={sortField} sortDir={sortDir} />
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedHoldings.map((deal, idx) => (
                  <tr
                    key={deal.id}
                    onClick={() => navigate(`/deals/${deal.id}`)}
                    className="border-b border-[#F3F4F6] hover:bg-[#FAFAF8] cursor-pointer transition-colors"
                    data-testid={`holding-row-${idx}`}
                  >
                    <td className="px-4 py-3 font-medium text-[#1F2937] whitespace-nowrap">
                      {deal.company_name}
                    </td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{deal.sector}</td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">{deal.geography}</td>
                    <td className="px-4 py-3">
                      <span className="font-mono text-xs text-[#1B3A6B] bg-[#1B3A6B]/10 px-1.5 py-0.5 rounded-sm">
                        {deal.entity_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className="text-xs font-mono px-1.5 py-0.5 rounded-sm"
                        style={{
                          color: STAGE_COLORS[deal.pipeline_stage] || '#6B7280',
                          backgroundColor: `${STAGE_COLORS[deal.pipeline_stage] || '#6B7280'}15`,
                        }}
                      >
                        {STAGE_LABELS[deal.pipeline_stage] || deal.pipeline_stage}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-[#1F2937] whitespace-nowrap">
                      {formatUSD(deal.entry_valuation)}
                    </td>
                    <td className="px-4 py-3 font-mono text-[#1F2937] whitespace-nowrap">
                      {typeof deal.expected_irr === 'number' ? `${deal.expected_irr.toFixed(1)}%` : '—'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <MandateBadge status={deal.mandate_status} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <HealthBadge score={deal.health_score} />
                    </td>
                  </tr>
                ))}
                {sortedHoldings.length === 0 && (
                  <tr>
                    <td colSpan={9} className="px-4 py-12 text-center text-gray-400 text-sm">
                      No holdings found. Add deals to see portfolio data.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useState, useEffect, useCallback } from 'react';
import {
  FileText, Download, Filter, ChevronLeft, ChevronRight,
  RefreshCw, AlertTriangle, Loader2, BarChart3, X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

const ACTION_LABELS = {
  login: 'Login',
  investor_created: 'Investor Created',
  investor_approved: 'Investor Approved',
  investor_rejected: 'Investor Rejected',
  investor_more_info_requested: 'More Info Requested',
  investor_decision: 'Investor Decision',
  deal_created: 'Deal Created',
  deal_stage_moved: 'Stage Advanced',
  deal_executed: 'Transaction Executed',
};

const ACTION_COLORS = {
  login: '#6B7280',
  investor_created: '#00A8C6',
  investor_approved: '#10B981',
  investor_rejected: '#EF4444',
  investor_more_info_requested: '#F59E0B',
  investor_decision: '#00A8C6',
  deal_created: '#00A8C6',
  deal_stage_moved: '#1B3A6B',
  deal_executed: '#10B981',
};

const ROLE_COLORS = {
  compliance: '#10B981',
  risk: '#F59E0B',
  manager: '#00A8C6',
};

function getCurrentQuarter() {
  const now = new Date();
  const q = Math.floor(now.getMonth() / 3);
  const qStart = new Date(now.getFullYear(), q * 3, 1);
  const qEnd = new Date(now.getFullYear(), q * 3 + 3, 0);
  return {
    label: `Q${q + 1} ${now.getFullYear()}`,
    from: qStart.toISOString().split('T')[0],
    to: qEnd.toISOString().split('T')[0],
  };
}

function formatTs(ts) {
  if (!ts) return '—';
  return new Date(ts).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function ActionBadge({ action }) {
  const label = ACTION_LABELS[action] || action;
  const color = ACTION_COLORS[action] || '#6B7280';
  return (
    <span
      className="inline-flex items-center px-2 py-0.5 rounded-sm text-xs font-mono font-medium border"
      style={{ color, borderColor: `${color}30`, backgroundColor: `${color}10` }}
    >
      {label}
    </span>
  );
}

function RoleBadge({ role }) {
  const color = ROLE_COLORS[role] || '#6B7280';
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded-sm text-xs font-mono uppercase"
      style={{ color, backgroundColor: `${color}15` }}
    >
      {role}
    </span>
  );
}

export default function Reports() {
  const { user } = useAuth();

  const [logs, setLogs] = useState([]);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Filters
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [page, setPage] = useState(1);
  const LIMIT = 20;

  // TAV Modal
  const { label: defaultLabel, from: defaultFrom, to: defaultTo } = getCurrentQuarter();
  const [showTAV, setShowTAV] = useState(false);
  const [tavFrom, setTavFrom] = useState(defaultFrom);
  const [tavTo, setTavTo] = useState(defaultTo);
  const [generatingTAV, setGeneratingTAV] = useState(false);
  const [tavError, setTavError] = useState('');

  const fetchLogs = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const params = new URLSearchParams({ page, limit: LIMIT });
      if (fromDate) params.set('from', fromDate);
      if (toDate) params.set('to', toDate);
      if (actionFilter) params.set('action', actionFilter);
      if (roleFilter) params.set('role', roleFilter);
      const res = await fetch(`${API}/api/audit-logs?${params}`, { credentials: 'include' });
      if (!res.ok) {
        const e = await res.json();
        throw new Error(e.detail || 'Failed to load audit logs');
      }
      const data = await res.json();
      setLogs(data.logs || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 1);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [fromDate, toDate, actionFilter, roleFilter, page]);

  useEffect(() => { fetchLogs(); }, [fetchLogs]);

  const applyFilters = (e) => {
    e.preventDefault();
    setPage(1);
    fetchLogs();
  };

  const clearFilters = () => {
    setFromDate('');
    setToDate('');
    setActionFilter('');
    setRoleFilter('');
    setPage(1);
  };

  const exportCSV = () => {
    if (!logs.length) return;
    const headers = ['Timestamp', 'Action', 'Actor Email', 'Actor Role', 'Actor Name', 'Target ID', 'Target Type', 'Notes'];
    const rows = logs.map(l => [
      l.timestamp ? new Date(l.timestamp).toISOString() : '',
      ACTION_LABELS[l.action] || l.action,
      l.user_email || '',
      l.user_role || '',
      l.user_name || '',
      l.target_id || '',
      l.target_type || '',
      (l.notes || '').replace(/,/g, ';'),
    ]);
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit_log_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const generateTAV = async () => {
    setGeneratingTAV(true);
    setTavError('');
    try {
      const params = new URLSearchParams({ from: tavFrom, to: tavTo });
      const res = await fetch(`${API}/api/reports/tav-pdf?${params}`, { credentials: 'include' });
      if (!res.ok) {
        const e = await res.json();
        throw new Error(e.detail || 'TAV generation failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `TAV_Report_${tavFrom}_to_${tavTo}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setShowTAV(false);
    } catch (e) {
      setTavError(e.message);
    } finally {
      setGeneratingTAV(false);
    }
  };

  // Role guard
  if (user?.role !== 'compliance') {
    return (
      <div className="p-8 flex flex-col items-center justify-center min-h-[50vh] gap-3">
        <AlertTriangle size={28} color="#F59E0B" />
        <h2 className="text-lg font-semibold text-[#1F2937]">Access Restricted</h2>
        <p className="text-sm text-[#6B7280]">The Reports module is available to Compliance Officers only.</p>
      </div>
    );
  }

  const quarterLabel = (() => {
    if (!tavFrom) return defaultLabel;
    const d = new Date(tavFrom);
    return `Q${Math.floor(d.getMonth() / 3) + 1} ${d.getFullYear()}`;
  })();

  return (
    <div className="p-6 md:p-8 animate-fade-in">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <p className="text-overline mb-1">Compliance</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading flex items-center gap-3">
            <FileText size={28} strokeWidth={1.5} color="#1B3A6B" />
            Reports & Audit Log
          </h1>
          <p className="text-sm text-[#6B7280] mt-1">{total} log entries found</p>
        </div>
        <div className="flex items-center gap-3 flex-shrink-0">
          <button
            onClick={exportCSV}
            disabled={!logs.length}
            data-testid="export-csv-btn"
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-[#374151] bg-white border border-[#E5E7EB] rounded-sm hover:bg-[#F9FAFB] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download size={14} /> Export CSV
          </button>
          <button
            onClick={() => { setShowTAV(true); setTavError(''); }}
            data-testid="generate-tav-btn"
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#152e56] transition-colors"
          >
            <BarChart3 size={14} /> Generate TAV Report
          </button>
        </div>
      </div>

      {/* ── Filter Bar ──────────────────────────────────────────────────────── */}
      <form onSubmit={applyFilters} className="bg-white border border-[#E5E7EB] rounded-sm p-4 mb-5 flex flex-wrap items-end gap-3" data-testid="filter-bar">
        <div className="flex flex-col gap-1 min-w-[140px]">
          <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider">From Date</label>
          <input
            type="date"
            value={fromDate}
            onChange={e => setFromDate(e.target.value)}
            data-testid="filter-from-date"
            className="border border-[#E5E7EB] rounded-sm px-2.5 py-1.5 text-sm text-[#374151] focus:outline-none focus:border-[#1B3A6B] bg-white"
          />
        </div>
        <div className="flex flex-col gap-1 min-w-[140px]">
          <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider">To Date</label>
          <input
            type="date"
            value={toDate}
            onChange={e => setToDate(e.target.value)}
            data-testid="filter-to-date"
            className="border border-[#E5E7EB] rounded-sm px-2.5 py-1.5 text-sm text-[#374151] focus:outline-none focus:border-[#1B3A6B] bg-white"
          />
        </div>
        <div className="flex flex-col gap-1 min-w-[160px]">
          <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider">Action Type</label>
          <select
            value={actionFilter}
            onChange={e => setActionFilter(e.target.value)}
            data-testid="filter-action"
            className="border border-[#E5E7EB] rounded-sm px-2.5 py-1.5 text-sm text-[#374151] focus:outline-none focus:border-[#1B3A6B] bg-white"
          >
            <option value="">All Actions</option>
            {Object.entries(ACTION_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1 min-w-[130px]">
          <label className="text-xs text-[#6B7280] font-semibold uppercase tracking-wider">Role</label>
          <select
            value={roleFilter}
            onChange={e => setRoleFilter(e.target.value)}
            data-testid="filter-role"
            className="border border-[#E5E7EB] rounded-sm px-2.5 py-1.5 text-sm text-[#374151] focus:outline-none focus:border-[#1B3A6B] bg-white"
          >
            <option value="">All Roles</option>
            <option value="compliance">Compliance</option>
            <option value="risk">Risk</option>
            <option value="manager">Manager</option>
          </select>
        </div>
        <div className="flex items-end gap-2">
          <button type="submit" data-testid="apply-filters-btn" className="flex items-center gap-2 px-3 py-1.5 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#152e56] transition-colors">
            <Filter size={13} /> Apply
          </button>
          <button type="button" onClick={clearFilters} data-testid="clear-filters-btn" className="flex items-center gap-2 px-3 py-1.5 text-sm text-[#6B7280] bg-white border border-[#E5E7EB] rounded-sm hover:bg-[#F9FAFB] transition-colors">
            <X size={13} /> Clear
          </button>
          <button type="button" onClick={fetchLogs} className="flex items-center gap-2 px-3 py-1.5 text-sm text-[#6B7280] bg-white border border-[#E5E7EB] rounded-sm hover:bg-[#F9FAFB] transition-colors">
            <RefreshCw size={13} />
          </button>
        </div>
      </form>

      {/* ── Error ───────────────────────────────────────────────────────────── */}
      {error && (
        <div className="mb-4 p-3 bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-sm text-sm text-[#EF4444]" data-testid="audit-error">
          {error}
        </div>
      )}

      {/* ── Table ───────────────────────────────────────────────────────────── */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          {loading ? (
            <div className="flex items-center justify-center py-16 gap-3">
              <Loader2 size={22} className="animate-spin text-[#1B3A6B]" />
              <span className="text-sm text-[#6B7280]">Loading audit log...</span>
            </div>
          ) : logs.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-16 gap-3 text-[#9CA3AF]">
              <FileText size={28} strokeWidth={1.5} />
              <p className="text-sm">No audit log entries found for the selected filters.</p>
            </div>
          ) : (
            <table className="w-full text-sm" data-testid="audit-log-table">
              <thead>
                <tr className="border-b border-[#E5E7EB] bg-[#F8F9FA]">
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#6B7280] uppercase tracking-wider whitespace-nowrap">Timestamp</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#6B7280] uppercase tracking-wider whitespace-nowrap">Action</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#6B7280] uppercase tracking-wider whitespace-nowrap">Actor</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#6B7280] uppercase tracking-wider whitespace-nowrap hidden md:table-cell">Target</th>
                  <th className="text-left px-4 py-3 text-xs font-semibold text-[#6B7280] uppercase tracking-wider hidden lg:table-cell">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F3F4F6]">
                {logs.map((log, idx) => (
                  <tr key={log.id || idx} className="hover:bg-[#F9FAFB] transition-colors" data-testid={`audit-log-row-${idx}`}>
                    <td className="px-4 py-3 text-xs text-[#6B7280] font-mono whitespace-nowrap">
                      {formatTs(log.timestamp)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <ActionBadge action={log.action} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex flex-col gap-0.5">
                        <span className="text-xs font-medium text-[#374151]">{log.user_email || '—'}</span>
                        {log.user_role && <RoleBadge role={log.user_role} />}
                      </div>
                    </td>
                    <td className="px-4 py-3 hidden md:table-cell">
                      <span className="text-xs text-[#374151] font-mono capitalize">{log.target_type || '—'}</span>
                    </td>
                    <td className="px-4 py-3 hidden lg:table-cell max-w-xs">
                      <span className="text-xs text-[#6B7280] truncate block" title={log.notes}>
                        {log.notes || '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="border-t border-[#E5E7EB] px-4 py-3 flex items-center justify-between bg-white" data-testid="pagination">
            <span className="text-xs text-[#6B7280]">
              Page {page} of {totalPages} &middot; {total} total entries
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                data-testid="prev-page-btn"
                className="p-1.5 rounded-sm border border-[#E5E7EB] text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft size={14} />
              </button>
              {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                const pg = page <= 3 ? i + 1 : page - 2 + i;
                if (pg < 1 || pg > totalPages) return null;
                return (
                  <button
                    key={pg}
                    onClick={() => setPage(pg)}
                    className={`px-2.5 py-1 text-xs rounded-sm border transition-colors ${pg === page ? 'bg-[#1B3A6B] text-white border-[#1B3A6B]' : 'border-[#E5E7EB] text-[#374151] hover:bg-[#F9FAFB]'}`}
                  >
                    {pg}
                  </button>
                );
              })}
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                data-testid="next-page-btn"
                className="p-1.5 rounded-sm border border-[#E5E7EB] text-[#374151] hover:bg-[#F9FAFB] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
        )}
      </div>

      {/* ── TAV Report Modal ────────────────────────────────────────────────── */}
      {showTAV && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="tav-modal">
          <div className="bg-white rounded-sm shadow-xl w-full max-w-md">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#E5E7EB]">
              <div className="flex items-center gap-2">
                <BarChart3 size={18} color="#1B3A6B" />
                <h2 className="text-base font-semibold text-[#1F2937]">Generate TAV Report</h2>
              </div>
              <button onClick={() => setShowTAV(false)} className="text-[#9CA3AF] hover:text-[#374151] transition-colors" data-testid="close-tav-modal">
                <X size={18} />
              </button>
            </div>

            <div className="px-6 py-5 space-y-4">
              <div className="bg-[#F8F9FA] border border-[#E5E7EB] rounded-sm p-3">
                <p className="text-xs text-[#6B7280] mb-1 font-semibold uppercase tracking-wider">Reporting Quarter</p>
                <p className="text-lg font-bold text-[#1B3A6B] font-heading">{quarterLabel}</p>
                <p className="text-xs text-[#9CA3AF] mt-0.5 font-mono">Auto-calculated from current quarter</p>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">From</label>
                  <input
                    type="date"
                    value={tavFrom}
                    onChange={e => setTavFrom(e.target.value)}
                    data-testid="tav-from-date"
                    className="w-full border border-[#E5E7EB] rounded-sm px-2.5 py-1.5 text-sm text-[#374151] focus:outline-none focus:border-[#1B3A6B] bg-white"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">To</label>
                  <input
                    type="date"
                    value={tavTo}
                    onChange={e => setTavTo(e.target.value)}
                    data-testid="tav-to-date"
                    className="w-full border border-[#E5E7EB] rounded-sm px-2.5 py-1.5 text-sm text-[#374151] focus:outline-none focus:border-[#1B3A6B] bg-white"
                  />
                </div>
              </div>

              <div className="bg-[#1B3A6B]/5 border border-[#1B3A6B]/10 rounded-sm p-3">
                <p className="text-xs text-[#6B7280]">
                  The TAV report aggregates live data from all <strong>Closing</strong> and <strong>IC Review</strong> deals
                  and all approved investors. The PDF will include 5 sections: Fund Overview, Portfolio Summary,
                  Total Asset Value breakdown, Investor Base, and Compliance Summary.
                </p>
              </div>

              {tavError && (
                <div className="p-3 bg-[#EF4444]/10 border border-[#EF4444]/20 rounded-sm text-sm text-[#EF4444]" data-testid="tav-error">
                  {tavError}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-[#E5E7EB]">
              <button
                onClick={() => setShowTAV(false)}
                data-testid="tav-cancel-btn"
                className="px-4 py-2 text-sm text-[#374151] bg-white border border-[#E5E7EB] rounded-sm hover:bg-[#F9FAFB] transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={generateTAV}
                disabled={generatingTAV || !tavFrom || !tavTo}
                data-testid="tav-confirm-btn"
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-[#1B3A6B] text-white rounded-sm hover:bg-[#152e56] transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {generatingTAV ? (
                  <><Loader2 size={14} className="animate-spin" /> Generating...</>
                ) : (
                  <><Download size={14} /> Generate &amp; Download PDF</>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

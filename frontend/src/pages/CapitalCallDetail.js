import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, Loader2, Download, AlertTriangle, CheckCircle2, Clock } from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

function formatUSD(v) {
  if (!v && v !== 0) return '—';
  if (v >= 1000000) return `$${(v / 1000000).toFixed(2)}M`;
  if (v >= 1000) return `$${(v / 1000).toFixed(0)}K`;
  return `$${Number(v).toLocaleString()}`;
}
function formatDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

const LINE_STATUS = {
  pending: { color: '#F59E0B', label: 'Pending', Icon: Clock },
  received: { color: '#10B981', label: 'Received', Icon: CheckCircle2 },
  defaulted: { color: '#EF4444', label: 'Defaulted', Icon: AlertTriangle },
};

const CALL_STATUS = {
  draft: { color: '#6B7280', label: 'Draft' },
  issued: { color: '#00A8C6', label: 'Issued' },
  closed: { color: '#10B981', label: 'Closed' },
};

export default function CapitalCallDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [call, setCall] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updatingId, setUpdatingId] = useState('');
  const [exporting, setExporting] = useState(false);
  const isCompliance = user?.role === 'compliance';

  const fetchCall = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/capital-calls/${id}`, { credentials: 'include' });
      if (!res.ok) throw new Error('Capital call not found');
      setCall(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchCall(); }, [fetchCall]);

  const updateLineItem = async (investorId, status) => {
    setUpdatingId(investorId);
    try {
      const res = await fetch(`${API}/api/capital-calls/${id}/line-items/${investorId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ status }),
      });
      if (!res.ok) throw new Error((await res.json()).detail || 'Update failed');
      toast.success(`Line item marked as ${status}`);
      fetchCall();
    } catch (e) {
      toast.error(e.message);
    } finally {
      setUpdatingId('');
    }
  };

  const handleExportNotices = async () => {
    setExporting(true);
    try {
      const res = await fetch(`${API}/api/capital-calls/${id}/notices`, { credentials: 'include' });
      if (!res.ok) throw new Error('Export failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ct = res.headers.get('Content-Type') || '';
      a.download = ct.includes('zip') ? `CallNotices_${call?.call_name?.replace(/ /g, '_')}.zip` : `CallNotice_${call?.call_name?.replace(/ /g, '_')}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Notices exported successfully');
    } catch (e) {
      toast.error(e.message);
    } finally {
      setExporting(false);
    }
  };

  const handleExportCSV = async () => {
    try {
      const res = await fetch(`${API}/api/capital-calls/${id}/export-csv`, { credentials: 'include' });
      if (!res.ok) throw new Error('CSV export failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CapitalCall_${call?.call_name?.replace(/ /g, '_')}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(e.message);
    }
  };

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-[50vh]">
        <Loader2 size={28} className="animate-spin text-[#1B3A6B]" />
      </div>
    );
  }

  if (!call) {
    return (
      <div className="p-8">
        <button onClick={() => navigate('/capital-calls')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] mb-6"><ArrowLeft size={15} /> Back</button>
        <p className="text-[#EF4444] text-sm">Capital call not found.</p>
      </div>
    );
  }

  const cs = CALL_STATUS[call.status] || CALL_STATUS.draft;
  const lineItems = call.line_items || [];
  const totalReceived = lineItems.filter(li => li.status === 'received').reduce((s, li) => s + (li.call_amount || 0), 0);
  const totalDefaulted = lineItems.filter(li => li.status === 'defaulted').reduce((s, li) => s + (li.call_amount || 0), 0);

  return (
    <div className="p-6 md:p-8 animate-fade-in" data-testid="capital-call-detail">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <button onClick={() => navigate('/capital-calls')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] mb-3 transition-colors">
            <ArrowLeft size={15} /> Back to Capital Calls
          </button>
          <p className="text-overline mb-1">Capital Call</p>
          <h1 className="text-2xl font-bold tracking-tight text-[#1F2937] font-heading">{call.call_name}</h1>
          <div className="flex items-center gap-3 mt-2">
            <span className="text-xs font-mono px-1.5 py-0.5 rounded-sm" style={{ color: cs.color, backgroundColor: `${cs.color}15`, border: `1px solid ${cs.color}30` }}>{cs.label}</span>
            <span className="text-xs text-gray-400">{call.call_type === 'fund_level' ? 'Fund Level' : 'Deal Specific'}</span>
            <span className="text-xs text-gray-400">Due: {formatDate(call.due_date)}</span>
          </div>
        </div>
        <div className="flex items-center gap-3 mt-1">
          <button onClick={fetchCall} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#1B3A6B] transition-colors">
            <RefreshCw size={15} strokeWidth={1.5} />
          </button>
          {call.status === 'issued' && (
            <>
              <button
                onClick={handleExportNotices}
                disabled={exporting}
                data-testid="export-notices-btn"
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold bg-[#252523] text-white rounded-sm hover:bg-[#333333] transition-colors border border-[#444444] disabled:opacity-50"
              >
                <Download size={13} /> {exporting ? 'Exporting…' : 'Export Notices'}
              </button>
              <button
                onClick={handleExportCSV}
                data-testid="export-csv-btn"
                className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-[#1B3A6B] border border-[#1B3A6B]/30 rounded-sm hover:bg-[#1B3A6B]/5 transition-colors"
              >
                <Download size={13} /> CSV
              </button>
            </>
          )}
        </div>
      </div>

      {/* Summary Strip */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { label: 'Total Called', value: formatUSD(call.total_amount), color: '#1B3A6B' },
          { label: 'Received', value: formatUSD(totalReceived), color: '#10B981' },
          { label: 'Defaulted', value: formatUSD(totalDefaulted), color: '#EF4444' },
          { label: '% Received', value: `${call.pct_received ?? 0}%`, color: '#00A8C6' },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-4">
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">{label}</p>
            <p className="text-xl font-bold font-mono" style={{ color }}>{value}</p>
          </div>
        ))}
      </div>

      {/* Progress Bar */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-4 mb-6">
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Call Receipt Progress</p>
          <p className="text-xs font-mono text-[#6B7280]">{lineItems.filter(li => li.status === 'received').length} / {lineItems.length} investors</p>
        </div>
        <div className="h-2 bg-[#E5E7EB] rounded-full overflow-hidden">
          <div className="h-full rounded-full bg-[#10B981] transition-all duration-500" style={{ width: `${call.pct_received || 0}%` }} />
        </div>
      </div>

      {/* Line Items Table */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm" data-testid="line-items-table">
        <div className="border-b border-[#E5E7EB] px-4 py-4">
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-0.5">Investor Line Items</p>
          <p className="text-sm font-bold text-[#1F2937]">{lineItems.length} investor{lineItems.length !== 1 ? 's' : ''}</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#FAFAF8]">
                {['Investor Name', 'Class', 'Committed Capital', 'Call Amount', 'Status', 'Interest Accrued', isCompliance ? 'Actions' : ''].filter(Boolean).map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wider whitespace-nowrap">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {lineItems.map((li, idx) => {
                const ls = LINE_STATUS[li.status] || LINE_STATUS.pending;
                const LsIcon = ls.Icon;
                return (
                  <tr key={li.investor_id} className="border-b border-[#F3F4F6]" data-testid={`line-item-${idx}`}>
                    <td className="px-4 py-3 font-medium text-[#1F2937]">{li.investor_name}</td>
                    <td className="px-4 py-3 font-mono text-xs text-[#1B3A6B]">Class {li.share_class}</td>
                    <td className="px-4 py-3 font-mono text-[#1F2937]">{formatUSD(li.committed_capital)}</td>
                    <td className="px-4 py-3 font-mono font-semibold text-[#1B3A6B]">{formatUSD(li.call_amount)}</td>
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-1.5 text-xs font-mono" style={{ color: ls.color }}>
                        <LsIcon size={12} /> {ls.label}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-mono text-xs">
                      {li.status === 'defaulted' && li.accrued_interest > 0 ? (
                        <span className="text-[#EF4444]">
                          {formatUSD(li.accrued_interest)}<br />
                          <span className="text-[#9CA3AF] text-xs">{li.days_overdue}d overdue</span>
                        </span>
                      ) : <span className="text-gray-300">—</span>}
                    </td>
                    {isCompliance && (
                      <td className="px-4 py-3">
                        {call.status === 'issued' && (
                          <div className="flex items-center gap-2">
                            {li.status !== 'received' && (
                              <button
                                onClick={() => updateLineItem(li.investor_id, 'received')}
                                disabled={updatingId === li.investor_id}
                                data-testid={`mark-received-${idx}`}
                                className="text-xs px-2 py-1 bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20 rounded-sm hover:bg-[#10B981]/20 transition-colors disabled:opacity-50"
                              >
                                {updatingId === li.investor_id ? '…' : 'Received'}
                              </button>
                            )}
                            {li.status !== 'defaulted' && (
                              <button
                                onClick={() => updateLineItem(li.investor_id, 'defaulted')}
                                disabled={updatingId === li.investor_id}
                                data-testid={`mark-defaulted-${idx}`}
                                className="text-xs px-2 py-1 bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20 rounded-sm hover:bg-[#EF4444]/20 transition-colors disabled:opacity-50"
                              >
                                {updatingId === li.investor_id ? '…' : 'Defaulted'}
                              </button>
                            )}
                            {li.status !== 'pending' && (
                              <button
                                onClick={() => updateLineItem(li.investor_id, 'pending')}
                                disabled={updatingId === li.investor_id}
                                className="text-xs px-2 py-1 bg-[#F59E0B]/10 text-[#F59E0B] border border-[#F59E0B]/20 rounded-sm hover:bg-[#F59E0B]/20 transition-colors disabled:opacity-50"
                              >
                                Reset
                              </button>
                            )}
                          </div>
                        )}
                      </td>
                    )}
                  </tr>
                );
              })}
              {lineItems.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 py-12 text-center text-gray-400 text-sm">No line items in this capital call</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';
import { Loader2, Bell, X, Download, CreditCard } from 'lucide-react';
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

function CallStatusBadge({ status, days }) {
  const map = {
    received:  { bg: '#F0FDF4', text: '#15803D', label: 'Received' },
    pending:   { bg: daysBg(days), text: daysColor(days), label: days != null ? `${days}d remaining` : 'Pending' },
    defaulted: { bg: '#FEF2F2', text: '#991B1B', label: 'Defaulted' },
  };
  const s = map[status] || map.pending;
  return (
    <span className="px-2 py-0.5 rounded-sm text-xs font-semibold whitespace-nowrap" style={{ backgroundColor: s.bg, color: s.text }}>
      {s.label}
    </span>
  );
}

function CallDetailModal({ call, onClose }) {
  const [downloading, setDownloading] = useState(false);

  const downloadNotice = async () => {
    setDownloading(true);
    try {
      const res = await portalFetch(`${API}/api/portal/capital-calls/${call.call_id}/notice-pdf`);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `CapitalCallNotice_${call.call_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(e);
    } finally {
      setDownloading(false);
    }
  };

  const pi = call.payment_instructions || {};

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="call-detail-modal">
      <div className="bg-white rounded-sm shadow-xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E8E6E0] sticky top-0 bg-white z-10">
          <div className="flex items-center gap-2">
            <Bell size={16} color="#00A8C6" />
            <h2 className="text-base font-semibold text-[#0F0F0E]">Capital Call Details</h2>
          </div>
          <button onClick={onClose} className="text-[#888880] hover:text-[#0F0F0E] transition-colors" data-testid="close-call-modal">
            <X size={18} />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {/* Call summary */}
          <div>
            <p className="text-lg font-semibold text-[#0F0F0E] mb-1">{call.call_name}</p>
            <p className="text-sm text-[#888880]">Zephyr Caribbean Growth Fund I</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-xs text-[#888880] uppercase font-semibold mb-0.5">Call Percentage</p>
              <p className="text-sm font-mono font-semibold text-[#0F0F0E]">{call.call_percentage || 0}%</p>
            </div>
            <div>
              <p className="text-xs text-[#888880] uppercase font-semibold mb-0.5">Share Class</p>
              <p className="text-sm font-mono font-semibold text-[#0F0F0E]">Class {call.share_class || 'A'}</p>
            </div>
            <div>
              <p className="text-xs text-[#888880] uppercase font-semibold mb-0.5">Issue Date</p>
              <p className="text-sm text-[#0F0F0E]">{fmtDate(call.issue_date)}</p>
            </div>
            <div>
              <p className="text-xs text-[#888880] uppercase font-semibold mb-0.5">Due Date</p>
              <p className="text-sm text-[#0F0F0E]">{fmtDate(call.due_date)}</p>
            </div>
          </div>

          {/* Amount Due — prominent */}
          <div className="bg-[#FAFAF8] border border-[#E8E6E0] rounded-sm p-4 text-center">
            <p className="text-xs text-[#888880] uppercase font-semibold mb-1">Amount Due</p>
            <p className="text-3xl font-bold font-mono" style={{ color: '#00A8C6' }} data-testid="modal-amount-due">
              {fmt(call.amount_due)}
            </p>
            <div className="mt-2">
              <CallStatusBadge status={call.status} days={call.days_remaining} />
            </div>
          </div>

          {/* Payment Instructions */}
          {pi.fund_name && (
            <div className="border border-[#E8E6E0] rounded-sm overflow-hidden" data-testid="payment-instructions">
              <div className="bg-[#FAFAF8] px-4 py-2.5 border-b border-[#E8E6E0] flex items-center gap-2">
                <CreditCard size={13} color="#00A8C6" />
                <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">Payment Instructions</span>
              </div>
              <div className="px-4 py-3 space-y-2">
                {[
                  { label: 'Fund Name', value: pi.fund_name },
                  { label: 'Bank Name', value: pi.bank_name },
                  { label: 'Account Number', value: pi.account_number },
                  { label: 'SWIFT Code', value: pi.swift },
                  { label: 'Payment Reference', value: pi.reference },
                ].map(({ label, value }) => (
                  <div key={label} className="flex items-start justify-between gap-4 py-1.5 border-b border-[#F3F4F6] last:border-0">
                    <span className="text-xs text-[#888880] uppercase font-semibold flex-shrink-0">{label}</span>
                    <span className="text-xs font-mono text-[#0F0F0E] text-right">{value || '—'}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-[#E8E6E0] flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm text-[#888880] bg-white border border-[#E8E6E0] rounded-sm hover:bg-[#FAFAF8] transition-colors"
          >
            Close
          </button>
          <button
            onClick={downloadNotice}
            disabled={downloading}
            data-testid="download-notice-btn"
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white rounded-sm transition-colors disabled:opacity-60"
            style={{ backgroundColor: '#00A8C6' }}
          >
            {downloading ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
            Download Call Notice PDF
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PortalCapitalCalls() {
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedCall, setSelectedCall] = useState(null);

  useEffect(() => {
    portalFetch(`${API}/api/portal/capital-calls`)
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load capital calls');
        return r.json();
      })
      .then(setCalls)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={24} className="animate-spin text-[#00A8C6]" />
        <p className="text-sm text-[#888880]">Loading capital calls...</p>
      </div>
    </div>
  );

  return (
    <div className="px-6 md:px-10 py-8 max-w-5xl mx-auto" data-testid="portal-capital-calls">
      {/* Header */}
      <div className="mb-8">
        <p className="text-xs text-[#888880] font-mono uppercase tracking-wider mb-1">Investment Portal</p>
        <h1 className="text-2xl font-semibold text-[#0F0F0E] tracking-tight flex items-center gap-2">
          <Bell size={22} color="#00A8C6" />
          Capital Calls
        </h1>
        <p className="text-sm text-[#888880] mt-1">{calls.length} capital call{calls.length !== 1 ? 's' : ''} recorded</p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-sm text-sm text-red-600">
          {error}
        </div>
      )}

      <div className="bg-white border border-[#E8E6E0] rounded-sm shadow-sm overflow-hidden">
        {calls.length === 0 ? (
          <div className="py-16 text-center">
            <Bell size={28} className="mx-auto mb-3 text-[#D1D5DB]" />
            <p className="text-sm text-[#888880]">No capital calls recorded yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E8E6E0] bg-[#FAFAF8]">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Call Name</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider hidden sm:table-cell">Issue Date</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider hidden sm:table-cell">Due Date</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">My Amount</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F3F4F6]">
                {calls.map((call, i) => (
                  <tr
                    key={call.call_id || i}
                    className="hover:bg-[#FAFAF8] cursor-pointer transition-colors"
                    onClick={() => setSelectedCall(call)}
                    data-testid={`capital-call-row-${i}`}
                  >
                    <td className="px-5 py-4 text-sm font-medium text-[#0F0F0E]">{call.call_name}</td>
                    <td className="px-5 py-4 text-xs font-mono text-[#888880] hidden sm:table-cell">{fmtDate(call.issue_date)}</td>
                    <td className="px-5 py-4 text-xs font-mono text-[#888880] hidden sm:table-cell">{fmtDate(call.due_date)}</td>
                    <td className="px-5 py-4 text-right font-mono text-sm font-bold text-[#0F0F0E]">{fmt(call.amount_due)}</td>
                    <td className="px-5 py-4 text-right">
                      <CallStatusBadge status={call.status} days={call.days_remaining} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <p className="text-xs text-[#888880] mt-4 text-center">
        Click any row to view details and payment instructions.
      </p>

      {selectedCall && (
        <CallDetailModal call={selectedCall} onClose={() => setSelectedCall(null)} />
      )}
    </div>
  );
}

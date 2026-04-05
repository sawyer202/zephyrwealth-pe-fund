import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, RefreshCw, CheckCircle2, XCircle, Loader2, FileText, Download } from 'lucide-react';
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

const STATUS_BADGE = {
  draft: { color: '#6B7280', label: 'Draft' },
  issued: { color: '#00A8C6', label: 'Issued' },
  paid: { color: '#10B981', label: 'Paid' },
};

export default function AgentDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [agent, setAgent] = useState(null);
  const [loading, setLoading] = useState(true);
  const isCompliance = user?.role === 'compliance';

  const fetchAgent = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API}/api/agents/${id}`, { credentials: 'include' });
      if (!res.ok) throw new Error('Agent not found');
      setAgent(await res.json());
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => { fetchAgent(); }, [fetchAgent]);

  const handleDownloadInvoicePDF = async (invoiceId, invoiceNumber) => {
    try {
      const res = await fetch(`${API}/api/trailer-fees/${invoiceId}/pdf`, { credentials: 'include' });
      if (!res.ok) throw new Error('PDF generation failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `TrailerFeeInvoice_${invoiceNumber}.pdf`;
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

  if (!agent) {
    return (
      <div className="p-8">
        <button onClick={() => navigate('/agents')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] mb-6"><ArrowLeft size={15} /> Back to Agents</button>
        <p className="text-[#EF4444] text-sm">Agent not found.</p>
      </div>
    );
  }

  return (
    <div className="p-6 md:p-8 animate-fade-in" data-testid="agent-detail-page">
      <div className="flex items-start justify-between mb-6">
        <div>
          <button onClick={() => navigate('/agents')} className="flex items-center gap-1.5 text-sm text-[#6B7280] hover:text-[#1B3A6B] mb-3 transition-colors">
            <ArrowLeft size={15} /> Back to Agents
          </button>
          <p className="text-overline mb-1">Placement Agent</p>
          <h1 className="text-3xl font-bold tracking-tight text-[#1F2937] font-heading">{agent.agent_name}</h1>
          <p className="text-sm text-gray-500 mt-1">{agent.company_name}</p>
        </div>
        <button onClick={fetchAgent} className="flex items-center gap-1.5 text-sm text-gray-500 hover:text-[#1B3A6B] transition-colors mt-1">
          <RefreshCw size={15} strokeWidth={1.5} /> Refresh
        </button>
      </div>

      {/* Agent Info + Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Contact & Banking */}
        <div className="lg:col-span-2 bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
          <div className="border-b border-[#E5E7EB] px-4 py-3">
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider">Agent Details</p>
          </div>
          <div className="px-4 py-3 grid grid-cols-2 gap-x-6">
            {[
              ['Email', agent.email],
              ['Phone', agent.phone],
              ['Bank Name', agent.bank_name],
              ['Account Number', agent.bank_account_number],
              ['SWIFT / BIC', agent.swift_code],
              ['VAT Status', agent.vat_registered ? `Registered (${agent.vat_number || ''})` : 'Not Registered'],
            ].map(([label, value]) => (
              <div key={label} className="flex items-start justify-between py-2 border-b border-[#F3F4F6]">
                <span className="text-xs text-[#6B7280] uppercase tracking-wider font-semibold">{label}</span>
                <span className="text-sm text-[#1F2937] font-mono text-right ml-4">{value || '—'}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Summary Cards */}
        <div className="flex flex-col gap-4">
          <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-4">
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Linked Investors</p>
            <p className="text-3xl font-bold font-mono text-[#1B3A6B]">{(agent.linked_investors || []).length}</p>
            <p className="text-xs text-gray-400 mt-1">Class C investors</p>
          </div>
          <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm p-4">
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-1">Total Fees Invoiced</p>
            <p className="text-2xl font-bold font-mono text-[#1B3A6B]">{formatUSD(agent.total_fees_invoiced)}</p>
            <div className="flex items-center gap-1 mt-1">
              {agent.vat_registered ? <CheckCircle2 size={11} className="text-[#10B981]" /> : <XCircle size={11} className="text-[#6B7280]" />}
              <p className="text-xs text-gray-400">{agent.vat_registered ? 'VAT registered' : 'No VAT'}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Linked Class C Investors */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm mb-6">
        <div className="border-b border-[#E5E7EB] px-4 py-3">
          <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-0.5">Linked Investors</p>
          <p className="text-sm font-bold text-[#1F2937]">{(agent.linked_investors || []).length} Class C investor{(agent.linked_investors || []).length !== 1 ? 's' : ''}</p>
        </div>
        {(agent.linked_investors || []).length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-gray-400">No investors linked to this agent</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#FAFAF8]">
                {['Investor Name', 'Share Class', 'Committed Capital', 'KYC Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(agent.linked_investors || []).map((inv, i) => (
                <tr
                  key={inv.id}
                  onClick={() => navigate(`/investors/${inv.id}`)}
                  className="border-b border-[#F3F4F6] hover:bg-[#FAFAF8] cursor-pointer transition-colors"
                  data-testid={`linked-investor-${i}`}
                >
                  <td className="px-4 py-3 font-medium text-[#1F2937]">{inv.name}</td>
                  <td className="px-4 py-3 font-mono text-xs text-[#1B3A6B]">Class {inv.share_class}</td>
                  <td className="px-4 py-3 font-mono text-[#1F2937]">{formatUSD(inv.committed_capital)}</td>
                  <td className="px-4 py-3">
                    <span className={`text-xs font-mono px-1.5 py-0.5 rounded-sm ${inv.kyc_status === 'approved' ? 'text-[#10B981] bg-[#10B981]/10' : 'text-[#F59E0B] bg-[#F59E0B]/10'}`}>
                      {inv.kyc_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Invoice History */}
      <div className="bg-white border border-[#E5E7EB] rounded-sm shadow-sm">
        <div className="border-b border-[#E5E7EB] px-4 py-3 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-[#6B7280] uppercase tracking-wider mb-0.5">Invoice History</p>
            <p className="text-sm font-bold text-[#1F2937]">{(agent.invoices || []).length} trailer fee invoice{(agent.invoices || []).length !== 1 ? 's' : ''}</p>
          </div>
        </div>
        {(agent.invoices || []).length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-gray-400">No invoices generated yet</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[#E5E7EB] bg-[#FAFAF8]">
                {['Invoice Number', 'Period', 'Total Due', 'Status', 'Issued Date', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(agent.invoices || []).map((inv, i) => {
                const s = STATUS_BADGE[inv.status] || STATUS_BADGE.draft;
                return (
                  <tr key={inv.id} className="border-b border-[#F3F4F6]" data-testid={`invoice-row-${i}`}>
                    <td className="px-4 py-3 font-mono text-xs text-[#1B3A6B]">{inv.invoice_number}</td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{inv.period_year}</td>
                    <td className="px-4 py-3 font-mono text-[#1F2937]">{formatUSD(inv.total_due)}</td>
                    <td className="px-4 py-3">
                      <span className="text-xs font-mono px-1.5 py-0.5 rounded-sm" style={{ color: s.color, backgroundColor: `${s.color}15` }}>{s.label}</span>
                    </td>
                    <td className="px-4 py-3 text-gray-500 text-xs">{formatDate(inv.issued_date)}</td>
                    <td className="px-4 py-3">
                      <button onClick={() => handleDownloadInvoicePDF(inv.id, inv.invoice_number)} className="flex items-center gap-1 text-xs text-[#1B3A6B] hover:text-[#122A50] transition-colors">
                        <Download size={12} /> PDF
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

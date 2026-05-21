import React, { useState, useEffect } from 'react';
import { Loader2, FolderOpen, Download, FileText } from 'lucide-react';
import { portalFetch } from '../../utils/authFetch';

const API = process.env.REACT_APP_BACKEND_URL;

const DOC_LABELS = {
  passport: 'Passport / National ID',
  proof_of_address: 'Proof of Address',
  source_of_wealth_doc: 'Source of Wealth',
  corporate_documents: 'Corporate Documents',
  capital_call_notice: 'Capital Call Notice',
  capital_call_report: 'Capital Call Report',
  distribution_notice: 'Distribution Notice',
  fund_report: 'Fund Report',
  im: 'Information Memorandum',
  financials: 'Financials',
  cap_table: 'Cap Table',
  audited_financials: 'Audited Financials',
  fund_factsheet: 'Fund Factsheet',
  quarterly_report: 'Quarterly Report',
  fund_prospectus: 'Fund Prospectus',
  lpa: 'Limited Partnership Agreement',
  scb_license: 'SCB License Certificate',
  aml_policy: 'AML / CFT Policy',
  risk_disclosure: 'Risk Disclosure',
  subscription_agreement: 'Subscription Agreement',
};

const FUND_DOC_TYPES = [
  'audited_financials', 'fund_factsheet', 'quarterly_report', 'fund_prospectus',
  'lpa', 'scb_license', 'aml_policy', 'risk_disclosure', 'subscription_agreement',
];

const FILTER_TABS = [
  { key: 'all', label: 'All' },
  { key: 'fund', label: 'Fund Documents', types: FUND_DOC_TYPES },
  { key: 'kyc', label: 'KYC Documents', types: ['passport', 'proof_of_address', 'source_of_wealth_doc', 'corporate_documents'] },
  { key: 'capital_call', label: 'Capital Calls', types: ['capital_call_notice', 'capital_call_report'] },
  { key: 'distribution_notice', label: 'Distributions', types: ['distribution_notice'] },
];

function formatSize(b) {
  if (!b) return '—';
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}
function fmtDate(d) {
  if (!d) return '—';
  return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function PortalDocuments() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('all');
  const [downloading, setDownloading] = useState('');
  // NDA gate
  const [ndaDoc, setNdaDoc] = useState(null);
  const [ndaConfirmed, setNdaConfirmed] = useState(false);
  const [ndaSubmitting, setNdaSubmitting] = useState(false);

  useEffect(() => {
    Promise.all([
      portalFetch(`${API}/api/portal/documents`).then((r) => {
        if (!r.ok) throw new Error('Failed to load documents');
        return r.json();
      }),
      portalFetch(`${API}/api/portal/fund-documents`).then((r) => {
        if (!r.ok) return [];
        return r.json();
      }),
    ])
      .then(([investorDocs, fundDocs]) => {
        const taggedFund = fundDocs.map((d) => ({ ...d, _isFundDoc: true }));
        setDocs([...taggedFund, ...investorDocs]);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const performDownload = async (doc) => {
    setDownloading(doc.id);
    try {
      const endpoint = doc._isFundDoc
        ? `${API}/api/portal/fund-documents/${doc.id}/download`
        : `${API}/api/portal/documents/${doc.id}/download`;
      const res = await portalFetch(endpoint);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Download failed');
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = doc.file_name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.message);
    } finally {
      setDownloading('');
    }
  };

  const handleDownload = async (doc) => {
    if (doc._isFundDoc && doc.nda_required) {
      setNdaDoc(doc);
      setNdaConfirmed(false);
      setError('');
      return;
    }
    await performDownload(doc);
  };

  const handleNdaConfirm = async () => {
    if (!ndaDoc || !ndaConfirmed) return;
    setNdaSubmitting(true);
    try {
      const res = await portalFetch(
        `${API}/api/portal/fund-documents/${ndaDoc.id}/acknowledge-nda`,
        { method: 'POST' },
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Acknowledgement failed');
      }
      const doc = ndaDoc;
      setNdaDoc(null);
      setNdaConfirmed(false);
      await performDownload(doc);
    } catch (e) {
      setError(e.message);
    } finally {
      setNdaSubmitting(false);
    }
  };

  const activeFilter = FILTER_TABS.find((t) => t.key === activeTab);
  const filtered = activeFilter?.types
    ? docs.filter((d) => activeFilter.types.includes(d.document_type))
    : docs;

  if (loading) return (
    <div className="flex items-center justify-center min-h-[60vh]">
      <div className="flex flex-col items-center gap-3">
        <Loader2 size={24} className="animate-spin text-[#00A8C6]" />
        <p className="text-sm text-[#888880]">Loading documents...</p>
      </div>
    </div>
  );

  return (
    <div className="px-6 md:px-10 py-8 max-w-5xl mx-auto" data-testid="portal-documents">
      {/* Header */}
      <div className="mb-6">
        <p className="text-xs text-[#888880] font-mono uppercase tracking-wider mb-1">Investment Portal</p>
        <h1 className="text-2xl font-semibold text-[#0F0F0E] tracking-tight flex items-center gap-2">
          <FolderOpen size={22} color="#00A8C6" />
          Documents
        </h1>
        <p className="text-sm text-[#888880] mt-1">Secure document data room — {docs.length} file{docs.length !== 1 ? 's' : ''}</p>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-sm text-sm text-red-600">
          {error}
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-1 overflow-x-auto mb-5 pb-0.5" data-testid="doc-filter-tabs">
        {FILTER_TABS.map((tab) => {
          const count = tab.types
            ? docs.filter((d) => tab.types.includes(d.document_type)).length
            : docs.length;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-3 py-1.5 text-xs font-semibold rounded-sm whitespace-nowrap transition-colors border ${
                activeTab === tab.key
                  ? 'border-[#00A8C6] text-white'
                  : 'border-[#E8E6E0] text-[#888880] bg-white hover:border-[#C0C0BC] hover:text-[#0F0F0E]'
              }`}
              style={activeTab === tab.key ? { backgroundColor: '#00A8C6' } : {}}
              data-testid={`tab-${tab.key}`}
            >
              {tab.label} ({count})
            </button>
          );
        })}
      </div>

      <div className="bg-white border border-[#E8E6E0] rounded-sm shadow-sm overflow-hidden">
        {filtered.length === 0 ? (
          <div className="py-16 text-center px-6">
            <FolderOpen size={28} className="mx-auto mb-3 text-[#D1D5DB]" />
            <p className="text-sm text-[#888880]">
              {docs.length === 0
                ? "No documents available yet. Documents will appear here as your onboarding progresses."
                : "No documents in this category."}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[#E8E6E0] bg-[#FAFAF8]">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Document</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider hidden sm:table-cell">Type</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider hidden md:table-cell">Date</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider hidden md:table-cell">Size</th>
                  <th className="text-right px-5 py-3 text-xs font-semibold text-[#888880] uppercase tracking-wider">Download</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#F3F4F6]">
                {filtered.map((doc) => (
                  <tr key={doc.id} className="hover:bg-[#FAFAF8] transition-colors" data-testid={`doc-row-${doc.id}`}>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 bg-[#F3F4F6] rounded-sm flex items-center justify-center flex-shrink-0">
                          <FileText size={15} color="#888880" />
                        </div>
                        <div className="flex items-center gap-2 min-w-0">
                          <p className="text-sm font-medium text-[#0F0F0E] truncate max-w-[200px]">{doc.file_name}</p>
                          {doc.nda_required && (
                            <span
                              className="inline-flex items-center px-1.5 py-0.5 rounded-sm text-[10px] font-mono font-bold uppercase tracking-wider"
                              style={{ color: '#B45309', backgroundColor: '#FEF3C7', border: '1px solid #FCD34D' }}
                              title="NDA acknowledgement required"
                              data-testid={`nda-badge-${doc.id}`}
                            >
                              NDA
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3.5 hidden sm:table-cell">
                      <span className="text-xs text-[#888880]">{DOC_LABELS[doc.document_type] || doc.document_type?.replace(/_/g, ' ')}</span>
                    </td>
                    <td className="px-5 py-3.5 text-xs font-mono text-[#888880] hidden md:table-cell">{fmtDate(doc.uploaded_at)}</td>
                    <td className="px-5 py-3.5 text-xs font-mono text-[#888880] hidden md:table-cell">{formatSize(doc.file_size)}</td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => handleDownload(doc)}
                        disabled={downloading === doc.id}
                        data-testid={`download-doc-${doc.id}`}
                        className="inline-flex items-center gap-1.5 text-xs font-semibold border px-3 py-1.5 rounded-sm transition-colors disabled:opacity-50"
                        style={{ color: '#00A8C6', borderColor: '#00A8C620' }}
                        onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#00A8C610'; }}
                        onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
                      >
                        {downloading === doc.id ? (
                          <Loader2 size={13} className="animate-spin" />
                        ) : (
                          <Download size={13} />
                        )}
                        Download
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── NDA Acknowledgement Modal ──────────────────────────────────────── */}
      {ndaDoc && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-4"
          data-testid="nda-modal"
          onClick={(e) => {
            if (e.target === e.currentTarget && !ndaSubmitting) setNdaDoc(null);
          }}
        >
          <div className="bg-white rounded-sm shadow-xl max-w-lg w-full overflow-hidden">
            <div className="px-6 py-4 border-b border-[#E8E6E0] bg-[#FAFAF8]">
              <h2 className="text-base font-semibold text-[#0F0F0E]">
                Professional Investor & Confidentiality Acknowledgement
              </h2>
              <p className="text-xs text-[#888880] mt-1">
                Required before downloading <span className="font-mono">{ndaDoc.title}</span>
              </p>
            </div>
            <div className="px-6 py-5 space-y-4">
              <p className="text-sm text-[#374151] leading-relaxed">
                The document you are about to download is a confidential
                offering document of <strong>Zephyr Caribbean Growth Fund I</strong>,
                a Bahamas-incorporated Professional Fund licensed by the
                Securities Commission of The Bahamas (SCB-2024-PE-0042) under
                the Investment Funds Act 2019.
              </p>
              <p className="text-sm text-[#374151] leading-relaxed">
                By proceeding, you acknowledge and agree that:
              </p>
              <ul className="text-sm text-[#374151] space-y-1.5 list-disc pl-5">
                <li>You qualify as a Professional or Accredited Investor under SCB regulations.</li>
                <li>The document is provided in confidence and may not be copied, distributed or disclosed to any third party.</li>
                <li>The contents do not constitute an offer to sell securities — only the executed Subscription Agreement creates a binding investment.</li>
                <li>You will return or destroy the document on request by the Fund Manager.</li>
              </ul>
              <label className="flex items-start gap-2.5 mt-3 cursor-pointer" data-testid="nda-confirm-checkbox-label">
                <input
                  type="checkbox"
                  checked={ndaConfirmed}
                  onChange={(e) => setNdaConfirmed(e.target.checked)}
                  className="mt-0.5 h-4 w-4 accent-[#00A8C6] cursor-pointer"
                  data-testid="nda-confirm-checkbox"
                />
                <span className="text-sm text-[#0F0F0E] leading-snug">
                  I confirm I am a Professional / Accredited Investor and accept the confidentiality terms above.
                </span>
              </label>
            </div>
            <div className="px-6 py-4 border-t border-[#E8E6E0] bg-[#FAFAF8] flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={() => setNdaDoc(null)}
                disabled={ndaSubmitting}
                data-testid="nda-cancel-btn"
                className="px-4 py-2 text-sm font-semibold text-[#374151] border border-[#E8E6E0] rounded-sm hover:bg-white transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleNdaConfirm}
                disabled={!ndaConfirmed || ndaSubmitting}
                data-testid="nda-accept-btn"
                className="px-4 py-2 text-sm font-semibold text-white rounded-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                style={{ backgroundColor: '#00A8C6' }}
              >
                {ndaSubmitting ? (
                  <><Loader2 size={13} className="animate-spin" /> Verifying…</>
                ) : (
                  'Accept & Download'
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

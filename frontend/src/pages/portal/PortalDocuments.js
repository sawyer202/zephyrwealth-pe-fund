import React, { useState, useEffect } from 'react';
import { Loader2, FolderOpen, Download, FileText } from 'lucide-react';

const API = process.env.REACT_APP_BACKEND_URL;

const DOC_LABELS = {
  passport: 'Passport / National ID',
  proof_of_address: 'Proof of Address',
  source_of_wealth_doc: 'Source of Wealth',
  corporate_documents: 'Corporate Documents',
  capital_call_notice: 'Capital Call Notice',
  distribution_notice: 'Distribution Notice',
  fund_report: 'Fund Report',
  im: 'Information Memorandum',
  financials: 'Financials',
  cap_table: 'Cap Table',
};

const FILTER_TABS = [
  { key: 'all', label: 'All' },
  { key: 'kyc', label: 'KYC Documents', types: ['passport', 'proof_of_address', 'source_of_wealth_doc', 'corporate_documents'] },
  { key: 'capital_call_notice', label: 'Capital Call Notices', types: ['capital_call_notice'] },
  { key: 'distribution_notice', label: 'Distribution Notices', types: ['distribution_notice'] },
  { key: 'fund_report', label: 'Fund Reports', types: ['fund_report'] },
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

  useEffect(() => {
    fetch(`${API}/api/portal/documents`, { credentials: 'include' })
      .then((r) => {
        if (!r.ok) throw new Error('Failed to load documents');
        return r.json();
      })
      .then(setDocs)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async (doc) => {
    setDownloading(doc.id);
    try {
      const res = await fetch(`${API}/api/portal/documents/${doc.id}/download`, { credentials: 'include' });
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
                        <p className="text-sm font-medium text-[#0F0F0E] truncate max-w-[200px]">{doc.file_name}</p>
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
    </div>
  );
}

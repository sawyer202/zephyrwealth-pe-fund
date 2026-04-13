import React, { useState } from 'react';
import { User, Building2, Eye, EyeOff, Loader2, CheckCircle2, X, KeyRound } from 'lucide-react';
import { toast } from 'sonner';
import { useInvestorAuth } from '../../context/InvestorAuthContext';

const API = process.env.REACT_APP_BACKEND_URL;

function InfoRow({ label, value }) {
  return (
    <div className="flex items-start justify-between py-3 border-b border-[#F3F4F6] last:border-0">
      <span className="text-xs text-[#888880] uppercase tracking-wider font-semibold w-36 flex-shrink-0">{label}</span>
      <span className="text-sm text-[#0F0F0E] text-right">{value || '—'}</span>
    </div>
  );
}

function ChangePasswordModal({ onClose }) {
  const { changePassword } = useInvestorAuth();
  const [current, setCurrent] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const validate = () => {
    if (newPwd.length < 8) return 'Password must be at least 8 characters.';
    if (!/[A-Z]/.test(newPwd)) return 'Password must contain at least one uppercase letter.';
    if (!/[0-9]/.test(newPwd)) return 'Password must contain at least one number.';
    if (newPwd !== confirm) return 'Passwords do not match.';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const err = validate();
    if (err) { setError(err); return; }
    setLoading(true);
    try {
      await changePassword(current, newPwd);
      toast.success('Password updated successfully');
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4" data-testid="change-pwd-modal">
      <div className="bg-white rounded-sm shadow-xl w-full max-w-md">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#E8E6E0]">
          <div className="flex items-center gap-2">
            <KeyRound size={16} color="#00A8C6" />
            <h2 className="text-base font-semibold text-[#0F0F0E]">Change Password</h2>
          </div>
          <button onClick={onClose} className="text-[#888880] hover:text-[#0F0F0E] transition-colors">
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          {[
            { label: 'Current Password', val: current, set: setCurrent, show: showCurrent, toggle: () => setShowCurrent((v) => !v), id: 'current-pwd' },
            { label: 'New Password', val: newPwd, set: setNewPwd, show: showNew, toggle: () => setShowNew((v) => !v), id: 'new-pwd' },
            { label: 'Confirm New Password', val: confirm, set: setConfirm, show: showNew, toggle: () => {}, id: 'confirm-pwd' },
          ].map(({ label, val, set, show, toggle, id }) => (
            <div key={id}>
              <label className="block text-xs font-semibold text-[#888880] uppercase tracking-wider mb-1.5">{label}</label>
              <div className="relative">
                <input
                  type={show ? 'text' : 'password'}
                  value={val}
                  onChange={(e) => set(e.target.value)}
                  required
                  data-testid={id}
                  className="w-full px-3.5 py-2.5 pr-10 text-sm border border-[#E8E6E0] rounded-sm outline-none focus:border-[#00A8C6] focus:ring-1 focus:ring-[#00A8C6]/20 transition-colors"
                />
                {(id === 'current-pwd' || id === 'new-pwd') && (
                  <button type="button" onClick={toggle} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#888880]">
                    {show ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                )}
              </div>
            </div>
          ))}

          <div className="p-3 bg-[#FAFAF8] border border-[#E8E6E0] rounded-sm">
            <p className="text-xs text-[#888880] font-semibold mb-2">Requirements:</p>
            {[
              { label: '8+ characters', ok: newPwd.length >= 8 },
              { label: 'One uppercase letter', ok: /[A-Z]/.test(newPwd) },
              { label: 'One number', ok: /[0-9]/.test(newPwd) },
            ].map(({ label, ok }) => (
              <div key={label} className="flex items-center gap-1.5 mb-1">
                <CheckCircle2 size={12} color={ok ? '#22C55E' : '#D1D5DB'} />
                <span className="text-xs" style={{ color: ok ? '#15803D' : '#888880' }}>{label}</span>
              </div>
            ))}
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-sm text-sm text-red-600" data-testid="profile-pwd-error">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm text-[#888880] bg-white border border-[#E8E6E0] rounded-sm hover:bg-[#FAFAF8] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              data-testid="change-pwd-confirm"
              className="flex items-center gap-2 px-4 py-2 text-sm font-semibold text-white rounded-sm transition-colors disabled:opacity-60"
              style={{ backgroundColor: '#00A8C6' }}
            >
              {loading ? <Loader2 size={14} className="animate-spin" /> : null}
              Update Password
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function PortalProfile() {
  const { investor } = useInvestorAuth();
  const [showChangeModal, setShowChangeModal] = useState(false);
  const [profileData, setProfileData] = useState(null);

  React.useEffect(() => {
    fetch(`${API}/api/portal/profile`, { credentials: 'include' })
      .then((r) => r.ok ? r.json() : null)
      .then(setProfileData)
      .catch(() => {});
  }, []);

  const data = profileData || {};
  const isCorporate = data.entity_type === 'corporate';

  return (
    <div className="px-6 md:px-10 py-8 max-w-3xl mx-auto" data-testid="portal-profile">
      {/* Header */}
      <div className="mb-8">
        <p className="text-xs text-[#888880] font-mono uppercase tracking-wider mb-1">Investment Portal</p>
        <h1 className="text-2xl font-semibold text-[#0F0F0E] tracking-tight flex items-center gap-2">
          <User size={22} color="#00A8C6" />
          Profile
        </h1>
      </div>

      <div className="bg-white border border-[#E8E6E0] rounded-sm shadow-sm">
        <div className="border-b border-[#E8E6E0] px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {isCorporate ? <Building2 size={16} color="#00A8C6" /> : <User size={16} color="#00A8C6" />}
            <span className="text-xs font-semibold text-[#888880] uppercase tracking-wider">Investor Information</span>
          </div>
          <button
            onClick={() => setShowChangeModal(true)}
            data-testid="change-password-btn"
            className="flex items-center gap-1.5 text-xs font-semibold border px-3 py-1.5 rounded-sm transition-colors"
            style={{ color: '#00A8C6', borderColor: '#00A8C640' }}
            onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#00A8C610'; }}
            onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = 'transparent'; }}
          >
            <KeyRound size={12} /> Change Password
          </button>
        </div>

        <div className="px-5 py-2">
          <InfoRow label="Legal Name" value={data.legal_name} />
          <InfoRow label="Email" value={data.email || investor?.email} />
          <InfoRow label="Entity Type" value={data.entity_type ? (data.entity_type.charAt(0).toUpperCase() + data.entity_type.slice(1)) : '—'} />
          <InfoRow label="Share Class" value={data.share_class ? `Class ${data.share_class}` : '—'} />
          <InfoRow label="Nationality" value={data.nationality} />
          <InfoRow label="KYC Status" value={data.kyc_status ? (data.kyc_status.charAt(0).toUpperCase() + data.kyc_status.slice(1)) : '—'} />
        </div>

        <div className="border-t border-[#E8E6E0] px-5 py-4 bg-[#FAFAF8]">
          <p className="text-xs text-[#888880]">
            Your profile information is managed by Zephyr Asset Management Ltd. To update your details, please contact{' '}
            <span className="text-[#0F0F0E]">compliance@zephyrwealth.ai</span>.
          </p>
        </div>
      </div>

      {showChangeModal && <ChangePasswordModal onClose={() => setShowChangeModal(false)} />}
    </div>
  );
}

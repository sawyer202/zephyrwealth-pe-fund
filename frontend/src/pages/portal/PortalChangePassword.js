import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Eye, EyeOff, KeyRound, CheckCircle2 } from 'lucide-react';
import { useInvestorAuth } from '../../context/InvestorAuthContext';

export default function PortalChangePassword() {
  const navigate = useNavigate();
  const { changePassword, investor } = useInvestorAuth();

  const [current, setCurrent] = useState('');
  const [newPwd, setNewPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const validate = () => {
    if (newPwd.length < 8) return 'Password must be at least 8 characters.';
    if (!/[A-Z]/.test(newPwd)) return 'Password must contain at least one uppercase letter.';
    if (!/[0-9]/.test(newPwd)) return 'Password must contain at least one number.';
    if (newPwd !== confirm) return 'New passwords do not match.';
    return null;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const validationError = validate();
    if (validationError) { setError(validationError); return; }
    setLoading(true);
    try {
      await changePassword(current, newPwd);
      navigate('/portal/dashboard', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FAFAF8] flex flex-col items-center justify-center px-4 py-12" data-testid="change-password-page">
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="text-2xl font-medium tracking-tight" style={{ fontFamily: 'Inter, sans-serif' }}>
          <span className="text-[#0F0F0E]">Zephyr</span>
          <span style={{ color: '#00A8C6' }}>Wealth</span>
          <span className="text-[#888880] text-sm font-light ml-1">.ai</span>
        </div>
      </div>

      <div className="bg-white border border-[#E8E6E0] rounded-sm shadow-sm w-full max-w-[420px] p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-sm bg-[#00A8C6]/10 flex items-center justify-center flex-shrink-0">
            <KeyRound size={18} color="#00A8C6" />
          </div>
          <div>
            <h1 className="text-lg font-semibold text-[#0F0F0E]">Set Your Password</h1>
            <p className="text-xs text-[#888880] mt-0.5">
              {investor?.first_login
                ? 'Welcome! Please create a secure password to continue.'
                : 'Update your portal password below.'}
            </p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-[#888880] uppercase tracking-wider mb-1.5">
              Current / Temporary Password
            </label>
            <div className="relative">
              <input
                type={showCurrent ? 'text' : 'password'}
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                required
                placeholder="Enter current password"
                data-testid="current-password-input"
                className="w-full px-3.5 py-2.5 pr-10 text-sm text-[#0F0F0E] border border-[#E8E6E0] rounded-sm bg-white outline-none focus:border-[#00A8C6] focus:ring-1 focus:ring-[#00A8C6]/20 transition-colors"
              />
              <button type="button" onClick={() => setShowCurrent((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#888880]">
                {showCurrent ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#888880] uppercase tracking-wider mb-1.5">
              New Password
            </label>
            <div className="relative">
              <input
                type={showNew ? 'text' : 'password'}
                value={newPwd}
                onChange={(e) => setNewPwd(e.target.value)}
                required
                placeholder="Create new password"
                data-testid="new-password-input"
                className="w-full px-3.5 py-2.5 pr-10 text-sm text-[#0F0F0E] border border-[#E8E6E0] rounded-sm bg-white outline-none focus:border-[#00A8C6] focus:ring-1 focus:ring-[#00A8C6]/20 transition-colors"
              />
              <button type="button" onClick={() => setShowNew((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#888880]">
                {showNew ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-[#888880] uppercase tracking-wider mb-1.5">
              Confirm New Password
            </label>
            <div className="relative">
              <input
                type={showConfirm ? 'text' : 'password'}
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                required
                placeholder="Repeat new password"
                data-testid="confirm-password-input"
                className="w-full px-3.5 py-2.5 pr-10 text-sm text-[#0F0F0E] border border-[#E8E6E0] rounded-sm bg-white outline-none focus:border-[#00A8C6] focus:ring-1 focus:ring-[#00A8C6]/20 transition-colors"
              />
              <button type="button" onClick={() => setShowConfirm((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#888880]">
                {showConfirm ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </div>

          {/* Requirements */}
          <div className="p-3 bg-[#FAFAF8] border border-[#E8E6E0] rounded-sm">
            <p className="text-xs text-[#888880]">
              Requirements: minimum 8 characters, at least one uppercase letter and one number.
            </p>
            <div className="mt-2 space-y-1">
              {[
                { label: '8+ characters', ok: newPwd.length >= 8 },
                { label: 'Uppercase letter', ok: /[A-Z]/.test(newPwd) },
                { label: 'Number', ok: /[0-9]/.test(newPwd) },
                { label: 'Passwords match', ok: newPwd.length > 0 && newPwd === confirm },
              ].map(({ label, ok }) => (
                <div key={label} className="flex items-center gap-1.5">
                  <CheckCircle2 size={12} color={ok ? '#22C55E' : '#D1D5DB'} />
                  <span className="text-xs" style={{ color: ok ? '#15803D' : '#888880' }}>{label}</span>
                </div>
              ))}
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-sm text-sm text-red-600" data-testid="change-pwd-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            data-testid="change-pwd-submit"
            className="w-full py-2.5 text-sm font-semibold text-white rounded-sm transition-all disabled:opacity-60 flex items-center justify-center gap-2"
            style={{ backgroundColor: '#00A8C6' }}
          >
            {loading ? (
              <><Loader2 size={15} className="animate-spin" /> Updating...</>
            ) : (
              'Set New Password'
            )}
          </button>
        </form>
      </div>

      <p className="text-xs text-[#888880] text-center mt-6">
        Zephyr Asset Management Ltd · SCB Licensed Fund SCB-2024-PE-0042
      </p>
    </div>
  );
}

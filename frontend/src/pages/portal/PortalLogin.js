import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import { useInvestorAuth } from '../../context/InvestorAuthContext';

export default function PortalLogin() {
  const navigate = useNavigate();
  const { login } = useInvestorAuth();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPwd, setShowPwd] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await login(email.trim(), password);
      if (data.first_login) {
        navigate('/portal/change-password', { replace: true });
      } else {
        navigate('/portal/dashboard', { replace: true });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col md:flex-row" data-testid="portal-login-page">
      {/* ── Left panel ── */}
      <div className="bg-[#111110] md:w-[45%] flex flex-col justify-between px-10 py-8 md:py-0 md:px-16 md:justify-center relative overflow-hidden">
        {/* Subtle texture overlay */}
        <div className="absolute inset-0 opacity-[0.03]"
          style={{ backgroundImage: 'radial-gradient(circle at 25% 25%, #ffffff 1px, transparent 1px)', backgroundSize: '32px 32px' }}
        />

        <div className="relative z-10">
          {/* Logo */}
          <div className="mb-8">
            <div className="text-[28px] font-medium tracking-tight leading-none" style={{ fontFamily: 'Inter, sans-serif' }}>
              <span className="text-white">Zephyr</span>
              <span style={{ color: '#00A8C6' }}>Wealth</span>
              <span className="text-white text-sm font-light ml-2 opacity-60">.ai</span>
            </div>
          </div>

          {/* Tagline */}
          <p className="text-[#5A5A56] text-base font-normal mt-2 leading-relaxed">
            Your investment, at a glance.
          </p>

          {/* Fund name */}
          <p className="text-[#3A3A38] text-sm font-mono mt-3 tracking-wide">
            Zephyr Caribbean Growth Fund I
          </p>

          {/* Divider */}
          <div className="w-12 h-px bg-[#2A2A28] mt-8" />

          {/* Bottom note */}
          <p className="text-[#3A3A38] text-xs mt-8 leading-relaxed max-w-xs">
            Secure investor access portal. All data is encrypted in transit and at rest.
          </p>
        </div>

        {/* Mobile: bottom spacer */}
        <div className="md:hidden h-2" />
      </div>

      {/* ── Right panel ── */}
      <div className="flex-1 bg-white flex flex-col justify-center items-center px-8 py-12 md:py-0">
        <div className="w-full max-w-[380px]">
          {/* Mobile logo */}
          <div className="md:hidden text-center mb-8">
            <div className="text-2xl font-medium" style={{ fontFamily: 'Inter, sans-serif' }}>
              <span className="text-[#0F0F0E]">Zephyr</span>
              <span style={{ color: '#00A8C6' }}>Wealth</span>
              <span className="text-[#888880] text-sm font-light ml-1">.ai</span>
            </div>
          </div>

          <h1 className="text-2xl font-semibold text-[#0F0F0E] mb-1 tracking-tight">
            Investor Sign In
          </h1>
          <p className="text-sm text-[#888880] mb-8">
            Access your fund portal
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-xs font-semibold text-[#888880] uppercase tracking-wider mb-1.5">
                Email Address
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoFocus
                placeholder="you@example.com"
                data-testid="portal-email-input"
                className="w-full px-3.5 py-2.5 text-sm text-[#0F0F0E] border border-[#E8E6E0] rounded-sm bg-white placeholder:text-[#C0C0BC] outline-none focus:border-[#00A8C6] focus:ring-1 focus:ring-[#00A8C6]/20 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#888880] uppercase tracking-wider mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="Enter your password"
                  data-testid="portal-password-input"
                  className="w-full px-3.5 py-2.5 pr-10 text-sm text-[#0F0F0E] border border-[#E8E6E0] rounded-sm bg-white placeholder:text-[#C0C0BC] outline-none focus:border-[#00A8C6] focus:ring-1 focus:ring-[#00A8C6]/20 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPwd((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-[#888880] hover:text-[#0F0F0E] transition-colors"
                >
                  {showPwd ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div
                className="p-3 bg-red-50 border border-red-200 rounded-sm text-sm text-red-600"
                data-testid="portal-login-error"
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              data-testid="portal-signin-btn"
              className="w-full py-2.5 text-sm font-semibold text-white rounded-sm transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              style={{ backgroundColor: '#00A8C6' }}
              onMouseEnter={(e) => !loading && (e.currentTarget.style.backgroundColor = '#0096B3')}
              onMouseLeave={(e) => !loading && (e.currentTarget.style.backgroundColor = '#00A8C6')}
            >
              {loading ? (
                <><Loader2 size={15} className="animate-spin" /> Signing in...</>
              ) : (
                'Sign In'
              )}
            </button>
          </form>

          <p className="text-xs text-[#888880] text-center mt-8 leading-relaxed">
            Having trouble accessing your account? Contact{' '}
            <span className="text-[#0F0F0E]">compliance@zephyrwealth.ai</span>
          </p>
        </div>
      </div>
    </div>
  );
}

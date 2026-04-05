import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Eye, EyeOff, AlertCircle, Shield } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const HINT_ACCOUNTS = [
  { role: 'Compliance', email: 'compliance@zephyrwealth.ai', password: 'Comply1234!' },
  { role: 'Risk', email: 'risk@zephyrwealth.ai', password: 'Risk1234!' },
  { role: 'Manager', email: 'manager@zephyrwealth.ai', password: 'Manager1234!' },
];

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const fillAccount = (account) => {
    setEmail(account.email);
    setPassword(account.password);
    setError('');
  };

  return (
    <div className="min-h-screen relative flex items-center justify-center">
      {/* Bahamas aerial background */}
      <div
        className="absolute inset-0 bg-cover bg-center"
        style={{
          backgroundImage: `url('https://images.unsplash.com/photo-1720044332118-3c4741abb0de?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NTYxODh8MHwxfHNlYXJjaHwxfHxiYWhhbWFzJTIwYWVyaWFsJTIwb2NlYW58ZW58MHx8fHwxNzc1MzU1OTYwfDA&ixlib=rb-4.1.0&q=85')`,
        }}
      />
      <div className="absolute inset-0 bg-black/70" />

      {/* Login card */}
      <div className="relative z-10 w-full max-w-md mx-4 animate-fade-in">
        <div className="bg-white rounded-sm shadow-2xl overflow-hidden">
          {/* Header bar */}
          <div className="bg-[#252523] px-8 py-6">
            <div className="flex items-center gap-2.5 mb-1">
              <Shield size={22} color="#00A8C6" strokeWidth={1.5} />
              <span className="text-2xl font-bold font-heading tracking-tight">
                <span className="text-white">Zephyr</span>
                <span style={{ color: '#00A8C6' }}>Wealth</span>
              </span>
            </div>
            <p className="text-xs text-gray-500 ml-8">
              Private Equity Back-Office Platform
            </p>
          </div>

          {/* Form */}
          <div className="px-8 py-7">
            <p className="text-sm font-semibold text-[#1F2937] mb-5">
              Sign in to your account
            </p>

            {error && (
              <div
                className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-sm text-sm text-red-700 mb-4"
                data-testid="login-error"
              >
                <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1.5">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@zephyrwealth.ai"
                  required
                  autoComplete="email"
                  className="w-full bg-white border border-[#D1D5DB] rounded-sm px-3 py-2.5 text-sm text-[#1F2937] focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] focus:border-[#1B3A6B] placeholder:text-[#9CA3AF]"
                  data-testid="login-email-input"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-[#374151] mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    autoComplete="current-password"
                    className="w-full bg-white border border-[#D1D5DB] rounded-sm px-3 py-2.5 pr-10 text-sm text-[#1F2937] focus:outline-none focus:ring-1 focus:ring-[#1B3A6B] focus:border-[#1B3A6B] placeholder:text-[#9CA3AF]"
                    data-testid="login-password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    data-testid="toggle-password-visibility"
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#1B3A6B] text-white rounded-sm py-2.5 text-sm font-semibold hover:bg-[#122A50] transition-colors focus:outline-none focus:ring-2 focus:ring-[#1B3A6B]/40 disabled:opacity-50 disabled:cursor-not-allowed mt-1"
                data-testid="login-submit-button"
              >
                {loading ? 'Authenticating...' : 'Sign In to Platform'}
              </button>
            </form>

            {/* Quick access hints for demo */}
            <div className="mt-6 pt-5 border-t border-gray-100">
              <p className="text-overline mb-3 text-gray-400">
                Demo accounts
              </p>
              <div className="grid grid-cols-3 gap-2">
                {HINT_ACCOUNTS.map((a) => (
                  <button
                    key={a.role}
                    onClick={() => fillAccount(a)}
                    data-testid={`demo-account-${a.role.toLowerCase()}`}
                    className="text-xs py-1.5 px-2 border border-[#E5E7EB] rounded-sm text-[#6B7280] hover:border-[#1B3A6B] hover:text-[#1B3A6B] transition-colors"
                  >
                    {a.role}
                  </button>
                ))}
              </div>
            </div>

            <p className="text-xs text-center text-gray-400 mt-4">
              Authorized personnel only. All activity is logged.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

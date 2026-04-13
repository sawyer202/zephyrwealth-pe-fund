import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LogOut, Menu, X, LayoutDashboard, TrendingUp, Bell, FolderOpen, User } from 'lucide-react';
import { useInvestorAuth } from '../../context/InvestorAuthContext';

const NAV_ITEMS = [
  { to: '/portal/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/portal/investment', label: 'My Investment', icon: TrendingUp },
  { to: '/portal/capital-calls', label: 'Capital Calls', icon: Bell },
  { to: '/portal/documents', label: 'Documents', icon: FolderOpen },
  { to: '/portal/profile', label: 'Profile', icon: User },
];

export default function PortalLayout() {
  const { investor, logout } = useInvestorAuth();
  const navigate = useNavigate();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/portal/login', { replace: true });
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#FAFAF8]">
      {/* ── Top Nav ── */}
      <nav
        className="w-full flex items-center justify-between px-5 md:px-8 flex-shrink-0 z-30 relative"
        style={{ backgroundColor: '#111110', height: '56px' }}
        data-testid="portal-nav"
      >
        {/* Logo */}
        <div className="flex items-center gap-6">
          <div className="text-[20px] font-medium tracking-tight" style={{ fontFamily: 'Inter, sans-serif' }}>
            <span className="text-white">Zephyr</span>
            <span style={{ color: '#00A8C6' }}>Wealth</span>
          </div>

          {/* Desktop nav items */}
          <div className="hidden md:flex items-center gap-1">
            {NAV_ITEMS.map(({ to, label }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `px-3 py-1.5 text-sm font-medium transition-colors relative group ${
                    isActive ? 'text-white' : 'text-[#5A5A56] hover:text-[#C0C0BC]'
                  }`
                }
                data-testid={`nav-${label.toLowerCase().replace(/ /g, '-')}`}
              >
                {({ isActive }) => (
                  <>
                    {label}
                    {isActive && (
                      <span
                        className="absolute bottom-0 left-3 right-3 h-0.5 rounded-t-full"
                        style={{ backgroundColor: '#00A8C6' }}
                      />
                    )}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        </div>

        {/* Right: user + logout */}
        <div className="flex items-center gap-4">
          <span className="hidden sm:block text-xs text-[#5A5A56] font-mono truncate max-w-[180px]">
            {investor?.name || investor?.email || ''}
          </span>
          <button
            onClick={handleLogout}
            data-testid="portal-logout-btn"
            className="hidden md:flex items-center gap-1.5 text-xs text-[#5A5A56] hover:text-white border border-[#2A2A28] hover:border-[#3A3A38] px-3 py-1.5 rounded-sm transition-colors"
          >
            <LogOut size={13} /> Logout
          </button>

          {/* Mobile hamburger */}
          <button
            className="md:hidden text-[#5A5A56] hover:text-white transition-colors"
            onClick={() => setMenuOpen((v) => !v)}
            data-testid="portal-hamburger"
          >
            {menuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </nav>

      {/* Mobile dropdown menu */}
      {menuOpen && (
        <div
          className="md:hidden absolute top-14 left-0 right-0 z-40 border-b border-[#2A2A28] py-2 shadow-lg"
          style={{ backgroundColor: '#111110' }}
          data-testid="portal-mobile-menu"
        >
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                `flex items-center gap-3 px-6 py-3 text-sm font-medium transition-colors ${
                  isActive ? 'text-white border-l-2 border-[#00A8C6] bg-[#1A1A18]' : 'text-[#5A5A56] hover:text-white'
                }`
              }
            >
              <Icon size={16} /> {label}
            </NavLink>
          ))}
          <button
            onClick={() => { setMenuOpen(false); handleLogout(); }}
            className="flex items-center gap-3 px-6 py-3 text-sm text-[#5A5A56] hover:text-white w-full transition-colors border-t border-[#2A2A28] mt-1"
          >
            <LogOut size={16} /> Logout
          </button>
        </div>
      )}

      {/* ── Page Content ── */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>

      {/* ── Footer ── */}
      <footer className="py-4 text-center" data-testid="portal-footer">
        <p className="text-xs text-[#888880]">
          Zephyr Asset Management Ltd &nbsp;|&nbsp; SCB Licensed Fund SCB-2024-PE-0042 &nbsp;|&nbsp; Confidential
        </p>
      </footer>
    </div>
  );
}

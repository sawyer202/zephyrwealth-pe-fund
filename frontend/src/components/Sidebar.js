import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Users,
  TrendingUp,
  Briefcase,
  FileText,
  Settings,
  LogOut,
  Shield,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/investors', icon: Users, label: 'Investors' },
  { path: '/deals', icon: TrendingUp, label: 'Deals' },
  { path: '/portfolio', icon: Briefcase, label: 'Portfolio' },
  { path: '/reports', icon: FileText, label: 'Reports' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

const roleColors = {
  compliance: '#10B981',
  risk: '#F59E0B',
  manager: '#00A8C6',
};

const roleLabels = {
  compliance: 'Compliance',
  risk: 'Risk Officer',
  manager: 'Fund Manager',
};

export default function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuth();

  return (
    <div
      className="w-64 flex-shrink-0 flex flex-col h-screen sticky top-0"
      style={{ backgroundColor: '#252523', borderRight: '1px solid #333333' }}
      data-testid="sidebar"
    >
      {/* Logo */}
      <div className="px-6 py-6 border-b border-[#333333]">
        <div className="flex items-center gap-2 mb-1">
          <Shield size={20} color="#00A8C6" strokeWidth={1.5} />
          <span className="text-xl font-bold font-heading tracking-tight">
            <span className="text-white">Zephyr</span>
            <span style={{ color: '#00A8C6' }}>Wealth</span>
          </span>
        </div>
        <p className="text-xs text-gray-500 ml-7">Private Equity Platform</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 overflow-y-auto">
        <p className="text-overline px-6 mb-3 text-gray-600">Navigation</p>
        {navItems.map(({ path, icon: Icon, label }) => {
          const isActive = location.pathname === path || location.pathname.startsWith(path + '/');
          return (
            <Link
              key={path}
              to={path}
              data-testid={`sidebar-nav-${label.toLowerCase()}`}
              className={`flex items-center gap-3 px-6 py-2.5 text-sm font-medium transition-all duration-150 ${
                isActive
                  ? 'text-white bg-[#1B3A6B] border-r-2 border-[#C9A84C]'
                  : 'text-gray-400 hover:text-white hover:bg-[#333333]'
              }`}
            >
              <Icon
                size={17}
                strokeWidth={1.5}
                color={isActive ? '#C9A84C' : undefined}
              />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* User Info */}
      <div className="p-4 border-t border-[#333333]">
        <div className="flex items-start gap-3 mb-3">
          <div
            className="w-8 h-8 rounded-sm flex items-center justify-center flex-shrink-0 text-xs font-bold text-white"
            style={{ backgroundColor: roleColors[user?.role] || '#6B7280' }}
          >
            {user?.name?.charAt(0) || '?'}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-white truncate">{user?.name}</p>
            <p
              className="text-xs font-mono"
              style={{ color: roleColors[user?.role] || '#9CA3AF' }}
            >
              {roleLabels[user?.role] || user?.role}
            </p>
          </div>
        </div>
        <button
          onClick={logout}
          data-testid="logout-button"
          className="flex items-center gap-2 w-full text-xs text-gray-500 hover:text-gray-200 transition-colors py-1"
        >
          <LogOut size={13} strokeWidth={1.5} />
          Sign out
        </button>
      </div>
    </div>
  );
}

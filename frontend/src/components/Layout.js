import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import Sidebar from './Sidebar';
import { useAuth } from '../context/AuthContext';

export default function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user } = useAuth();

  return (
    <div className="flex min-h-screen bg-[#FAFAF8] font-sans">
      {/* Mobile backdrop */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setSidebarOpen(false)}
          data-testid="sidebar-backdrop"
        />
      )}

      {/* Sidebar wrapper */}
      <div
        className={`fixed md:sticky top-0 left-0 z-50 md:z-auto h-screen flex-shrink-0 transition-transform duration-200 ease-in-out ${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <Sidebar onClose={() => setSidebarOpen(false)} />
      </div>

      {/* Main content */}
      <main className="flex-1 overflow-auto min-h-screen animate-fade-in">
        {/* Mobile top bar */}
        <div className="md:hidden sticky top-0 z-30 flex items-center gap-3 px-4 py-3 bg-[#FAFAF8] border-b border-[#E5E7EB]">
          <button
            onClick={() => setSidebarOpen(true)}
            data-testid="hamburger-btn"
            className="p-1.5 text-[#374151] hover:text-[#1B3A6B] transition-colors rounded-sm"
            aria-label="Open navigation"
          >
            <Menu size={20} />
          </button>
          <div className="flex items-center gap-1.5">
            <span className="text-sm font-bold font-heading">
              <span className="text-[#1F2937]">Zephyr</span>
              <span style={{ color: '#00A8C6' }}>Wealth</span>
            </span>
          </div>
          {user && (
            <span className="ml-auto text-xs text-[#9CA3AF] font-mono capitalize">{user.role}</span>
          )}
        </div>
        <Outlet />
      </main>
    </div>
  );
}

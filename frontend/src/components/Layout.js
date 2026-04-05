import React from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';

export default function Layout() {
  return (
    <div className="flex min-h-screen bg-[#FAFAF8] font-sans">
      <Sidebar />
      <main className="flex-1 overflow-auto min-h-screen animate-fade-in">
        <Outlet />
      </main>
    </div>
  );
}

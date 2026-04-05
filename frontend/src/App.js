import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Investors from './pages/Investors';
import InvestorOnboarding from './pages/InvestorOnboarding';
import InvestorDetail from './pages/InvestorDetail';
import Deals from './pages/Deals';
import DealDetail from './pages/DealDetail';
import Portfolio from './pages/Portfolio';
import Reports from './pages/Reports';
import Settings from './pages/Settings';

function LoadingScreen() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#FAFAF8]">
      <div className="text-center">
        <div className="text-2xl font-bold font-heading mb-2">
          <span className="text-[#1F2937]">Zephyr</span>
          <span className="text-[#00A8C6]">Wealth</span>
        </div>
        <div className="flex items-center gap-1.5 justify-center mt-4">
          <div className="w-1.5 h-1.5 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <div className="w-1.5 h-1.5 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <div className="w-1.5 h-1.5 bg-[#1B3A6B] rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function PublicRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen />;
  if (user) return <Navigate to="/dashboard" replace />;
  return children;
}

function AppRoutes() {
  return (
    <Routes>
      <Route
        path="/login"
        element={
          <PublicRoute>
            <Login />
          </PublicRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<Dashboard />} />
        <Route path="investors" element={<Investors />} />
        <Route path="investors/new" element={<InvestorOnboarding />} />
        <Route path="investors/:id" element={<InvestorDetail />} />
        <Route path="deals" element={<Deals />} />
        <Route path="deals/:id" element={<DealDetail />} />
        <Route path="portfolio" element={<Portfolio />} />
        <Route path="reports" element={<Reports />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
        <Toaster position="bottom-right" richColors closeButton />
      </BrowserRouter>
    </AuthProvider>
  );
}

import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const InvestorAuthContext = createContext(null);
const API = process.env.REACT_APP_BACKEND_URL;
const TOKEN_KEY = 'zw_investor_token';

function formatApiError(detail) {
  if (detail == null) return 'Something went wrong. Please try again.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail))
    return detail
      .map((e) => (e && typeof e.msg === 'string' ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(' ');
  if (detail && typeof detail.msg === 'string') return detail.msg;
  return String(detail);
}

function getInvestorAuthHeaders() {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function InvestorAuthProvider({ children }) {
  const [investor, setInvestor] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios
      .get(`${API}/api/portal/auth/me`, { withCredentials: true, headers: getInvestorAuthHeaders() })
      .then((res) => setInvestor(res.data))
      .catch(() => setInvestor(false))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    try {
      const { data } = await axios.post(
        `${API}/api/portal/auth/login`,
        { email, password },
        { withCredentials: true }
      );
      if (data.investor_token) {
        localStorage.setItem(TOKEN_KEY, data.investor_token);
      }
      setInvestor(data);
      return data;
    } catch (e) {
      const msg = formatApiError(e.response?.data?.detail) || e.message;
      throw new Error(msg);
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/api/portal/auth/logout`, {}, { withCredentials: true, headers: getInvestorAuthHeaders() });
    } finally {
      localStorage.removeItem(TOKEN_KEY);
      setInvestor(false);
    }
  };

  const changePassword = async (current_password, new_password) => {
    try {
      const { data } = await axios.post(
        `${API}/api/portal/auth/change-password`,
        { current_password, new_password },
        { withCredentials: true, headers: getInvestorAuthHeaders() }
      );
      setInvestor((prev) => prev ? { ...prev, first_login: false } : prev);
      return data;
    } catch (e) {
      const msg = formatApiError(e.response?.data?.detail) || e.message;
      throw new Error(msg);
    }
  };

  return (
    <InvestorAuthContext.Provider value={{ investor, loading, login, logout, changePassword, setInvestor, getInvestorAuthHeaders }}>
      {children}
    </InvestorAuthContext.Provider>
  );
}

export function useInvestorAuth() {
  const ctx = useContext(InvestorAuthContext);
  if (!ctx) throw new Error('useInvestorAuth must be used within InvestorAuthProvider');
  return ctx;
}

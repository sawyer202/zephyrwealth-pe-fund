import React, { createContext, useContext, useState, useEffect } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);
const API = process.env.REACT_APP_BACKEND_URL;
const TOKEN_KEY = 'zw_access_token';

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

function getAuthHeaders() {
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    axios
      .get(`${API}/api/auth/me`, { withCredentials: true, headers: getAuthHeaders() })
      .then((res) => setUser(res.data))
      .catch(() => setUser(false))
      .finally(() => setLoading(false));
  }, []);

  const login = async (email, password) => {
    try {
      const { data } = await axios.post(
        `${API}/api/auth/login`,
        { email, password },
        { withCredentials: true }
      );
      if (data.access_token) {
        localStorage.setItem(TOKEN_KEY, data.access_token);
      }
      setUser(data);
      return data;
    } catch (e) {
      const msg = formatApiError(e.response?.data?.detail) || e.message;
      throw new Error(msg);
    }
  };

  const logout = async () => {
    try {
      await axios.post(`${API}/api/auth/logout`, {}, { withCredentials: true, headers: getAuthHeaders() });
    } finally {
      localStorage.removeItem(TOKEN_KEY);
      setUser(false);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, getAuthHeaders }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}

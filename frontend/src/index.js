import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';

// Global fetch interceptor — automatically inject Bearer token for our API.
// Required so back-office + portal pages keep working on custom domains where
// HttpOnly cookies set by the backend are not sent cross-origin.
(function patchFetchWithAuth() {
  const BACKEND = process.env.REACT_APP_BACKEND_URL || '';
  if (!BACKEND) return;
  const originalFetch = window.fetch.bind(window);
  window.fetch = function (resource, init = {}) {
    try {
      const url = typeof resource === 'string' ? resource : resource && resource.url;
      if (url && url.startsWith(BACKEND)) {
        const isPortal = url.includes('/api/portal/');
        const token = localStorage.getItem(isPortal ? 'zw_investor_token' : 'zw_access_token');
        if (token) {
          const headers = new Headers(init.headers || (typeof resource !== 'string' ? resource.headers : undefined) || {});
          if (!headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
          init = { ...init, headers };
        }
        if (init.credentials === undefined) init.credentials = 'include';
      }
    } catch (_) { /* fall through to original fetch */ }
    return originalFetch(resource, init);
  };
})();

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

const TOKEN_KEY = 'zw_investor_token';

/**
 * Wrapper around fetch that adds both credentials (cookies) AND
 * Authorization Bearer header (for environments where cookies are blocked).
 */
export function portalFetch(url, options = {}) {
  const token = localStorage.getItem(TOKEN_KEY);
  return fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

const BO_TOKEN_KEY = 'zw_access_token';

/**
 * Same for back-office fetch calls.
 */
export function boFetch(url, options = {}) {
  const token = localStorage.getItem(BO_TOKEN_KEY);
  return fetch(url, {
    ...options,
    credentials: 'include',
    headers: {
      ...options.headers,
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}

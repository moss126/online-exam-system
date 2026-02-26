export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000/api';

export const authFetch = (url, options = {}) => {
  const token = localStorage.getItem('token');
  const headers = new Headers(options.headers || {});
  if (token) headers.set('X-Token', token);
  return fetch(url, { ...options, headers });
};
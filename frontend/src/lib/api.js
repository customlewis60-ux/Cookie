import axios from 'axios';
export const API_URL = `${process.env.REACT_APP_BACKEND_URL}/api`;
export const api = axios.create({ baseURL: API_URL });
api.interceptors.request.use(config => {
  const token = sessionStorage.getItem('cookie-session');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});
export const errorMessage = error => {
  const detail = error.response?.data?.detail;
  return typeof detail === 'string' ? detail : 'Something went wrong. Please try again.';
};
export const CATEGORIES = ['Personal', 'Preferences', 'Work', 'Trading', 'Projects', 'Knowledge', 'AI Context', 'Custom'];
export const shortAddress = a => a ? `${a.slice(0, 6)}…${a.slice(-4)}` : '';
export const relativeTime = value => {
  if (!value) return 'Not accessed yet';
  const m = Math.max(0, Math.floor((Date.now() - new Date(value)) / 60000));
  if (m < 1) return 'Just now';
  if (m < 60) return `${m}m ago`;
  if (m < 1440) return `${Math.floor(m / 60)}h ago`;
  return `${Math.floor(m / 1440)}d ago`;
};
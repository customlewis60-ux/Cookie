import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
const Context = createContext(null);
export const useVault = () => useContext(Context);
export const VaultProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [key, setKey] = useState(null);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState({ memories: [], agents: [], permissions: [], activity: [] });
  const refresh = useCallback(async () => {
    const result = (await api.get('/dashboard')).data;
    setData(result); setUser(result.user);
    return result;
  }, []);
  useEffect(() => {
    if (!sessionStorage.getItem('cookie-session')) { setLoading(false); return; }
    refresh().catch(() => sessionStorage.removeItem('cookie-session')).finally(() => setLoading(false));
  }, [refresh]);
  const connect = async () => {
    let credential = localStorage.getItem('cookie-demo-identity');
    if (!credential) {
      credential = Array.from(crypto.getRandomValues(new Uint8Array(32)), b => b.toString(16).padStart(2, '0')).join('');
      localStorage.setItem('cookie-demo-identity', credential);
    }
    const result = (await api.post('/auth/demo', { credential })).data;
    sessionStorage.setItem('cookie-session', result.token);
    setUser(result.user);
    return result.user;
  };
  const disconnect = async () => {
    await api.post('/auth/logout');
    sessionStorage.removeItem('cookie-session'); setUser(null); setKey(null);
    setData({ memories: [], agents: [], permissions: [], activity: [] });
  };
  return <Context.Provider value={{ user, setUser, key, setKey, loading, data, refresh, connect, disconnect }}>{children}</Context.Provider>;
};
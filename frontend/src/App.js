import { BrowserRouter, Routes, Route, useLocation, Link } from 'react-router-dom';
import { useEffect } from 'react';
import { VaultProvider } from './context/VaultContext';
import { AppShell } from './components/AppShell';
import { Toaster } from './components/ui/sonner';
import Landing from './pages/Landing';
import Overview from './pages/Overview';
import Memory from './pages/Memory';
import Agents from './pages/Agents';
import Permissions from './pages/Permissions';
import Activity from './pages/Activity';
import Settings from './pages/Settings';
import Developer from './pages/Developer';
import Docs from './pages/Docs';
import Studio from './pages/Studio';
import './App.css';
const ScrollReset = () => { const { pathname } = useLocation(); useEffect(() => { window.scrollTo(0, 0); }, [pathname]); return null; };
export default function App() {
  return <BrowserRouter><VaultProvider><ScrollReset/><Routes><Route path="/" element={<Landing/>}/><Route path="/docs" element={<Docs/>}/><Route path="/app" element={<AppShell/>}><Route index element={<Overview/>}/><Route path="memory" element={<Memory/>}/><Route path="agents" element={<Agents/>}/><Route path="studio" element={<Studio/>}/><Route path="permissions" element={<Permissions/>}/><Route path="activity" element={<Activity/>}/><Route path="api" element={<Developer/>}/><Route path="settings" element={<Settings/>}/></Route><Route path="*" element={<div className="locked-vault"><h1>Nothing to remember here.</h1><Link to="/" data-testid="not-found-home" className="btn btn-primary">Back to COOKIE</Link></div>}/></Routes><Toaster theme="dark" position="bottom-right" richColors closeButton/></VaultProvider></BrowserRouter>;
}
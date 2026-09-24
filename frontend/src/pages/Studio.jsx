import { useCallback, useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { ArrowUpRight, Bot, Check, Clock3, Play, RefreshCw, ShieldCheck } from 'lucide-react';
import { PageHeading, Btn, Empty } from '../components/Common';
import { Textarea } from '../components/ui/textarea';
import { StudioConsent } from '../components/StudioConsent';
import { StudioContext } from '../components/StudioContext';
import { StudioResult } from '../components/StudioResult';
import { MemoryDialog } from '../components/MemoryDialog';
import { useVault } from '../context/VaultContext';
import { useStudioRun } from '../hooks/useStudioRun';
import { api, errorMessage, relativeTime } from '../lib/api';
import { agentIcons } from '../lib/studio';
import '../styles/studio.css';

const templates = [
  ['Recall my context', 'Based only on the provided memories, summarize my preferences and suggest one useful next step. If no memories were provided, explain that you do not have my personal context instead of guessing.'],
  ['Plan my next step', 'Suggest three practical next steps for my current project, tailored to the provided context. Distinguish what you know from what you would need to ask me.'],
  ['Explain my stack', 'Use my developer preferences to recommend a small implementation plan. Follow my preferred technologies and communication style when they are available.'],
];
export default function Studio() {
  const { data, refresh } = useVault(); const [params] = useSearchParams();
  const [agentId, setAgentId] = useState(params.get('agent') || '');
  const [task, setTask] = useState(''); const [selected, setSelected] = useState([]); const [mode, setMode] = useState('with');
  const [review, setReview] = useState(null); const [saving, setSaving] = useState(null);
  const [settings, setSettings] = useState(null); const [receipts, setReceipts] = useState([]); const [error, setError] = useState(''); const [refreshing, setRefreshing] = useState(false);
  const loadReceipts = useCallback(async () => { const r = await api.get('/studio/runs'); setReceipts(r.data); }, []);
  const load = useCallback(async () => { const r = await api.get('/studio/config'); setSettings(r.data); await loadReceipts(); }, [loadReceipts]);
  useEffect(() => { load().catch(e => setError(errorMessage(e))); }, [load]);
  useEffect(() => {
    if (!receipts.some(r => r.status === 'running')) return;
    const timer = setInterval(() => loadReceipts().catch(() => {}), 1500);
    return () => clearInterval(timer);
  }, [receipts, loadReceipts]);
  useEffect(() => { if (!agentId && data.agents.length) setAgentId(data.agents.find(a => a.status === 'connected')?.id || ''); }, [agentId, data.agents]);
  const runner = useStudioRun({ refresh, loadReceipts, timeoutSeconds: settings?.timeout_seconds });
  const agent = data.agents.find(a => a.id === agentId);
  const authorizedIds = selected.filter(id => data.memories.some(m => m.id === id && m.privacy === 'shareable' && m.agent_ids.includes(agentId)));
  const currentResults = runner.group === `${agentId}:${task.trim()}` ? runner.results : {};
  const canReview = Boolean(settings?.configured && agent?.status === 'connected' && task.trim() && (mode === 'without' || authorizedIds.length));
  const refreshAccess = async () => { setRefreshing(true); setError(''); try { await Promise.all([refresh(), load()]); } catch (e) { setError(errorMessage(e)); } finally { setRefreshing(false); } };
  return <><PageHeading eyebrow="YOUR MEMORY, PUT TO WORK" title="Your context. In action." subtitle="A real agent. A task that matters. Only the memories you approve."><Btn variant="secondary" data-testid="studio-refresh-access" busy={refreshing} disabled={runner.busy} onClick={refreshAccess}><RefreshCw size={14}/> Refresh access</Btn></PageHeading>
    <div className="studio-runtime-band" data-testid="studio-runtime-band"><span className="studio-runtime-icon"><Bot size={21}/></span><div><strong>COOKIE Agent Studio</strong><span>Reference agents · OpenAI · GPT-5.4 Mini</span></div><span className="studio-consent-badge"><ShieldCheck size={13}/> Consent for every task</span></div>
    {error && <p className="form-error" role="alert" data-testid="studio-load-error">{error}</p>}
    {settings && !settings.configured && <p className="form-error" role="alert" data-testid="studio-not-configured">The AI connection is not configured. No context will be sent.</p>}
    {!data.agents.length ? <Empty icon={Bot} title="First, choose your agent." text="Connect an agent identity, then grant it access to a shareable memory."><Link className="btn btn-primary" to="/app/agents" data-testid="studio-connect-first-agent">Connect an agent <ArrowUpRight size={14}/></Link></Empty> : <div className="studio-layout"><div className="studio-input-column">
      <section className="studio-agent-section"><div className="studio-section-title"><span>01</span><h2>Choose your agent</h2></div><label htmlFor="studio-agent" className="sr-only">Agent</label><select id="studio-agent" data-testid="studio-agent-select" className="field" value={agentId} disabled={runner.busy} onChange={e => { setAgentId(e.target.value); setSelected([]); }}><option value="" disabled>Select a connected agent</option>{data.agents.map(a => <option key={a.id} value={a.id} disabled={a.status !== 'connected'}>{a.name}{a.status === 'connected' ? '' : ' · Disconnected'}</option>)}</select><div className="studio-agent-caption"><span data-testid="studio-agent-role">{agent ? agentIcons[agent.kind] : 'Select an agent'}</span><Link data-testid="studio-agent-permissions" to="/app/permissions">Manage permissions <ArrowUpRight size={11}/></Link></div>{agent?.status === 'disconnected' && <p className="form-error" data-testid="studio-agent-disconnected">This agent is disconnected. Reconnect it before running a task.</p>}</section>
      <section className="studio-task-section"><div className="studio-section-title"><span>02</span><h2>Give it a task</h2><span data-testid="studio-task-length">{task.length} / 4,000</span></div><label className="sr-only" htmlFor="studio-task">Task</label><Textarea id="studio-task" data-testid="studio-task-input" className="field studio-task-input ph-no-capture" placeholder="What would you like this agent to help you with?" value={task} maxLength={4000} disabled={runner.busy} onChange={e => setTask(e.target.value)}/><div className="studio-task-suggestions">{templates.map(([label, text], i) => <button key={label} data-testid={`studio-template-${i}`} disabled={runner.busy} onClick={() => setTask(text)}>{label} <ArrowUpRight size={11}/></button>)}</div></section>
      <StudioContext memories={data.memories} agent={agent} selected={selected} setSelected={setSelected} disabled={runner.busy} mode={mode} setMode={value => { setMode(value); runner.setActiveMode(value); }}/>
      <div className="studio-run-control"><Btn data-testid="studio-review-run" disabled={!canReview || runner.busy} onClick={() => setReview({ agent, task: task.trim(), memoryIds: mode === 'with' ? authorizedIds : [], mode })}><ShieldCheck size={16}/> Review context & run <ArrowUpRight size={15}/></Btn><p data-testid="studio-review-note">Nothing is sent to AI before you approve.</p></div>
    </div><StudioResult results={currentResults} activeMode={runner.activeMode} setActiveMode={runner.setActiveMode} busy={runner.busy} onStop={runner.stop} modelLabel={settings?.model_label} onSave={result => setSaving({ title: `${result.agent.name} · Task result`, category: 'AI Context', privacy: 'private', content: result.output })}/></div>}
    <section className="studio-receipts"><div className="studio-receipts-heading"><div><h2>Task receipts</h2><p>Only access metadata is kept. Task text, context, and responses are not stored here.</p></div><Link to="/app/activity?filter=agents" data-testid="studio-view-activity">Full activity <ArrowUpRight size={13}/></Link></div>{receipts.length ? <div className="studio-receipt-list">{receipts.slice(0, 8).map(receipt => <div className="studio-receipt" data-testid={`studio-receipt-${receipt.id}`} key={receipt.id}><span className={`studio-receipt-icon ${receipt.status}`}>{receipt.status === 'completed' ? <Check size={14}/> : <Clock3 size={14}/>}</span><div><strong>{receipt.agent_name}</strong><span>{receipt.memory_count ? `${receipt.memory_count} authorized memories` : 'No vault context'} · {receipt.model}</span></div><span className={`studio-receipt-status ${receipt.status}`} data-testid={`studio-receipt-status-${receipt.id}`}>{receipt.status}</span><time>{relativeTime(receipt.created_at)}</time></div>)}</div> : <div className="studio-receipts-empty" data-testid="studio-no-receipts"><Play size={15}/><span>Your first approved task starts the record.</span></div>}</section>
    {review && <StudioConsent {...review} onClose={() => setReview(null)} onApprove={request => { setReview(null); runner.run(request); }}/>} {saving && <MemoryDialog memory={saving} onClose={() => setSaving(null)}/>}
  </>;
}
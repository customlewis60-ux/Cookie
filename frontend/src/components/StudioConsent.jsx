import { useEffect, useRef, useState } from 'react';
import { ArrowRight, Eye, LockKeyhole, Loader2, ShieldCheck, ExternalLink, Check } from 'lucide-react';
import { Modal, Btn } from './Common';
import { Input } from './ui/input';
import { useVault } from '../context/VaultContext';
import { api, errorMessage } from '../lib/api';
import { decrypt, unlock } from '../lib/crypto';
import { taskDigest } from '../lib/studio';

export const StudioConsent = ({ agent, task, memoryIds, mode, onClose, onApprove }) => {
  const { user } = useVault();
  const [preparation, setPreparation] = useState(null);
  const [stage, setStage] = useState('loading');
  const [password, setPassword] = useState('');
  const [contexts, setContexts] = useState([]);
  const [checked, setChecked] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const submitting = useRef(false);
  useEffect(() => {
    let live = true;
    (async () => {
      try {
        const result = (await api.post('/studio/prepare', { agent_id: agent.id, memory_ids: memoryIds, task_digest: await taskDigest(task) })).data;
        if (live) { setPreparation(result); setStage(result.memories.length ? 'unlock' : 'review'); }
      } catch (e) { if (live) { setError(errorMessage(e)); setStage('error'); } }
    })();
    return () => { live = false; };
  }, [agent.id, memoryIds, task]);
  const open = async e => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const verified = await unlock(password, user.vault);
      const plain = await Promise.all(preparation.memories.map(async memory => ({ memory_id: memory.id, content: await decrypt(memory.encrypted_payload, verified) })));
      if (plain.some(m => m.content.length > 20000) || plain.reduce((n, m) => n + m.content.length, 0) > 30000) throw new Error('Selected context is too large. Choose fewer memories or shorten them before sharing.');
      setContexts(plain); setPassword(''); setStage('review');
    } catch (e) { setError(e.message || 'This memory could not be unlocked.'); }
    finally { setBusy(false); }
  };
  const approve = () => {
    if (!checked || submitting.current) return;
    if (Date.now() >= new Date(preparation.expires_at).getTime()) { setError('This review expired. Close it and start a fresh review.'); return; }
    submitting.current = true;
    onApprove({ agent, mode, memories: preparation.memories.map(({ id, title, category }) => ({ id, title, category })),
      payload: { consent_token: preparation.consent_token, approved: true, task, contexts } });
  };
  return <Modal open wide onClose={onClose} title={stage === 'unlock' ? 'Unlock only what you choose.' : 'This context. This task. Your call.'} description={stage === 'unlock' ? 'Your passphrase is checked in this browser. It never reaches the agent or AI provider.' : 'Review the exact task and memory content before they leave your browser.'} testId="studio-consent-dialog">
    <div className="studio-consent-steps" data-testid="studio-consent-progress"><span className="complete"><Check size={12}/> Select</span><ArrowRight size={12}/><span className={stage === 'review' ? 'complete' : ''}><LockKeyhole size={12}/> Unlock</span><ArrowRight size={12}/><span className={stage === 'review' ? 'current' : ''}><Eye size={12}/> Review & approve</span></div>
    {stage === 'loading' && <div className="studio-consent-loading" data-testid="studio-consent-loading"><Loader2 className="spin" size={22}/><span>Checking current permissions…</span></div>}
    {stage === 'unlock' && <form onSubmit={open} className="form-stack"><div className="studio-review-agent" data-testid="studio-unlock-summary"><ShieldCheck size={21}/><div><strong>{agent.name}</strong><span>{memoryIds.length} authorized {memoryIds.length === 1 ? 'memory' : 'memories'} · not sent to AI yet</span></div></div><label htmlFor="studio-passphrase">Vault passphrase</label><Input data-testid="studio-unlock-passphrase" id="studio-passphrase" type="password" autoComplete="current-password" className="field" value={password} onChange={e => setPassword(e.target.value)} required placeholder="Enter your vault passphrase"/><Btn type="submit" data-testid="studio-unlock-context" busy={busy}><LockKeyhole size={15}/> Unlock & review locally</Btn></form>}
    {stage === 'review' && <>
      <div className="studio-review-agent" data-testid="studio-consent-recipient"><ExternalLink size={20}/><div><strong>{agent.name} → GPT-5.4 Mini</strong><span>Recipient: OpenAI through the Emergent AI gateway</span></div></div>
      <div className="studio-reviewed-context ph-no-capture"><div className="studio-reviewed-task"><span className="eyebrow">YOUR TASK</span><p data-testid="studio-task-preview">{task}</p></div>{contexts.length ? contexts.map((context, i) => <section key={context.memory_id} className="studio-context-preview"><div><LockKeyhole size={13}/><strong data-testid={`studio-preview-title-${context.memory_id}`}>{preparation.memories[i].title}</strong></div><p data-testid={`studio-preview-content-${context.memory_id}`}>{context.content}</p></section>) : <p className="studio-zero-context" data-testid="studio-no-context-preview">No vault memories will be sent. Only your task and the agent’s role are included.</p>}</div>
      <div className="notice studio-privacy-notice" data-testid="studio-privacy-boundary"><LockKeyhole size={16}/><span>Your task and selected context pass through COOKIE’s server and the AI gateway as readable text. COOKIE does not save them or the response unless you choose to save an encrypted result. Provider processing/retention terms apply. Passphrase and vault key stay in your browser. Revoking access cannot recall context already sent.</span></div>
      <label className="studio-explicit-consent"><input data-testid="studio-consent-checkbox" type="checkbox" checked={checked} onChange={e => setChecked(e.target.checked)}/><span>I approve sending exactly this task and context for one AI request. This uses my AI key balance.</span></label>
      <div className="dialog-actions"><Btn variant="secondary" data-testid="studio-cancel-consent" onClick={onClose}>Keep it private</Btn><Btn data-testid="studio-approve-run" disabled={!checked} onClick={approve}><ShieldCheck size={15}/> Approve & run once</Btn></div>
    </>}
    {error && <p role="alert" className="form-error" data-testid="studio-consent-error">{error}</p>}
  </Modal>;
};
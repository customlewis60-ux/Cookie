import { Copy, KeyRound, Play } from 'lucide-react';
import { Modal, Btn } from './Common';
import { Input } from './ui/input';
import { Switch } from './ui/switch';
import { toast } from './ui/sonner';

// A single persistent Radix Dialog prevents overlapping exit animations and
// focus traps when a create/rotate confirmation becomes the one-time secret.
export const DeveloperDialogs = ({ mode, onClose, busy, agents, name, setName, agent, setAgent, canWrite, setCanWrite, create, secret, pending, apply, testKey, setTestKey, testRequest, result }) => {
  const config = {
    create: { id: 'new-key-dialog', title: 'A key with boundaries.', description: 'Each API key belongs to one agent and inherits only its active permissions.' },
    secret: { id: 'key-secret-dialog', title: 'Keep this key somewhere safe.', description: 'The full secret is available only during this page session. COOKIE stores a hash, not a retrievable copy.' },
    action: { id: 'key-action-dialog', title: pending?.action === 'rotate' ? 'Rotate this API key?' : 'Revoke this API key?', description: pending?.action === 'rotate' ? 'A new secret will replace the old key. Requests with the old key stop working immediately.' : 'This key will stop working immediately. This cannot be undone.' },
    test: { id: 'test-request-dialog', title: 'Make a real API request.', description: 'Test GET /v1/memory with an agent-scoped demo key. The response only contains authorized encrypted payloads.' },
  }[mode] || { id: 'developer-dialog', title: 'COOKIE developer tools', description: 'Manage your agent credentials.' };
  return <Modal open={Boolean(mode)} onClose={busy ? () => {} : onClose} title={config.title} description={config.description} testId={config.id}>
    {mode === 'create' && <form className="form-stack" onSubmit={create}>
      <label htmlFor="key-name">Key name</label><Input id="key-name" data-testid="api-key-name" className="field" placeholder="e.g. Development Key" maxLength={80} required value={name} onChange={e => setName(e.target.value)}/>
      <label htmlFor="key-agent">Authorized agent</label><select id="key-agent" data-testid="api-key-agent" className="field" required value={agent} onChange={e => setAgent(e.target.value)}><option value="">Select an agent</option>{agents.filter(a => a.status === 'connected').map(a => <option key={a.id} value={a.id}>{a.name}</option>)}</select>
      {!agents.some(a => a.status === 'connected') && <p className="form-error" data-testid="key-no-agents">Connect an agent before creating a key.</p>}
      <div className="switch-field"><div><strong>Allow encrypted writes</strong><small>Also requires a category permission</small></div><Switch data-testid="api-key-write-toggle" aria-label="Allow encrypted writes" checked={canWrite} onCheckedChange={setCanWrite}/></div>
      <Btn type="submit" data-testid="save-api-key" disabled={!name.trim() || !agent} busy={busy}><KeyRound size={16}/> Create demo API key</Btn>
    </form>}
    {mode === 'secret' && <><div className="secret-display ph-no-capture" data-testid="api-key-secret">{secret}</div><Btn data-testid="copy-api-key" onClick={() => navigator.clipboard.writeText(secret).then(() => toast.success('API key copied. Keep it server-side.')).catch(() => toast.error('Clipboard unavailable. Select the key to copy.'))}><Copy size={16}/> Copy secret key</Btn><Btn variant="secondary" data-testid="key-secret-done" disabled={busy} onClick={onClose}>I’ve saved my key</Btn><p className="fine-print">Working demo credential · Not a blockchain key</p></>}
    {mode === 'action' && <div className="dialog-actions"><Btn variant="secondary" data-testid="cancel-key-action" disabled={busy} onClick={onClose}>Cancel</Btn><Btn data-testid="confirm-key-action" busy={busy} onClick={apply}>{pending?.action === 'rotate' ? 'Rotate key' : 'Revoke key'}</Btn></div>}
    {mode === 'test' && <form className="form-stack" onSubmit={testRequest}><label htmlFor="test-key">Demo API key</label><Input id="test-key" data-testid="test-api-key-input" type="password" className="field" placeholder="ck_demo_…" value={testKey} onChange={e => setTestKey(e.target.value)} required/><Btn data-testid="send-api-request" type="submit" busy={busy}><Play size={15}/> Send request</Btn>{result && <div role="status" className={`request-result ${result.status === 200 ? 'success' : 'failure'}`} data-testid="api-test-result"><strong>{result.status}</strong><span>{result.text}</span></div>}</form>}
  </Modal>;
};
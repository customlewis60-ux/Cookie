import { useState } from 'react';
import { Bot, LockKeyhole, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Modal, Btn, Empty } from './Common';
import { Switch } from './ui/switch';
import { toast } from './ui/sonner';
import { useVault } from '../context/VaultContext';
import { api, errorMessage } from '../lib/api';
export const AccessDialog = ({ memory, onClose }) => {
  const { data, refresh } = useVault();
  const [busy, setBusy] = useState(null);
  const [pending, setPending] = useState(null);
  const agents = data.agents.filter(a => a.status === 'connected');
  const apply = async () => {
    const { agent, direct } = pending; setBusy(agent.id);
    try {
      if (direct) await api.delete(`/permissions/${direct.id}`);
      else await api.post('/permissions', { agent_id: agent.id, target_type: 'memory', target: memory.id });
      await refresh(); toast.success(direct ? 'Permission revoked. Future access is blocked.' : `${agent.name} has access to this memory.`); setPending(null);
    } catch (e) { toast.error(errorMessage(e)); }
    finally { setBusy(null); }
  };
  return <Modal open onClose={onClose} testId="access-dialog" title="Your memory. Your permissions." description={`Control access to “${memory.title}”.`}>
    {memory.privacy === 'private' ? <div className="notice" data-testid="private-access-notice"><LockKeyhole size={18}/><span>This memory is private. Edit its privacy to Shareable before authorizing an agent.</span></div> : null}
    {agents.length ? <div className="access-list">{agents.map(agent => {
      const direct = data.permissions.find(p => p.agent_id === agent.id && p.target_type === 'memory' && p.target === memory.id);
      const inherited = data.permissions.find(p => p.agent_id === agent.id && p.target_type === 'category' && p.target === memory.category);
      return <div className="access-row" key={agent.id}><span className={`agent-icon ${agent.kind}`}><Bot size={19}/></span><div><strong>{agent.name}</strong><small>{inherited ? `Inherited from ${memory.category} category` : direct ? 'This memory only' : 'No access'}</small></div><Switch data-testid={`memory-access-${agent.id}`} aria-label={`Allow ${agent.name}`} checked={memory.privacy === 'shareable' && Boolean(direct || inherited)} disabled={memory.privacy === 'private' || Boolean(inherited) || Boolean(busy)} onCheckedChange={() => setPending({ agent, direct })}/></div>;
    })}</div> : <Empty icon={Bot} title="No connected agents" text="Connect an agent before granting access."/>}
    {pending && <div className="permission-confirm" data-testid="access-confirmation"><p>{pending.direct ? `Revoke ${pending.agent.name}’s access?` : `Allow ${pending.agent.name} to retrieve this encrypted memory?`}</p><div className="dialog-actions"><Btn variant="secondary" data-testid="cancel-access-change" onClick={() => setPending(null)}>Cancel</Btn><Btn data-testid="confirm-access-change" busy={Boolean(busy)} onClick={apply}>{pending.direct ? 'Revoke access' : 'Grant access'}</Btn></div></div>}
    <Link className="text-link" to="/app/permissions" data-testid="access-all-permissions" onClick={onClose}>Manage category permissions <ShieldCheck size={14}/></Link>
  </Modal>;
};
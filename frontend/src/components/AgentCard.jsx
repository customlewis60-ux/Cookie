import { Link } from 'react-router-dom';
import { Bot, Code2, TrendingUp, Search, UserRound, ArrowUpRight, ShieldCheck, Unplug, Plug, Copy, Play } from 'lucide-react';
import { Badge } from './Common';
import { toast } from './ui/sonner';
import { relativeTime } from '../lib/api';

const icons = { personal: UserRound, trading: TrendingUp, coding: Code2, research: Search, custom: Bot };
export const AgentCard = ({ agent, memories, onToggle }) => {
  const Icon = icons[agent.kind] || Bot;
  const allowed = memories.filter(m => m.agent_ids.includes(agent.id));
  return <article className="agent-card" data-testid={`agent-card-${agent.id}`}>
    <div className="agent-card-top"><span className={`agent-icon large ${agent.kind}`}><Icon size={25}/></span><Badge tone={agent.status === 'connected' ? 'green' : ''} testId={`agent-status-${agent.id}`}><i className="small-dot"/>{agent.status === 'connected' ? 'Connected' : 'Disconnected'}</Badge></div>
    <div className="agent-name"><h2 data-testid={`agent-name-${agent.id}`}>{agent.name}</h2><span className="mini-tag" data-testid={`agent-type-${agent.id}`}>{agent.type === 'demo' ? 'REFERENCE' : 'CUSTOM ID'}</span></div>
    <p className="agent-developer" data-testid={`agent-developer-${agent.id}`}>by {agent.developer}</p>
    <div className="agent-id"><span className="mono" data-testid={`agent-id-${agent.id}`}>{agent.id}</span><button data-testid={`copy-agent-id-${agent.id}`} className="icon-button" title="Copy agent ID" aria-label="Copy agent ID" onClick={() => navigator.clipboard.writeText(agent.id).then(() => toast.success('Agent ID copied.')).catch(() => toast.error('Clipboard is unavailable.'))}><Copy size={13}/></button></div>
    <div className="agent-access"><span className="field-label">AUTHORIZED MEMORIES</span><div>{allowed.length ? allowed.slice(0, 3).map(m => <span className="access-chip" data-testid={`agent-memory-${agent.id}-${m.id}`} key={m.id}><ShieldCheck size={11}/>{m.title}</span>) : <span className="muted-text" data-testid={`agent-no-access-${agent.id}`}>No memory access</span>}{allowed.length > 3 && <span>+{allowed.length - 3} more</span>}</div></div>
    <div className="agent-last">Last activity <span data-testid={`agent-last-activity-${agent.id}`}>{relativeTime(agent.last_activity)}</span></div>
    <div className="agent-actions"><Link className="text-link" to="/app/permissions" data-testid={`agent-permissions-${agent.id}`}><ShieldCheck size={14}/> Permissions <ArrowUpRight size={13}/></Link><Link className="text-link" data-testid={`run-agent-${agent.id}`} to={`/app/studio?agent=${agent.id}`}><Play size={13}/> Studio</Link><button className="icon-button" title={agent.status === 'connected' ? 'Disconnect agent' : 'Reconnect agent'} aria-label={`${agent.status === 'connected' ? 'Disconnect' : 'Reconnect'} ${agent.name}`} data-testid={`toggle-agent-${agent.id}`} onClick={() => onToggle(agent)}>{agent.status === 'connected' ? <Unplug size={17}/> : <Plug size={17}/>}</button></div>
  </article>;
};
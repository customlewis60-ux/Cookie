import ReactMarkdown from 'react-markdown';
import { Bot, Check, Copy, Download, LockKeyhole, Loader2, Square, AlertCircle, ArrowRight } from 'lucide-react';
import { Btn } from './Common';
import { CookieMark } from './Brand';
import { toast } from './ui/sonner';

// No remote images, raw HTML, or model-generated active links in private outputs.
const safeMarkdown = { a: ({ children }) => <span className="studio-inert-link">{children}</span>, img: () => null };
export const StudioResult = ({ results, activeMode, setActiveMode, busy, onStop, onSave, modelLabel }) => {
  const result = results[activeMode];
  return <section className="studio-output-section"><div className="studio-output-heading"><div><span className="eyebrow">THE CONTEXT MAKES THE DIFFERENCE</span><h2 data-testid="studio-result-heading">Same task. A little more you.</h2></div><span className="studio-model-tag" data-testid="studio-model-label">{modelLabel || 'GPT-5.4 Mini'}</span></div>
    <div className="studio-result-tabs" role="group" aria-label="Response comparison">{[['with', 'With memory'], ['without', 'Without memory']].map(([value, label]) => <button data-testid={`studio-result-tab-${value}`} key={value} onClick={() => setActiveMode(value)} className={activeMode === value ? 'active' : ''} disabled={busy && activeMode !== value}>{label}{results[value]?.status === 'completed' && <Check size={12}/>}</button>)}</div>
    <div className="studio-response-frame" data-testid="studio-response-frame" data-run-id={result?.run_id || ''} aria-busy={result?.status === 'running'}>
      {!result ? <div className="studio-output-empty" data-testid="studio-output-empty"><div className="studio-idle-symbol"><CookieMark/><ArrowRight size={17}/><Bot size={30}/></div><h3>A memory is more than a note.</h3><p>It’s the context behind a better answer.</p><div className="studio-idle-path"><span>Choose</span><i/><span>Review</span><i/><span>Approve</span></div></div> : <>
        <div className="studio-response-meta"><span data-testid="studio-result-agent"><Bot size={15}/>{result.agent.name}</span><span className={`studio-run-status ${result.status}`} data-testid="studio-result-status">{result.status === 'running' && <Loader2 size={12} className="spin"/>}{result.status === 'completed' ? 'Complete' : result.status === 'cancelled' ? 'Stopped' : result.status === 'failed' ? 'Not completed' : 'Generating'}</span></div>
        <div className="studio-sent-context" data-testid="studio-sent-context"><LockKeyhole size={12}/>{result.memories.length ? result.memories.map(m => m.title).join(' · ') : 'No vault memories sent'}</div>
        <div className="studio-answer ph-no-capture" data-testid="studio-ai-response">{result.output ? <ReactMarkdown skipHtml components={safeMarkdown}>{result.output}</ReactMarkdown> : result.status === 'running' ? <div className="studio-thinking"><span/><span/><span/><p>Preparing a thoughtful response…</p></div> : null}</div>
        {result.error && <div role="alert" className="studio-run-error" data-testid="studio-run-error"><AlertCircle size={17}/><span>{result.error}</span></div>}
        {result.finish_reason === 'length' && <p className="studio-truncated" data-testid="studio-output-truncated">The response reached its length limit. A narrower task may give a more complete answer.</p>}
        <div className="studio-response-actions">{busy ? <Btn variant="secondary" data-testid="studio-stop-run" onClick={onStop}><Square size={12}/> Stop task</Btn> : result.status === 'completed' ? <><Btn variant="secondary" data-testid="studio-copy-result" onClick={() => navigator.clipboard.writeText(result.output).then(() => toast.success('Response copied.')).catch(() => toast.error('Clipboard unavailable.'))}><Copy size={13}/> Copy</Btn><Btn data-testid="studio-save-result" onClick={() => onSave(result)}><Download size={13}/> Save encrypted</Btn></> : null}<span className="studio-latency" data-testid="studio-result-timing">{result.duration_ms ? `${(result.duration_ms / 1000).toFixed(1)}s` : ''}{result.output_tokens ? ` · ${result.output_tokens} output tokens` : ''}</span></div>
      </>}
    </div><div className="studio-output-footnote" data-testid="studio-output-privacy"><LockKeyhole size={13}/><span>Responses stay on this page unless you save them encrypted. A fresh consent is required for every run.</span></div>
  </section>;
};
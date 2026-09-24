import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';
import { streamTask } from '../lib/studio';

export const useStudioRun = ({ refresh, loadReceipts, timeoutSeconds }) => {
  const controller = useRef(null);
  const activeId = useRef(null);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState({});
  const [group, setGroup] = useState('');
  const [activeMode, setActiveMode] = useState('with');
  useEffect(() => () => {
    controller.current?.abort();
    if (activeId.current) api.post(`/studio/runs/${activeId.current}/cancel`).catch(() => {});
  }, []);
  const stop = useCallback(() => {
    if (activeId.current) api.post(`/studio/runs/${activeId.current}/cancel`).catch(() => {});
    controller.current?.abort();
  }, []);
  const run = async ({ payload, agent, memories, mode }) => {
    if (controller.current) return;
    const aborter = new AbortController(); controller.current = aborter;
    const nextGroup = `${agent.id}:${payload.task}`;
    const initial = { status: 'running', output: '', agent, memories, model: '', task: payload.task, mode };
    setResults(previous => nextGroup === group ? { ...previous, [mode]: initial } : { [mode]: initial });
    setGroup(nextGroup); setActiveMode(mode); setBusy(true);
    const update = fn => setResults(previous => ({ ...previous, [mode]: fn(previous[mode] || initial) }));
    const timeout = setTimeout(() => aborter.abort(), ((timeoutSeconds || 90) + 20) * 1000);
    try {
      await streamTask(payload, aborter.signal, (event, details) => {
        if (event === 'started') {
          activeId.current = details.run_id;
          update(old => ({ ...old, ...details, status: 'running' }));
        } else if (event === 'delta') update(old => ({ ...old, output: old.output + details.text }));
        else if (event === 'done') update(old => ({ ...old, ...details, status: 'completed' }));
      });
    } catch (e) {
      update(old => ({ ...old, status: e.name === 'AbortError' ? 'cancelled' : 'failed', error: e.name === 'AbortError' ? 'Task stopped. Context already sent cannot be recalled from the provider.' : e.message }));
    } finally {
      clearTimeout(timeout); controller.current = null; activeId.current = null; setBusy(false);
      await Promise.allSettled([refresh(), loadReceipts()]);
    }
  };
  return { run, stop, busy, results, group, activeMode, setActiveMode };
};
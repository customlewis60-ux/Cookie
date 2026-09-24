import { API_URL } from './api';

export async function taskDigest(task) {
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(task));
  return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, '0')).join('');
}

export async function streamTask(payload, signal, onEvent) {
  const response = await fetch(`${API_URL}/studio/execute`, {
    method: 'POST', signal, cache: 'no-store',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${sessionStorage.getItem('cookie-session')}` },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : 'This task could not be authorized. Review it again.');
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '', completed = false;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n');
      let boundary;
      while ((boundary = buffer.indexOf('\n\n')) >= 0) {
        const block = buffer.slice(0, boundary); buffer = buffer.slice(boundary + 2);
        const event = block.split('\n').find(l => l.startsWith('event: '))?.slice(7);
        const data = block.split('\n').filter(l => l.startsWith('data: ')).map(l => l.slice(6)).join('\n');
        if (!event || !data) continue;
        const details = JSON.parse(data);
        if (event === 'error') throw new Error(details.message);
        if (event === 'done') completed = true;
        onEvent(event, details);
      }
    }
    if (!completed) throw new Error('The AI connection ended before completion. No result was saved.');
  } finally {
    await reader.cancel().catch(() => {});
    reader.releaseLock();
  }
}

export const agentIcons = { personal: 'Personal assistant', coding: 'Coding assistant', research: 'Research assistant', trading: 'Strategy assistant', custom: 'Custom assistant' };
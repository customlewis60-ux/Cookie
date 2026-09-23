import { api } from './api';
import { encrypt } from './crypto';
const memories = [
  { title: 'Personal Profile', category: 'Personal', content: 'I am a product designer building at the intersection of AI and crypto. I prefer thoughtful, concise answers and learn best through practical examples.', privacy: 'shareable' },
  { title: 'Trading Preferences', category: 'Trading', content: 'I prefer high-conviction SOL trades and usually avoid holding more than 5 positions at once. I prioritize risk management over short-term returns.', privacy: 'shareable' },
  { title: 'Developer Preferences', category: 'Work', content: 'My preferred stack is React, TypeScript, Python, and MongoDB. Favor small, readable components, accessible interfaces, and well-tested APIs.', privacy: 'private' },
];
export async function seedDemo(key) {
  const existing = (await api.get('/dashboard')).data;
  if (existing.memories.length || existing.agents.length) return;
  for (const [index, item] of memories.entries()) {
    const { content, ...metadata } = item;
    const memory = (await api.post('/memories', { ...metadata, encrypted_payload: await encrypt(content, key) })).data;
    const agent = (await api.post('/agents', { name: ['Personal AI', 'Trading Agent', 'Coding Agent'][index], developer: 'COOKIE Labs', kind: ['personal', 'trading', 'coding'][index] })).data;
    if (item.privacy === 'shareable') await api.post('/permissions', { agent_id: agent.id, target_type: 'memory', target: memory.id });
  }
}
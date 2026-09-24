import { useState } from 'react';
import { LockKeyhole, ShieldCheck, Pencil } from 'lucide-react';
import { useVault } from '../context/VaultContext';
import { Modal, Btn, Badge } from './Common';
import { Input } from './ui/input';
import { Textarea } from './ui/textarea';
import { toast } from './ui/sonner';
import { encrypt, decrypt, unlock } from '../lib/crypto';
import { api, CATEGORIES, errorMessage } from '../lib/api';
export const MemoryDialog = ({ memory, onClose }) => {
  const { key, user, refresh } = useVault();
  const [mode, setMode] = useState(memory?.id ? 'unlock' : 'edit');
  const [title, setTitle] = useState(memory?.title || '');
  const [category, setCategory] = useState(memory?.category || 'Personal');
  const [privacy, setPrivacy] = useState(memory?.privacy || 'private');
  const [content, setContent] = useState(memory?.content || '');
  const [passphrase, setPassphrase] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const unlockMemory = async e => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const verifiedKey = await unlock(passphrase, user.vault);
      const encrypted = (await api.get(`/memories/${memory.id}`)).data;
      setContent(await decrypt(encrypted.encrypted_payload, verifiedKey)); setMode('view'); setPassphrase(''); await refresh();
    } catch (e) { setError(e.response ? errorMessage(e) : e.message); }
    finally { setBusy(false); }
  };
  const save = async e => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const payload = { title: title.trim(), category, privacy, encrypted_payload: await encrypt(content, key) };
      if (memory?.id) await api.patch(`/memories/${memory.id}`, payload);
      else await api.post('/memories', payload);
      await refresh(); toast.success('Memory encrypted successfully.'); onClose();
    } catch (e) { setError(errorMessage(e)); }
    finally { setBusy(false); }
  };
  return <Modal open onClose={busy ? () => {} : onClose} testId="memory-dialog" wide={mode !== 'unlock'} title={mode === 'unlock' ? 'A private moment.' : mode === 'view' ? title : memory?.id ? 'Edit your memory.' : 'Make a little memory.'} description={mode === 'unlock' ? 'This memory is protected and only available to authorized sessions.' : mode === 'view' ? 'Decrypted only in this browser session.' : 'The context worth carrying with you.'}>
    {mode === 'unlock' ? <form className="form-stack" onSubmit={unlockMemory}><div className="unlock-memory-info"><LockKeyhole size={24}/><span>{title}</span><Badge tone="green">Encrypted</Badge></div><label htmlFor="memory-unlock">Vault passphrase</label><Input data-testid="memory-unlock-passphrase" className="field" id="memory-unlock" type="password" autoComplete="current-password" placeholder="Enter your vault passphrase" value={passphrase} onChange={e => setPassphrase(e.target.value)} required/><Btn data-testid="memory-unlock-submit" busy={busy} type="submit"><LockKeyhole size={16}/> Unlock memory</Btn></form> : mode === 'view' ? <><div className="memory-view-meta"><Badge>{category}</Badge><Badge tone="green"><ShieldCheck size={12}/> Session authorized</Badge></div><div className="decrypted-content ph-no-capture" data-testid="memory-decrypted-content">{content}</div><div className="dialog-actions"><Btn variant="secondary" data-testid="close-memory-view" onClick={onClose}>Lock & close <LockKeyhole size={15}/></Btn><Btn data-testid="edit-memory" onClick={() => setMode('edit')}><Pencil size={15}/> Edit memory</Btn></div></> : <form className="form-stack" onSubmit={save}><label htmlFor="memory-title">Memory title</label><Input id="memory-title" className="field" data-testid="memory-title-input" placeholder="e.g. Trading Preferences" value={title} onChange={e => setTitle(e.target.value)} required maxLength={100}/><label htmlFor="memory-category">Category</label><select id="memory-category" className="field" data-testid="memory-category-select" value={category} onChange={e => setCategory(e.target.value)}>{CATEGORIES.map(c => <option key={c}>{c}</option>)}</select><label htmlFor="memory-content">Memory content</label><Textarea id="memory-content" className="field content-input ph-no-capture" data-testid="memory-content-input" placeholder="What should your AI remember?" value={content} onChange={e => setContent(e.target.value)} required maxLength={50000}/><div className="field-between"><label>Privacy</label><span className="fine-print">Always encrypted</span></div><div className="privacy-options">{['private', 'shareable'].map(v => <label key={v} className={privacy === v ? 'selected' : ''}><input data-testid={`privacy-${v}`} type="radio" name="privacy" value={v} checked={privacy === v} onChange={() => setPrivacy(v)}/>{v === 'private' ? <LockKeyhole size={17}/> : <ShieldCheck size={17}/>}<span><strong>{v === 'private' ? 'Private' : 'Shareable'}</strong><small>{v === 'private' ? 'Only you' : 'Only agents you authorize'}</small></span></label>)}</div><div className="notice" data-testid="memory-encryption-notice"><LockKeyhole size={15}/><span>Content is encrypted before saving. Titles and categories are visible metadata.{privacy === 'private' && memory?.privacy === 'shareable' ? ' Saving as Private removes direct permissions and blocks category access.' : ''}</span></div><div className="dialog-actions"><Btn type="button" variant="secondary" data-testid="cancel-memory" disabled={busy} onClick={onClose}>Cancel</Btn><Btn type="submit" data-testid="save-memory" busy={busy} disabled={!title.trim() || !content.trim()}>{busy ? 'Encrypting memory…' : <><LockKeyhole size={15}/> Save Memory</>}</Btn></div></form>}
    {error && <p role="alert" className="form-error" data-testid="memory-form-error">{error}</p>}
  </Modal>;
};
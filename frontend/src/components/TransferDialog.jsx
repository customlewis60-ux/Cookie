import { useState } from 'react';
import { Upload, LockKeyhole, FileKey2 } from 'lucide-react';
import { useVault } from '../context/VaultContext';
import { Modal, Btn } from './Common';
import { Input } from './ui/input';
import { api, errorMessage } from '../lib/api';
import { unlock, decrypt, encrypt } from '../lib/crypto';
import { toast } from './ui/sonner';
export const TransferDialog = ({ onClose }) => {
  const { key, refresh } = useVault(); const [file, setFile] = useState(null); const [password, setPassword] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  const choose = async e => { setError(''); setFile(null); const f = e.target.files[0]; if (!f) return; try { if (f.size > 10 * 1024 * 1024) throw new Error('Please choose a vault file smaller than 10 MB.'); const json = JSON.parse(await f.text()); if (json.format !== 'cookie-vault' || json.version !== 1 || !json.vault || !Array.isArray(json.memories) || json.memories.length > 1000) throw new Error('This is not a supported COOKIE vault file.'); if (!json.memories.length) throw new Error('This vault has no memories to import.'); setFile({ name: f.name, ...json }); } catch (e) { setError(e instanceof SyntaxError ? 'Invalid JSON. Please choose a COOKIE vault export.' : e.message); } };
  const submit = async e => { e.preventDefault(); setBusy(true); setError(''); try {
    if (file.vault.iterations !== 310000) throw new Error('Unsupported vault encryption settings.');
    const sourceKey = await unlock(password, file.vault); const memories = [];
    for (const m of file.memories) memories.push({ title: m.title, category: m.category, privacy: 'private', encrypted_payload: await encrypt(await decrypt(m.encrypted_payload, sourceKey), key) });
    const result = (await api.post('/vault/import', { memories })).data; await refresh(); toast.success(`${result.imported} memories imported and re-encrypted. All are private.`); onClose();
  } catch (e) { setError(e.response ? errorMessage(e) : e.message === 'The operation failed for an operation-specific reason' ? 'This vault contains damaged encrypted data.' : e.message); } finally { setBusy(false); } };
  return <Modal open onClose={busy ? () => {} : onClose} testId="import-dialog" title="Bring your memory with you." description="Import a COOKIE encrypted vault. Memories are re-encrypted for this vault, in your browser."><form className="form-stack" onSubmit={submit}><label className="file-drop" htmlFor="vault-file"><FileKey2 size={30}/><strong>{file ? file.name : 'Choose an encrypted vault'}</strong><span>{file ? `${file.memories.length} memories` : '.json · up to 10 MB'}</span><input id="vault-file" data-testid="import-file-input" type="file" accept=".json,application/json" onChange={choose}/></label><label htmlFor="import-password">Original vault passphrase</label><Input id="import-password" data-testid="import-passphrase" className="field" type="password" placeholder="Passphrase used for the exported vault" value={password} onChange={e => setPassword(e.target.value)} required/><div className="notice"><LockKeyhole size={16}/><span>Imported memories start private. Agent permissions and API keys are never imported. Existing memories are kept.</span></div>{error && <p role="alert" className="form-error" data-testid="import-error">{error}</p>}<Btn data-testid="confirm-import" type="submit" busy={busy} disabled={!file}>{busy ? 'Re-encrypting your memories…' : <><Upload size={16}/> Import Memory</>}</Btn></form></Modal>;
};
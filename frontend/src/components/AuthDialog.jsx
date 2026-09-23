import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { LockKeyhole, ArrowRight, Wallet } from 'lucide-react';
import { Input } from './ui/input';
import { Modal, Btn } from './Common';
import { useVault } from '../context/VaultContext';
import { setupVault, unlock } from '../lib/crypto';
import { api, errorMessage, shortAddress } from '../lib/api';
import { seedDemo } from '../lib/demo';
export const AuthDialog = ({ open, onClose, demo = false, redirect = true }) => {
  const { user, connect, setKey, refresh } = useVault();
  const [identity, setIdentity] = useState(user);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  useEffect(() => {
    if (!open) { setPassword(''); setConfirm(''); setError(''); return; }
    setPassword(''); setConfirm(''); setError('');
    if (user) setIdentity(user);
    else { setBusy(true); connect().then(setIdentity).catch(e => setError(errorMessage(e))).finally(() => setBusy(false)); }
    // A connection is established once each time the dialog opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);
  const existing = Boolean(identity?.vault);
  const submit = async e => {
    e.preventDefault(); setError('');
    if (!existing && password !== confirm) { setError('Your passphrases do not match.'); return; }
    setBusy(true);
    try {
      let key;
      if (existing) key = await unlock(password, identity.vault);
      else {
        const result = await setupVault(password);
        await api.post('/vault/setup', result.vault); key = result.key;
      }
      if (demo && !existing) await seedDemo(key);
      await refresh(); setKey(key); onClose();
      if (redirect) navigate('/app');
    } catch (e) { setError(e.response ? errorMessage(e) : e.message); }
    finally { setBusy(false); }
  };
  return <Modal open={open} onClose={onClose} testId="auth-dialog" title={existing ? 'Welcome back to your vault.' : 'A little memory. Entirely yours.'} description={existing ? 'Unlock your encrypted memory with your vault passphrase.' : 'Create a passphrase. Your memory is encrypted in your browser before it leaves your device.'}>
    <div className="identity-preview" data-testid="demo-identity"><Wallet size={20}/><div><strong>Demo wallet</strong><span className="mono">{identity ? shortAddress(identity.wallet_address) : 'Connecting…'}</span></div><span className="mini-tag">DEMO</span></div>
    <form onSubmit={submit} className="form-stack">
      <label htmlFor="vault-passphrase">Vault passphrase</label><Input id="vault-passphrase" data-testid="vault-passphrase" type="password" className="field" autoComplete={existing ? 'current-password' : 'new-password'} minLength={existing ? 1 : 10} maxLength={200} required value={password} onChange={e => setPassword(e.target.value)} placeholder={existing ? 'Enter your passphrase' : 'At least 10 characters'}/>
      {!existing && <><label htmlFor="vault-confirm">Confirm passphrase</label><Input id="vault-confirm" data-testid="vault-confirm" type="password" className="field" autoComplete="new-password" required value={confirm} onChange={e => setConfirm(e.target.value)} placeholder="Enter it once more"/></>}
      <div className="notice" data-testid="passphrase-notice"><LockKeyhole size={16}/><span>{existing ? 'Your key stays in this browser session.' : 'Keep your passphrase safe. COOKIE cannot recover it. You will need it to open exported memories.'}</span></div>
      {error && <p role="alert" className="form-error" data-testid="auth-error">{error}</p>}
      <Btn data-testid="vault-submit" type="submit" busy={busy} disabled={!identity}>{busy ? 'Preparing your encrypted vault…' : existing ? 'Unlock vault' : demo ? 'Create vault & explore demo' : 'Create encrypted vault'}{!busy && <ArrowRight size={16}/>}</Btn>
    </form>
    <p className="fine-print" data-testid="demo-auth-disclosure">Demo identity · No wallet signature or blockchain transaction. Encrypted storage is hosted by COOKIE. Titles and categories are visible metadata.</p>
  </Modal>;
};
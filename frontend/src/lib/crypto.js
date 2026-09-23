const encode = value => btoa(String.fromCharCode(...value));
const decode = value => Uint8Array.from(atob(value), c => c.charCodeAt(0));
export const createSalt = () => encode(crypto.getRandomValues(new Uint8Array(16)));
export async function deriveKey(passphrase, salt) {
  const material = await crypto.subtle.importKey('raw', new TextEncoder().encode(passphrase), 'PBKDF2', false, ['deriveKey']);
  return crypto.subtle.deriveKey({ name: 'PBKDF2', salt: decode(salt), iterations: 310000, hash: 'SHA-256' }, material, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']);
}
export async function encrypt(content, key) {
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const payload = await crypto.subtle.encrypt({ name: 'AES-GCM', iv }, key, new TextEncoder().encode(content));
  const bytes = new Uint8Array(payload);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
  return { algorithm: 'AES-GCM', iv: encode(iv), ciphertext: btoa(binary) };
}
export async function decrypt(payload, key) {
  const data = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: decode(payload.iv) }, key, decode(payload.ciphertext));
  return new TextDecoder().decode(data);
}
export async function unlock(passphrase, vault) {
  try {
    const key = await deriveKey(passphrase, vault.salt);
    if (await decrypt(vault.verifier, key) !== 'COOKIE_VAULT_V1') throw new Error();
    return key;
  } catch { throw new Error('Incorrect passphrase. Your vault remains locked.'); }
}
export async function setupVault(passphrase) {
  const salt = createSalt();
  const key = await deriveKey(passphrase, salt);
  return { key, vault: { salt, verifier: await encrypt('COOKIE_VAULT_V1', key), iterations: 310000 } };
}
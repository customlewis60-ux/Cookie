/** COOKIE v0.1 local adapter. Not a published npm package.
 * Keep API credentials in a trusted developer runtime.
 * Encryption/decryption adapters require separate user authorization.
 */
export class CookieMemory {
  constructor({ baseUrl, apiKey, encrypt, decrypt }) {
    if (!baseUrl || !apiKey) throw new Error('baseUrl and apiKey are required');
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.apiKey = apiKey;
    this.encrypt = encrypt;
    this.decrypt = decrypt;
  }
  async request(path, method = 'GET', body) {
    const response = await fetch(this.baseUrl + path, {
      method,
      headers: { Authorization: `Bearer ${this.apiKey}`, 'Content-Type': 'application/json' },
      ...(body ? { body: JSON.stringify(body) } : {})
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || `COOKIE request failed (${response.status})`);
    return result;
  }
  async getMemory({ category } = {}) {
    // User and agent are securely bound by the key, not caller parameters.
    const memories = await this.request('/v1/memory' + (category ? '?category=' + encodeURIComponent(category) : ''));
    if (!this.decrypt) return memories; // Encrypted envelopes; not readable AI context.
    return Promise.all(memories.map(async memory => ({
      id: memory.id, title: memory.title, category: memory.category,
      content: await this.decrypt(memory.encrypted_payload)
    })));
  }
  async storeMemory({ title, category, content, privacy = 'private' }) {
    if (!this.encrypt) throw new Error('A separately authorized encryption adapter is required');
    return this.request('/v1/memory', 'POST', {
      title, category, privacy, encrypted_payload: await this.encrypt(content)
    });
  }
  revokeAccess() {
    return this.request('/v1/permissions/revoke', 'POST');
  }
}
# COOKIE — Product Requirements & Implementation Record

## Original problem statement
Build a complete working web application called **COOKIE**, a private, portable memory layer for AI agents: “COOKIE lets users own, encrypt, control, and carry their AI memory between different AI agents.” It is not a chatbot, tracking product, privacy coin, or a generic crypto wallet. The first deliverable is a credible functional MVP, not merely a token landing page.

Primary tagline: **Private Memory for AI**. Secondary tagline: **Own your AI memory. Carry it between agents.** Central principle: **Your AI can change. Your memory doesn’t have to.** AI developers integrate COOKIE into their own agents; COOKIE does not need to directly control ChatGPT or Claude.

### Explicit user choices
- Fully working isolated **demo wallet**, with actual browser encryption and working permissions, no blockchain claims.
- **Vault passphrase** for browser encryption and portable exports.
- Additional design request, verbatim: “Buat tampilannya elegant dengan contoh gambar gambar bergerak seperti demo usecase ambil pilihan logo modelan cookie nya itu adalah kue gitu buat keren”.
- Original visual specification: near-black, white type, warm cookie/brown and amber/gold accents, subtle green verification states, glass-like panels, soft borders, minimal gradients, technical typography, recognizable cookie with encrypted chip/core. Avoid casino/token imagery and unlicensed Zcash branding.
- Communicate with the user in Indonesian. Product copy retains the supplied English language and taglines.

## Personas
1. AI power user: owns context across assistants, manages private/shareable memories, grants and revokes access.
2. Developer: connects an agent, creates scoped credentials, integrates the HTTP API and local JS adapter, inspects real request logs.
3. Privacy-conscious evaluator: tries the isolated demo, understands the encryption boundary and current protocol limitations.

## Core requirements (static)
1. Landing: COOKIE brand, product taglines, Create Memory and Explore Demo, user→COOKIE→agents diagram, problem/solution, Store/Authorize/Carry, privacy, developer docs, final CTA.
2. Demo wallet identity: connect, full/short address, disconnect, clear disclosure that backend and authentication are centralized MVP infrastructure; future EVM/Solana signature support separate.
3. Workspace routes: Overview, Memory, Agents, Permissions, Activity, API, Settings.
4. Memory CRUD: title, category (Personal, Preferences, Work, Trading, Projects, Knowledge, AI Context, Custom), content, Private default / Shareable, encryption status, unlock before view, edit/delete confirmations.
5. Real client-side encryption: modern Web Crypto AES-GCM; no plaintext content stored or returned by backend, no private text in URLs/query strings/logs.
6. Agent identity and connection status, developer, identifiers, authorized memories, last activity; demo identities clearly separate from real external AI integrations.
7. Specific memory and category access control. Private memories cannot be accessed by agents. Revocation blocks future access. Permission history logged.
8. Activity: creation, access, update, deletion, grants/revocations, connections, exports/imports, key changes.
9. Portable encrypted vault export/import; original passphrase required; no claim of universal AI interoperability.
10. API/SDK developer documentation, actual scoped key creation/rotation/revocation, secret exposure only to the owner at issuance; never embed credentials in frontend integration examples.
11. Real developer request counts, reads/writes/error rate and request log. No fabricated production metrics.
12. Honest roadmap: ZK verification is unimplemented future protocol architecture. No fake proofs, transaction hashes, chain activity or endorsement. COOKIE is independent of Zcash.
13. Usable demo seeds three real browser-encrypted sample memories, three demo agent identities and two real permission grants.
14. Responsive screens, meaningful animation, loading/success/error states, confirmation dialogs, and descriptive test IDs for key workflows.

## Architecture decisions
- **Frontend:** React 19, React Router, Shadcn/Radix UI, Sonner, Lucide, Framer Motion. Manrope / DM Sans / IBM Plex Mono. Generated cookie-chip hero bitmap, CSS cookie mark and animated illustrative context flows.
- **Backend:** FastAPI, Pydantic, Motor, MongoDB. Existing supervisor-managed services and protected environment values retained.
- **URLs:** Browser requests exclusively derive from `REACT_APP_BACKEND_URL`; backend API is mounted under `/api`. Database exclusively uses configured `MONGO_URL` and `DB_NAME`.
- **Demo authentication:** browser creates a random 256-bit device credential in localStorage; server stores its SHA-256 hash. Random demo wallet address is not a chain account. Opaque random bearer sessions are hashed server-side and expire after seven days. Session token is in sessionStorage. Disconnect revokes the session; reconnect with the same device credential restores the same identity. Cross-browser portability uses an encrypted vault export, not a fabricated wallet signature.
- **Vault cryptography:** 256-bit non-extractable AES-GCM CryptoKey derived through PBKDF2-SHA-256, 310,000 iterations, random 128-bit salt. Every envelope uses a fresh 96-bit nonce. An encrypted constant verifies passphrases locally. Only salt, iteration count and encrypted verifier are stored server-side. Passphrase and raw key never go to the API. CryptoKey remains in React session memory; refresh/manual lock requires another unlock. Auth-dialog passphrase inputs are cleared when the dialog closes.
- **Metadata boundary:** titles, categories, identities, privacy settings and access logs are visible server-side; memory content is ciphertext. This boundary is explicitly described in forms, Settings and documentation. Default template analytics/session recording scripts were removed.
- **Permissions:** memory or category target, bound to user+agent, read scope, created/revoked timestamps. Category permissions apply to current/future shareable memories. An individual grant and a category grant are additive; revoking one does not remove another matching grant. Private status always blocks agent access. Disconnect revokes every permission for the agent; reconnect never restores grants.
- **API keys:** random `ck_demo_` secrets scoped to one owner and one agent; hashes only persisted. Raw secrets appear once and may be re-revealed only within that page's ephemeral component state. Keys may optionally authorize encrypted writes, which still require an active category permission. Rotation invalidates the prior secret. API identity cannot be overridden by user/agent request parameters.
- **Agent context boundary:** the API returns encrypted envelopes, never plaintext. Readable context requires a separately user-authorized decryption adapter in a trusted runtime. Automatic key distribution to external agents is intentionally not implemented.
- **Import:** validate COOKIE v1 JSON and file limits; derive source key with original passphrase; decrypt locally and re-encrypt with destination key; import all memories as Private. Existing memories remain. Permissions and credentials are not imported.
- **Protocol extensibility:** `backend/protocol.py` contains separate IdentityProvider and PrivacyProofProvider interfaces. No concrete ZK, signed EVM/Solana, or Zcash adapter is installed or falsely claimed.

## Data model
- User: random `cookie_*` id, device credential hash, demo wallet address, creation time, encrypted vault settings.
- Session: token hash, user id, expiry.
- Memory: random id, owner id, title/category/privacy, AES-GCM envelope, creation/update/access times.
- Agent: random id, API identifier, owner, name/developer/kind/type/status, timestamps.
- Permission: random id, owner/agent, target type/value, scope, created/revoked timestamps.
- Activity: event id, owner/agent/memory references, action, metadata title, ISO UTC timestamp.
- API Key: random id, owner/agent, name/prefix/hash, write flag, created/revoked/last-used timestamps.
- API Request: owner/agent, request method/path/status/time. No private request content logged.

## Implemented — 2026-09-23
- Complete landing with generated cookie-chip visual, subtle float animation, three selectable animated use cases, privacy section and developer CTA.
- Demo wallet setup, returning identity reconnection, passphrase-protected vault initialization/unlock, manual lock and session disconnect.
- All seven workspace pages and public documentation route, responsive mobile sidebar.
- Real browser-encrypted memory creation/view/edit/delete, category/search/privacy filters, visible encrypted status and actual access counts.
- Demo seed of three memories and three agents; default private developer memory and two explicit sample permission grants.
- Custom/demo agent registration, Research Agent discovery, connection state changes, permission revocation on disconnect.
- Per-memory authorization dialog, category permission matrix, confirmation workflows and permission history.
- Persisted activity timeline with event filters/search.
- Encrypted export and cross-vault-capable client-side import/re-encryption, invalid-file and wrong-passphrase handling, all-memory deletion with confirmation.
- Agent-scoped real API keys, one-time secret view, rotation/revocation, optional write capability, real API tester and request metrics.
- Working GET/POST memory API, self-revocation endpoint, HTTP documentation and downloadable dependency-free `cookie-sdk.js` adapter. Proposed npm import is explicitly not published.
- Future protocol interfaces and accurate ZK/Zcash status documentation.
- Refactored developer modal content into `DeveloperDialogs.jsx`, a single persistent Radix dialog.
- Fixed Tailwind/Radix entrance keyframe name collision (`cookie-enter` is now independent).
- Fixed lingering modal close overlays intercepting subsequent clicks by removing exit animations; entrance animation and focus handling remain.

## Validation — 2026-09-23
- Production build succeeded (`/app/cookie-build.log`).
- External `/api/health` returns healthy database-backed service status.
- Testing agent completed backend regression: **11/11 passing**. Covers demo auth, setup conflict, memory CRUD, private-memory restrictions, scoped reads, disconnected agent denial, rotation, category+write permission enforcement, cross-owner access denial and missing authentication.
- Testing agent verified frontend demo setup, three-memory seed, wrong/correct unlock, encrypted network payloads, create/view/edit, export schema, invalid/wrong-passphrase import, successful import/re-encryption and mobile 390px no viewport overflow.
- Original test report: `/app/test_reports/iteration_1.json`. Its Developer-modal blocker is resolved by subsequent implementation and targeted verification.
- Main agent repeated create-key → close-secret → open tester **three times**, each returned **200 / one authorized encrypted memory**.
- Main agent verified disconnect → API tester **401 denied**, then reconnect → API tester **200 / zero authorized memories**, proving old permissions were not resurrected.
- Screenshots: `/app/landing-refined.jpg`, `/app/auth-refined.jpg`, `/app/developer-verified.jpg`, `/app/memory-verified.jpg`. Screenshots are build evidence, not user vault exports.
- No unresolved core blocking defect after targeted regression.
- Finalization validator initially lacked ESLint 9 flat configuration. Added project/root flat configs, handled cmdk's documented custom attribute, removed unused imports and escaped intentional SDK preview text nodes. No runtime behavior changed.

## Current honest limitations
- Demo browser identity, not signed wallet authentication; centralized storage and authorization.
- Sample agents are demo identities, not ChatGPT/Claude integrations or autonomous running models.
- Developer API and local JS adapter work; published npm SDK and automatic owner-to-agent decryption/key exchange do not exist yet.
- No ZK circuit, proof verification, blockchain transaction, or Zcash integration.
- No production security certification, independent cryptographic audit, rate-limit hardening or decentralized storage claims.
- Activity shows the latest 200 events; stats use actual developer endpoint requests, not demo fabricated numbers.

## Prioritized backlog / next tasks
### P0 before real public multi-user production
- Replace browser-bound demo identity with nonce-based signed wallet authentication through the IdentityProvider abstraction.
- Independent security review, rate limits/quotas, session lifecycle hardening, retention and operational recovery policy.
- Design and implement explicit user-authorized agent decryption/key delivery and rotation; maintain ciphertext-only API boundary.
### P1 product expansion
- Connect one real external developer-controlled agent end-to-end with a consented decryption adapter.
- Publish/version the SDK, add adapter examples and compatibility tests.
- Vault passphrase rotation with client-side re-encryption and carefully designed recovery options.
- Paginated long-term activity history and richer category organization.
### P2 future protocol / maintenance
- Concrete ZK proof provider, only after a real circuit and verifier exist; independent optional privacy ecosystem modules.
- Solana/EVM provider modules and optional decentralized storage.
- Split central stylesheet into route-level style modules as the product grows.
- Improve agent onboarding through a guided permission-and-key setup sequence.

## Product enhancement suggestion
A consent-first agent onboarding flow could turn “connect agent → choose exact context → run an authorized request” into one short guided journey, helping developers reach a meaningful integration faster without weakening privacy boundaries.

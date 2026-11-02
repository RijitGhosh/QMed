# Architecture
Client (CustomTkinter) ⇄ REST/JSON (`requests`) ⇄ Flask server ⇄ SQLite (SQLAlchemy; PostgreSQL-compatible models) + `storage/transfers/*.qmed`.

* **common/bb84.py** – textbook BB84: qubit = (bit, basis); wrong-basis measurement is random; optional intercept-resend Eve; sifting; random 25 % test sample; QBER = mismatches / sample.
* **common/crypto.py** – HKDF-SHA256 key derivation, AES-256-GCM, HMAC key confirmation, X25519 key wrapping, scrypt-protected private key.
* **server/** – app factory, models (`users`, `sessions`, `transfers`, `bb84_sessions`, `activity_logs`), token auth, per-transfer authorization, random-name file storage, standard JSON errors, rotating logs.
* **client/encryption.py** – the send/receive crypto workflow (no GUI imports, unit-tested).

## Send flow
1. Client runs BB84 locally (Alice/Bob/Eve simulated). If QBER > threshold or key confirmation fails → abort, report a *Blocked* attempt (statistics only), upload nothing.
2. Pass: key = HKDF(remaining sifted bits); mutual HMAC key confirmation; AES-256-GCM encrypt (AAD binds sender id, recipient id, SHA-256).
3. Key wrapped to the recipient's X25519 public key; upload ciphertext + nonce + wrapped key + BB84 statistics. Server re-validates (ciphertext length, QBER arithmetic, threshold ≤ server limit).
4. Recipient: authenticate → download ciphertext → fetch wrapped key → unwrap with private key (unlocked from password at login, memory only) → AES-GCM decrypt → SHA-256 compare → report result.

Identity always comes from the server-side session token, never from a typed username or client role toggle.

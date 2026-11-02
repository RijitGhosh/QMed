# QMed — Quantum-Secure Medical Data Sharing System

An **educational** desktop application (Python, CustomTkinter + Flask + SQLite) that shows how a medical document can be
exchanged with authenticated encryption while a **simulated BB84** key exchange detects an eavesdropper.

> **BB84 is simulated in software for educational demonstration. No physical quantum hardware is used.**
> QMed is not clinically certified, not HIPAA/GDPR certified, not real quantum communication and not production-ready
> healthcare infrastructure. Use fictional documents only.

## How it works (short)
`BB84 simulation → sifted key → remove QBER test bits → HKDF-SHA256 → 256-bit key → AES-256-GCM (encrypted on the sender's PC)`.
The key is wrapped for the recipient (X25519 + HKDF + AES-GCM). The server stores only ciphertext + a wrapped key it cannot open.
Eve ON → QBER ≈ 25 % → above the threshold (default 11 %) → exchange aborted, **nothing is uploaded**, transfer recorded as *Blocked*.

## Demo on One Laptop (No Second Computer Needed)
Requires Python 3.11+ (on Linux also `sudo apt install python3-tk`).

1. **Install dependencies** (from the project folder):
   ```bash
   python -m venv .venv
   # Windows:  .venv\Scripts\activate        Linux/macOS:  source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. **Start the backend** (terminal 1, leave it running):
   ```bash
   python run_server.py
   ```
   It prints `Local: http://127.0.0.1:5000`. The database, folders and secret key are created automatically on first run.
3. **Launch the client** (terminal 2):
   ```bash
   python run_client.py
   ```
4. **Create two accounts** through the UI (*Create Account*): e.g. `dr_smith` (Doctor) and `john_doe` (Patient).
   (Optional shortcut: `python seed_demo_data.py` creates `demo_doctor` / `demo_patient` and sample fictional files in `demo_data/`.)
5. **Send a file from Account A to Account B**: sign in as A → *Send Document* → choose a fictional file (e.g. `demo_data/demo_report_1.txt`)
   → pick the recipient → *Run BB84 Security Check* (Eve OFF) → *Continue* → *Encrypt & Send*. The success screen appears only after the server confirms.
6. **Log out** (sidebar *Logout*). The token is revoked and all client-side authenticated state and keys are cleared.
7. **Log in as Account B** (same window, same laptop).
8. **Decrypt, verify, save**: *Inbox* → *Decrypt* → *Start Decryption* → check `Integrity: VERIFIED` (original vs recovered SHA-256) → *Save Recovered File*.

**Eve demonstration:** *BB84 Security Lab* → *Run Without Eve* (QBER ≈ 0 %, PASS) then *Run With Eve* (QBER ≈ 25 %, BLOCKED).
In *Send Document* switch *Simulate Eavesdropper (Eve)* ON to see the transfer blocked and logged.

## Optional Two-Laptop Demo
1. Laptop 1 (server): keep `QMED_HOST=0.0.0.0` (default), run `python run_server.py`, note the `Network: http://<HOST-IP>:5000` line.
   Allow inbound TCP port 5000 in the OS firewall (Windows: “Allow an app” / inbound rule for Python).
2. Both laptops must be on the same trusted Wi-Fi/LAN. Laptop 2 needs the project + `pip install -r requirements.txt`.
3. On each client: sign-in screen → **Server settings** (or *Settings → Change Server URL*) → enter `http://<HOST-IP>:5000` → Save.
   Nothing is hard-coded; you can also set `QMED_SERVER_URL` in the environment.
4. Register/sign in different accounts on each laptop and send/receive exactly as above.

⚠ Plain HTTP is only suitable for a controlled classroom demo. A real deployment needs TLS and stronger operational security.

## Configuration
Copy `.env.example` to `.env` (host, port, database URL, session hours, max file MB, allowed types, QBER threshold, password rules).
The server secret is auto-generated to `data/server_secret.key` if `QMED_SECRET_KEY` is empty. Never commit `.env` or `data/`.
Server-controlled settings (QBER limit, file limits, password policy) are shown read-only in *Settings*; theme, server URL and BB84 defaults are local.

## Tests
```bash
python -m pytest
```
36+ tests: authentication, authorization, path traversal / size / extension checks, encrypted storage, BB84 (Eve OFF vs ON, QBER, threshold),
AES-GCM (tamper / wrong key), full sender → logout → recipient flow.

## Project layout
`common/` (BB84 simulation, crypto, validation) · `server/` (Flask API, SQLAlchemy models, auth, storage, logging) ·
`client/` (CustomTkinter UI: `screens/`, `components/`, `bb84_view.py`, `api_client.py`) · `tests/` · `docs/`.
Logs: `logs/application.log`, `logs/backend.log`, `logs/error.log` (no passwords, tokens, keys or document content).
See `docs/architecture.md`, `docs/security.md`, `docs/bb84_explanation.md`, `docs/demo_guide.md`.

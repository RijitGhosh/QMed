# Security model & limitations
**Considered:** unauthorised login (scrypt + random salt, throttling, expiring server-side tokens stored as HMAC hashes), access to others' transfers (403/404 checks), ciphertext/metadata tampering (GCM tag + AAD), unsafe uploads (random server file names, extension/size checks, traversal-safe storage), simulated eavesdropping (QBER test), secrets in logs (never logged).

**Trust model / prototype limitations (honest list):**
* BB84 is a software simulation run inside the sender's client; the server records client-reported statistics and only sanity-checks them (it cannot prove the simulation ran honestly). Real QKD provides keys from a physical channel.
* The server relays the recipient's *wrapped* key; it cannot open it, but the account password is sent to the server at login (plain HTTP in the demo), and the password-protected private key is stored on the server. A malicious server operator or network attacker is out of scope.
* No TLS, no email verification, no HSM/KMS, no account recovery, in-memory login throttle only.
* Not clinically certified, not HIPAA/GDPR compliant, not production-ready. Use fictional data only.

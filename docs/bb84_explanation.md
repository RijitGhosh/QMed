# BB84 (as simulated)
1. Alice picks random bits and random bases (+ or ×). 2. Bob picks random bases and measures. Same basis → correct bit; different basis → random bit.
3. Optional Eve measures with random bases and resends – in a wrong basis (50 %) she randomises the bit, so Bob errs half of the time there → ≈ 25 % errors on the sifted key.
4. Alice and Bob publicly compare bases and keep matching positions (≈ 50 %). 5. They compare a random 25 % sample: QBER = mismatches / sample.
6. QBER ≤ threshold (default 11 %, configurable educational value) → PASS; else abort. 7. Sample bits are discarded; the rest is key material → HKDF-SHA256 → AES key.
No real quantum states exist in this program.

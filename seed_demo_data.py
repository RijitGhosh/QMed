"""Optional demo data: creates two clearly-labelled DEMO accounts and fictional sample documents.

Run explicitly (nothing is created automatically):
    python seed_demo_data.py                 # prompts for a password (or press Enter to generate one)
    python seed_demo_data.py --docs-only     # only write demo_data/*.txt
Accounts: demo_doctor (Doctor), demo_patient (Patient).  Fictional data only - never real patients.
"""
from __future__ import annotations

import argparse
import getpass
import secrets
import string
from pathlib import Path

from client.encryption import new_account_keys
from common.validation import PasswordPolicy, check_password
from server.app import create_app
from server.config import load_settings
from server.models import User
from server.security import hash_password

DEMO_DIR = Path(__file__).parent / "demo_data"
REPORT = """QMed Demonstration Medical Report

Patient Name: Demo Patient
Patient ID: DEMO-{n:03d}
Age: 42

This document contains fictional information created
for demonstration purposes only.

Diagnosis:
Example condition

Notes:
This report is not real medical data.
"""


def write_docs() -> None:
    DEMO_DIR.mkdir(exist_ok=True)
    for n in (1, 2, 3):
        (DEMO_DIR / f"demo_report_{n}.txt").write_text(REPORT.format(n=n))
    (DEMO_DIR / "demo_labs.csv").write_text("test,value,unit\nDEMO-A,1.0,units\nDEMO-B,2.0,units\n")
    print(f"Fictional demo documents written to {DEMO_DIR}")


def generate_password() -> str:
    alphabet = string.ascii_letters + string.digits
    while True:
        pw = "".join(secrets.choice(alphabet) for _ in range(14))
        if not check_password(pw, PasswordPolicy()):
            return pw


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs-only", action="store_true")
    args = ap.parse_args()
    write_docs()
    if args.docs_only:
        return
    settings = load_settings()
    app = create_app(settings)
    pw = getpass.getpass("Choose a password for the demo accounts (Enter = generate one): ")
    generated = not pw
    if generated:
        pw = generate_password()
    problems = check_password(pw, settings.password_policy)
    if problems:
        raise SystemExit("Password rejected: " + " ".join(problems))
    db = app.extensions["qmed_db"].session()
    for username, name, role in (("demo_doctor", "Dr. Demo Doctor", "Doctor"), ("demo_patient", "Demo Patient", "Patient")):
        if db.query(User).filter_by(username=username).first():
            print(f"{username} already exists - skipped")
            continue
        import json
        pub, blob = new_account_keys(pw)
        h, salt = hash_password(pw)
        db.add(User(full_name=name, username=username, email=f"{username}@demo.invalid", password_hash=h, password_salt=salt,
                    role=role, department="DEMO ACCOUNT", public_key=pub, encrypted_private_key=json.dumps(blob)))
        print(f"Created DEMO account: {username} ({role})")
    db.commit()
    if generated:
        print(f"\nGenerated demo password (shown once): {pw}")
    print("These are demonstration accounts. Delete data/qmed.db to remove them.")


if __name__ == "__main__":
    main()

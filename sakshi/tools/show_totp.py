import os
import sys

# Dynamically locate sakshi/backend and its venv site-packages
possible_backend_dirs = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "sakshi", "backend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "sakshi", "backend")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")),
    os.path.abspath(r"E:\criminal analysis project\sakshi\backend")
]

backend_dir = None
for d in possible_backend_dirs:
    if os.path.exists(d):
        backend_dir = d
        break

if backend_dir and backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Add venv site-packages so any Python interpreter can import pyotp & qrcode
if backend_dir:
    site_packages = os.path.join(backend_dir, "venv", "Lib", "site-packages")
    if os.path.exists(site_packages) and site_packages not in sys.path:
        sys.path.insert(0, site_packages)

import pyotp
import sqlite3

# Pre-seeded secrets for official roles
DEFAULT_SECRETS = {
    "ig@demo.in": ("NB2HI4DTHIXS653VNB2HI4DTHIXS653V", "IG V. Sharma (Range)"),
    "spdysp@demo.in": ("JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP", "SP A. Kashyap (Durg)"),
    "spraipur@demo.in": ("KRSXG5CTMVRXEZLUKRSXG5CTMVRXEZLU", "SP R. Sen (Raipur)"),
    "cybercell@demo.in": ("MZXW6YTBOJRGC4TGNRXWO33PN5XW4===", "Insp. P. Nayak (Cyber)"),
    "headconstable@demo.in": ("NBSWY3DPEHPK3PXPJBSWY3DPEHPK3PX", "HC S. Deshmukh"),
    "constable@demo.in": ("OB2HI4DTHIXS653VNB2HI4DTHIXS653", "Constable R. Verma"),
    "auditor@demo.in": ("ORSXG5CTMVRXEZLUKRSXG5CTMVRXEZL", "Auditor M. Raman")
}

def show_all_totp():
    print("=" * 65)
    print("SAKSHI OFFICIAL MFA TOTP CODES (Presenter Reference)")
    print("=" * 65)
    
    # Check DB if available
    db_path = os.path.join(backend_dir, "sakshi.db") if backend_dir else None
    db_secrets = {}
    if db_path and os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("CREATE TABLE IF NOT EXISTS user_totp (email TEXT PRIMARY KEY, secret TEXT NOT NULL, enrolled INTEGER DEFAULT 0)")
            conn.commit()
            cur.execute("SELECT email, secret, enrolled FROM user_totp")
            for r in cur.fetchall():
                db_secrets[r["email"]] = (r["secret"], bool(r["enrolled"]))
            conn.close()
        except Exception:
            pass

    for email, (default_sec, label) in DEFAULT_SECRETS.items():
        if email in db_secrets:
            secret, enrolled = db_secrets[email]
            status_label = "Enrolled" if enrolled else "Initial Enrolment"
        else:
            secret = default_sec
            status_label = "Initial Enrolment"
            
        totp = pyotp.TOTP(secret)
        code = totp.now()
        print(f"User:  {email} ({label})")
        print(f"Code:  {code}  [Status: {status_label}]")
        print(f"Key:   {secret}")
        print("-" * 65)

if __name__ == "__main__":
    show_all_totp()

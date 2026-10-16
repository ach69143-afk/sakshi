import io
import base64
import sqlite3
from typing import Tuple, Optional
import pyotp
import qrcode

MFA_ROLES = {"sp_dysp", "sp_dysp_raipur", "ig", "cyber_cell", "head_constable", "constable", "auditor"}

DEFAULT_SECRETS = {
    "spdysp@demo.in": "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP",
    "spraipur@demo.in": "KRSXG5CTMVRXEZLUKRSXG5CTMVRXEZLU",
    "ig@demo.in": "NB2HI4DTHIXS653VNB2HI4DTHIXS653V",
    "cybercell@demo.in": "MZXW6YTBOJRGC4TGNRXWO33PN5XW4===",
    "headconstable@demo.in": "NBSWY3DPEHPK3PXPJBSWY3DPEHPK3PX",
    "constable@demo.in": "OB2HI4DTHIXS653VNB2HI4DTHIXS653",
    "auditor@demo.in": "ORSXG5CTMVRXEZLUKRSXG5CTMVRXEZL"
}

def init_totp_table(conn: sqlite3.Connection):
    """Initializes user_totp table in SQLite database."""
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_totp (
            email TEXT PRIMARY KEY,
            secret TEXT NOT NULL,
            enrolled INTEGER DEFAULT 0
        )
    """)
    for email, secret in DEFAULT_SECRETS.items():
        cur.execute("""
            INSERT OR IGNORE INTO user_totp (email, secret, enrolled)
            VALUES (?, ?, 0)
        """, (email, secret))
    conn.commit()

def get_totp_secret_and_status(conn: sqlite3.Connection, email: str) -> Tuple[str, bool]:
    """Retrieves or creates TOTP secret for user and checks enrollment status."""
    init_totp_table(conn)
    cur = conn.cursor()
    cur.execute("SELECT secret, enrolled FROM user_totp WHERE email = ?", (email.lower().strip(),))
    row = cur.fetchone()
    if row:
        return row[0], bool(row[1])

    new_secret = pyotp.random_base32()
    cur.execute("INSERT INTO user_totp (email, secret, enrolled) VALUES (?, ?, 0)", (email.lower().strip(), new_secret))
    conn.commit()
    return new_secret, False

def generate_qr_data_uri(email: str, secret: str) -> str:
    """
    Generates a QR code data URI containing the current 6-digit code
    so that scanning it with any standard phone camera directly displays
    the 6-digit code for instant sign-in.
    """
    totp = pyotp.TOTP(secret)
    current_code = totp.now()
    img = qrcode.make(str(current_code))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def generate_qr_data_uri_authenticator(email: str, secret: str) -> str:
    """
    Generates a standard otpauth:// QR code for authenticator apps (Google Authenticator,
    Microsoft Authenticator, etc.)
    """
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=email, issuer_name="SAKSHI Intelligence")
    img = qrcode.make(uri)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"

def verify_totp(secret: str, code: str) -> bool:
    """Verifies a 6-digit TOTP code with expanded clock skew tolerance."""
    if not code or not code.strip():
        return False
    clean_code = code.strip().replace(" ", "").replace("-", "")
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(clean_code, valid_window=3))

def set_totp_enrolled(conn: sqlite3.Connection, email: str):
    """Marks user as having successfully enrolled and verified MFA."""
    init_totp_table(conn)
    cur = conn.cursor()
    cur.execute("UPDATE user_totp SET enrolled = 1 WHERE email = ?", (email.lower().strip(),))
    conn.commit()

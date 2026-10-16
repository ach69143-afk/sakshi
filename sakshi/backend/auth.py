import hashlib
import os
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Set
import jwt
from fastapi import HTTPException, Header, Depends
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "sakshi_jwt_secret_key_2026_durg_chhattisgarh_secure")
JWT_ALGORITHM = "HS256"
PASSWORD_SALT = "sakshi_salt_2026_evidence_custody"

def hash_password(password: str) -> str:
    """PBKDF2 HMAC-SHA256 password hashing with 100,000 iterations."""
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), PASSWORD_SALT.encode("utf-8"), 100000)
    return dk.hex()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hash_password(plain_password) == hashed_password

# Pre-seeded authorized accounts
SEED_USERS_RAW = [
    {"email": "spdysp@demo.in", "name": "SP A. Kashyap (IPS)", "role": "sp_dysp", "password": "demo123"},
    {"email": "cybercell@demo.in", "name": "Insp. P. Nayak (Cyber)", "role": "cyber_cell", "password": "demo123"},
    {"email": "headconstable@demo.in", "name": "HC S. Deshmukh", "role": "head_constable", "password": "demo123"},
    {"email": "constable@demo.in", "name": "Constable R. Verma", "role": "constable", "password": "demo123"},
    {"email": "auditor@demo.in", "name": "Auditor M. Raman", "role": "auditor", "password": "demo123"},
    {"email": "ig@demo.in", "name": "IG P. Agrawal (IPS)", "role": "ig", "password": "demo123"},
    {"email": "spraipur@demo.in", "name": "SP R. Sen (Raipur)", "role": "sp_dysp_raipur", "password": "demo123"},
]

USERS_DB = {}
for u in SEED_USERS_RAW:
    USERS_DB[u["email"]] = {
        "email": u["email"],
        "name": u["name"],
        "role": u["role"],
        "password_hash": hash_password(u["password"])
    }

def create_jwt_token(email: str, role: str, name: str, demo: bool = False) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": email,
        "role": role,
        "name": name,
        "demo": demo,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=7)).timestamp())
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return None

def get_current_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    """Extracts and verifies JWT token or prototype bearer token."""
    if not authorization:
        # Default guest for demo convenience
        return {"email": "spdysp@demo.in", "name": "SP A. Kashyap (IPS)", "role": "sp_dysp", "demo": False}

    parts = authorization.split(" ")
    if len(parts) == 2 and parts[0].lower() == "bearer":
        token = parts[1]

        # 1. Try decoding standard JWT
        payload = decode_jwt_token(token)
        if payload and "sub" in payload:
            email = payload["sub"]
            if email in USERS_DB and not payload.get("demo", False):
                u = dict(USERS_DB[email])
                u["demo"] = False
                return u
            return {
                "email": email,
                "name": payload.get("name", "User"),
                "role": payload.get("role", "constable"),
                "demo": payload.get("demo", False)
            }

        # 2. Stage 1 token backward-compatibility
        for user in USERS_DB.values():
            if token.startswith(f"token_{user['role']}") or token == f"mock_token_{user['role']}":
                return user
        for email, user in USERS_DB.items():
            if email in token:
                return user
        for role in ["constable", "head_constable", "cyber_cell", "sp_dysp", "auditor", "ig", "sp_dysp_raipur"]:
            if role in token:
                for u in USERS_DB.values():
                    if u["role"] == role:
                        return u

        # Explicitly reject invalid or expired bearer token
        raise HTTPException(status_code=401, detail="Invalid or expired authentication token")

    raise HTTPException(status_code=401, detail="Invalid authorization header format")

def require_roles(allowed_roles: List[str]):
    """FastAPI dependency enforcing role-based access control."""
    def role_checker(user: Dict[str, Any] = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Action not permitted for role: {user['role']}. Required: {', '.join(allowed_roles)}"
            )
        return user
    return role_checker

def mask_phone_str(phone: Optional[str]) -> str:
    """Masks phone numbers to standard 98XXXXX210 format."""
    if not phone:
        return ""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 10:
        ten = digits[-10:]
        prefix = ten[:2]
        suffix = ten[-3:]
        masked = f"{prefix}XXXXX{suffix}"
        if "+91" in phone:
            return f"+91 {masked}"
        return masked
    elif len(digits) >= 4:
        return f"{digits[:2]}XXXXX{digits[-2:]}"
    return "XXXXXXXXXX"

def mask_phone_for_user(phone: Optional[str], user_role: str, is_unmasked: bool = False) -> str:
    """Returns raw phone for sp_dysp, ig or explicitly unmasked records; masks for all other roles."""
    if not phone:
        return ""
    if user_role in ("sp_dysp", "ig") or is_unmasked:
        return phone
    return mask_phone_str(phone)

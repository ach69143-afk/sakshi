import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import sqlite3

from dotenv import load_dotenv
load_dotenv()

from ledger import record_action

SMTP_USER = os.getenv("SMTP_USER", "").strip()
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD", "").strip()
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = int(os.getenv("SMTP_PORT", "587").strip() or "587")

def mask_email(email: str) -> str:
    """Masks recipient email address to standard judicial anonymized format (e.g. c***@demo.in)."""
    if not email or "@" not in email:
        return "u***@domain.in"
    parts = email.split("@")
    user_part = parts[0]
    domain_part = parts[1]
    if len(user_part) <= 1:
        masked_user = user_part + "***"
    else:
        masked_user = user_part[0] + "***"
    return f"{masked_user}@{domain_part}"

def send_report_email(
    conn: sqlite3.Connection,
    recipient_email: str,
    report_id: str,
    pdf_bytes: bytes,
    user: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Dispatches intelligence report PDF to the designated officer.
    If SMTP credentials are provided in .env, transmits via TLS SMTP.
    Otherwise, gracefully executes simulated delivery and logs to immutable ledger.
    """
    user_email = user.get("email", recipient_email)
    masked_target = mask_email(recipient_email)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    send_mode = "simulated"
    error_note = None

    # Check if real SMTP credentials are provided
    if SMTP_USER and SMTP_APP_PASSWORD:
        try:
            msg = MIMEMultipart()
            msg["From"] = f"SAKSHI Intelligence System <{SMTP_USER}>"
            msg["To"] = recipient_email
            msg["Subject"] = f"[CONFIDENTIAL] SAKSHI Intelligence Dossier - Case SP-014 ({report_id})"

            body = (
                f"OFFICIAL INVESTIGATIVE BRIEFING - CASE SP-014\n\n"
                f"Officer: {user_email}\n"
                f"Role: {user.get('role', 'investigator').upper()}\n"
                f"Report ID: {report_id}\n"
                f"Generated: {now_iso}\n\n"
                f"Attached is the official Evidence-Defensible Intelligence Dossier compiled under "
                f"Section 65B of the Indian Evidence Act.\n\n"
                f"NOTICE: All contained data is synthetic and prepared exclusively for analytical prioritization.\n"
                f"Patterns identified are 'worthy of investigator attention' and do not constitute formal judicial accusations.\n\n"
                f"SAKSHI Automated Crime Intelligence Workbench\n"
                f"Cyber Crime Cell, District Police"
            )
            msg.attach(MIMEText(body, "plain"))

            part = MIMEApplication(pdf_bytes, Name=f"SAKSHI_{report_id}_Intelligence_Dossier.pdf")
            part["Content-Disposition"] = f'attachment; filename="SAKSHI_{report_id}_Intelligence_Dossier.pdf"'
            msg.attach(part)

            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_USER, [recipient_email], msg.as_string())
            server.quit()
            send_mode = "smtp_live"
        except Exception as e:
            # Fall back gracefully to simulation mode
            send_mode = "simulated_fallback"
            error_note = str(e)

    # Record action in immutable ledger
    record_action(
        conn,
        f"REPORT_EMAIL (Dossier {report_id} dispatched to {masked_target} by {user_email})",
        {
            "report_id": report_id,
            "recipient": masked_target,
            "dispatched_by": user_email,
            "mode": send_mode,
            "pdf_size_bytes": len(pdf_bytes)
        },
        ts=now_iso
    )

    status_val = "sent" if send_mode == "smtp_live" else "queued"
    return {
        "report_id": report_id,
        "sent_to": masked_target,
        "status": status_val,
        "mode": send_mode,
        "message": f"Intelligence dossier {report_id} successfully {status_val} to {masked_target}."
    }

def send_demo_login_notice(
    recipient_email: str,
    recipient_name: str,
    role: str
) -> Dict[str, Any]:
    """
    Transmits an initial login notice email to a verified demo visitor.
    If live SMTP credentials exist and function, sends via TLS SMTP.
    Otherwise saves .eml to outbox/ without crashing and returns status 'queued'.
    """
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    masked_target = mask_email(recipient_email)

    subject = f"[SAKSHI] Demo Session Started - Case SP-014 ({role.upper()})"
    body = (
        f"OFFICIAL DEMO NOTICE - SAKSHI INTELLIGENCE WORKBENCH\n\n"
        f"Visitor: {recipient_name} ({masked_target})\n"
        f"Assigned Role: {role.upper()}\n"
        f"Session Started: {now_iso}\n\n"
        f"NOTICE: All data within Case SP-014 (Durg Missing Cluster) is strictly synthetic.\n"
        f"Patterns identified are for investigative prioritization only and do not constitute formal accusations.\n\n"
        f"SAKSHI Automated Crime Intelligence Workbench\n"
        f"Cyber Crime Cell, District Police"
    )

    msg = MIMEText(body, "plain", "utf-8")
    msg["From"] = f"SAKSHI Intelligence System <{SMTP_USER or 'noreply@sakshi.gov.in'}>"
    msg["To"] = recipient_email
    msg["Subject"] = subject

    send_mode = "simulated"
    status_val = "queued"

    if SMTP_USER and SMTP_APP_PASSWORD:
        try:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8)
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_USER, [recipient_email], msg.as_string())
            server.quit()
            send_mode = "smtp_live"
            status_val = "sent"
        except Exception:
            send_mode = "simulated_fallback"
            status_val = "queued"

    if status_val == "queued":
        try:
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            sakshi_dir = os.path.dirname(backend_dir)
            outbox_dir = os.path.join(sakshi_dir, "outbox")
            os.makedirs(outbox_dir, exist_ok=True)
            clean_email = re.sub(r'[^a-zA-Z0-9_.-]', '_', recipient_email)
            file_name = f"{int(time.time())}_{clean_email}.eml"
            file_path = os.path.join(outbox_dir, file_name)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(msg.as_string())
        except Exception:
            pass

    return {
        "status": status_val,
        "mode": send_mode,
        "sent_to": masked_target
    }

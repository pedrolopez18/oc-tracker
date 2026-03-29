import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from app.config import get_settings

logger = logging.getLogger(__name__)


def send_supplier_email(
    supplier:    str,
    email_to:    str,
    excel_bytes: bytes,
    body:        str,
    filename:    str,
    subject:     str | None = None,
    cc:          str = "",
) -> dict:
    s = get_settings()

    msg            = MIMEMultipart()
    msg["From"]    = s.smtp_from or s.smtp_user
    msg["To"]      = email_to
    msg["Subject"] = subject or f"Seguimiento de Órdenes de Compra — {supplier}"
    if cc and cc.strip():
        msg["Cc"]  = cc

    msg.attach(MIMEText(body, "plain", "utf-8"))

    part = MIMEBase("application", "octet-stream")
    part.set_payload(excel_bytes)
    encoders.encode_base64(part)
    part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
    msg.attach(part)

    recipients = [email_to] + ([cc] if cc and cc.strip() else [])

    try:
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(s.smtp_user, s.smtp_password)
            server.sendmail(msg["From"], recipients, msg.as_string())
        logger.info("Email enviado → %s (%s)", supplier, email_to)
        return {"status": "sent", "to": email_to}
    except Exception as e:
        logger.error("Error enviando a %s: %s", supplier, e)
        return {"status": "error", "reason": str(e)}

"""Generic SMTP sender for system-originated emails (scheduled reports,
alerts) — distinct from core/google_integration.py's send_email, which
sends *as* a signed-in user via their own Gmail OAuth token. Uses
Config.SMTP_* (defaults to the local MailHog sandbox, see docker-compose.yml
and core/config.py)."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from core.config import Config
from core.logger import get_logger

logger = get_logger(__name__)


def send_smtp_email(to_addrs, subject, html_body):
    """to_addrs: str or list of recipient addresses. Returns True/False."""
    if isinstance(to_addrs, str):
        to_addrs = [a.strip() for a in to_addrs.split(',') if a.strip()]
    if not to_addrs:
        return False
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = Config.SMTP_FROM
    msg['To'] = ', '.join(to_addrs)
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    try:
        with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT, timeout=10) as server:
            if Config.SMTP_SECURE:
                server.starttls()
            if Config.SMTP_USER:
                server.login(Config.SMTP_USER, Config.SMTP_PASS)
            server.sendmail(Config.SMTP_FROM, to_addrs, msg.as_string())
        return True
    except Exception as exc:
        logger.error('[smtp_mailer] Failed to send to %s: %s', to_addrs, exc)
        return False

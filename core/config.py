import os
from dotenv import load_dotenv

load_dotenv()

# Core Configuration
class Config:
    # Project/branding configuration
    PROJECT_NAME = "Workflow Automation for Retail"

    # Must be overridden via SECRET_KEY env var in production.
    # The sentinel value 'change_me_to_a_secure_random_value' is intentionally
    # identical to the one app.py raises RuntimeError on — do not change it.
    SECRET_KEY = os.environ.get('SECRET_KEY', 'change_me_to_a_secure_random_value')

    # Database Configuration
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'group_project_ai_ml.db')
    POSTGRES_URL = os.environ.get('POSTGRES_URL')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    ALLOW_AI_QUEUE_WITHOUT_WORKER = os.environ.get('ALLOW_AI_QUEUE_WITHOUT_WORKER', 'False').lower() == 'true'
    USE_POSTGRES = bool(POSTGRES_URL) or os.environ.get('USE_POSTGRES', 'False').lower() == 'true'

    # Business data (products/imports/exports/wallet/workflows/...) lives in
    # its own Neon database, separate from POSTGRES_URL above (which now
    # holds only `users` — shared, read by Gateway/Sản xuất too). Falls back
    # to POSTGRES_URL if unset so existing local/dev setups keep working
    # unchanged until they're given a BUSINESS_POSTGRES_URL of their own.
    BUSINESS_POSTGRES_URL = os.environ.get('BUSINESS_POSTGRES_URL') or POSTGRES_URL
    
    # Site domain and base URL (override with env vars)
    SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'auto-flowai.com')
    BASE_URL = os.environ.get('BASE_URL', f"https://{SITE_DOMAIN}")

    # n8n host port — override with N8N_PORT env var if 5680 collides with
    # another local project's docker-compose (e.g. a separate n8n stack).
    N8N_PORT = os.environ.get('N8N_PORT', '5680')
    N8N_ORIGIN = f"http://localhost:{N8N_PORT}"

    # SMTP for emails this app sends directly (core/smtp_mailer.py — the
    # in-app scheduled-reports runner). This process runs on the host, not
    # in Docker, so it reaches MailHog via its published host port.
    # Override with real SMTP (Gmail/Brevo/SendGrid/...) before going live.
    SMTP_HOST = os.environ.get('SMTP_HOST', '127.0.0.1')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', '1025'))
    SMTP_USER = os.environ.get('SMTP_USER', '')
    SMTP_PASS = os.environ.get('SMTP_PASS', '')
    SMTP_FROM = os.environ.get('SMTP_FROM', 'alerts@anser.local')
    SMTP_SECURE = os.environ.get('SMTP_SECURE', 'False').lower() == 'true'

    # SMTP as reached from *inside* the n8n container (its "Send Email"
    # nodes — low-stock alerts, daily sales report) — Docker compose service
    # name, not a host address. See core/config.py's SMTP_HOST for the
    # host-side equivalent this app's own process uses.
    N8N_SMTP_HOST = os.environ.get('N8N_SMTP_HOST', 'mailhog')

    # NOT the same meaning as SMTP_SECURE above, despite sharing a name.
    # n8n's node uses nodemailer, where secure=true means "TLS from the
    # first byte" (port 465 style) and secure=false means "plain/STARTTLS"
    # (port 587 style, auto-upgraded) — the opposite framing from
    # smtplib's starttls()-if-True flag SMTP_SECURE drives. Gmail/most
    # providers on port 587 want SMTP_SECURE=True (so smtp_mailer.py calls
    # starttls()) *and* N8N_SMTP_SECURE=False (so nodemailer takes its own
    # STARTTLS path) at the same time — reusing one flag for both broke this.
    N8N_SMTP_SECURE = os.environ.get('N8N_SMTP_SECURE', 'False').lower() == 'true'

    # Sản xuất — a separate Flask app/API/DB (see ANSER_san-xuat), not part
    # of this codebase.
    SANXUAT_ORIGIN = os.environ.get('SANXUAT_ORIGIN', 'http://127.0.0.1:5003')

    # Gateway — landing page + email/password signin/signup/logout +
    # choose-area now live there (see ANSER_gateway), not in this app.
    # This app (Retail) only reads the shared session cookie it issues.
    GATEWAY_ORIGIN = os.environ.get('GATEWAY_ORIGIN', 'http://127.0.0.1:5000')

    # UI Themes
    THEMES = {
        'auth': {
            'primary': '#00d4aa',
            'secondary': '#1a1a1a', 
            'background': '#0f0f0f',
            'surface': '#1a1a1a',
            'text': '#ffffff',
            'text_secondary': '#a0a0a0'
        },
        'workspace': {
            'primary': '#007acc',
            'secondary': '#252526',
            'background': '#1e1e1e',
            'sidebar': '#252526',
            'panel': '#2d2d30',
            'text': '#cccccc',
            'text_secondary': '#969696'
        }
    }
    
    # Workspace Types
    WORKSPACE_TYPES = [
        'personal',
        'team', 
        'scenarios',
        'projects'
    ]

    # --- Google Analytics & OAuth ---
    # Numeric Google Analytics Property ID (replace with your property id or set env var `GA_PROPERTY_ID`)
    GA_PROPERTY_ID = os.environ.get('GA_PROPERTY_ID', '517047582')
    GA_ENABLE_CACHING = True
    GA_CACHE_LIFETIME_SECONDS = int(os.environ.get('GA_CACHE_LIFETIME_SECONDS', 3600))

    _BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    GA_SERVICE_ACCOUNT_FILE = os.path.join(_BASE_DIR, 'secrets', 'analytics_service_account.json')

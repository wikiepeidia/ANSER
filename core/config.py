import os
from core.env_loader import load_project_env

load_project_env()


class Config:
    """Gateway config — landing + email/password auth + choose-area only.

    Owns the `users` table for real (read+write) — this is now the single
    source of truth for identity across all mảng. Retail and Sản xuất only
    ever read it (via a shared SECRET_KEY + the session cookie this app
    issues on login).
    """

    PROJECT_NAME = "ANSER"

    SECRET_KEY = os.environ.get('SECRET_KEY', 'change_me_to_a_secure_random_value')

    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'group_project_ai_ml.db')
    POSTGRES_URL = os.environ.get('POSTGRES_URL')
    USE_POSTGRES = bool(POSTGRES_URL) or os.environ.get('USE_POSTGRES', 'False').lower() == 'true'

    PORT = int(os.environ.get('PORT', 5000))

    # Where each mảng's own app lives — choose-area links out to these.
    RETAIL_ORIGIN = os.environ.get('RETAIL_ORIGIN', 'http://127.0.0.1:5002')
    SANXUAT_ORIGIN = os.environ.get('SANXUAT_ORIGIN', 'http://127.0.0.1:5003')

    SITE_DOMAIN = os.environ.get('SITE_DOMAIN', f'127.0.0.1:{PORT}')
    BASE_URL = os.environ.get('BASE_URL', f'http://{SITE_DOMAIN}')

    # Cross-app internal admin page (team-only — aggregates Retail + Sản
    # xuất, never shown to shop-owner customers). Comma-separated emails;
    # empty by default so this stays inaccessible to everyone until
    # explicitly configured, rather than defaulting open.
    INTERNAL_ADMIN_EMAILS = {
        e.strip().lower() for e in os.environ.get('INTERNAL_ADMIN_EMAILS', '').split(',') if e.strip()
    }

    # Shared secret sent as X-Platform-Token when calling Retail's/Sản
    # xuất's own GET /api/internal/platform-stats — same value must be set
    # on all 3 apps.
    PLATFORM_STATS_TOKEN = os.environ.get('PLATFORM_STATS_TOKEN', '')

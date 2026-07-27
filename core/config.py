import os
from core.env_loader import load_project_env

load_project_env()


class Config:
    """Sản xuất backend config.

    SECRET_KEY, DATABASE_PATH/POSTGRES_URL here must match the values in
    Gateway's own .env — this app authenticates against Gateway's shared
    `users` table (read-only) so a user who logs in on :5000 is already
    recognized here when they switch tab, with no separate signin flow of
    its own.

    Business data (products/imports/exports/customers) is fully separate —
    see SANXUAT_DATABASE_PATH below, never mixed into the auth database.
    """

    PROJECT_NAME = "ANSER — Sản xuất"

    SECRET_KEY = os.environ.get('SECRET_KEY', 'change_me_to_a_secure_random_value')

    # Shared auth DB (same physical DB as Gateway — read-only from here)
    AUTH_DATABASE_PATH = os.environ.get('DATABASE_PATH', 'group_project_ai_ml.db')
    AUTH_POSTGRES_URL = os.environ.get('POSTGRES_URL')
    AUTH_USE_POSTGRES = bool(AUTH_POSTGRES_URL)

    # San Xuat's own business database — fully separate from Gateway/Retail's.
    # SQLite by default; set SANXUAT_POSTGRES_URL to use its own Neon database
    # instead (a DIFFERENT database than AUTH_POSTGRES_URL/POSTGRES_URL above —
    # never the same one, that would defeat the point of keeping it separate).
    SANXUAT_DATABASE_PATH = os.environ.get('SANXUAT_DATABASE_PATH', 'san_xuat.db')
    SANXUAT_POSTGRES_URL = os.environ.get('SANXUAT_POSTGRES_URL')
    SANXUAT_USE_POSTGRES = bool(SANXUAT_POSTGRES_URL)

    PORT = int(os.environ.get('PORT', 5003))
    GATEWAY_ORIGIN = os.environ.get('GATEWAY_ORIGIN', 'http://127.0.0.1:5000')

    # Own n8n instance (docker-compose.yml), separate from ANSER's (port 5680)
    N8N_ORIGIN = os.environ.get('N8N_ORIGIN', 'http://127.0.0.1:5681')

    # Shared secret for GET /api/internal/platform-stats — read by Gateway's
    # team-only cross-app admin page. Same value must be set on Gateway (as
    # PLATFORM_STATS_TOKEN) and on Retail's own copy of this same var. Empty
    # by default so this endpoint fails closed instead of leaking
    # aggregate production data to an unauthenticated caller.
    PLATFORM_STATS_TOKEN = os.environ.get('PLATFORM_STATS_TOKEN', '')

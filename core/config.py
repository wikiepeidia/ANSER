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
    see SANXUAT_POSTGRES_URL below, never mixed into the auth database.
    Postgres-only (Neon sanxuat_business); no SQLite fallback.
    """

    PROJECT_NAME = "ANSER — Sản xuất"

    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        raise RuntimeError(
            "SECRET_KEY environment variable is not set -- San Xuat's session "
            "cookie must be signed with the same SECRET_KEY as Gateway's own "
            ".env, or cross-app login silently breaks; set it before starting "
            "the app."
        )

    # Shared auth DB (same physical DB as Gateway — read-only from here)
    AUTH_DATABASE_PATH = os.environ.get('DATABASE_PATH', 'group_project_ai_ml.db')
    AUTH_POSTGRES_URL = os.environ.get('POSTGRES_URL')
    AUTH_USE_POSTGRES = bool(AUTH_POSTGRES_URL)

    # San Xuat's own business database — fully separate from Gateway/Retail's
    # (a DIFFERENT Neon database than AUTH_POSTGRES_URL/POSTGRES_URL above —
    # never the same one, that would defeat the point of keeping it
    # separate). Postgres-only, no SQLite fallback -- fail fast, same
    # pattern as SECRET_KEY above, rather than silently defaulting to a
    # SQLite file nothing in this app still supports.
    SANXUAT_POSTGRES_URL = os.environ.get('SANXUAT_POSTGRES_URL')
    if not SANXUAT_POSTGRES_URL:
        raise RuntimeError(
            "SANXUAT_POSTGRES_URL environment variable is not set -- this app "
            "is Postgres-only (Neon sanxuat_business), there is no SQLite "
            "fallback; set it before starting the app."
        )

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

    # Shared secret for every /api/n8n/internal/* route (rag/<action>,
    # notify, brain/chat, brain/upload, brain/mcp/validate-invoice) — called
    # by n8n's HTTP Request nodes (workflow_templates/*.json), which send it
    # as the x-anser-token header. Must byte-match docker-compose.yml's n8n
    # service ANSER_WEBHOOK_TOKEN env var. Empty by default so these
    # endpoints fail closed instead of accepting unauthenticated writes from
    # anyone on the network, matching PLATFORM_STATS_TOKEN's own pattern.
    ANSER_WEBHOOK_TOKEN = os.environ.get('ANSER_WEBHOOK_TOKEN', '')

import os
from dotenv import load_dotenv

load_dotenv()


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

    # San Xuat's own business database — fully separate from Gateway/Retail's
    SANXUAT_DATABASE_PATH = os.environ.get('SANXUAT_DATABASE_PATH', 'san_xuat.db')

    PORT = int(os.environ.get('PORT', 5003))
    GATEWAY_ORIGIN = os.environ.get('GATEWAY_ORIGIN', 'http://127.0.0.1:5000')

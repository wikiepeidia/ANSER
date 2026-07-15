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
    
    # Site domain and base URL (override with env vars)
    SITE_DOMAIN = os.environ.get('SITE_DOMAIN', 'auto-flowai.com')
    BASE_URL = os.environ.get('BASE_URL', f"https://{SITE_DOMAIN}")

    # n8n host port — override with N8N_PORT env var if 5680 collides with
    # another local project's docker-compose (e.g. a separate n8n stack).
    N8N_PORT = os.environ.get('N8N_PORT', '5680')
    N8N_ORIGIN = f"http://localhost:{N8N_PORT}"

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

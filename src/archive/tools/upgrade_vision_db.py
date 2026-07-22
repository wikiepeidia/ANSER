import os
import sys
from sqlalchemy import create_engine, text

# SETUP
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path: sys.path.insert(0, project_root)

NEON_URL = "postgresql://neondb_owner:npg_3YuVdgK7eUIf@ep-cold-firefly-a1rimyve-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def upgrade_vision():
    print("👁️ Upgrading Database for Persistent Vision...")
    
    db_url = NEON_URL.replace("postgres://", "postgresql+psycopg2://")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        print("🔨 Creating 'chat_attachments' table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_attachments (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES chat_sessions(id),
                file_name TEXT,
                file_type TEXT,
                analysis_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        conn.commit()
        print("✅ Vision Memory Layer Installed.")

if __name__ == "__main__":
    upgrade_vision()
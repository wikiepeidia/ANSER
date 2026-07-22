import os
import sys
from sqlalchemy import create_engine, text

# 1. SETUP PATHS
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path: sys.path.insert(0, project_root)

# 2. CONFIG
NEON_URL = "postgresql://neondb_owner:npg_3YuVdgK7eUIf@ep-cold-firefly-a1rimyve-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def fix_db():
    print(f"🔧 Integrating Chat History with existing Schema...")
    
    # Fix URL for SQLAlchemy
    db_url = NEON_URL.replace("postgres://", "postgresql+psycopg2://")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # --- 1. RESET CHAT HISTORY (To fix Type Mismatches) ---
        # We drop it to ensure we don't have a lingering table with INTEGER columns
        print("♻️  Resetting 'ai_chat_history' definition...")
        conn.execute(text("DROP TABLE IF EXISTS ai_chat_history"))
        
        # --- 2. CREATE TABLE WITH TEXT IDs ---
        # We use TEXT for user_id and workspace_id to match your 'ws-100' / 'scn-001' format
        print("🔨 Creating flexible 'ai_chat_history' table...")
        conn.execute(text("""
            CREATE TABLE ai_chat_history (
                id SERIAL PRIMARY KEY,
                user_id TEXT,       -- Changed to TEXT to support 'u-001' etc.
                workspace_id TEXT,  -- Changed to TEXT to support 'ws-100'
                role TEXT,
                content TEXT,
                timestamp TEXT
            );
        """))
        
        conn.commit()
        print("✅ Integration Complete.")
        print("   -> 'ai_chat_history' is now ready and compatible with String IDs.")

if __name__ == "__main__":
    fix_db()
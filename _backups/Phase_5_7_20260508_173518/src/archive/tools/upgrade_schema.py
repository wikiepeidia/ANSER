import os
import sys
from sqlalchemy import create_engine, text
import uuid

# SETUP
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path: sys.path.insert(0, project_root)

NEON_URL = "postgresql://neondb_owner:npg_3YuVdgK7eUIf@ep-cold-firefly-a1rimyve-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

def upgrade_db():
    print("🚀 Starting Database Schema Upgrade (Session Architecture)...")
    
    db_url = NEON_URL.replace("postgres://", "postgresql+psycopg2://")
    engine = create_engine(db_url)

    with engine.connect() as conn:
        # 1. Create SESSIONS Table
        print("🔨 Creating 'chat_sessions' table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_sessions (
                id SERIAL PRIMARY KEY,
                user_id TEXT,
                workspace_id TEXT,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # 2. Create MESSAGES Table (Linked to Session)
        print("🔨 Creating 'chat_messages' table...")
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                session_id INTEGER REFERENCES chat_sessions(id),
                role TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """))
        
        # 3. MIGRATE OLD DATA
        # We check if there is old data in 'ai_chat_history'
        try:
            old_msgs = conn.execute(text("SELECT user_id, workspace_id, role, content, timestamp FROM ai_chat_history")).fetchall()
            
            if old_msgs:
                print(f"📦 Migrating {len(old_msgs)} old messages...")
                
                # Create a "Legacy Session" for each user found
                users = set([row[0] for row in old_msgs])
                
                for uid in users:
                    # Create Session
                    res = conn.execute(text("""
                        INSERT INTO chat_sessions (user_id, workspace_id, title, last_active)
                        VALUES (:uid, '1', 'Legacy Conversation', CURRENT_TIMESTAMP)
                        RETURNING id
                    """), {"uid": uid}).fetchone()
                    session_id = res[0]
                    
                    # Move Messages
                    for row in old_msgs:
                        if row[0] == uid:
                            conn.execute(text("""
                                INSERT INTO chat_messages (session_id, role, content, created_at)
                                VALUES (:sid, :role, :content, CURRENT_TIMESTAMP)
                            """), {"sid": session_id, "role": row[2], "content": row[3]})
                
                print("✅ Migration Complete.")
                # Optional: Drop old table
                # conn.execute(text("DROP TABLE ai_chat_history")) 
            else:
                print("ℹ️  No old data to migrate.")
                
        except Exception as e:
            print(f"⚠️  Migration Warning: {e}")

        conn.commit()
        print("✨ Database Upgrade Finished.")

if __name__ == "__main__":
    upgrade_db()
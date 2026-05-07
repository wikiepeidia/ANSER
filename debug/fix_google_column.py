
import sys
import os

# Add root directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.database import Database

print("🔧 Checking database schema for 'google_email' column...")

db = Database()
conn = db.get_connection()
c = conn.cursor()

try:
    # Check if column exists
    if db.use_postgres:
        c.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'google_email'")
        exists = c.fetchone()
    else:
        # SQLite
        c.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in c.fetchall()]
        exists = 'google_email' in columns

    if not exists:
        print("⚠️ 'google_email' column missing. Adding it now...")
        if db.use_postgres:
             c.execute("ALTER TABLE users ADD COLUMN google_email TEXT")
        else:
             c.execute("ALTER TABLE users ADD COLUMN google_email TEXT")
        conn.commit()
        print("✅ Added 'google_email' column to users table.")
    else:
        print("✅ 'google_email' column already exists.")

except Exception as e:
    print(f"❌ Error updating schema: {e}")
finally:
    conn.close()

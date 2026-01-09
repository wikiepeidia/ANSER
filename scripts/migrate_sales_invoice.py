import sys
import os
import psycopg2

# Add root to python path
sys.path.append(os.getcwd())

from core.config import Config

def migrate_sales_table():
    print("Migrating sales table...")
    
    if not Config.USE_POSTGRES:
        print("Not using Postgres. Skipping.")
        return

    try:
        conn = psycopg2.connect(Config.POSTGRES_URL)
        cursor = conn.cursor()
        
        # Add columns if they don't exist
        columns_to_add = [
            ("payment_method", "TEXT DEFAULT 'cash'"),
            ("workspace_id", "INTEGER"),
            ("category", "TEXT DEFAULT 'Retail'")
        ]
        
        for col_name, col_type in columns_to_add:
            try:
                cursor.execute(f"ALTER TABLE sales ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
                conn.commit()
            except Exception as e:
                print(f"Column {col_name} might already exist or error: {e}")
                conn.rollback()

        conn.close()
        print("Migration complete.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate_sales_table()

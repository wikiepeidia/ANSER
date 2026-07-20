import sys
sys.path.insert(0, '.')
from core.extensions import db_manager

# Restore original value
with db_manager.get_business_db_connection() as conn:
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO system_settings (key, value, group_name, updated_at) "
        "VALUES (%s, %s, %s, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
        ('store_name', 'My AI Store', 'store')
    )
    conn.commit()
    cur.execute("SELECT key, value FROM system_settings ORDER BY key")
    print('Current state:')
    for r in cur.fetchall(): print(' ', r)

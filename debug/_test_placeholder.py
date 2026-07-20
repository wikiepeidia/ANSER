import sys
sys.path.insert(0, '.')
from core.config import Config
from core.extensions import db_manager

with db_manager.get_business_db_connection() as conn:
    cur = conn.cursor()
    cur.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE tablename = 'system_settings'
    """)
    print('Indexes on system_settings:')
    for row in cur.fetchall():
        print(f'  {row}')

    # Test actual save SQL
    print('\n--- Test save SQL ---')
    cur.execute(
        "INSERT INTO system_settings (key, value, group_name, updated_at) "
        "VALUES (%s, %s, %s, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=CURRENT_TIMESTAMP",
        ('store_name', 'Cửa hàng Test Mới', 'store')
    )
    conn.commit()
    cur.execute("SELECT key, value FROM system_settings WHERE key = 'store_name'")
    print(f'After save: {cur.fetchall()}')

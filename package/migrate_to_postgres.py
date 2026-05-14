"""
migrate_to_postgres.py
Migrate toàn bộ SQLite database sang PostgreSQL (Neon DB).

Cách chạy:
    # Dùng URL trong secrets/database.json (khuyến nghị)
    python package/migrate_to_postgres.py

    # Hoặc truyền URL trực tiếp qua env
    set POSTGRES_URL=postgresql://user:pass@...neon.tech/neondb?sslmode=require
    python package/migrate_to_postgres.py

    # Chỉ định file SQLite khác
    set SQLITE_PATH=path/to/other.db
    python package/migrate_to_postgres.py
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from pathlib import Path

# ── Đảm bảo import được core/ từ root project ─────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import psycopg2
except ImportError:
    print("❌ Thiếu psycopg2. Chạy: pip install psycopg2-binary")
    sys.exit(1)


# ── Đọc config ─────────────────────────────────────────────────────────────

def _load_postgres_url() -> str:
    # 1. CLI arg
    if len(sys.argv) > 1:
        return sys.argv[1]
    # 2. Env var
    url = os.environ.get("POSTGRES_URL", "")
    if url:
        return url
    # 3. secrets/database.json
    secrets_path = ROOT / "secrets" / "database.json"
    if secrets_path.exists():
        data = json.loads(secrets_path.read_text(encoding="utf-8"))
        url = data.get("POSTGRES_URL", "")
        if url:
            return url
    # 4. Hỏi người dùng
    print("⚠️  Không tìm thấy POSTGRES_URL.")
    url = input("   Paste Neon DB connection string: ").strip()
    if not url:
        print("❌ Không có URL, thoát.")
        sys.exit(1)
    return url


def _load_sqlite_path() -> str:
    path = os.environ.get("SQLITE_PATH", "")
    if path:
        return path
    # Thử đọc từ config
    try:
        from core.config import Config
        return Config.DATABASE_PATH
    except Exception:
        return str(ROOT / "group_project_ai_ml.db")


# ── PostgreSQL Schema (22 bảng) ────────────────────────────────────────────

# Thứ tự: không có FK trước, có FK sau
TABLE_ORDER = [
    "system_settings",
    "users",
    "workspaces",
    "items",
    "customers",
    "products",
    "import_transactions",
    "import_details",
    "export_transactions",
    "export_details",
    "sales",
    "manager_subscriptions",
    "subscription_history",
    "wallets",
    "wallet_transactions",
    "workflows",
    "se_automations",
    "scheduled_reports",
    "activity_logs",
    "ai_chat_history",
    "chat_sessions",
    "chat_attachments",
]

# Bảng có SERIAL id (cần reset sequence sau khi copy)
SERIAL_TABLES = TABLE_ORDER.copy()
SERIAL_TABLES.remove("system_settings")  # system_settings dùng TEXT PK

PG_DDL: dict[str, str] = {
    "system_settings": """
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            group_name TEXT,
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            name TEXT,
            role TEXT DEFAULT 'user',
            avatar TEXT,
            theme TEXT DEFAULT 'dark',
            first_name TEXT,
            last_name TEXT,
            google_token TEXT,
            manager_id INTEGER,
            subscription_expires_at TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "workspaces": """
        CREATE TABLE IF NOT EXISTS workspaces (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT DEFAULT 'personal',
            description TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "items": """
        CREATE TABLE IF NOT EXISTS items (
            id SERIAL PRIMARY KEY,
            workspace_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            type TEXT DEFAULT 'task',
            status TEXT DEFAULT 'todo',
            priority TEXT DEFAULT 'medium',
            assignee_id INTEGER,
            due_date TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "customers": """
        CREATE TABLE IF NOT EXISTS customers (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "products": """
        CREATE TABLE IF NOT EXISTS products (
            id SERIAL PRIMARY KEY,
            code TEXT UNIQUE,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT,
            price DOUBLE PRECISION DEFAULT 0,
            stock_quantity INTEGER DEFAULT 0,
            description TEXT,
            created_by INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "import_transactions": """
        CREATE TABLE IF NOT EXISTS import_transactions (
            id SERIAL PRIMARY KEY,
            code TEXT,
            supplier_name TEXT,
            total_amount DOUBLE PRECISION DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'completed',
            created_by INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "import_details": """
        CREATE TABLE IF NOT EXISTS import_details (
            id SERIAL PRIMARY KEY,
            import_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity DOUBLE PRECISION DEFAULT 0,
            unit_price DOUBLE PRECISION DEFAULT 0,
            total_price DOUBLE PRECISION DEFAULT 0
        )""",

    "export_transactions": """
        CREATE TABLE IF NOT EXISTS export_transactions (
            id SERIAL PRIMARY KEY,
            code TEXT,
            customer_name TEXT,
            total_amount DOUBLE PRECISION DEFAULT 0,
            notes TEXT,
            status TEXT DEFAULT 'completed',
            created_by INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "export_details": """
        CREATE TABLE IF NOT EXISTS export_details (
            id SERIAL PRIMARY KEY,
            export_id INTEGER NOT NULL,
            product_id INTEGER,
            quantity DOUBLE PRECISION DEFAULT 0,
            unit_price DOUBLE PRECISION DEFAULT 0,
            total_price DOUBLE PRECISION DEFAULT 0
        )""",

    "sales": """
        CREATE TABLE IF NOT EXISTS sales (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            total_amount DOUBLE PRECISION,
            amount_given DOUBLE PRECISION,
            change_amount DOUBLE PRECISION,
            items TEXT,
            payment_method TEXT DEFAULT 'cash',
            workspace_id INTEGER,
            category TEXT DEFAULT 'Retail',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "manager_subscriptions": """
        CREATE TABLE IF NOT EXISTS manager_subscriptions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE,
            subscription_type TEXT,
            amount DOUBLE PRECISION,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'inactive',
            auto_renew INTEGER DEFAULT 0,
            payment_method TEXT,
            transaction_id TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "subscription_history": """
        CREATE TABLE IF NOT EXISTS subscription_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            subscription_type TEXT,
            amount DOUBLE PRECISION,
            payment_date TEXT,
            payment_method TEXT,
            transaction_id TEXT,
            status TEXT,
            notes TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "wallets": """
        CREATE TABLE IF NOT EXISTS wallets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE,
            balance DOUBLE PRECISION DEFAULT 0,
            currency TEXT DEFAULT 'VND',
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "wallet_transactions": """
        CREATE TABLE IF NOT EXISTS wallet_transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            amount DOUBLE PRECISION,
            currency TEXT DEFAULT 'VND',
            type TEXT,
            status TEXT DEFAULT 'pending',
            method TEXT,
            reference TEXT,
            notes TEXT,
            metadata TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "workflows": """
        CREATE TABLE IF NOT EXISTS workflows (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            name TEXT,
            description TEXT,
            data TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "se_automations": """
        CREATE TABLE IF NOT EXISTS se_automations (
            id SERIAL PRIMARY KEY,
            name TEXT,
            type TEXT,
            config TEXT,
            enabled INTEGER DEFAULT 0,
            last_run TEXT,
            created_by INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "scheduled_reports": """
        CREATE TABLE IF NOT EXISTS scheduled_reports (
            id SERIAL PRIMARY KEY,
            name TEXT,
            report_type TEXT,
            frequency TEXT,
            channel TEXT,
            recipients TEXT,
            status TEXT DEFAULT 'active',
            last_sent_at TEXT,
            created_by INTEGER,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "activity_logs": """
        CREATE TABLE IF NOT EXISTS activity_logs (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            action TEXT,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "ai_chat_history": """
        CREATE TABLE IF NOT EXISTS ai_chat_history (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",

    "chat_sessions": """
        CREATE TABLE IF NOT EXISTS chat_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER,
            workspace_id INTEGER,
            title TEXT,
            last_active TIMESTAMPTZ DEFAULT NOW()
        )""",

    "chat_attachments": """
        CREATE TABLE IF NOT EXISTS chat_attachments (
            id SERIAL PRIMARY KEY,
            session_id INTEGER,
            file_name TEXT,
            file_type TEXT,
            analysis_summary TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )""",
}


# ── Helpers ────────────────────────────────────────────────────────────────

def _sqlite_cols(sqlite_cur: sqlite3.Cursor, table: str) -> list[str]:
    sqlite_cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in sqlite_cur.fetchall()]


def _pg_cols(pg_cur, table: str) -> list[str]:
    pg_cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name = %s ORDER BY ordinal_position",
        (table,),
    )
    return [row[0] for row in pg_cur.fetchall()]


def _table_exists_sqlite(sqlite_cur: sqlite3.Cursor, table: str) -> bool:
    sqlite_cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
    )
    return sqlite_cur.fetchone() is not None


# ── Core logic ─────────────────────────────────────────────────────────────

def create_schema(pg_conn) -> None:
    print("\n📐 Tạo schema trên PostgreSQL...")
    cur = pg_conn.cursor()
    for table in TABLE_ORDER:
        cur.execute(PG_DDL[table])
        print(f"   ✅ {table}")
    pg_conn.commit()
    cur.close()


def migrate_table(table: str, sqlite_conn: sqlite3.Connection, pg_conn) -> int:
    sqlite_cur = sqlite_conn.cursor()

    if not _table_exists_sqlite(sqlite_cur, table):
        print(f"   ⚠️  {table}: bảng không tồn tại trong SQLite — bỏ qua")
        return 0

    # Lấy cột SQLite và PostgreSQL, lấy phần giao (chỉ copy cột tồn tại cả hai)
    sqlite_cols = _sqlite_cols(sqlite_cur, table)
    pg_cur = pg_conn.cursor()
    pg_cols = _pg_cols(pg_cur, table)
    common_cols = [c for c in sqlite_cols if c in pg_cols]

    if not common_cols:
        print(f"   ⚠️  {table}: không có cột chung — bỏ qua")
        pg_cur.close()
        return 0

    # Đọc toàn bộ data từ SQLite
    col_list = ", ".join(common_cols)
    sqlite_cur.execute(f"SELECT {col_list} FROM {table}")
    rows = sqlite_cur.fetchall()

    if not rows:
        print(f"   ⏭️  {table}: 0 dòng — bỏ qua")
        pg_cur.close()
        return 0

    # Insert vào PostgreSQL — ON CONFLICT DO NOTHING (không cần chỉ định cột,
    # PostgreSQL tự xử lý mọi constraint vi phạm)
    placeholders = ", ".join(["%s"] * len(common_cols))
    insert_sql = (
        f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
        "ON CONFLICT DO NOTHING"
    )

    try:
        pg_cur.executemany(insert_sql, rows)
        pg_conn.commit()
    except Exception as e:
        pg_conn.rollback()
        print(f"   ❌ {table}: lỗi khi insert — {e}")
        pg_cur.close()
        return 0

    pg_cur.close()
    return len(rows)


def reset_sequences(pg_conn) -> None:
    print("\n🔄 Reset PostgreSQL sequences...")
    cur = pg_conn.cursor()
    for table in SERIAL_TABLES:
        try:
            cur.execute(
                f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), "
                f"COALESCE((SELECT MAX(id::bigint) FROM {table}), 0) + 1, false)"
            )
            pg_conn.commit()
            print(f"   ✅ {table}")
        except Exception as e:
            pg_conn.rollback()
            print(f"   ⚠️  {table}: {e}")
    cur.close()


def save_secrets(postgres_url: str) -> None:
    secrets_dir = ROOT / "secrets"
    secrets_dir.mkdir(exist_ok=True)
    secrets_file = secrets_dir / "database.json"
    data: dict = {}
    if secrets_file.exists():
        try:
            data = json.loads(secrets_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    data["POSTGRES_URL"] = postgres_url
    secrets_file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n💾 Đã lưu POSTGRES_URL vào {secrets_file}")


# ── Main ───────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  MIGRATE SQLite → PostgreSQL (Neon DB)")
    print("=" * 60)

    postgres_url = _load_postgres_url()
    sqlite_path = _load_sqlite_path()

    print(f"\n📂 SQLite  : {sqlite_path}")
    print(f"🌐 Postgres: {postgres_url[:50]}...")

    if not Path(sqlite_path).exists():
        print(f"\n❌ Không tìm thấy file SQLite: {sqlite_path}")
        sys.exit(1)

    # Kết nối
    print("\n🔌 Đang kết nối...")
    sqlite_conn = sqlite3.connect(sqlite_path)
    try:
        pg_conn = psycopg2.connect(postgres_url)
    except Exception as e:
        print(f"❌ Không kết nối được PostgreSQL: {e}")
        sqlite_conn.close()
        sys.exit(1)
    print("   ✅ SQLite  — OK")
    print("   ✅ Postgres — OK")

    t0 = time.time()

    # Tạo schema
    create_schema(pg_conn)

    # Copy data
    print("\n📦 Copy data...")
    summary: dict[str, int] = {}
    total = 0
    for table in TABLE_ORDER:
        count = migrate_table(table, sqlite_conn, pg_conn)
        summary[table] = count
        total += count
        if count > 0:
            print(f"   ✅ {table}: {count} dòng")

    # Reset sequences
    reset_sequences(pg_conn)

    # Lưu URL vào secrets để app tự bật Postgres
    save_secrets(postgres_url)

    # Đóng kết nối
    sqlite_conn.close()
    pg_conn.close()

    elapsed = time.time() - t0

    # Báo cáo
    print("\n" + "=" * 60)
    print(f"  ✅ MIGRATION HOÀN THÀNH ({elapsed:.1f}s)")
    print("=" * 60)
    print(f"  Tổng dòng đã copy: {total:,}")
    print()
    for table, count in summary.items():
        if count > 0:
            print(f"  {table:<30} {count:>6} dòng")
    print()
    print("📝 Bước tiếp theo:")
    print("   App sẽ tự dùng Neon DB vì secrets/database.json đã có POSTGRES_URL.")
    print("   Khởi động lại app để kiểm tra.")
    print()


if __name__ == "__main__":
    main()

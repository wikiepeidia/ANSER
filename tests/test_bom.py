"""Insert/query tests for bom_items — runs against the real Postgres/Neon
sanxuat_business DB (bom_items only exists in SCHEMA_PG, not SQLite).

Skipped entirely when SANXUAT_POSTGRES_URL isn't configured. Forces
Config.SANXUAT_USE_POSTGRES on for the duration of each test regardless of
what conftest.py's `app` fixture did to that flag elsewhere in the session
(it forces it off for SQLite isolation), and restores the prior value after
— so this module behaves the same whether it runs before or after the
SQLite-backed test modules. All rows created here are deleted in teardown,
success or failure.
"""
import time

import pytest

from core.config import Config
from core.sanxuat_db import get_connection, init_db, now

pytestmark = pytest.mark.skipif(
    not Config.SANXUAT_POSTGRES_URL,
    reason="SANXUAT_POSTGRES_URL not set — skipping live Postgres BOM test",
)


@pytest.fixture
def pg_conn():
    original = Config.SANXUAT_USE_POSTGRES
    Config.SANXUAT_USE_POSTGRES = True
    init_db()
    conn = get_connection()
    try:
        yield conn
    finally:
        conn.close()
        Config.SANXUAT_USE_POSTGRES = original


@pytest.fixture
def bom_products(pg_conn):
    """Creates 1 finished product + 2 material products for a BOM test, and
    deletes them (and any bom_items referencing them) afterwards."""
    tag = str(int(time.time() * 1000))
    codes = {
        "finished": f"__TEST_BOM_FIN_{tag}__",
        "mat1": f"__TEST_BOM_MAT1_{tag}__",
        "mat2": f"__TEST_BOM_MAT2_{tag}__",
    }
    ids = {}
    for key, code in codes.items():
        pg_conn.execute(
            "INSERT INTO products (code, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (code, f"Test product {code}", now(), now()),
        )
    pg_conn.commit()
    for key, code in codes.items():
        row = pg_conn.execute("SELECT id FROM products WHERE code = ?", (code,)).fetchone()
        ids[key] = row["id"]

    try:
        yield ids
    finally:
        pg_conn.execute("DELETE FROM bom_items WHERE product_id = ?", (ids["finished"],))
        pg_conn.execute(
            "DELETE FROM products WHERE id IN (?, ?, ?)",
            (ids["finished"], ids["mat1"], ids["mat2"]),
        )
        pg_conn.commit()


def test_bom_items_insert_and_query_materials_for_product(pg_conn, bom_products):
    finished_id = bom_products["finished"]
    mat1_id = bom_products["mat1"]
    mat2_id = bom_products["mat2"]

    pg_conn.execute(
        "INSERT INTO bom_items (product_id, material_product_id, quantity_per_unit, unit, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (finished_id, mat1_id, 2.5, "kg", "test"),
    )
    pg_conn.execute(
        "INSERT INTO bom_items (product_id, material_product_id, quantity_per_unit, unit, notes) "
        "VALUES (?, ?, ?, ?, ?)",
        (finished_id, mat2_id, 0.75, "cái", "test"),
    )
    pg_conn.commit()

    rows = pg_conn.execute(
        "SELECT bi.material_product_id, bi.quantity_per_unit, bi.unit, mp.code AS material_code "
        "FROM bom_items bi JOIN products mp ON mp.id = bi.material_product_id "
        "WHERE bi.product_id = ? ORDER BY bi.material_product_id",
        (finished_id,),
    ).fetchall()

    assert len(rows) == 2
    by_material = {r["material_product_id"]: r for r in rows}
    assert float(by_material[mat1_id]["quantity_per_unit"]) == 2.5
    assert by_material[mat1_id]["unit"] == "kg"
    assert float(by_material[mat2_id]["quantity_per_unit"]) == 0.75
    assert by_material[mat2_id]["unit"] == "cái"


def test_bom_items_unique_product_material_pair(pg_conn, bom_products):
    finished_id = bom_products["finished"]
    mat1_id = bom_products["mat1"]

    pg_conn.execute(
        "INSERT INTO bom_items (product_id, material_product_id, quantity_per_unit, unit) "
        "VALUES (?, ?, ?, ?)",
        (finished_id, mat1_id, 1, "kg"),
    )
    pg_conn.commit()

    with pytest.raises(Exception):
        pg_conn.execute(
            "INSERT INTO bom_items (product_id, material_product_id, quantity_per_unit, unit) "
            "VALUES (?, ?, ?, ?)",
            (finished_id, mat1_id, 5, "kg"),
        )
        pg_conn.commit()
    pg_conn.rollback()

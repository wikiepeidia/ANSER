import sqlite3

import pytest

from core.extensions import db_manager


def _create_test_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        '''CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            password TEXT,
            name TEXT,
            avatar TEXT,
            theme TEXT,
            role TEXT,
            first_name TEXT,
            last_name TEXT,
            google_token TEXT,
            manager_id INTEGER,
            subscription_expires_at TEXT
        )'''
    )
    cursor.execute(
        '''CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT,
            unit TEXT,
            price REAL,
            stock_quantity INTEGER,
            description TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )'''
    )
    cursor.execute(
        '''CREATE TABLE customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT,
            notes TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )'''
    )
    cursor.execute(
        '''INSERT INTO users (
            id, email, password, name, avatar, theme, role, first_name, last_name, google_token
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (1, 'tester@example.com', 'hashed', 'Test User', None, None, 'admin', 'Test', 'User', None),
    )
    conn.commit()
    conn.close()


def _execute(db_path, query, params=()):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


def _fetchall(db_path, query, params=()):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


@pytest.fixture()
def catalog_client(app, tmp_path):
    db_path = tmp_path / 'catalog-smoke.db'
    old_db_path = db_manager.db_path
    old_use_postgres = db_manager.use_postgres

    db_manager.db_path = str(db_path)
    db_manager.use_postgres = False
    _create_test_schema(str(db_path))

    try:
        with app.test_client() as client:
            with client.session_transaction() as session:
                session['_user_id'] = '1'
                session['_fresh'] = True
            yield client, str(db_path)
    finally:
        db_manager.db_path = old_db_path
        db_manager.use_postgres = old_use_postgres


@pytest.mark.parametrize(
    ('table_name', 'endpoint', 'seed_sql', 'expected_key'),
    [
        (
            'products',
            '/api/products',
            "INSERT INTO products (code, name, category, unit, price, stock_quantity, description, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            'products',
        ),
        (
            'customers',
            '/api/customers',
            "INSERT INTO customers (code, name, phone, email, address, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            'customers',
        ),
    ],
)
def test_catalog_list_endpoints_return_seeded_records(catalog_client, table_name, endpoint, seed_sql, expected_key):
    client, db_path = catalog_client

    if table_name == 'products':
        _execute(db_path, seed_sql, ('P-001', 'Seed Product', 'cat', 'pcs', 10, 2, 'seed', 1))
        expected_code = 'P-001'
    else:
        _execute(db_path, seed_sql, ('C-001', 'Seed Customer', '123', 'seed@example.com', 'Addr', 'seed', 1))
        expected_code = 'C-001'

    response = client.get(endpoint)

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload[expected_key][0]['code'] == expected_code


@pytest.mark.parametrize(
    ('endpoint', 'payload', 'table_name', 'code_value'),
    [
        (
            '/api/products',
            {
                'code': 'P-NEW',
                'name': 'Created Product',
                'category': 'tools',
                'unit': 'pcs',
                'price': 42,
                'stock_quantity': 8,
                'description': 'created in test',
            },
            'products',
            'P-NEW',
        ),
        (
            '/api/customers',
            {
                'code': 'C-NEW',
                'name': 'Created Customer',
                'phone': '555',
                'email': 'created@example.com',
                'address': 'District 1',
                'notes': 'created in test',
            },
            'customers',
            'C-NEW',
        ),
    ],
)
def test_catalog_create_endpoints_persist_records(catalog_client, endpoint, payload, table_name, code_value):
    client, db_path = catalog_client

    response = client.post(endpoint, json=payload)

    assert response.status_code == 200
    payload_json = response.get_json()
    assert payload_json['success'] is True

    rows = _fetchall(db_path, f'SELECT code, name, created_by FROM {table_name} WHERE code = ?', (code_value,))
    assert rows == [(code_value, payload['name'], 1)]


def test_authenticated_user_can_update_product(catalog_client):
    client, db_path = catalog_client
    _execute(
        db_path,
        "INSERT INTO products (id, code, name, category, unit, price, stock_quantity, description, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 'P-UP', 'Before Product', 'cat', 'pcs', 10, 2, 'before', 1),
    )

    response = client.put(
        '/api/products/1',
        json={
            'name': 'After Product',
            'category': 'updated-cat',
            'unit': 'box',
            'price': 25,
            'stock_quantity': 9,
            'description': 'after',
        },
    )

    assert response.status_code == 200
    assert response.get_json()['success'] is True
    rows = _fetchall(
        db_path,
        'SELECT name, category, unit, price, stock_quantity, description FROM products WHERE id = ?',
        (1,),
    )
    assert rows == [('After Product', 'updated-cat', 'box', 25.0, 9, 'after')]


def test_authenticated_user_can_update_customer(catalog_client):
    client, db_path = catalog_client
    _execute(
        db_path,
        "INSERT INTO customers (id, code, name, phone, email, address, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 'C-UP', 'Before Customer', '111', 'before@example.com', 'Old Addr', 'old', 1),
    )

    response = client.put(
        '/api/customers/1',
        json={
            'name': 'After Customer',
            'phone': '999',
            'email': 'after@example.com',
            'address': 'New Addr',
            'notes': 'after',
        },
    )

    assert response.status_code == 200
    assert response.get_json()['success'] is True
    rows = _fetchall(
        db_path,
        'SELECT name, phone, email, address, notes FROM customers WHERE id = ?',
        (1,),
    )
    assert rows == [('After Customer', '999', 'after@example.com', 'New Addr', 'after')]


def test_authenticated_user_can_delete_product(catalog_client):
    client, db_path = catalog_client
    _execute(
        db_path,
        "INSERT INTO products (id, code, name, category, unit, price, stock_quantity, description, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 'P-DEL', 'Delete Product', 'cat', 'pcs', 10, 1, 'delete', 1),
    )

    response = client.delete('/api/products/1')

    assert response.status_code == 200
    assert response.get_json()['success'] is True
    assert _fetchall(db_path, 'SELECT id FROM products WHERE id = ?', (1,)) == []


def test_authenticated_user_can_delete_customer(catalog_client):
    client, db_path = catalog_client
    _execute(
        db_path,
        "INSERT INTO customers (id, code, name, phone, email, address, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (1, 'C-DEL', 'Delete Customer', '222', 'delete@example.com', 'Addr', 'delete', 1),
    )

    response = client.delete('/api/customers/1')

    assert response.status_code == 200
    assert response.get_json()['success'] is True
    assert _fetchall(db_path, 'SELECT id FROM customers WHERE id = ?', (1,)) == []


@pytest.mark.parametrize(
    ('endpoint', 'seed_sql', 'seed_params', 'payload', 'expected_message'),
    [
        (
            '/api/products',
            "INSERT INTO products (code, name, category, unit, price, stock_quantity, description, created_by) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ('P-DUP', 'Seed Product', 'cat', 'pcs', 10, 2, 'seed', 1),
            {
                'code': 'P-DUP',
                'name': 'Duplicate Product',
                'category': 'cat',
                'unit': 'pcs',
                'price': 11,
                'stock_quantity': 3,
                'description': 'dup',
            },
            'Product code already exists',
        ),
        (
            '/api/customers',
            "INSERT INTO customers (code, name, phone, email, address, notes, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ('C-DUP', 'Seed Customer', '111', 'seed@example.com', 'Addr', 'seed', 1),
            {
                'code': 'C-DUP',
                'name': 'Duplicate Customer',
                'phone': '333',
                'email': 'dup@example.com',
                'address': 'Addr 2',
                'notes': 'dup',
            },
            'Customer code already exists',
        ),
    ],
)
def test_duplicate_catalog_codes_are_rejected(catalog_client, endpoint, seed_sql, seed_params, payload, expected_message):
    client, db_path = catalog_client
    _execute(db_path, seed_sql, seed_params)

    response = client.post(endpoint, json=payload)

    assert response.status_code == 400
    payload_json = response.get_json()
    assert payload_json['success'] is False
    assert expected_message in payload_json['message']
"""Sales and point-of-sale routes extracted from main_routes."""

from flask import current_app

import app as app_module


# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value


def register_sales_routes(app):
    @app.route('/sale')
    @login_required
    def sale_page():
        return render_template('sale.html')

    @app.route('/api/products/search')
    @login_required
    def search_products():
        query = request.args.get('q', '').lower()
        random_mode = request.args.get('random') == 'true'

        try:
            catalog_path = os.path.join(current_app.root_path, 'dl_service/data/product_catalogs.json')
            if not os.path.exists(catalog_path):
                catalog_path = os.path.join(os.getcwd(), 'dl_service/data/product_catalogs.json')

            with open(catalog_path, 'r', encoding='utf-8') as f:
                products = json.load(f)

            if random_mode:
                import random

                results = random.sample(products, min(len(products), 8))
            else:
                results = [
                    p for p in products
                    if query in p.get('name', '').lower() or query in str(p.get('id', '')).lower()
                ][:5]

            return jsonify(results)
        except Exception as e:
            print(f"Error searching products: {e}")
            return jsonify([])

    @app.route('/api/sales/create', methods=['POST'])
    @login_required
    def create_sale():
        data = request.json
        try:
            db = Database()
            conn = db.get_connection()
            c = conn.cursor()

            items_json = json.dumps(data.get('items', []))
            workspace_id = data.get('workspace_id')

            c.execute(
                '''
                INSERT INTO sales (user_id, total_amount, amount_given, change_amount, items, payment_method, workspace_id, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    current_user.id,
                    data.get('total_amount'),
                    data.get('amount_given'),
                    data.get('change_amount'),
                    items_json,
                    data.get('payment_method', 'cash'),
                    workspace_id,
                    data.get('category', 'Retail')
                )
            )

            conn.commit()
            return jsonify({'success': True, 'message': 'Sale recorded successfully'})
        except Exception as e:
            print(f"Error creating sale: {e}")
            try:
                conn.rollback()
            except:
                pass
            return jsonify({'success': False, 'message': str(e)}), 500

    @app.route('/api/sales/history', methods=['GET'])
    @login_required
    def get_sales_history():
        try:
            search_query = request.args.get('q', '').strip()
            limit = request.args.get('limit', 10, type=int)

            db = Database()
            conn = db.get_connection()
            c = conn.cursor()

            base_query = '''
                SELECT id, created_at, total_amount, payment_method, items
                FROM sales
                WHERE user_id = ?
            '''
            params = [current_user.id]

            if search_query:
                if search_query.isdigit():
                    if Config.USE_POSTGRES:
                        base_query += " AND CAST(id AS TEXT) LIKE ?"
                    else:
                        base_query += " AND CAST(id AS TEXT) LIKE ?"
                    params.append(f"%{search_query}%")
                else:
                    base_query += " AND LOWER(payment_method) LIKE ?"
                    params.append(f"%{search_query.lower()}%")

            base_query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            c.execute(base_query, tuple(params))
            rows = c.fetchall()

            history = []
            for row in rows:
                try:
                    if not row[4]:
                        items = []
                    elif isinstance(row[4], str):
                        items = json.loads(row[4])
                    elif isinstance(row[4], (dict, list)):
                        items = row[4]
                    else:
                        items = []

                    if isinstance(items, list):
                        item_count = sum(int(item.get('qty', 0)) for item in items if isinstance(item, dict))
                    else:
                        item_count = 0
                except Exception as e:
                    print(f"Error parsing items for sale {row[0]}: {e}")
                    item_count = 0

                history.append(
                    {
                        'id': row[0],
                        'date': format_display_datetime(row[1]) or str(row[1]),
                        'amount': row[2],
                        'payment_method': row[3] or 'Cash',
                        'item_count': item_count,
                        'items': items,
                    }
                )

            return jsonify(history)
        except Exception as e:
            print(f"Error fetching history: {e}")
            import traceback

            traceback.print_exc()
            return jsonify({'error': str(e)}), 500

    @app.route('/api/sales/history/<int:sale_id>', methods=['DELETE'])
    @login_required
    def delete_sale(sale_id):
        try:
            if Config.USE_POSTGRES:
                db = Database()
                conn = db.get_connection()
                cur = conn.cursor()
                cur.execute("DELETE FROM sales WHERE id = %s", (sale_id,))
                if cur.rowcount == 0:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Sale not found'}), 404
                conn.commit()
                conn.close()
            else:
                db = Database()
                conn = db.get_connection()
                c = conn.cursor()
                c.execute("DELETE FROM sales WHERE id = ?", (sale_id,))
                if c.rowcount == 0:
                    conn.close()
                    return jsonify({'success': False, 'message': 'Sale not found'}), 404
                conn.commit()
                conn.close()

            return jsonify({'success': True, 'message': 'Sale deleted successfully'})
        except Exception as e:
            print(f"Error deleting sale: {e}")
            return jsonify({'success': False, 'message': str(e)}), 500
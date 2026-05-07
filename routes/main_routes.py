"""Legacy main route surface extracted from app.py."""

import sqlite3

import app as app_module

from routes.admin_subscription_routes import register_admin_subscription_routes
from routes.admin_user_routes import register_admin_user_routes
from routes.google_routes import register_google_routes
from routes.operations_routes import register_operations_routes
from routes.page_routes import register_page_routes
from routes.sales_routes import register_sales_routes
from routes.wallet_routes import register_wallet_routes
from routes.workspace_routes import register_workspace_routes

# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value


def register_main_routes(app):
    register_workspace_routes(app)
    
    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        # Use 'success' category so the alert renders with success styling in templates
        flash('You have been logged out successfully.', 'success')
        return redirect(url_for('auth.signin'))
    
    # ============= CUSTOMERS API (Khách hàng) =============
    @app.route('/api/customers', methods=['GET'])
    @login_required
    def api_get_customers():
        """Get all customers"""
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM customers ORDER BY created_at DESC')
        customers = []
        for row in c.fetchall():
            customers.append({
                'id': row[0], 'code': row[1], 'name': row[2], 'phone': row[3],
                'email': row[4], 'address': row[5], 'notes': row[6], 'created_at': row[8]
            })
        conn.close()
        return jsonify({'success': True, 'customers': customers})
    
    @app.route('/api/customers', methods=['POST'])
    @login_required
    def api_create_customer():
        """Create new customer"""
        data = request.get_json()
        if not data or 'code' not in data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO customers (code, name, phone, email, address, notes, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                     (data['code'], data['name'], data.get('phone', ''), data.get('email', ''),
                      data.get('address', ''), data.get('notes', ''), current_user.id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Customer created successfully'})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'message': 'Customer code already exists'}), 400
        finally:
            conn.close()
    
    @app.route('/api/customers/<int:customer_id>', methods=['PUT'])
    @login_required
    def api_update_customer(customer_id):
        """Update customer"""
        data = request.get_json()
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('''UPDATE customers SET name=?, phone=?, email=?, address=?, notes=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?''',
                     (data['name'], data.get('phone', ''), data.get('email', ''),
                      data.get('address', ''), data.get('notes', ''), customer_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Customer updated successfully'})
        finally:
            conn.close()
    
    @app.route('/api/customers/<int:customer_id>', methods=['DELETE'])
    @login_required
    def api_delete_customer(customer_id):
        """Delete customer"""
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM customers WHERE id=?', (customer_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Customer deleted successfully'})
    
    # ============= PRODUCTS API (Sản phẩm) =============
    @app.route('/api/products', methods=['GET'])
    @login_required
    def api_get_products():
        """Get all products"""
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM products ORDER BY created_at DESC')
        products = []
        for row in c.fetchall():
            products.append({
                'id': row[0], 'code': row[1], 'name': row[2], 'category': row[3],
                'unit': row[4], 'price': row[5], 'stock_quantity': row[6],
                'description': row[7], 'created_at': row[9]
            })
        conn.close()
        return jsonify({'success': True, 'products': products})
    
    @app.route('/api/products', methods=['POST'])
    @login_required
    def api_create_product():
        """Create new product"""
        data = request.get_json()
        if not data or 'code' not in data or 'name' not in data:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('''INSERT INTO products (code, name, category, unit, price, stock_quantity, description, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (data['code'], data['name'], data.get('category', ''), data.get('unit', 'cái'),
                      data.get('price', 0), data.get('stock_quantity', 0), data.get('description', ''), current_user.id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Product created successfully'})
        except sqlite3.IntegrityError:
            return jsonify({'success': False, 'message': 'Product code already exists'}), 400
        finally:
            conn.close()
    
    @app.route('/api/products/<int:product_id>', methods=['PUT'])
    @login_required
    def api_update_product(product_id):
        """Update product"""
        data = request.get_json()
        conn = db_manager.get_connection()
        c = conn.cursor()
        try:
            c.execute('''UPDATE products SET name=?, category=?, unit=?, price=?, stock_quantity=?, description=?, updated_at=CURRENT_TIMESTAMP
                        WHERE id=?''',
                     (data['name'], data.get('category', ''), data.get('unit', 'cái'),
                      data.get('price', 0), data.get('stock_quantity', 0), data.get('description', ''), product_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Product updated successfully'})
        finally:
            conn.close()
    
    @app.route('/api/products/<int:product_id>', methods=['DELETE'])
    @login_required
    def api_delete_product(product_id):
        """Delete product"""
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM products WHERE id=?', (product_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Product deleted successfully'})
    
    register_admin_user_routes(app)
    register_admin_subscription_routes(app)
    register_operations_routes(app)
    register_page_routes(app)
    register_sales_routes(app)
    register_wallet_routes(app)
    register_google_routes(app)

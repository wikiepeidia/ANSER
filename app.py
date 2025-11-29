from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect, CSRFError, generate_csrf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.database import Database
from core.auth import AuthManager
from core.config import Config
from core.utils import Utils
import os
import json
import sqlite3



# Update template folder to use ui/templates
app = Flask(__name__, template_folder='ui/templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change_me_to_a_secure_random_value')
app.config['WTF_CSRF_ENABLED'] = True
app.secret_key = app.config['SECRET_KEY']

limiter = Limiter(get_remote_address, app=app, default_limits=["100 per day", "66 per hour"])
Talisman(app, force_https=False, content_security_policy=None)
csrf = CSRFProtect(app)

# Store database manager in app extensions for decorator access
app.extensions['database'] = None  # Will be initialized after db_manager creation



# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.signin'

# Initialize core components
db_manager = Database()
db = db_manager  # Alias for convenience
auth_manager = AuthManager(db_manager)
config = Config()
utils = Utils()

# Store database manager in app extensions for permission decorator
app.extensions['database'] = db_manager


@app.context_processor
def inject_csrf_token():
    """Expose csrf_token helper in all templates."""
    return dict(csrf_token=lambda: generate_csrf())


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    """Provide graceful feedback when CSRF validation fails."""
    if request.path.startswith('/api/'):
        return jsonify({'success': False, 'message': 'CSRF token missing or invalid'}), 400
    flash('Security check failed. Please refresh the page and try again.', 'error')
    referer = request.referrer or url_for('auth.signin')
    return redirect(referer)

class User(UserMixin):
    def __init__(self, id, email, first_name, last_name, role='user'):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    user_data = auth_manager.get_user_by_id(int(user_id))
    if user_data:
        return User(user_data['id'], user_data['email'], user_data['first_name'], 
                    user_data['last_name'],user_data.get('role','user'))

    return None

# Auth Blueprint
from flask import Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signin', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=['POST'], error_message="Too many login attempts. Please try again later.")
def signin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user_data = auth_manager.verify_user(email, password)
        if user_data:
            user = User(user_data['id'], user_data['email'], user_data['first_name'], 
                        user_data['last_name'],user_data.get('role','user'))
            print(">>> Đăng nhập:", user.email, "role =", user.role)
            login_user(user)
            flash('Login Successful!', 'success')
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin_workspace'))
            else:
                return redirect(url_for('workspace'))
        else:
            flash('Email hoặc mật khẩu không đúng!', 'error')
    
    return render_template('signin.html')

@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per hour", methods=['POST'], error_message="Too many registrations from this address. Please try again later.")
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        phone = request.form.get('phone', '')
        
        success, message = auth_manager.register_user(email, password, first_name, last_name, phone)
        if success:
            flash('Đăng ký thành công! Vui lòng đăng nhập.', 'success')
            return redirect(url_for('auth.signin'))
        else:
            flash(message, 'error')
    
    return render_template('signup.html')
    

app.register_blueprint(auth_bp, url_prefix='/auth')

# Main routes
@app.route('/')
def index():
    if current_user.is_authenticated:
     # Check user role and redirect accordingly
        user_data = auth_manager.get_user_by_id(current_user.id)
        if user_data and user_data.get('role') == 'admin':
            return redirect(url_for('admin_workspace'))  # Admin goes to admin workspace
        else:
            return redirect(url_for('workspace'))  # Regular user goes to workspace
    return render_template('index.html')  # Show login page


@app.route('/admin')
@login_required
def admin_dashboard():
    # Check admin permission
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('workspace'))
    return render_template('admin_dashboard.html', user=current_user)

@app.route('/admin/workspace')
@login_required
def admin_workspace():
    # Redirect to new admin dashboard
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('workspace'))
    return redirect(url_for('admin_dashboard'))

@app.route('/workspace')
@login_required
def workspace():
     # Redirect admin users to admin dashboard (admin workspace)
    #user_data = auth_manager.get_user_by_id(current_user.id)
    #if user_data and user_data.get('role') == 'admin':
        #return redirect(url_for('admin_workspace'))
    return render_template('workspace.html', user=current_user)  # Regular users see user dashboard

@app.route('/manager/permissions')
@login_required
def manager_permissions():
    """Manager page to manage user permissions"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('workspace'))
    return render_template('manager_permissions.html', user=current_user)

@app.route('/admin/managers')
@login_required
def admin_managers():
    """Admin page to manage managers"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('workspace'))
    return render_template('admin_managers.html', user=current_user)

@app.route('/admin/roles')
@login_required
def admin_roles():
    """Admin page to manage user roles"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('workspace'))
    return render_template('admin_roles.html', user=current_user)

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    """Admin page for analytics and statistics"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('workspace'))
    return render_template('admin_analytics.html', user=current_user)

@app.route('/admin/subscriptions')
@login_required
def admin_subscriptions():
    """Admin page for managing manager subscriptions"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('workspace'))
    return render_template('admin_subscriptions.html', user=current_user)

# Route pages for main modules
@app.route('/customers')
@login_required
def customers():
    """Customers management page"""
    return render_template('customers.html', user=current_user)

@app.route('/products')
@login_required
def products():
    """Products management page"""
    return render_template('products.html', user=current_user)

@app.route('/imports')
@login_required
def imports():
    """Import transactions page"""
    return render_template('imports.html', user=current_user)

@app.route('/exports')
@login_required
def exports():
    """Export transactions page"""
    return render_template('exports.html', user=current_user)

@app.route('/se/auto-import')
@login_required
def se_auto_import():
    """SE Auto Import page"""
    return render_template('se_auto_import.html', user=current_user)

@app.route('/se/reports')
@login_required
def se_reports():
    """SE Reports page"""
    return render_template('se_reports.html', user=current_user)


    # add scenarios page route if you need it
@app.route('/scenarios')
@login_required
def scenarios():
    return render_template('scenarios.html', user=current_user)

@app.route('/workspace/builder')
@login_required
def workspace_builder():
    return render_template('workspace_builder.html', user=current_user)

# Workspace API Routes
@app.route('/api/workspaces')
@login_required
def get_workspaces():
    """Get all workspaces for current user"""
    try:
        workspaces = auth_manager.get_user_workspaces(current_user.id)
        return jsonify([{
            'id': w[0],
            'name': w[2],
            'type': w[3],
            'description': w[4],
            'created_at': w[6]
        } for w in workspaces])
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workspace/<int:workspace_id>/items')
@login_required
def get_workspace_items(workspace_id):
    """Get all items in a workspace"""
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    try:
        # Verify workspace exists and user has access
        c.execute('SELECT id FROM workspaces WHERE id = ? AND user_id = ?', (workspace_id, current_user.id))
        if not c.fetchone():
            return jsonify({'success': False, 'message': 'Workspace not found or access denied'}), 403
        
        c.execute('''SELECT * FROM items WHERE workspace_id = ? ORDER BY created_at DESC''', (workspace_id,))
        items = c.fetchall()
        
        return jsonify([{
            'id': item[0],
            'title': item[2],
            'description': item[3],
            'type': item[4],
            'status': item[5],
            'priority': item[6],
            'created_at': item[9]
        } for item in items])
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/workspace/<int:workspace_id>/items', methods=['POST'])
@login_required
def create_item(workspace_id):
    """Create new item in workspace"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data:
        return jsonify({'success': False, 'message': 'Missing required field: title'}), 400
    
    if not data['title'].strip():
        return jsonify({'success': False, 'message': 'Item title cannot be empty'}), 400
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    try:
        # Verify workspace exists and user has access
        c.execute('SELECT id FROM workspaces WHERE id = ? AND user_id = ?', (workspace_id, current_user.id))
        if not c.fetchone():
            return jsonify({'success': False, 'message': 'Workspace not found or access denied'}), 403
        
        c.execute('''INSERT INTO items (workspace_id, title, description, type, status, priority, assignee_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)''',
                 (workspace_id, data['title'].strip(), data.get('description', ''), 
                  data.get('type', 'task'), data.get('status', 'todo'),
                  data.get('priority', 'medium'), current_user.id))
        
        item_id = c.lastrowid
        conn.commit()
        
        return jsonify({'success': True, 'item_id': item_id, 'message': 'Item created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/items/<int:item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    """Update existing item"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'title' not in data:
        return jsonify({'success': False, 'message': 'Missing required field: title'}), 400
    
    if not data['title'].strip():
        return jsonify({'success': False, 'message': 'Item title cannot be empty'}), 400
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    try:
        c.execute('''UPDATE items SET title = ?, description = ?, status = ?, priority = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND assignee_id = ?''',
                 (data['title'].strip(), data.get('description', ''), 
                  data.get('status', 'todo'), data.get('priority', 'medium'),
                  item_id, current_user.id))
        
        conn.commit()
        
        if c.rowcount > 0:
            return jsonify({'success': True, 'message': 'Item updated successfully'})
        else:
            return jsonify({'success': False, 'message': 'Item not found or unauthorized'}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/items/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    """Delete item"""
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    try:
        c.execute('DELETE FROM items WHERE id = ? AND assignee_id = ?', (item_id, current_user.id))
        conn.commit()
        
        if c.rowcount > 0:
            return jsonify({'success': True, 'message': 'Item deleted successfully'})
        else:
            return jsonify({'success': False, 'message': 'Item not found or unauthorized'}), 404
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

@app.route('/api/workspace', methods=['POST'])
@login_required
def create_workspace():
    """Create new workspace"""
    data = request.get_json()
    
    # Validate required fields
    if not data or 'name' not in data or 'type' not in data:
        return jsonify({'success': False, 'message': 'Missing required fields: name and type'}), 400
    
    if not data['name'].strip():
        return jsonify({'success': False, 'message': 'Workspace name cannot be empty'}), 400
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    try:
        c.execute('''INSERT INTO workspaces (user_id, name, type, description)
                    VALUES (?, ?, ?, ?)''',
                 (current_user.id, data['name'].strip(), data['type'], data.get('description', '')))
        
        workspace_id = c.lastrowid
        conn.commit()
        
        return jsonify({'success': True, 'workspace_id': workspace_id, 'message': 'Workspace created successfully'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 400
    finally:
        conn.close()

# API Routes for scenarios
@app.route('/api/scenarios', methods=['GET'])
@login_required
def get_scenarios():
    try:
        scenarios = db.get_scenarios(current_user.id)
        return jsonify(scenarios)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scenarios', methods=['POST'])
@login_required
def create_scenario():
    try:
        data = request.get_json()
        scenario_id = db.create_scenario(
            user_id=current_user.id,
            name=data.get('name'),
            description=data.get('description', ''),
            active=data.get('active', False)
        )
        return jsonify({'success': True, 'message': 'Scenario created successfully', 'id': scenario_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scenarios/<int:scenario_id>', methods=['PUT'])
@login_required
def update_scenario(scenario_id):
    try:
        data = request.get_json()
        db.update_scenario(scenario_id, current_user.id, data)
        return jsonify({'success': True, 'message': 'Scenario updated successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/scenarios/<int:scenario_id>', methods=['DELETE'])
@login_required
def delete_scenario(scenario_id):
    try:
        db.delete_scenario(scenario_id, current_user.id)
        return jsonify({'success': True, 'message': 'Scenario deleted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/logout')
@login_required
def logout():
    logout_user()
    # Use 'success' category so the alert renders with success styling in templates
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('auth.signin'))

# Admin API Routes
@app.route('/api/admin/users')
@login_required
def admin_get_users():
    """Get all users for admin dashboard"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('''SELECT id, email, name, role, created_at FROM users ORDER BY created_at DESC''')
    users = c.fetchall()
    conn.close()
    
    return jsonify([{
        'id': user[0],
        'email': user[1],
        'name': user[2],
        'role': user[3],
        'created_at': user[4]
    } for user in users])

@app.route('/api/admin/stats')
@login_required
def admin_get_stats():
    """Get system statistics for admin dashboard"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    # Get user count
    c.execute('SELECT COUNT(*) FROM users')
    user_count = c.fetchone()[0]
    
    # Get workspace count
    c.execute('SELECT COUNT(*) FROM workspaces')
    workspace_count = c.fetchone()[0]
    
    # Get task count
    c.execute('SELECT COUNT(*) FROM items')
    task_count = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'users': user_count,
        'workspaces': workspace_count,
        'tasks': task_count,
        'uptime': '99.8%'  # Mock data
    })

@app.route('/api/admin/create-manager', methods=['POST'])
@login_required
def admin_create_manager():
    """Create a new manager (Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data or 'email' not in data or 'name' not in data or 'password' not in data:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    try:
        user_id = db_manager.create_user(data['email'], data['password'], data['name'], role='manager')
        return jsonify({'success': True, 'message': 'Manager created successfully', 'user_id': user_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/admin/users/<int:user_id>', methods=['DELETE'])
@login_required
def admin_delete_user(user_id):
    """Delete user (Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Prevent deleting self
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'User deleted successfully'})

@app.route('/api/admin/users/promote', methods=['POST'])
@login_required
def admin_promote_user():
    """Promote user to manager (Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    new_role = data.get('role', 'manager')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Missing user_id'}), 400
    
    # Prevent changing own role
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot change your own role'}), 400
    
    # Only allow promoting to manager
    if new_role not in ['manager']:
        return jsonify({'success': False, 'message': 'Can only promote to manager'}), 400
    
    try:
        conn = db_manager.get_connection()
        c = conn.cursor()
        
        # Check if user exists and is not already admin
        c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        if user[0] == 'admin':
            conn.close()
            return jsonify({'success': False, 'message': 'Cannot change admin role'}), 400
        
        # Update role
        c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'User promoted to {new_role} successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/admin/users/demote', methods=['POST'])
@login_required
def admin_demote_user():
    """Demote manager to user (Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    new_role = data.get('role', 'user')
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Missing user_id'}), 400
    
    # Prevent changing own role
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot change your own role'}), 400
    
    # Only allow demoting to user
    if new_role not in ['user']:
        return jsonify({'success': False, 'message': 'Can only demote to user'}), 400
    
    try:
        conn = db_manager.get_connection()
        c = conn.cursor()
        
        # Check if user exists and is not admin
        c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'User not found'}), 404
        
        if user[0] == 'admin':
            conn.close()
            return jsonify({'success': False, 'message': 'Cannot change admin role'}), 400
        
        # Update role
        c.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': f'User demoted to {new_role} successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# Manager Permission API Routes
@app.route('/api/manager/users-permissions')
@login_required
def manager_get_users_permissions():
    """Get all users with their permissions (Manager/Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    try:
        users = db_manager.get_all_users_with_permissions()
        return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/manager/permissions/grant', methods=['POST'])
@login_required
def manager_grant_permission():
    """Grant permission to a user (Manager/Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data or 'user_id' not in data or 'permission_type' not in data:
        return jsonify({'success': False, 'message': 'Missing required fields: user_id, permission_type'}), 400
    
    # Valid permission types
    valid_permissions = ['export', 'import', 'view_reports', 'manage_data', 'create_scenarios', 'delete_items']
    if data['permission_type'] not in valid_permissions:
        return jsonify({'success': False, 'message': f'Invalid permission type. Valid: {valid_permissions}'}), 400
    
    try:
        db_manager.grant_permission(data['user_id'], data['permission_type'], current_user.id)
        return jsonify({'success': True, 'message': 'Permission granted successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/manager/permissions/revoke', methods=['POST'])
@login_required
def manager_revoke_permission():
    """Revoke permission from a user (Manager/Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data or 'user_id' not in data or 'permission_type' not in data:
        return jsonify({'success': False, 'message': 'Missing required fields: user_id, permission_type'}), 400
    
    try:
        success = db_manager.revoke_permission(data['user_id'], data['permission_type'])
        if success:
            return jsonify({'success': True, 'message': 'Permission revoked successfully'})
        else:
            return jsonify({'success': False, 'message': 'Permission not found'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/user/permissions')
@login_required
def get_my_permissions():
    """Get current user's permissions"""
    try:
        permissions = db_manager.get_user_permissions(current_user.id)
        return jsonify({'success': True, 'permissions': permissions})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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

# ============= IMPORT/EXPORT TRANSACTIONS API =============
@app.route('/api/imports', methods=['GET'])
@login_required
def api_get_imports():
    """Get all import transactions"""
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM import_transactions ORDER BY created_at DESC')
    imports = []
    for row in c.fetchall():
        imports.append({
            'id': row[0], 'code': row[1], 'supplier_name': row[2],
            'total_amount': row[3], 'notes': row[4], 'status': row[5], 'created_at': row[7]
        })
    conn.close()
    return jsonify({'success': True, 'imports': imports})

@app.route('/api/exports', methods=['GET'])
@login_required
def api_get_exports():
    """Get all export transactions"""
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('''SELECT e.*, c.name as customer_name FROM export_transactions e
                 LEFT JOIN customers c ON e.customer_id = c.id
                 ORDER BY e.created_at DESC''')
    exports = []
    for row in c.fetchall():
        exports.append({
            'id': row[0], 'code': row[1], 'customer_id': row[2],
            'total_amount': row[3], 'notes': row[4], 'status': row[5],
            'created_at': row[7], 'customer_name': row[8] if len(row) > 8 else ''
        })
    conn.close()
    return jsonify({'success': True, 'exports': exports})

# ============= SUBSCRIPTION MANAGEMENT API =============
@app.route('/api/admin/subscriptions', methods=['GET'])
@login_required
def api_get_subscriptions():
    """Get all manager subscriptions"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    from datetime import datetime
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    c.execute('''SELECT 
                    s.id, s.user_id, s.subscription_type, s.amount, 
                    s.start_date, s.end_date, s.status,
                    u.name as user_name, u.email as user_email
                FROM manager_subscriptions s
                JOIN users u ON s.user_id = u.id
                ORDER BY s.end_date DESC''')
    
    subscriptions = []
    for row in c.fetchall():
        subscriptions.append({
            'id': row[0],
            'user_id': row[1],
            'subscription_type': row[2],
            'amount': row[3],
            'start_date': row[4],
            'end_date': row[5],
            'status': row[6],
            'user_name': row[7],
            'user_email': row[8]
        })
    
    conn.close()
    return jsonify({'success': True, 'subscriptions': subscriptions})

@app.route('/api/admin/subscription-history', methods=['GET'])
@login_required
def api_get_subscription_history():
    """Get subscription payment history"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    c.execute('''SELECT 
                    h.id, h.user_id, h.subscription_type, h.amount,
                    h.payment_date, h.payment_method, h.transaction_id, h.status,
                    u.name as user_name
                FROM subscription_history h
                JOIN users u ON h.user_id = u.id
                ORDER BY h.payment_date DESC
                LIMIT 50''')
    
    history = []
    for row in c.fetchall():
        history.append({
            'id': row[0],
            'user_id': row[1],
            'subscription_type': row[2],
            'amount': row[3],
            'payment_date': row[4],
            'payment_method': row[5],
            'transaction_id': row[6],
            'status': row[7],
            'user_name': row[8]
        })
    
    conn.close()
    return jsonify({'success': True, 'history': history})

@app.route('/api/admin/extend-subscription', methods=['POST'])
@login_required
def api_extend_subscription():
    """Extend manager subscription"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    from datetime import datetime, timedelta
    
    data = request.get_json()
    user_id = data.get('user_id')
    subscription_type = data.get('subscription_type')
    payment_method = data.get('payment_method')
    transaction_id = data.get('transaction_id', '')
    
    # Define subscription plans
    plans = {
        'monthly': {'days': 30, 'amount': 500000},
        'quarterly': {'days': 90, 'amount': 1200000},
        'yearly': {'days': 365, 'amount': 4000000}
    }
    
    if subscription_type not in plans:
        return jsonify({'success': False, 'message': 'Invalid subscription type'}), 400
    
    plan = plans[subscription_type]
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    try:
        # Get current subscription
        c.execute('SELECT end_date FROM manager_subscriptions WHERE user_id = ?', (user_id,))
        current_sub = c.fetchone()
        
        # Calculate new dates
        now = datetime.now()
        if current_sub:
            current_end = datetime.strptime(current_sub[0], '%Y-%m-%d %H:%M:%S')
            # If current subscription is still active, extend from end date
            start_date = max(now, current_end)
        else:
            start_date = now
        
        end_date = start_date + timedelta(days=plan['days'])
        
        # Update or insert subscription
        if current_sub:
            c.execute('''UPDATE manager_subscriptions 
                        SET subscription_type = ?, amount = ?, 
                            start_date = ?, end_date = ?, 
                            status = 'active', payment_method = ?,
                            transaction_id = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?''',
                     (subscription_type, plan['amount'], 
                      start_date.strftime('%Y-%m-%d %H:%M:%S'),
                      end_date.strftime('%Y-%m-%d %H:%M:%S'),
                      payment_method, transaction_id, user_id))
        else:
            c.execute('''INSERT INTO manager_subscriptions 
                        (user_id, subscription_type, amount, start_date, end_date, 
                         status, payment_method, transaction_id)
                        VALUES (?, ?, ?, ?, ?, 'active', ?, ?)''',
                     (user_id, subscription_type, plan['amount'],
                      start_date.strftime('%Y-%m-%d %H:%M:%S'),
                      end_date.strftime('%Y-%m-%d %H:%M:%S'),
                      payment_method, transaction_id))
        
        # Update user's subscription_expires_at
        c.execute('UPDATE users SET subscription_expires_at = ? WHERE id = ?',
                 (end_date.strftime('%Y-%m-%d %H:%M:%S'), user_id))
        
        # Log payment history
        c.execute('''INSERT INTO subscription_history 
                    (user_id, subscription_type, amount, payment_method, 
                     transaction_id, status)
                    VALUES (?, ?, ?, ?, ?, 'completed')''',
                 (user_id, subscription_type, plan['amount'], 
                  payment_method, transaction_id))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Subscription extended successfully'})
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/check-expired-subscriptions', methods=['POST'])
@login_required
def api_check_expired_subscriptions():
    """Check and demote expired manager subscriptions"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    from datetime import datetime
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Find expired subscriptions
        c.execute('''SELECT user_id FROM manager_subscriptions 
                    WHERE end_date < ? AND status = 'active' ''', (now,))
        expired_users = c.fetchall()
        
        demoted_count = 0
        for (user_id,) in expired_users:
            # Update subscription status
            c.execute('''UPDATE manager_subscriptions 
                        SET status = 'expired', updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ?''', (user_id,))
            
            # Demote user to regular user
            c.execute('UPDATE users SET role = ? WHERE id = ?', ('user', user_id))
            demoted_count += 1
        
        conn.commit()
        return jsonify({
            'success': True, 
            'demoted_count': demoted_count,
            'message': f'Demoted {demoted_count} expired managers'
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    db_manager.init_database()
    app.run(host='0.0.0.0', port=5000, debug=True, ssl_context='adhoc')


from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from core.database import Database
from core.auth import AuthManager
from core.config import Config
from core.utils import Utils
import os
import json



# Update template folder to use ui/templates
app = Flask(__name__, template_folder='ui/templates')
app.secret_key = 'your-secret-key-here'

from flask import Flask, render_template



# Route mặc định (kept as internal helper) — not used as main index
@app.route('/_home')
def home():
    return render_template('index.html')


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
    return redirect(url_for('admin_workspace'))

@app.route('/admin/workspace')
@login_required
def admin_workspace():
    return render_template('admin_workspace.html', user=current_user)

@app.route('/workspace_old')
@login_required
def workspace_old_redirect():
    return redirect(url_for('admin_workspace'))

@app.route('/workspace')
@login_required
def workspace():
     # Redirect admin users to admin dashboard (admin workspace)
    #user_data = auth_manager.get_user_by_id(current_user.id)
    #if user_data and user_data.get('role') == 'admin':
        #return redirect(url_for('admin_workspace'))
    return render_template('workspace.html', user=current_user)  # Regular users see user dashboard


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

if __name__ == '__main__':
    db_manager.init_database()
    app.run(debug=True)


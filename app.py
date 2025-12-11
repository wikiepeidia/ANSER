from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect, CSRFError, generate_csrf
from flask_talisman import Talisman 
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from core.database import Database
from core.auth import AuthManager
from core.config import Config
from core.utils import Utils
from core.workflow_engine import execute_workflow
from datetime import datetime, timedelta
from authlib.integrations.flask_client import OAuth
import secrets
import os
import json
import sqlite3
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Allow OAuth over HTTP for local development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Update template folder to use ui/templates
app = Flask(__name__, template_folder='ui/templates')
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change_me_to_a_secure_random_value')
app.config['WTF_CSRF_ENABLED'] = True
app.secret_key = app.config['SECRET_KEY']
app.config['SESSION_COOKIE_SECURE'] = False
app.config['PREFERRED_URL_SCHEME'] = 'http'

#OAuth2 configuration
# Load secrets from file
try:
    with open('secrets/google_oauth.json') as f:
        oauth_secrets = json.load(f)
        app.config['GOOGLE_CLIENT_ID'] = oauth_secrets.get('GOOGLE_CLIENT_ID')
        app.config['GOOGLE_CLIENT_SECRET'] = oauth_secrets.get('GOOGLE_CLIENT_SECRET')
except FileNotFoundError:
    print("Warning: secrets/google_oauth.json not found. OAuth will not work.")
    app.config['GOOGLE_CLIENT_ID'] = os.environ.get('GOOGLE_CLIENT_ID')
    app.config['GOOGLE_CLIENT_SECRET'] = os.environ.get('GOOGLE_CLIENT_SECRET')

Talisman(app,
         force_https=False,
         content_security_policy={
             'default-src': ["'self'","*"],
             'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'", "*"],
             'style-src': ["'self'", "'unsafe-inline'", "*"],
             'img-src': ["'self'", "data:", "*"],
             'font-src': ["'self'", "*"],
             'object-src': ["'none'"],
             'frame-ancestors': ["'none'"],
         },
         strict_transport_security=False,
         frame_options='DENY',
         x_content_type_options=True,
         session_cookie_secure=False,
         force_file_save=False
         )

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/gmail.send'}
)

# Session configuration - 30 minutes
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)
app.config['SESSION_REFRESH_EACH_REQUEST'] = True

limiter = Limiter(get_remote_address, app=app, default_limits=["100 per day", "66 per hour"])
csrf = CSRFProtect(app)

# Store database manager in app extensions for decorator access
app.extensions['database'] = None  # Will be initialized after db_manager creation



# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.signin'


@login_manager.unauthorized_handler
def login_unauthorized():
    """Return JSON 401 for api endpoints or redirect to signin for normal routes"""
    try:
        path = request.path or ''
        accepts_json = 'application/json' in (request.headers.get('Accept') or '')
    except Exception:
        path = ''
        accepts_json = False
    if path.startswith('/api/') or accepts_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'success': False, 'message': 'Unauthorized - please login'}), 401
    flash('Please log in to continue', 'error')
    return redirect(url_for('auth.signin'))

# Initialize core components
db_manager = Database()
db = db_manager  # Alias for convenience
auth_manager = AuthManager(db_manager)
config = Config()
utils = Utils()

# Store database manager in app extensions for permission decorator
app.extensions['database'] = db_manager

# Central subscription plans (used in wallet/subscription logic)
SUBSCRIPTION_PLANS = {
    'monthly': {'name': 'Monthly', 'days': 30, 'amount': 500000, 'description': 'Gói hàng tháng'},
    'quarterly': {'name': 'Quarterly', 'days': 90, 'amount': 1200000, 'description': 'Gói 3 tháng'},
    'yearly': {'name': 'Yearly', 'days': 365, 'amount': 4000000, 'description': 'Gói hàng năm'}
}

def format_plan_dict(plan_key):
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        return None
    return {
        'key': plan_key,
        'name': plan['name'],
        'amount': plan['amount'],
        'days': plan['days'],
        'description': plan.get('description', '')
    }


# Inject project-wide variables into templates
@app.context_processor
def inject_project_config():
    try:
        project_name = getattr(config, 'PROJECT_NAME', 'Group Project AI-ML')
    except Exception:
        project_name = 'Group Project AI-ML'
    return {
        'project_name': project_name,
        'project_config': config
    }

def parse_db_datetime(value):
    if not value:
        return None
    if isinstance(value, (str,)):
        # Try multiple formats
        from datetime import datetime
        for fmt in ('%Y-%m-%d %H:%M:%S.%f', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value)
        except Exception:
            return None
    return None

def format_display_datetime(value):
    dt = parse_db_datetime(value)
    return dt.strftime('%d/%m/%Y %H:%M') if dt else None

def parse_metadata(raw_value):
    if not raw_value:
        return {}
    if isinstance(raw_value, dict):
        return raw_value
    try:
        return json.loads(raw_value)
    except Exception:
        return {}



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
    def __init__(self, id, email, first_name, last_name, role='user', google_token=None, avatar=None):
        self.id = id
        self.email = email
        self.first_name = first_name
        self.last_name = last_name
        self.role = role
        self.google_token = google_token
        self.avatar = avatar

    @property
    def name(self):
        return f"{self.first_name} {self.last_name}"

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = auth_manager.get_user_by_id(int(user_id))
        if user_data:
            return User(
                user_data['id'], 
                user_data['email'], 
                user_data['first_name'], 
                user_data['last_name'],
                user_data.get('role', 'user'), 
                user_data.get('google_token'),
                user_data.get('avatar')
            )
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
    return None

# Auth Blueprint
from flask import Blueprint
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signin', methods=['GET', 'POST'])
@limiter.limit("5 per minute", methods=['POST'], error_message="Too many login attempts. Please try again later.")
def signin():
    if request.method == 'POST':
        try:
            email = request.form['email']
            password = request.form['password']
            
            user_data = auth_manager.verify_user(email, password)
            if user_data:
                user = User(user_data['id'], user_data['email'], user_data['first_name'], 
                            user_data['last_name'],user_data.get('role','user'), user_data.get('google_token'))
                print(">>> Đăng nhập:", user.email, "role =", user.role)
                login_user(user, remember=True)  # Remember user to extend session
                session.permanent = True  # Set session to use PERMANENT_SESSION_LIFETIME
                flash('Login Successful!', 'success')
                
                # Redirect based on role
                if user.role == 'admin':
                    return redirect(url_for('admin_workspace'))
                else:
                    return redirect(url_for('workspace'))
            else:
                flash('Invalid email or password!', 'error')
        except Exception as e:
            print(f"Login Error: {e}")
            import traceback
            traceback.print_exc()
            flash('An unexpected error occurred. Please try again later.', 'error')
    
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
            flash('Registration successful! Please log in.', 'success')
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
        flash('You do not have permission to access this page', 'error')
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

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard - chức năng kiếm tiền"""
    return render_template('dashboard.html', user=current_user)

@app.route('/workspace')
@login_required
def workspace():
     # Redirect admin users to admin dashboard (admin workspace)
    #user_data = auth_manager.get_user_by_id(current_user.id)
    #if user_data and user_data.get('role') == 'admin':
        #return redirect(url_for('admin_workspace'))
    return render_template('workspace.html', user=current_user)  # Regular users see user dashboard

@app.route('/manager/create-user')
@login_required
def create_user_account():
    """Manager/Admin page to create user accounts"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        flash('Bạn không có quyền truy cập trang này', 'error')
        return redirect(url_for('workspace'))
    return render_template('create_user_account.html', user=current_user)

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

@app.route('/api/workflow/execute', methods=['POST'])
@login_required
@csrf.exempt
def run_workflow():
    try:
        workflow_data = request.json
        
        # Get token from current_user
        token_info = None
        if current_user.google_token:
            try:
                token_info = json.loads(current_user.google_token)
            except Exception as e:
                print(f"Error parsing google_token for user {current_user.id}: {e}")
        
        result = execute_workflow(workflow_data, token_info)
        return jsonify(result)
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



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

@app.route('/api/create-user', methods=['POST'])
@login_required
def create_user():
    """Create a new user account (Manager/Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    try:
        # Build full name
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        full_name = f"{first_name} {last_name}".strip() or data['email'].split('@')[0]
        
        # Create user with 'user' role only
        user_id = db_manager.create_user(data['email'], data['password'], full_name, role='user')
        return jsonify({'success': True, 'message': 'User created successfully', 'user_id': user_id})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

@app.route('/api/users', methods=['GET'])
@login_required
@csrf.exempt
def get_users():
    """Get list of users (Manager/Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    role_filter = request.args.get('role', None)
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    # Check if first_name column exists
    c.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in c.fetchall()]
    has_first_name = 'first_name' in columns
    
    if has_first_name:
        if role_filter:
            c.execute('''
                SELECT id, email, first_name, last_name, role, created_at 
                FROM users 
                WHERE role = ?
                ORDER BY created_at DESC
            ''', (role_filter,))
        else:
            c.execute('''
                SELECT id, email, first_name, last_name, role, created_at 
                FROM users 
                ORDER BY created_at DESC
            ''')
        
        users = []
        for row in c.fetchall():
            users.append({
                'id': row[0],
                'email': row[1],
                'first_name': row[2] or '',
                'last_name': row[3] or '',
                'role': row[4],
                'created_at': row[5]
            })
    else:
        # Fallback to name column
        if role_filter:
            c.execute('''
                SELECT id, email, name, role, created_at 
                FROM users 
                WHERE role = ?
                ORDER BY created_at DESC
            ''', (role_filter,))
        else:
            c.execute('''
                SELECT id, email, name, role, created_at 
                FROM users 
                ORDER BY created_at DESC
            ''')
        
        users = []
        for row in c.fetchall():
            users.append({
                'id': row[0],
                'email': row[1],
                'first_name': row[2] or '',
                'last_name': '',
                'role': row[3],
                'created_at': row[4]
            })
    
    conn.close()
    return jsonify({'success': True, 'users': users})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user_account(user_id):
    """Delete user account (Manager/Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    # Prevent deleting self
    if user_id == current_user.id:
        return jsonify({'success': False, 'message': 'Cannot delete yourself'}), 400
    
    # Check if user exists and is a regular user
    conn = db_manager.get_connection()
    c = conn.cursor()
    c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Only allow deleting regular users
    if user[0] != 'user':
        conn.close()
        return jsonify({'success': False, 'message': 'Can only delete regular users'}), 403
    
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'User deleted successfully'})

@app.route('/api/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_user_password(user_id):
    """Reset user password (Manager/Admin only)"""
    if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    if not data or 'password' not in data:
        return jsonify({'success': False, 'message': 'Missing password'}), 400
    
    new_password = data['password']
    if len(new_password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters'}), 400
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    
    # Check if user exists
    c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    user = c.fetchone()
    
    if not user:
        conn.close()
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    # Hash new password
    from werkzeug.security import generate_password_hash
    hashed_password = generate_password_hash(new_password)
    
    c.execute('UPDATE users SET password = ? WHERE id = ?', (hashed_password, user_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Password reset successfully'})

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
                    s.start_date, s.end_date, s.status, s.auto_renew,
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
            'auto_renew': bool(row[7]) if len(row) > 7 and row[7] is not None else False,
            'user_name': row[8] if len(row) > 8 else 'Unknown',
            'user_email': row[9] if len(row) > 9 else 'Unknown'
        })
    
    conn.close()
    return jsonify({'success': True, 'subscriptions': subscriptions})

@app.route('/api/admin/subscription/auto-renew', methods=['POST'])
@login_required
@csrf.exempt
def api_toggle_auto_renew():
    """Toggle auto-renew for a subscription"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json()
    user_id = data.get('user_id')
    auto_renew = data.get('auto_renew', False)
    
    if not user_id:
        return jsonify({'success': False, 'message': 'Missing user_id'}), 400
    
    try:
        conn = db_manager.get_connection()
        c = conn.cursor()
        
        # Check if auto_renew column exists
        c.execute("PRAGMA table_info(manager_subscriptions)")
        columns = [col[1] for col in c.fetchall()]
        
        if 'auto_renew' not in columns:
            # Add column if not exists
            c.execute("ALTER TABLE manager_subscriptions ADD COLUMN auto_renew INTEGER DEFAULT 0")
            conn.commit()
        
        # Update auto_renew status
        c.execute('''UPDATE manager_subscriptions 
                     SET auto_renew = ? 
                     WHERE user_id = ? AND status = 'active' ''', 
                  (1 if auto_renew else 0, user_id))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Auto-renew updated'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

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


@app.route('/wallet')
@login_required
def wallet_dashboard():
    return render_template('wallet.html', user=current_user)


@app.route('/api/user/wallet')
@login_required
def api_get_wallet():
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        # Ensure user has a wallet row
        c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (current_user.id,))
        conn.commit()

        # Get wallet
        c.execute('SELECT balance, currency, updated_at FROM wallets WHERE user_id = ?', (current_user.id,))
        wallet_row = c.fetchone()
        wallet_data = {
            'balance': wallet_row[0] if wallet_row else 0,
            'currency': wallet_row[1] if wallet_row else 'VND',
            'updated_at': format_display_datetime(wallet_row[2]) if wallet_row else None
        }

        # Get subscription
        c.execute('''SELECT subscription_type, amount, start_date, end_date, status, auto_renew
                     FROM manager_subscriptions WHERE user_id = ?''', (current_user.id,))
        sub_row = c.fetchone()
        subscription_data = None
        if sub_row:
            subscription_data = {
                'subscription_type': sub_row[0],
                'amount': sub_row[1],
                'start_date': format_display_datetime(sub_row[2]),
                'end_date': format_display_datetime(sub_row[3]),
                'status': sub_row[4],
                'auto_renew': sub_row[5]
            }

        # Recent transactions
        c.execute('''SELECT id, amount, type, status, created_at
                     FROM wallet_transactions
                     WHERE user_id = ?
                     ORDER BY created_at DESC
                     LIMIT 10''', (current_user.id,))
        transactions = [{
            'id': row[0], 'amount': row[1], 'type': row[2], 'status': row[3], 'created_at': format_display_datetime(row[4])
        } for row in c.fetchall()]

        plans = {key: format_plan_dict(key) for key in SUBSCRIPTION_PLANS.keys()}

        return jsonify({'success': True, 'wallet': wallet_data, 'subscription': subscription_data, 'transactions': transactions, 'plans': plans})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/session')
def api_session():
    """Return session status for the current client (used by JS to detect session expiration)."""
    if not current_user.is_authenticated:
        return jsonify({'authenticated': False})
    return jsonify({'authenticated': True, 'user': {
        'id': current_user.id,
        'email': current_user.email,
        'role': getattr(current_user, 'role', 'user')
    }})


@app.route('/api/user/wallet/topup', methods=['POST'])
@login_required
def api_topup_wallet():
    data = request.get_json() or {}
    try:
        amount = int(data.get('amount', 0))
    except (TypeError, ValueError):
        amount = 0

    if amount < 50000:
        return jsonify({'success': False, 'message': 'Minimum amount is 50,000 VND'}), 400

    method = (data.get('method') or 'bank_transfer').strip()
    reference = (data.get('reference') or '').strip()[:120]
    note = (data.get('note') or '').strip()[:200]

    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (current_user.id,))

        metadata = json.dumps({'initiated_by': 'user', 'method': method, 'reference': reference})

        c.execute('''INSERT INTO wallet_transactions
                     (user_id, amount, currency, type, status, method, reference, notes, metadata)
                     VALUES (?, ?, 'VND', ?, 'pending', ?, ?, ?, ?)''',
                  (current_user.id, amount, 'topup', method, reference or None, note or None, metadata))
        conn.commit()

        return jsonify({'success': True, 'message': 'Top-up request submitted. Admin will confirm shortly.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/admin/wallet/withdraw', methods=['POST'])
@login_required
@csrf.exempt
def api_admin_withdraw():
    """Admin withdraw money from wallet to bank account"""
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    data = request.get_json() or {}
    try:
        amount = int(data.get('amount', 0))
    except (TypeError, ValueError):
        amount = 0
    
    if amount < 100000:
        return jsonify({'success': False, 'message': 'Minimum withdrawal amount is 100,000 VND'}), 400
    
    bank_name = (data.get('bank_name') or '').strip()
    account_number = (data.get('account_number') or '').strip()
    account_name = (data.get('account_name') or '').strip()
    note = (data.get('note') or '').strip()
    
    if not bank_name or not account_number or not account_name:
        return jsonify({'success': False, 'message': 'Please provide complete bank information'}), 400
    
    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (current_user.id,))
        c.execute('SELECT balance FROM wallets WHERE user_id = ?', (current_user.id,))
        row = c.fetchone()
        balance = float(row[0]) if row else 0
        
        if amount > balance:
            return jsonify({'success': False, 'message': 'Insufficient balance'}), 400
        
        # Deduct balance
        c.execute('UPDATE wallets SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?',
                  (amount, current_user.id))
        
        # Create withdrawal transaction
        metadata = json.dumps({
            'bank_name': bank_name,
            'account_number': account_number,
            'account_name': account_name,
            'note': note
        })
        
        c.execute('''INSERT INTO wallet_transactions
                     (user_id, amount, currency, type, status, method, notes, metadata)
                     VALUES (?, ?, 'VND', 'withdrawal', 'completed', 'bank_transfer', ?, ?)''',
                  (current_user.id, -amount, f'Rút về {bank_name} - {account_number}', metadata))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Withdrawal request submitted. Funds will be transferred within 1-2 business days.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/user/subscription/upgrade', methods=['POST'])
@login_required
def api_upgrade_subscription():
    data = request.get_json() or {}
    plan_key = data.get('plan')
    if plan_key is None:
        return jsonify({'success': False, 'message': 'Invalid plan'}), 400
    plan_key = str(plan_key)
    plan = SUBSCRIPTION_PLANS.get(plan_key)
    if not plan:
        return jsonify({'success': False, 'message': 'Invalid plan'}), 400

    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (current_user.id,))
        c.execute('SELECT balance FROM wallets WHERE user_id = ?', (current_user.id,))
        wallet_row = c.fetchone()
        balance = wallet_row[0] if wallet_row else 0

        if balance < plan['amount']:
            conn.rollback()
            return jsonify({'success': False, 'message': 'Insufficient wallet balance to upgrade this plan'}), 400

        from datetime import datetime, timedelta
        now = datetime.utcnow()
        c.execute('SELECT subscription_type, amount, start_date, end_date, status, auto_renew FROM manager_subscriptions WHERE user_id = ?', (current_user.id,))
        existing = c.fetchone()
        current_end = parse_db_datetime(existing[3]) if existing else None
        new_start = current_end if current_end and current_end > now else now
        new_end = new_start + timedelta(days=plan['days'])
        start_str = new_start.strftime('%Y-%m-%d %H:%M:%S')
        end_str = new_end.strftime('%Y-%m-%d %H:%M:%S')

        auto_renew = existing[5] if existing and existing[5] is not None else 0
        if existing:
            c.execute('''UPDATE manager_subscriptions
                         SET subscription_type = ?, amount = ?, start_date = ?, end_date = ?, status = 'active', auto_renew = ?, updated_at = CURRENT_TIMESTAMP
                         WHERE user_id = ?''', (plan_key, plan['amount'], start_str, end_str, auto_renew, current_user.id))
        else:
            c.execute('''INSERT INTO manager_subscriptions (user_id, subscription_type, amount, start_date, end_date, status, auto_renew)
                         VALUES (?, ?, ?, ?, ?, 'active', ?)''', (current_user.id, plan_key, plan['amount'], start_str, end_str, auto_renew))

        c.execute('''UPDATE users SET role = CASE WHEN role = 'admin' THEN role ELSE 'manager' END, subscription_expires_at = ? WHERE id = ?''', (end_str, current_user.id))

        c.execute('''UPDATE wallets SET balance = balance - ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?''', (plan['amount'], current_user.id))

        txn_id = f"SUB-{current_user.id}-{int(datetime.utcnow().timestamp())}"
        c.execute('''INSERT INTO subscription_history (user_id, subscription_type, amount, payment_method, transaction_id, status, notes)
                     VALUES (?, ?, ?, 'wallet', ?, 'completed', ?)''', (current_user.id, plan_key, plan['amount'], txn_id, f'Upgrade to {plan["name"]}'))

        metadata = json.dumps({'plan': plan_key, 'transaction_id': txn_id})
        c.execute('''INSERT INTO wallet_transactions (user_id, amount, currency, type, status, method, reference, notes, metadata)
                     VALUES (?, ?, 'VND', 'subscription', 'completed', 'wallet', ?, ?, ?)''', (current_user.id, -plan['amount'], txn_id, f'Upgrade {plan["name"]}', metadata))

        conn.commit()

        c.execute('SELECT balance FROM wallets WHERE user_id = ?', (current_user.id,))
        new_balance = c.fetchone()[0]

        return jsonify({'success': True, 'message': 'Upgrade successful.', 'balance': new_balance, 'expires_at': format_display_datetime(end_str)})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/user/subscription/auto-renew', methods=['POST'])
@login_required
def api_user_toggle_auto_renew():
    data = request.get_json() or {}
    enabled = data.get('enabled')
    if enabled is None:
        return jsonify({'success': False, 'message': 'Invalid parameter: enabled'}), 400

    enabled_flag = 1 if bool(enabled) else 0

    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT id FROM manager_subscriptions WHERE user_id = ?', (current_user.id,))
        if not c.fetchone():
            return jsonify({'success': False, 'message': 'No subscription found to toggle auto-renew'}), 400

        c.execute('''UPDATE manager_subscriptions SET auto_renew = ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?''', (enabled_flag, current_user.id))
        conn.commit()

        return jsonify({'success': True, 'message': 'Auto-renew updated'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/admin/wallet/pending', methods=['GET'])
@login_required
def api_admin_pending_wallet_transactions():
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    conn = db_manager.get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute('''SELECT wt.id, wt.user_id, wt.amount, wt.currency, wt.type, wt.status, wt.method, wt.reference, wt.notes, wt.metadata, wt.created_at, u.name AS user_name, u.email AS user_email
                     FROM wallet_transactions wt
                     JOIN users u ON wt.user_id = u.id
                     WHERE wt.status = 'pending' ORDER BY wt.created_at ASC''')
        rows = c.fetchall()
        transactions = []
        for row in rows:
            metadata = parse_metadata(row['metadata'])
            plan_hint = metadata.get('plan') or metadata.get('target_plan')
            transactions.append({
                'id': row['id'], 'user_id': row['user_id'], 'user_name': row['user_name'], 'user_email': row['user_email'], 'amount': row['amount'], 'currency': row['currency'], 'type': row['type'], 'status': row['status'], 'method': row['method'], 'reference': row['reference'], 'notes': row['notes'], 'metadata': metadata, 'plan_label': plan_hint, 'created_at': format_display_datetime(row['created_at'])
            })
        return jsonify({'success': True, 'transactions': transactions})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()


@app.route('/api/admin/wallet/pending/<int:transaction_id>', methods=['POST'])
@login_required
def api_admin_process_wallet_transaction(transaction_id):
    if not hasattr(current_user, 'role') or current_user.role != 'admin':
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    data = request.get_json() or {}
    action = data.get('action')
    note = (data.get('note') or '').strip()
    if action not in ['approve', 'reject']:
        return jsonify({'success': False, 'message': 'Hành động không hợp lệ'}), 400

    conn = db_manager.get_connection()
    c = conn.cursor()
    try:
        c.execute('SELECT id, user_id, amount, currency, type, status, metadata FROM wallet_transactions WHERE id = ?', (transaction_id,))
        row = c.fetchone()
        if not row:
            return jsonify({'success': False, 'message': 'Không tìm thấy giao dịch'}), 404
        if row[5] != 'pending':
            return jsonify({'success': False, 'message': 'Transaction has already been processed'}), 400

        metadata = parse_metadata(row[6])
        metadata.update({'admin_id': current_user.id, 'admin_email': current_user.email, 'admin_action_at': datetime.utcnow().isoformat()})
        if note:
            metadata['admin_note'] = note

        if action == 'approve':
            c.execute("INSERT OR IGNORE INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')", (row[1],))
            if row[2] != 0:
                c.execute('UPDATE wallets SET balance = balance + ?, updated_at = CURRENT_TIMESTAMP WHERE user_id = ?', (row[2], row[1]))
            c.execute("UPDATE wallet_transactions SET status = 'completed', metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(metadata), transaction_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Transaction approved and wallet updated.'})
        else:
            c.execute("UPDATE wallet_transactions SET status = 'rejected', metadata = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(metadata), transaction_id))
            conn.commit()
            return jsonify({'success': True, 'message': 'Transaction rejected.'})
    except Exception as e:
        conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# Routes OAuth2

@app.route('/auth/login/google')
def google_login():
    # Redirect to Google signin
    redirect_uri = url_for('google_authorize', _external=True)
    print(f"DEBUG: Generated Redirect URI: {redirect_uri}")
    return google.authorize_redirect(redirect_uri)

@app.route('/auth/google/callback')
def google_authorize():
    try:
        print(f"DEBUG: Callback URL: {request.url}")
        # Receive token from Google
        token = google.authorize_access_token()
        user_info = token['userinfo']  # Include email, name, picture
        
        email = user_info['email']
        name = user_info.get('name', 'Google User')
        
        # Check user in database
        conn = db_manager.get_connection()
        c = conn.cursor()
        c.execute("SELECT id, role FROM users WHERE email = ?", (email,))
        user_row = c.fetchone()
        
        user_id = None
        role = 'user'
        token_json = json.dumps(token)
        
        if user_row:
            # User already exists -> Get ID
            user_id = user_row[0]
            role = user_row[1]
            # Update token
            c.execute("UPDATE users SET google_token = ? WHERE id = ?", (token_json, user_id))
            conn.commit()
        else:
            # User does not exist -> Automatically register new
            # Random password because Google login
            random_password = secrets.token_hex(16)
            from werkzeug.security import generate_password_hash
            hashed_pw = generate_password_hash(random_password)
            
            # Separate full name (if any)
            names = name.split(' ')
            first_name = names[0]
            last_name = ' '.join(names[1:]) if len(names) > 1 else ''
            
            c.execute('''INSERT INTO users (email, password, name, first_name, last_name, role, avatar, google_token) 
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (email, hashed_pw, name, first_name, last_name, 'user', user_info.get('picture'), token_json))
            user_id = c.lastrowid
            conn.commit()
            print(f"Created new user from Google: {email}")

        conn.close()
        
        # Login to Flask-Login
        # Need to get full information to create User object
        user_data = auth_manager.get_user_by_id(user_id)
        
        if not user_data:
            raise Exception("Could not retrieve user data from database")

        user_obj = User(
            user_data['id'], 
            user_data['email'], 
            user_data['first_name'], 
            user_data['last_name'],
            user_data.get('role', 'user'),
            user_data.get('google_token'),
            user_data.get('avatar')
        )
        
        login_user(user_obj, remember=True)
        session.permanent = True
        flash('Google login successful!', 'success')
        
        # Redirect
        if role == 'admin':
            return redirect(url_for('admin_workspace'))
        return redirect(url_for('workspace'))

    except Exception as e:
        print(f"Lỗi OAuth: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Google login failed. Please try again. ({str(e)})', 'error')
        return redirect(url_for('auth.signin'))

# Workflow API Routes
@app.route('/api/workflows', methods=['GET'])
@login_required
def get_user_workflows():
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute('SELECT id, name, data, created_at, updated_at FROM workflows WHERE user_id = ? ORDER BY updated_at DESC', (current_user.id,))
        rows = c.fetchall()
        conn.close()
        
        workflows = []
        for row in rows:
            workflows.append({
                'id': row[0],
                'name': row[1],
                'data': json.loads(row[2]) if row[2] else {},
                'created_at': row[3],
                'updated_at': row[4]
            })
        return jsonify({'success': True, 'workflows': workflows})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workflows', methods=['POST'])
@login_required
def save_workflow():
    try:
        data = request.get_json()
        name = data.get('name', 'Untitled Workflow')
        workflow_data = json.dumps(data.get('data', {}))
        workflow_id = data.get('id')

        conn = db.get_connection()
        c = conn.cursor()
        
        if workflow_id:
            # Update existing
            c.execute('UPDATE workflows SET name = ?, data = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?',
                     (name, workflow_data, workflow_id, current_user.id))
        else:
            # Create new
            c.execute('INSERT INTO workflows (user_id, name, data) VALUES (?, ?, ?)',
                     (current_user.id, name, workflow_data))
            workflow_id = c.lastrowid
            
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'id': workflow_id, 'message': 'Workflow saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/workflows/<int:workflow_id>', methods=['DELETE'])
@login_required
def delete_workflow(workflow_id):
    try:
        conn = db.get_connection()
        c = conn.cursor()
        c.execute('DELETE FROM workflows WHERE id = ? AND user_id = ?', (workflow_id, current_user.id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Workflow deleted'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    db_manager.init_database()
    # Changed to HTTP for development - no SSL certificate warnings
    app.run(host='0.0.0.0', port=5000, debug=True) 

 
"""Template-rendering and page access routes extracted from main_routes."""

import app as app_module


# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value


def get_settings_config():
    return {
        'store': {
            'title': 'Store Profile',
            'description': 'Manage store identity, address, and currency.',
            'icon': 'fa-store',
            'gradient': 'linear-gradient(135deg, #f6d365 0%, #fda085 100%)',
            'links': []
        },
        'appearance': {
            'title': 'Appearance',
            'description': 'Customize workspace theme and layout.',
            'icon': 'fa-palette',
            'gradient': 'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',
            'links': []
        },
        'system': {
            'title': 'System & Backup',
            'description': 'Database backups, storage management, and maintenance.',
            'icon': 'fa-server',
            'gradient': 'linear-gradient(135deg, #ff9a9e 0%, #fecfef 99%, #fecfef 100%)',
            'links': []
        }
    }


def register_page_routes(app):
    @app.route('/')
    def index():
        return redirect(url_for('workspace')) if current_user.is_authenticated else render_template('signin.html')

    @app.route('/admin')
    @login_required
    def admin_dashboard():
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('workspace'))

        db_type = 'PostgreSQL' if getattr(Config, 'USE_POSTGRES', False) else 'SQLite'
        return render_template('admin_dashboard.html', user=current_user, db_type=db_type)

    @app.route('/admin/workspace')
    @login_required
    def admin_workspace():
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('workspace'))
        return redirect(url_for('admin_dashboard'))

    @app.route('/dashboard')
    @login_required
    def dashboard():
        """Main dashboard - monetization features"""
        return render_template('dashboard.html', user=current_user)

    @app.route('/workspace')
    @login_required
    def workspace():
        return render_template('workspace.html', user=current_user)

    @app.route('/settings')
    @login_required
    def settings():
        """Settings page for store info and preferences"""
        config = get_settings_config()

        all_settings = {}
        try:
            with db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, value FROM system_settings")
                rows = cursor.fetchall()
                for row in rows:
                    all_settings[row[0]] = row[1]
        except Exception as e:
            print(f"Error fetching settings: {e}")

        return render_template('settings.html', user=current_user, settings_sections=config, all_settings=all_settings)

    @app.route('/manager/create-user')
    @login_required
    def create_user_account():
        """Manager/Admin page to create user accounts"""
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('workspace'))
        return render_template('create_user_account.html', user=current_user)

    @app.route('/admin/managers')
    @login_required
    def admin_managers():
        """Admin page to manage managers"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('workspace'))
        return render_template('admin_managers.html', user=current_user)

    @app.route('/admin/roles')
    @login_required
    def admin_roles():
        """Admin page to manage user roles"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('workspace'))
        return render_template('admin_roles.html', user=current_user)

    @app.route('/admin/analytics')
    @login_required
    def admin_analytics():
        """Admin page for analytics and statistics"""
        if not hasattr(current_user, 'role') or current_user.role not in ['admin', 'manager']:
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('workspace'))

        return render_template('admin_analytics.html', user=current_user, analytics_data=None)

    @app.route('/admin/subscriptions')
    @login_required
    def admin_subscriptions():
        """Admin page for managing manager subscriptions"""
        if not hasattr(current_user, 'role') or current_user.role != 'admin':
            flash('You do not have permission to access this page', 'error')
            return redirect(url_for('workspace'))
        return render_template('admin_subscriptions.html', user=current_user)

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

    @app.route('/scenarios')
    @login_required
    def scenarios():
        return render_template('scenarios.html', user=current_user)

    @app.route('/workspace/builder')
    @login_required
    def workspace_builder():
        return render_template('workspace_builder.html', user=current_user)
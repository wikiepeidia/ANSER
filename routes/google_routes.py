"""Google OAuth and Google API routes extracted from main_routes."""

import app as app_module

# Reuse initialized objects/functions from app module during migration.
for _name, _value in vars(app_module).items():
    if _name.startswith('__'):
        continue
    if _name in globals():
        continue
    globals()[_name] = _value

def register_google_routes(app):
    @app.route('/auth/connect/google')
    @login_required
    def google_connect():
        """Connect Google account to existing user"""
        session['google_connect_mode'] = True
        redirect_uri = url_for('google_authorize', _external=True)
        return google.authorize_redirect(
            redirect_uri,
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
    
    @app.route('/auth/login/google')
    def google_login():
        # Redirect to Google signin
        redirect_uri = url_for('google_authorize', _external=True)
        print(f"DEBUG: Generated Redirect URI: {redirect_uri}")
        # Request offline access so we receive refresh_token and can reuse tokens server-side
        return google.authorize_redirect(
            redirect_uri,
            access_type='offline',
            prompt='consent',
            include_granted_scopes='true'
        )
    
    @app.route('/auth/google/callback')
    def google_authorize():
        try:
            print(f"DEBUG: Callback URL: {request.url}")
            # Receive token from Google
            token = google.authorize_access_token()
            user_info = token['userinfo']  # Include email, name, picture
            email = user_info['email'] # Extract email early
    
            # Normalize token to the format expected by google.oauth2.credentials.Credentials
            normalized_token = {
                'access_token': token.get('access_token') or token.get('token'),
                'refresh_token': token.get('refresh_token'),
                'token_uri': 'https://oauth2.googleapis.com/token',
                'client_id': app.config.get('GOOGLE_CLIENT_ID'),
                'client_secret': app.config.get('GOOGLE_CLIENT_SECRET'),
                'scope': token.get('scope') or 'openid email profile',
                'expires_at': token.get('expires_at'),
                'id_token': token.get('id_token'),
                # Preserve original for debugging/forward compatibility
                'raw_token': token
            }
            
            # Check if in connect mode (connecting existing user)
            if session.pop('google_connect_mode', False):
                if not current_user.is_authenticated:
                    flash('Session expired during connection. Please login again.', 'error')
                    return redirect(url_for('auth.signin'))
                
                # Update current user's token
                conn = db_manager.get_connection()
                c = conn.cursor()
                token_json = json.dumps(normalized_token)
                # Update google_token AND google_email
                c.execute("UPDATE users SET google_token = ?, google_email = ? WHERE id = ?", (token_json, email, current_user.id))
                conn.commit()
                conn.close()
                
                flash('Google account connected successfully!', 'success')
                # Redirect to builder if that's where they came from, or workspace
                return redirect(url_for('workspace_builder'))
    
            # email = user_info['email'] # Already extracted above
            name = user_info.get('name', 'Google User')
            
            # Check user in database
            conn = db_manager.get_connection()
            c = conn.cursor()
            
            # 1. Check by primary email
            c.execute("SELECT id, role, email, google_token FROM users WHERE email = ?", (email,))
            user_row = c.fetchone()
            
            # 2. If not found, check by connected google_email
            if not user_row:
                c.execute("SELECT id, role, email, google_token FROM users WHERE google_email = ?", (email,))
                user_row = c.fetchone()
            
            user_id = None
            role = 'user'
            token_json = json.dumps(normalized_token)
            
            if user_row:
                # User already exists -> Get ID
                user_id = user_row[0]
                role = user_row[1]
                
                # Update token AND avatar - Ensure we have the latest profile pic
                avatar_url = user_info.get('picture')
                c.execute("UPDATE users SET google_token = ?, google_email = ?, avatar = ? WHERE id = ?", 
                         (token_json, email, avatar_url, user_id))
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
                
                # Insert with google_email
                c.execute('''INSERT INTO users (email, password, name, first_name, last_name, role, avatar, google_token, google_email) 
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                         (email, hashed_pw, name, first_name, last_name, 'manager', user_info.get('picture'), token_json, email))
                user_id = c.lastrowid
                
                # Create default workspace for Google user
                c.execute('''INSERT INTO workspaces (user_id, name, type, description) 
                            VALUES (?, ?, ?, ?)''',
                         (user_id, f"{first_name}'s Personal Workspace", 'personal', 
                          'Your personal productivity space'))
                
                conn.commit()
                print(f"Created new user from Google: {email}")
                
                # Send Welcome Email
                try:
                    subject = "Welcome to Workflow Automation for Retail!"
                    body = f"""Hello {first_name},
    
    Welcome to Workflow Automation for Retail! We are excited to have you on board.
    
    Your account has been successfully created via Google Login. You can now start building intelligent automation workflows for your retail business.
    
    Get started by exploring your personal workspace:
    - Manage customers
    - Track inventory
    - Automate tasks
    
    Best regards,
    The Workflow Automation Team
    """
                    # Use core.google_integration.send_email
                    google_integration.send_email(email, subject, body)
                except Exception as e:
                    print(f"Failed to send welcome email: {e}")
    
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
    
    
    @app.route('/api/google/files', methods=['GET'])
    @login_required
    def list_google_files():
        """List Google Drive files (Sheets/Docs) for the logged-in user."""
        if not current_user.google_token:
            return jsonify({'success': False, 'message': 'Google account not connected'}), 400
    
        try:
            token_info = json.loads(current_user.google_token)
        except Exception:
            return jsonify({'success': False, 'message': 'Invalid Google token'}), 400
    
        file_type = request.args.get('type', 'sheets')
        search = request.args.get('q', '').strip()
        page_token = request.args.get('pageToken') or None
        page_size = min(int(request.args.get('pageSize', 50)), 100)
    
        mime_map = {
            'sheets': ['application/vnd.google-apps.spreadsheet'],
            'docs': ['application/vnd.google-apps.document'],
            'files': None
        }
        mime_types = mime_map.get(file_type, mime_map['sheets'])
    
        resp = google_integration.list_files(
            token_info=token_info,
            mime_types=mime_types,
            query_text=search,
            page_size=page_size,
            page_token=page_token
        )
    
        if resp.get('error') == 'service_unavailable':
            return jsonify({'success': False, 'message': 'Google API unavailable on server'}), 503
        if resp.get('error'):
            return jsonify({'success': False, 'message': resp['error']}), 400
    
        return jsonify({
            'success': True,
            'files': resp.get('files', []),
            'nextPageToken': resp.get('nextPageToken')
        })

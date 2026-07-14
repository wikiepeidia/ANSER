"""Google OAuth and Google Drive API routes — google_bp Blueprint."""
import json
import secrets

from flask import Blueprint, current_app, flash, jsonify, redirect, request, session, url_for
from flask_login import current_user, login_required, login_user

from core import google_integration
from core.auth import AuthManager
from core.models import User
from core.logger import get_logger

logger = get_logger(__name__)

google_bp = Blueprint('google', __name__)


@google_bp.route('/auth/connect/google')
@login_required
def google_connect():
    session['google_connect_mode'] = True
    redirect_uri = url_for('google.google_authorize', _external=True)
    google = current_app.extensions['google']
    return google.authorize_redirect(redirect_uri, access_type='offline',
                                     prompt='consent', include_granted_scopes='true')


@google_bp.route('/auth/login/google')
def google_login():
    redirect_uri = url_for('google.google_authorize', _external=True)
    logger.info("Generated Redirect URI: %s", redirect_uri)
    google = current_app.extensions['google']
    return google.authorize_redirect(redirect_uri, access_type='offline',
                                     prompt='consent', include_granted_scopes='true')


@google_bp.route('/auth/google/callback')
def google_authorize():
    try:
        logger.info("OAuth callback URL: %s", request.url)
        google = current_app.extensions['google']
        auth_manager = current_app.extensions['auth_manager']
        token = google.authorize_access_token()
        user_info = token['userinfo']
        email = user_info['email']

        normalized_token = {
            'access_token': token.get('access_token') or token.get('token'),
            'refresh_token': token.get('refresh_token'),
            'token_uri': 'https://oauth2.googleapis.com/token',
            'client_id': current_app.config.get('GOOGLE_CLIENT_ID'),
            'client_secret': current_app.config.get('GOOGLE_CLIENT_SECRET'),
            'scope': token.get('scope') or 'openid email profile',
            'expires_at': token.get('expires_at'),
            'id_token': token.get('id_token'),
            'raw_token': token,
        }

        if session.pop('google_connect_mode', False):
            if not current_user.is_authenticated:
                flash('Session expired during connection. Please login again.', 'error')
                return redirect(url_for('auth.signin'))
            token_json = json.dumps(normalized_token)
            current_app.extensions['database'].update_google_account(current_user.id, token_json, email)
            flash('Google account connected successfully!', 'success')
            return redirect(url_for('pages.scenarios'))

        name = user_info.get('name', 'Google User')
        token_json = json.dumps(normalized_token)
        random_password = secrets.token_hex(16)
        google_user = current_app.extensions['database'].upsert_google_user(
            email=email,
            name=name,
            avatar=user_info.get('picture'),
            token_json=token_json,
            hashed_password=AuthManager.hash_password(random_password),
        )
        user_id = google_user['id']
        role = google_user['role']
        if google_user['created']:
            logger.info("Created new user from Google: %s", email)
            try:
                subject = 'Welcome to Workflow Automation for Retail!'
                body = (f"Hello {google_user['first_name']},\n\nWelcome to Workflow Automation for Retail! "
                        'Your account has been created via Google Login.\n\nBest regards,\nThe Team')
                google_integration.send_email(email, subject, body)
            except Exception as e:
                logger.warning("Failed to send welcome email to %s: %s", email, e)

        user_data = auth_manager.get_user_by_id(user_id)
        if not user_data:
            raise Exception('Could not retrieve user data from database')
        user_obj = User(
            user_data['id'], user_data['email'],
            user_data['first_name'], user_data['last_name'],
            user_data.get('role', 'user'), user_data.get('google_token'), user_data.get('avatar'),
        )
        login_user(user_obj, remember=True)
        session.permanent = True
        flash('Google login successful!', 'success')
        if role == 'admin':
            return redirect(url_for('pages.admin_workspace'))
        return redirect(url_for('pages.workspace'))

    except Exception as e:
        logger.error("OAuth error: %s", e, exc_info=True)
        flash('Google login failed. Please try again.', 'error')
        return redirect(url_for('auth.signin'))


@google_bp.route('/api/google/files', methods=['GET'])
@login_required
def list_google_files():
    if not current_user.google_token:
        return jsonify({'success': False, 'message': 'Chưa kết nối tài khoản Google'}), 400
    try:
        token_info = json.loads(current_user.google_token)
    except Exception:
        return jsonify({'success': False, 'message': 'Google token không hợp lệ'}), 400
    file_type = request.args.get('type', 'sheets')
    search = request.args.get('q', '').strip()
    page_token = request.args.get('pageToken') or None
    page_size = min(int(request.args.get('pageSize', 50)), 100)
    mime_map = {
        'sheets': ['application/vnd.google-apps.spreadsheet'],
        'docs':   ['application/vnd.google-apps.document'],
        'files':  None,
    }
    resp = google_integration.list_files(
        token_info=token_info,
        mime_types=mime_map.get(file_type, mime_map['sheets']),
        query_text=search,
        page_size=page_size,
        page_token=page_token,
    )
    if resp.get('error') == 'service_unavailable':
        return jsonify({'success': False, 'message': 'Google API không khả dụng trên máy chủ'}), 503
    if resp.get('error'):
        return jsonify({'success': False, 'message': resp['error']}), 400
    return jsonify({'success': True, 'files': resp.get('files', []),
                    'nextPageToken': resp.get('nextPageToken')})

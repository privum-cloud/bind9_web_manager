"""
Auth API - JWT Authentication endpoints
Supports both local authentication and Keycloak SSO
"""
from flask import Blueprint, request, jsonify, current_app, g
from functools import wraps
import jwt
import datetime

from models import User, audit_log

auth_api = Blueprint('auth_api', __name__, url_prefix='/api/auth')


def get_limiter():
    """Get the rate limiter instance from app module"""
    from app import limiter
    return limiter


def validate_local_token(token):
    """Validate local HS256 JWT token"""
    data = jwt.decode(
        token,
        current_app.config['SECRET_KEY'],
        algorithms=['HS256']
    )
    return User.get_by_username(data['username'])


def validate_keycloak_token(token):
    """Validate Keycloak RS256 JWT token and auto-provision user"""
    from api.keycloak_service import KeycloakService
    import sys

    payload = KeycloakService.validate_token(token)
    user_info = KeycloakService.extract_user_info(payload)

    print(f"[SSO USER] Keycloak user_info: {user_info}", file=sys.stderr)

    # Try to find existing user by Keycloak ID
    user = User.get_by_keycloak_id(user_info['keycloak_id'])
    print(f"[SSO USER] Found by keycloak_id: {user.username if user else None}", file=sys.stderr)

    if not user:
        # Try to find by email (user might exist from before SSO)
        user = User.get_by_email(user_info['email'])
        print(f"[SSO USER] Found by email: {user.username if user else None}", file=sys.stderr)

    if not user:
        # Create new user from Keycloak
        role = KeycloakService.map_groups_to_role(user_info['groups'])
        user = User.create_from_keycloak(
            keycloak_id=user_info['keycloak_id'],
            username=user_info['username'],
            email=user_info['email'],
            role=role
        )
    else:
        # Update existing user
        from models import db

        if not user.keycloak_id:
            user.keycloak_id = user_info['keycloak_id']
            user.auth_source = 'keycloak'

        # Update role based on groups (unless is_local_admin)
        if not user.is_local_admin:
            new_role = KeycloakService.map_groups_to_role(user_info['groups'])
            if user.role != new_role:
                user.role = new_role

        user.update_last_login()
        db.session.commit()

    return user


def token_required(f):
    """Decorator to require valid JWT token - supports both local and Keycloak tokens"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        # Check for token in Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            # Try to detect token type by examining header
            unverified_header = jwt.get_unverified_header(token)
            algorithm = unverified_header.get('alg', 'HS256')

            if algorithm == 'RS256' and current_app.config.get('KEYCLOAK_ENABLED'):
                # Keycloak token (RS256)
                user = validate_keycloak_token(token)
            else:
                # Local token (HS256)
                user = validate_local_token(token)

            if not user:
                return jsonify({'error': 'User not found'}), 401
            if not user.active:
                return jsonify({'error': 'Account is disabled'}), 401

            # Store user in g for audit logging
            g.current_user = user

        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError as e:
            return jsonify({'error': f'Invalid token: {str(e)}'}), 401
        except ValueError as e:
            return jsonify({'error': str(e)}), 401

        return f(user, *args, **kwargs)

    return decorated


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if not current_user.is_admin():
            return jsonify({'error': 'Admin access required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated


def operator_required(f):
    """Decorator to require admin or operator role (backup access)"""
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if current_user.role not in ['admin', 'operator']:
            return jsonify({'error': 'Operator access required'}), 403
        return f(current_user, *args, **kwargs)
    return decorated


def permission_required(permission):
    """Decorator to require specific permission"""
    def decorator(f):
        @wraps(f)
        def decorated(current_user, *args, **kwargs):
            if not current_user.has_permission(permission):
                return jsonify({'error': f'Permission "{permission}" required'}), 403
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator


@auth_api.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token

    Rate limited to 5 attempts per minute to prevent brute-force attacks.
    (Rate limit is applied via Flask-Limiter in app.py)

    When Keycloak SSO is enabled, only local admin users can use this endpoint.
    """
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username')
    password = data.get('password')
    totp_code = data.get('totp_code')  # Optional 2FA code

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    user = User.get_by_username(username)

    if not user:
        audit_log('login_failed', 'auth', username, new_value={'reason': 'user_not_found'})
        return jsonify({'error': 'Invalid credentials'}), 401

    # When Keycloak is enabled, only allow local admin login
    if current_app.config.get('KEYCLOAK_ENABLED'):
        if not user.is_local_admin:
            audit_log('login_failed', 'auth', username, new_value={'reason': 'sso_required'})
            return jsonify({
                'error': 'Local login is restricted. Please use SSO.',
                'sso_required': True
            }), 401

    if not user.check_password(password):
        audit_log('login_failed', 'auth', username, new_value={'reason': 'invalid_password'})
        return jsonify({'error': 'Invalid credentials'}), 401

    if not user.active:
        audit_log('login_failed', 'auth', username, new_value={'reason': 'account_disabled'})
        return jsonify({'error': 'Account is disabled'}), 401

    # Check 2FA if enabled
    if user.totp_enabled:
        if not totp_code:
            # Return special response indicating 2FA is required
            return jsonify({
                'error': '2FA required',
                'requires_2fa': True,
                'username': username
            }), 401

        # Verify TOTP code or backup code
        if not user.verify_totp(totp_code) and not user.verify_backup_code(totp_code):
            audit_log('login_failed', 'auth', username, new_value={'reason': 'invalid_2fa_code'})
            return jsonify({'error': 'Invalid 2FA code'}), 401

    # Update last login timestamp
    user.update_last_login()

    # Generate JWT token
    token = jwt.encode({
        'username': user.username,
        'user_id': user.id,
        'role': user.role,
        'auth_type': 'local',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')

    # Log successful login
    audit_log('login', 'auth', user.username, user=user, new_value={'method': 'local'})

    return jsonify({
        'token': token,
        'user': user.to_dict(include_email=True)
    })


@auth_api.route('/me', methods=['GET'])
@token_required
def get_current_user(current_user):
    """Get current authenticated user info"""
    return jsonify(current_user.to_dict(include_email=True))


@auth_api.route('/refresh', methods=['POST'])
@token_required
def refresh_token(current_user):
    """Refresh JWT token"""
    token = jwt.encode({
        'username': current_user.username,
        'user_id': current_user.id,
        'role': current_user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }, current_app.config['SECRET_KEY'], algorithm='HS256')

    return jsonify({'token': token})


@auth_api.route('/change-password', methods=['POST'])
@token_required
def change_password(current_user):
    """Change current user's password"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password required'}), 400

    if len(new_password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    if not current_user.check_password(current_password):
        return jsonify({'error': 'Current password is incorrect'}), 401

    current_user.set_password(new_password)
    current_user.must_change_password = False  # Clear the flag after password change
    from models import db
    db.session.commit()

    audit_log('password_change', 'user', current_user.username, user=current_user)

    return jsonify({'message': 'Password changed successfully'})


@auth_api.route('/logout', methods=['POST'])
@token_required
def logout(current_user):
    """Logout user (client should discard token)"""
    audit_log('logout', 'auth', current_user.username, user=current_user)
    return jsonify({'message': 'Logged out successfully'})


# ============================================
# 2FA/TOTP Endpoints
# ============================================

@auth_api.route('/2fa/setup', methods=['POST'])
@token_required
def setup_2fa(current_user):
    """Initialize 2FA setup - generates secret and returns QR code"""
    import qrcode
    import io
    import base64

    if current_user.totp_enabled:
        return jsonify({'error': '2FA is already enabled'}), 400

    # Generate new TOTP secret
    secret = current_user.generate_totp_secret()
    totp_uri = current_user.get_totp_uri()

    # Generate QR code as base64
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(totp_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    return jsonify({
        'secret': secret,
        'qr_code': f'data:image/png;base64,{qr_base64}',
        'uri': totp_uri
    })


@auth_api.route('/2fa/verify', methods=['POST'])
@token_required
def verify_2fa(current_user):
    """Verify TOTP code and enable 2FA"""
    data = request.get_json()

    if not data or 'code' not in data:
        return jsonify({'error': 'Verification code required'}), 400

    code = data['code']

    if not current_user.totp_secret:
        return jsonify({'error': '2FA setup not initialized'}), 400

    if current_user.totp_enabled:
        return jsonify({'error': '2FA is already enabled'}), 400

    if not current_user.verify_totp(code):
        return jsonify({'error': 'Invalid verification code'}), 401

    # Enable 2FA and generate backup codes
    current_user.enable_totp()

    audit_log('2fa_enabled', 'security', current_user.username, user=current_user)

    return jsonify({
        'message': '2FA enabled successfully',
        'backup_codes': current_user.backup_codes
    })


@auth_api.route('/2fa/disable', methods=['POST'])
@token_required
def disable_2fa(current_user):
    """Disable 2FA for current user"""
    data = request.get_json()

    if not current_user.totp_enabled:
        return jsonify({'error': '2FA is not enabled'}), 400

    # Require password confirmation
    if not data or 'password' not in data:
        return jsonify({'error': 'Password confirmation required'}), 400

    if not current_user.check_password(data['password']):
        return jsonify({'error': 'Invalid password'}), 401

    current_user.disable_totp()

    audit_log('2fa_disabled', 'security', current_user.username, user=current_user)

    return jsonify({'message': '2FA disabled successfully'})


@auth_api.route('/2fa/backup-codes', methods=['POST'])
@token_required
def regenerate_backup_codes(current_user):
    """Regenerate backup codes (requires password)"""
    data = request.get_json()

    if not current_user.totp_enabled:
        return jsonify({'error': '2FA is not enabled'}), 400

    # Require password confirmation
    if not data or 'password' not in data:
        return jsonify({'error': 'Password confirmation required'}), 400

    if not current_user.check_password(data['password']):
        return jsonify({'error': 'Invalid password'}), 401

    codes = current_user.generate_backup_codes()

    audit_log('2fa_backup_codes_regenerated', 'security', current_user.username, user=current_user)

    return jsonify({
        'message': 'Backup codes regenerated',
        'backup_codes': codes
    })


@auth_api.route('/2fa/status', methods=['GET'])
@token_required
def get_2fa_status(current_user):
    """Get 2FA status for current user"""
    return jsonify({
        'enabled': current_user.totp_enabled,
        'backup_codes_remaining': len(current_user.backup_codes) if current_user.backup_codes else 0
    })


# ============================================
# SSO/Keycloak Endpoints
# ============================================

@auth_api.route('/sso/config', methods=['GET'])
def sso_config():
    """Return SSO configuration for frontend

    This endpoint is public (no auth required) so the frontend
    can determine if SSO is available before login.
    """
    if not current_app.config.get('KEYCLOAK_ENABLED'):
        return jsonify({
            'enabled': False
        })

    return jsonify({
        'enabled': True,
        'server_url': current_app.config['KEYCLOAK_SERVER_URL'],
        'realm': current_app.config['KEYCLOAK_REALM'],
        'client_id': current_app.config['KEYCLOAK_CLIENT_ID'],
        'local_admin_enabled': current_app.config.get('LOCAL_ADMIN_ENABLED', True)
    })


@auth_api.route('/sso/callback', methods=['POST'])
def sso_callback():
    """Handle Keycloak SSO callback - exchanges code for token and returns internal session

    The frontend can send either:
    - 'code': Authorization code from Keycloak redirect (preferred)
    - 'token': Direct Keycloak access token (legacy)

    We validate the token, provision/update the user, and return our own JWT for API calls.
    """
    if not current_app.config.get('KEYCLOAK_ENABLED'):
        return jsonify({'error': 'SSO is not enabled'}), 400

    data = request.get_json()
    print(f"[SSO DEBUG] Received data: {data}")

    if not data:
        return jsonify({'error': 'Request body required'}), 400

    auth_code = data.get('token')  # Frontend sends code as 'token' field
    redirect_uri = data.get('redirect_uri', 'http://localhost:3000/login/callback')

    print(f"[SSO DEBUG] Auth code (first 20 chars): {auth_code[:20] if auth_code else 'None'}...")
    print(f"[SSO DEBUG] Redirect URI: {redirect_uri}")

    if not auth_code:
        return jsonify({'error': 'Authorization code required'}), 400

    try:
        # Authorization codes from Keycloak contain UUIDs with hyphens
        # JWT tokens are base64 encoded and don't contain hyphens in their parts
        # Simple check: if the code contains hyphens, it's an auth code
        is_auth_code = '-' in auth_code

        print(f"[SSO DEBUG] Contains hyphens: {is_auth_code}")

        if not is_auth_code:
            # Looks like a JWT token - validate directly
            print("[SSO DEBUG] Detected JWT token format")
            keycloak_token = auth_code
        else:
            # Authorization code - exchange for token
            print("[SSO DEBUG] Detected authorization code, exchanging...")
            from .keycloak_service import KeycloakService
            token_response = KeycloakService.exchange_code_for_token(auth_code, redirect_uri)
            print(f"[SSO DEBUG] Token response keys: {token_response.keys() if token_response else 'None'}")
            keycloak_token = token_response.get('access_token')

            if not keycloak_token:
                print("[SSO DEBUG] No access_token in response!")
                return jsonify({'error': 'Failed to get access token from Keycloak'}), 401

        # Validate Keycloak token and get/create user
        user = validate_keycloak_token(keycloak_token)

        if not user:
            return jsonify({'error': 'Failed to authenticate user'}), 401

        if not user.active:
            return jsonify({'error': 'Account is disabled'}), 401

        # Generate internal JWT for API calls
        internal_token = jwt.encode({
            'username': user.username,
            'user_id': user.id,
            'role': user.role,
            'auth_type': 'keycloak',
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }, current_app.config['SECRET_KEY'], algorithm='HS256')

        # Log SSO login
        audit_log('login', 'auth', user.username, user=user, new_value={'method': 'sso'})

        return jsonify({
            'token': internal_token,
            'user': user.to_dict(include_email=True)
        })

    except ValueError as e:
        print(f"[SSO DEBUG] ValueError: {str(e)}")
        audit_log('sso_login_failed', 'auth', 'unknown', new_value={'error': str(e)})
        return jsonify({'error': str(e)}), 401
    except Exception as e:
        import traceback
        print(f"[SSO DEBUG] Exception: {str(e)}")
        traceback.print_exc()
        audit_log('sso_login_failed', 'auth', 'unknown', new_value={'error': str(e)})
        return jsonify({'error': 'SSO authentication failed'}), 500

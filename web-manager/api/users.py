"""
Users API - User management endpoints
"""
from flask import Blueprint, request, jsonify
from api.auth import token_required, admin_required
from models import User, db, audit_log

users_api = Blueprint('users_api', __name__, url_prefix='/api/users')


@users_api.route('', methods=['GET'])
@token_required
@admin_required
def list_users(current_user):
    """List all users"""
    users = User.get_all()
    users_list = [user.to_dict(include_email=True) for user in users]

    return jsonify({
        'users': users_list,
        'total': len(users_list)
    })


@users_api.route('/<int:user_id>', methods=['GET'])
@token_required
@admin_required
def get_user(current_user, user_id):
    """Get user by ID"""
    user = User.get_by_id(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user.to_dict(include_email=True))


@users_api.route('', methods=['POST'])
@token_required
@admin_required
def create_user(current_user):
    """Create a new user"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['username', 'email', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    username = data['username']
    email = data['email']

    # Check for existing username
    if User.get_by_username(username):
        return jsonify({'error': 'Username already exists'}), 409

    # Check for existing email
    if User.get_by_email(email):
        return jsonify({'error': 'Email already exists'}), 409

    # Validate role
    valid_roles = ['admin', 'operator', 'viewer']
    if data['role'] not in valid_roles:
        return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400

    # Validate password length
    if len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    try:
        user = User.create(
            username=username,
            email=email,
            password=data['password'],
            role=data['role']
        )

        audit_log(
            'create',
            'user',
            username,
            new_value={'username': username, 'email': email, 'role': data['role']},
            user=current_user
        )

        return jsonify({
            'success': True,
            'message': 'User created successfully',
            'user': user.to_dict(include_email=True)
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to create user: {str(e)}'}), 500


@users_api.route('/<int:user_id>', methods=['PUT'])
@token_required
@admin_required
def update_user(current_user, user_id):
    """Update an existing user"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    user = User.get_by_id(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Store old values for audit
    old_values = user.to_dict(include_email=True)

    # Check for username conflict
    if 'username' in data and data['username'] != user.username:
        existing = User.get_by_username(data['username'])
        if existing:
            return jsonify({'error': 'Username already exists'}), 409

    # Check for email conflict
    if 'email' in data and data['email'] != user.email:
        existing = User.get_by_email(data['email'])
        if existing:
            return jsonify({'error': 'Email already exists'}), 409

    # Validate role if provided
    if 'role' in data:
        valid_roles = ['admin', 'operator', 'viewer']
        if data['role'] not in valid_roles:
            return jsonify({'error': f'Invalid role. Must be one of: {", ".join(valid_roles)}'}), 400

    # Validate password if provided
    if 'password' in data and data['password'] and len(data['password']) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    try:
        user.update(**data)

        audit_log(
            'update',
            'user',
            user.username,
            old_value=old_values,
            new_value=user.to_dict(include_email=True),
            user=current_user
        )

        return jsonify({
            'success': True,
            'message': 'User updated successfully',
            'user': user.to_dict(include_email=True)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to update user: {str(e)}'}), 500


@users_api.route('/<int:user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(current_user, user_id):
    """Delete a user permanently"""
    # Prevent self-deletion
    if current_user.id == user_id:
        return jsonify({'error': 'Cannot delete your own account'}), 400

    user = User.get_by_id(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    # Prevent deleting admin user
    if user.username == 'admin':
        return jsonify({'error': 'Cannot delete the admin user'}), 400

    username = user.username
    user_data = user.to_dict(include_email=True)

    try:
        # Hard delete - remove from database permanently
        db.session.delete(user)
        db.session.commit()

        audit_log(
            'delete',
            'user',
            username,
            old_value=user_data,
            new_value=None,
            user=current_user
        )

        return jsonify({
            'success': True,
            'message': 'User deleted permanently'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to delete user: {str(e)}'}), 500


@users_api.route('/<int:user_id>/activate', methods=['POST'])
@token_required
@admin_required
def activate_user(current_user, user_id):
    """Reactivate a deleted user"""
    user = User.get_by_id(user_id)

    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.active:
        return jsonify({'error': 'User is already active'}), 400

    try:
        user.active = True
        db.session.commit()

        audit_log(
            'activate',
            'user',
            user.username,
            old_value={'active': False},
            new_value={'active': True},
            user=current_user
        )

        return jsonify({
            'success': True,
            'message': 'User activated successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to activate user: {str(e)}'}), 500

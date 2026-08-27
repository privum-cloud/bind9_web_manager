"""
Users Routes - User management (placeholder for Phase 3)
"""
from flask import Blueprint, render_template
from flask_login import login_required

users_bp = Blueprint('users', __name__, url_prefix='/users')


@users_bp.route('/')
@login_required
def list():
    """List all users (placeholder)"""
    # TODO: Implement with PostgreSQL in Phase 3
    users = [
        {'id': 1, 'username': 'admin', 'email': 'admin@example.com', 'role': 'admin', 'active': True}
    ]
    return render_template('users/list.html', users=users)

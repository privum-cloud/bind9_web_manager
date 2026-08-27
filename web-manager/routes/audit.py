"""
Audit Routes - Audit log viewer (placeholder for Phase 3)
"""
from flask import Blueprint, render_template
from flask_login import login_required

audit_bp = Blueprint('audit', __name__, url_prefix='/audit')


@audit_bp.route('/')
@login_required
def list():
    """List audit logs (placeholder)"""
    # TODO: Implement with PostgreSQL in Phase 3
    logs = [
        {
            'id': 1,
            'timestamp': '2025-11-27 14:30:00',
            'user': 'admin',
            'action': 'CREATE',
            'target_type': 'zone',
            'target_name': 'example.com',
            'details': 'Zone created'
        }
    ]
    return render_template('audit/list.html', logs=logs)

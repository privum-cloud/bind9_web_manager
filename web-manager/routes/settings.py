"""
Settings Routes - Application settings
"""
from flask import Blueprint, render_template, current_app
from flask_login import login_required

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
@login_required
def index():
    """Settings page"""
    settings = {
        'dns_master': current_app.config.get('DNS_MASTER_HOST', 'dns-master'),
        'dns_slave': current_app.config.get('DNS_SLAVE_HOST', 'dns-slave'),
        'zones_path': current_app.config.get('ZONES_PATH', '/etc/bind/zones'),
        'backup_path': current_app.config.get('BACKUP_PATH', '/backup'),
        'version': '1.0.0'
    }

    return render_template('settings/index.html', settings=settings)

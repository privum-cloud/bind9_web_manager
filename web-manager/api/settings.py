"""
Settings API - Application settings endpoints
"""
from flask import Blueprint, request, jsonify, current_app
from api.auth import token_required, admin_required
from services.dns_service import DNSService
from models import Settings, audit_log

settings_api = Blueprint('settings_api', __name__, url_prefix='/api/settings')


@settings_api.route('', methods=['GET'])
@token_required
def get_settings(current_user):
    """Get application settings"""
    settings = {
        'system': {
            'version': '1.0.0',
            'dns_master': current_app.config.get('DNS_MASTER_HOST', 'dns-master'),
            'dns_slave': current_app.config.get('DNS_SLAVE_HOST', 'dns-slave'),
            'zones_path': current_app.config.get('ZONES_PATH', '/etc/bind/zones'),
            'backup_path': current_app.config.get('BACKUP_PATH', '/backup')
        },
        'dns': Settings.get_dns_settings(),
        'security': Settings.get_security_settings()
    }

    return jsonify(settings)


@settings_api.route('/dns', methods=['PUT'])
@token_required
@admin_required
def update_dns_settings(current_user):
    """Update DNS default settings"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate numeric fields
    numeric_fields = ['default_ttl', 'default_refresh', 'default_retry', 'default_expire', 'default_minimum']
    for field in numeric_fields:
        if field in data:
            try:
                data[field] = int(data[field])
                if data[field] < 0:
                    return jsonify({'error': f'{field} must be a positive number'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': f'{field} must be a number'}), 400

    # Get old values for audit
    old_values = Settings.get_dns_settings()

    # Save to database
    Settings.set_dns_settings(data, user_id=current_user.id)

    # Log the change
    audit_log(
        'update',
        'settings',
        'dns',
        old_value=old_values,
        new_value=Settings.get_dns_settings(),
        user=current_user
    )

    return jsonify({
        'success': True,
        'message': 'DNS settings updated'
    })


@settings_api.route('/security', methods=['PUT'])
@token_required
@admin_required
def update_security_settings(current_user):
    """Update security settings"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # Validate numeric fields
    numeric_fields = ['session_timeout', 'max_login_attempts', 'lockout_duration']
    for field in numeric_fields:
        if field in data:
            try:
                data[field] = int(data[field])
                if data[field] < 0:
                    return jsonify({'error': f'{field} must be a positive number'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': f'{field} must be a number'}), 400

    # Get old values for audit
    old_values = Settings.get_security_settings()

    # Save to database
    Settings.set_security_settings(data, user_id=current_user.id)

    # Log the change
    audit_log(
        'update',
        'settings',
        'security',
        old_value=old_values,
        new_value=Settings.get_security_settings(),
        user=current_user
    )

    return jsonify({
        'success': True,
        'message': 'Security settings updated'
    })


@settings_api.route('/reload-bind', methods=['POST'])
@token_required
@admin_required
def reload_bind(current_user):
    """Reload BIND9 configuration"""
    dns = DNSService()
    success, message = dns.reload_all()

    audit_log(
        'reload',
        'system',
        'bind',
        new_value={'success': success, 'message': message},
        user=current_user
    )

    if success:
        return jsonify({
            'success': True,
            'message': 'BIND reloaded successfully'
        })
    else:
        return jsonify({'error': message}), 500


@settings_api.route('/flush-cache', methods=['POST'])
@token_required
@admin_required
def flush_cache(current_user):
    """Flush DNS cache"""
    dns = DNSService()
    success, message = dns.flush_cache()

    audit_log(
        'flush_cache',
        'system',
        'dns',
        new_value={'success': success, 'message': message},
        user=current_user
    )

    if success:
        return jsonify({
            'success': True,
            'message': 'DNS cache flushed'
        })
    else:
        return jsonify({'error': message}), 500


@settings_api.route('/all', methods=['GET'])
@token_required
@admin_required
def get_all_settings(current_user):
    """Get all settings from database"""
    return jsonify(Settings.get_all())


@settings_api.route('/set', methods=['POST'])
@token_required
@admin_required
def set_setting(current_user):
    """Set a custom setting"""
    data = request.get_json()

    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'error': 'Key and value required'}), 400

    old_value = Settings.get(data['key'])
    Settings.set(
        data['key'],
        data['value'],
        description=data.get('description'),
        user_id=current_user.id
    )

    audit_log(
        'update' if old_value else 'create',
        'settings',
        data['key'],
        old_value={'value': old_value} if old_value else None,
        new_value={'value': data['value']},
        user=current_user
    )

    return jsonify({
        'success': True,
        'message': 'Setting saved'
    })

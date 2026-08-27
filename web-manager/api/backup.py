"""
Backup API - Backup management endpoints
"""
from flask import Blueprint, request, jsonify, current_app, send_file
from api.auth import token_required, admin_required, operator_required
import os
import tarfile
from datetime import datetime

backup_api = Blueprint('backup_api', __name__, url_prefix='/api/backup')


@backup_api.route('/settings', methods=['GET'])
@token_required
def get_settings(current_user):
    """Get backup settings"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')

    # TODO: Load from database in Phase 3
    settings = {
        'enabled': False,
        'frequency': 'daily',
        'time': '02:00',
        'retention': {
            'daily': current_app.config.get('BACKUP_RETENTION_DAILY', 7),
            'weekly': current_app.config.get('BACKUP_RETENTION_WEEKLY', 4),
            'monthly': current_app.config.get('BACKUP_RETENTION_MONTHLY', 12)
        },
        'destination': 'local',
        'path': backup_path
    }

    return jsonify(settings)


@backup_api.route('/settings', methods=['PUT'])
@token_required
@admin_required
def update_settings(current_user):
    """Update backup settings"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    # TODO: Save to database in Phase 3
    return jsonify({
        'success': True,
        'message': 'Settings updated successfully'
    })


@backup_api.route('/list', methods=['GET'])
@token_required
@operator_required
def list_backups(current_user):
    """List all available backups"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')
    backups = []

    if os.path.exists(backup_path):
        for filename in sorted(os.listdir(backup_path), reverse=True):
            if filename.endswith('.tar.gz'):
                filepath = os.path.join(backup_path, filename)
                stat = os.stat(filepath)
                backups.append({
                    'filename': filename,
                    'size': stat.st_size,
                    'size_formatted': f"{stat.st_size / 1024:.1f} KB",
                    'created': datetime.fromtimestamp(stat.st_mtime).isoformat()
                })

    return jsonify({
        'backups': backups[:50],  # Limit to last 50
        'total': len(backups)
    })


@backup_api.route('/run', methods=['POST'])
@token_required
@operator_required
def run_backup(current_user):
    """Execute backup now"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')
    zones_path = current_app.config.get('ZONES_PATH', '/etc/bind/zones')
    named_conf = current_app.config.get('NAMED_CONF_LOCAL', '/etc/bind/named.conf.local')

    # Ensure backup directory exists
    os.makedirs(backup_path, exist_ok=True)

    # Create backup filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(backup_path, f'dns-backup-{timestamp}.tar.gz')

    try:
        with tarfile.open(backup_file, 'w:gz') as tar:
            # Backup zones
            if os.path.exists(zones_path):
                tar.add(zones_path, arcname='zones')

            # Backup named.conf.local
            if os.path.exists(named_conf):
                tar.add(named_conf, arcname='named.conf.local')

        stat = os.stat(backup_file)

        return jsonify({
            'success': True,
            'message': 'Backup created successfully',
            'backup': {
                'filename': os.path.basename(backup_file),
                'size': stat.st_size,
                'size_formatted': f"{stat.st_size / 1024:.1f} KB",
                'created': datetime.now().isoformat()
            }
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_api.route('/<filename>/restore', methods=['POST'])
@token_required
@admin_required
def restore_backup(current_user, filename):
    """Restore from a backup"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')
    zones_path = current_app.config.get('ZONES_PATH', '/etc/bind/zones')

    backup_file = os.path.join(backup_path, filename)

    if not os.path.exists(backup_file):
        return jsonify({'error': 'Backup file not found'}), 404

    try:
        with tarfile.open(backup_file, 'r:gz') as tar:
            import tempfile
            import shutil

            with tempfile.TemporaryDirectory() as tmpdir:
                tar.extractall(tmpdir)

                # Copy zones back
                extracted_zones = os.path.join(tmpdir, 'zones')
                if os.path.exists(extracted_zones):
                    for f in os.listdir(extracted_zones):
                        src = os.path.join(extracted_zones, f)
                        dst = os.path.join(zones_path, f)
                        shutil.copy2(src, dst)

        # Reload BIND
        from services.dns_service import DNSService
        dns = DNSService()
        dns.reload_all()

        return jsonify({
            'success': True,
            'message': f'Backup {filename} restored successfully'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@backup_api.route('/<filename>/download', methods=['GET'])
@token_required
@operator_required
def download_backup(current_user, filename):
    """Download a backup file"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')
    backup_file = os.path.join(backup_path, filename)

    if not os.path.exists(backup_file):
        return jsonify({'error': 'Backup file not found'}), 404

    return send_file(
        backup_file,
        as_attachment=True,
        download_name=filename
    )


@backup_api.route('/<filename>', methods=['DELETE'])
@token_required
@admin_required
def delete_backup(current_user, filename):
    """Delete a backup file"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')
    backup_file = os.path.join(backup_path, filename)

    if not os.path.exists(backup_file):
        return jsonify({'error': 'Backup file not found'}), 404

    try:
        os.remove(backup_file)
        return jsonify({
            'success': True,
            'message': f'Backup {filename} deleted'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

"""
Backup Routes - Backup configuration and management
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required
import os
import tarfile
from datetime import datetime

backup_bp = Blueprint('backup', __name__, url_prefix='/backup')


@backup_bp.route('/')
@login_required
def settings():
    """Backup settings page"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')

    # Get existing backups
    backups = []
    if os.path.exists(backup_path):
        for filename in sorted(os.listdir(backup_path), reverse=True):
            if filename.endswith('.tar.gz'):
                filepath = os.path.join(backup_path, filename)
                stat = os.stat(filepath)
                backups.append({
                    'filename': filename,
                    'size': f"{stat.st_size / 1024:.1f} KB",
                    'created': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })

    # Current settings
    settings = {
        'enabled': False,  # TODO: Load from config/DB
        'frequency': 'daily',
        'time': '02:00',
        'retention_daily': current_app.config.get('BACKUP_RETENTION_DAILY', 7),
        'retention_weekly': current_app.config.get('BACKUP_RETENTION_WEEKLY', 4),
        'retention_monthly': current_app.config.get('BACKUP_RETENTION_MONTHLY', 12),
        'destination': 'local',
        'path': backup_path
    }

    return render_template('backup/settings.html', settings=settings, backups=backups[:20])


@backup_bp.route('/run', methods=['POST'])
@login_required
def run_backup():
    """Run backup now"""
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

        return jsonify({
            'success': True,
            'message': f'Backup created: {os.path.basename(backup_file)}',
            'filename': os.path.basename(backup_file)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@backup_bp.route('/<filename>/restore', methods=['POST'])
@login_required
def restore_backup(filename):
    """Restore from backup"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')
    zones_path = current_app.config.get('ZONES_PATH', '/etc/bind/zones')

    backup_file = os.path.join(backup_path, filename)

    if not os.path.exists(backup_file):
        return jsonify({
            'success': False,
            'message': 'Backup file not found'
        }), 404

    try:
        with tarfile.open(backup_file, 'r:gz') as tar:
            # Extract to temp location first
            import tempfile
            with tempfile.TemporaryDirectory() as tmpdir:
                tar.extractall(tmpdir)

                # Copy zones back
                import shutil
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
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500


@backup_bp.route('/<filename>/delete', methods=['DELETE'])
@login_required
def delete_backup(filename):
    """Delete a backup file"""
    backup_path = current_app.config.get('BACKUP_PATH', '/backup')
    backup_file = os.path.join(backup_path, filename)

    if not os.path.exists(backup_file):
        return jsonify({
            'success': False,
            'message': 'Backup file not found'
        }), 404

    try:
        os.remove(backup_file)
        return jsonify({
            'success': True,
            'message': f'Backup {filename} deleted'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

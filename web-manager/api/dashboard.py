"""
Dashboard API - Stats and overview endpoints
"""
from flask import Blueprint, jsonify, current_app
from api.auth import token_required
from services.dns_service import DNSService
from models import AuditLog, User

dashboard_api = Blueprint('dashboard_api', __name__, url_prefix='/api/dashboard')


@dashboard_api.route('/stats', methods=['GET'])
@token_required
def get_stats(current_user):
    """Get dashboard statistics"""
    dns = DNSService()
    zones = dns.list_zones()

    # Calculate total records
    total_records = 0
    for zone in zones[:20]:  # Limit for performance
        records = dns.get_zone_records(zone['name'])
        total_records += len(records)

    # Get user count from database
    user_count = len(User.get_all_active())

    # Get server count (master + registered slaves)
    status = dns.get_server_status()
    server_count = 1 + len(status.get('slaves', []))  # 1 master + slaves

    return jsonify({
        'zones': len(zones),
        'records': total_records,
        'servers': server_count,
        'users': user_count,
        'pending': 0
    })


@dashboard_api.route('/servers', methods=['GET'])
@token_required
def get_servers(current_user):
    """Get DNS server status"""
    dns = DNSService()
    status = dns.get_server_status()

    servers = [
        {
            'id': 1,
            'name': status['master']['name'],
            'ip': status['master']['ip'],
            'role': 'master',
            'status': status['master']['status']
        }
    ]

    # Add all registered slaves
    for idx, slave in enumerate(status.get('slaves', []), start=2):
        servers.append({
            'id': idx,
            'name': slave['name'],
            'ip': slave['ip'],
            'role': 'slave',
            'status': slave['status']
        })

    return jsonify({'servers': servers})


@dashboard_api.route('/activity', methods=['GET'])
@token_required
def get_activity(current_user):
    """Get recent activity from audit logs"""
    logs = AuditLog.get_recent(limit=50)

    activity = [log.to_dict() for log in logs]

    return jsonify({'activity': activity})


@dashboard_api.route('/recent-zones', methods=['GET'])
@token_required
def get_recent_zones(current_user):
    """Get recently modified zones"""
    dns = DNSService()
    zones = dns.list_zones()[:5]  # Last 5 zones

    recent = []
    for zone in zones:
        records = dns.get_zone_records(zone['name'])
        recent.append({
            'name': zone['name'],
            'type': zone.get('type', 'master'),
            'record_count': len(records),
            'serial': zone.get('serial', 'N/A'),
            'status': 'active'
        })

    return jsonify({'zones': recent})


@dashboard_api.route('/audit-stats', methods=['GET'])
@token_required
def get_audit_stats(current_user):
    """Get audit log statistics"""
    stats = AuditLog.get_stats()
    return jsonify(stats)

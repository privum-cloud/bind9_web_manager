"""
Dashboard Routes - Main dashboard view
"""
from flask import Blueprint, render_template, current_app
from flask_login import login_required

from services.dns_service import DNSService

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
@dashboard_bp.route('/dashboard')
@login_required
def index():
    """Dashboard page with stats"""
    dns = DNSService()
    zones = dns.list_zones()

    # Count total records (limit for performance)
    total_records = 0
    for zone in zones[:10]:
        records = dns.get_zone_records(zone['name'])
        total_records += len(records)

    stats = {
        'zones': len(zones),
        'records': total_records,
        'servers': 2,  # Master + Slave
        'pending': 0
    }

    # Server status
    servers = [
        {
            'name': 'dns-master',
            'ip': current_app.config.get('DNS_MASTER_HOST', 'dns-master'),
            'status': 'online' if dns.check_status() else 'offline'
        },
        {
            'name': 'dns-slave',
            'ip': current_app.config.get('DNS_SLAVE_HOST', 'dns-slave'),
            'status': 'online'
        }
    ]

    # Recent activity (placeholder - will use audit log in Phase 3)
    recent_activity = [
        {'type': 'create', 'description': 'Zona example.com criada', 'time': 'há 5 minutos'},
        {'type': 'update', 'description': 'Registro A atualizado', 'time': 'há 15 minutos'},
    ]

    # Recent zones
    recent_zones = []
    for zone in zones[:5]:
        records = dns.get_zone_records(zone['name'])
        recent_zones.append({
            'name': zone['name'],
            'type': zone.get('type', 'master'),
            'records': len(records),
            'serial': zone.get('serial', 'N/A'),
            'status': 'active'
        })

    return render_template('dashboard.html',
                           stats=stats,
                           servers=servers,
                           recent_activity=recent_activity,
                           recent_zones=recent_zones)


@dashboard_bp.route('/health')
def health():
    """Health check endpoint for Docker/K8s"""
    return {'status': 'healthy', 'service': 'dns-web-manager'}, 200

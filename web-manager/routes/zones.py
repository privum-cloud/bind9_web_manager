"""
Zones Routes - CRUD operations for DNS zones
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required

from services.dns_service import DNSService

zones_bp = Blueprint('zones', __name__, url_prefix='/zones')


@zones_bp.route('/')
@login_required
def list():
    """List all zones"""
    dns = DNSService()
    zones = dns.get_zones()

    # Get record count for each zone
    for zone_name, zone_info in zones.items():
        content = dns.get_zone_content(zone_name)
        if content:
            records = dns.parse_zone_records(content)
            zone_info['record_count'] = len(records)
        else:
            zone_info['record_count'] = 0

    return render_template('zones/list.html', zones=zones)


@zones_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new zone"""
    if request.method == 'POST':
        zone_name = request.form.get('zone_name', '').strip()
        nameserver_ip = request.form.get('nameserver_ip', '').strip()
        admin_email = request.form.get('admin_email', '').strip()

        if not zone_name or not nameserver_ip:
            flash('Zone name and nameserver IP are required', 'error')
            return redirect(url_for('zones.create'))

        dns = DNSService()
        success, message = dns.create_zone(zone_name, nameserver_ip, admin_email)

        if success:
            flash(message, 'success')
            return redirect(url_for('zones.view', zone_name=zone_name))
        else:
            flash(message, 'error')
            return redirect(url_for('zones.create'))

    return render_template('zones/create.html')


@zones_bp.route('/<zone_name>')
@login_required
def view(zone_name):
    """View zone details and records"""
    dns = DNSService()
    zones = dns.get_zones()

    if zone_name not in zones:
        flash(f'Zone {zone_name} not found', 'error')
        return redirect(url_for('zones.list'))

    zone_info = zones[zone_name]
    content = dns.get_zone_content(zone_name)
    records = dns.parse_zone_records(content) if content else []

    return render_template('zones/view.html',
                           zone_name=zone_name,
                           zone_info=zone_info,
                           records=records,
                           raw_content=content)


@zones_bp.route('/<zone_name>', methods=['DELETE'])
@login_required
def delete(zone_name):
    """Delete zone (API)"""
    dns = DNSService()
    success, message = dns.delete_zone(zone_name)

    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 500


@zones_bp.route('/<zone_name>/reload', methods=['POST'])
@login_required
def reload(zone_name):
    """Reload zone (API)"""
    dns = DNSService()
    success, message = dns.reload_zone(zone_name)

    return jsonify({
        'success': success,
        'message': message
    }), 200 if success else 500


@zones_bp.route('/<zone_name>/records', methods=['POST'])
@login_required
def add_record(zone_name):
    """Add record to zone"""
    hostname = request.form.get('hostname', '').strip()
    record_type = request.form.get('type', 'A').strip()
    value = request.form.get('value', '').strip()

    if not hostname or not value:
        return jsonify({
            'success': False,
            'message': 'Hostname and value are required'
        }), 400

    dns = DNSService()
    success, message = dns.add_record(zone_name, hostname, record_type, value)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 500
    else:
        flash(message, 'success' if success else 'error')
        return redirect(url_for('zones.view', zone_name=zone_name))


@zones_bp.route('/<zone_name>/records/delete', methods=['POST'])
@login_required
def delete_record(zone_name):
    """Delete record from zone"""
    hostname = request.form.get('hostname', '').strip()
    record_type = request.form.get('type', '').strip()
    value = request.form.get('value', '').strip()

    if not hostname or not record_type or not value:
        return jsonify({
            'success': False,
            'message': 'Hostname, type and value are required'
        }), 400

    dns = DNSService()
    success, message = dns.delete_record(zone_name, hostname, record_type, value)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': success,
            'message': message
        }), 200 if success else 500
    else:
        flash(message, 'success' if success else 'error')
        return redirect(url_for('zones.view', zone_name=zone_name))

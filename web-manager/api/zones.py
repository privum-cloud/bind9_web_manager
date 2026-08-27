"""
Zones API - DNS Zone management endpoints
"""
from flask import Blueprint, request, jsonify
from api.auth import token_required, admin_required, operator_required
from services.dns_service import DNSService
from services.slave_notifier import notify_zone_added, notify_zone_deleted
from models import audit_log

zones_api = Blueprint('zones_api', __name__, url_prefix='/api/zones')


@zones_api.route('', methods=['GET'])
@token_required
def list_zones(current_user):
    """List all DNS zones"""
    dns = DNSService()
    zones = dns.list_zones()

    # Enrich with record count
    for zone in zones:
        records = dns.get_zone_records(zone['name'])
        zone['record_count'] = len(records)

    return jsonify({
        'zones': zones,
        'total': len(zones)
    })


@zones_api.route('/<zone_name>', methods=['GET'])
@token_required
def get_zone(current_user, zone_name):
    """Get zone details with all records"""
    dns = DNSService()
    zone = dns.get_zone(zone_name)

    if not zone:
        return jsonify({'error': 'Zone not found'}), 404

    records = dns.get_zone_records(zone_name)
    zone['records'] = records

    return jsonify(zone)


@zones_api.route('', methods=['POST'])
@token_required
@operator_required
def create_zone(current_user):
    """Create a new DNS zone"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['name', 'primary_ns', 'admin_email']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    dns = DNSService()

    # Check if zone already exists
    existing = dns.get_zone(data['name'])
    if existing:
        return jsonify({'error': 'Zone already exists'}), 409

    # Create zone with defaults
    zone_data = {
        'name': data['name'],
        'type': data.get('type', 'master'),
        'primary_ns': data['primary_ns'],
        'admin_email': data['admin_email'],
        'ttl': data.get('ttl', 3600),
        'refresh': data.get('refresh', 7200),
        'retry': data.get('retry', 3600),
        'expire': data.get('expire', 1209600),
        'minimum': data.get('minimum', 3600),
    }

    success, message = dns.create_zone_from_data(zone_data)

    if success:
        # Push the new zone to every registered slave so they pick it up
        # as a secondary zone without waiting for any polling. Fire-and-forget;
        # slaves reconcile themselves at startup if a push is missed.
        try:
            zone_record = dns.get_zone(zone_data['name']) or {}
            notify_zone_added(
                zone_data['name'],
                zone_record.get('file') or f"db.{zone_data['name']}",
            )
        except Exception:
            # Notification failures must never fail the user request.
            pass
        return jsonify({
            'success': True,
            'message': 'Zone created successfully',
            'zone': zone_data
        }), 201
    else:
        return jsonify({'error': message}), 500


@zones_api.route('/<zone_name>', methods=['PUT'])
@token_required
@operator_required
def update_zone(current_user, zone_name):
    """Update zone SOA settings"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    dns = DNSService()
    zone = dns.get_zone(zone_name)

    if not zone:
        return jsonify({'error': 'Zone not found'}), 404

    success, message = dns.update_zone_soa(zone_name, data)

    if success:
        return jsonify({
            'success': True,
            'message': 'Zone updated successfully'
        })
    else:
        return jsonify({'error': message}), 500


@zones_api.route('/<zone_name>', methods=['DELETE'])
@token_required
@admin_required
def delete_zone(current_user, zone_name):
    """Delete a DNS zone"""
    dns = DNSService()
    zone = dns.get_zone(zone_name)

    if not zone:
        return jsonify({'error': 'Zone not found'}), 404

    success, message = dns.delete_zone(zone_name)

    if success:
        try:
            notify_zone_deleted(zone_name)
        except Exception:
            pass
        return jsonify({
            'success': True,
            'message': 'Zone deleted successfully'
        })
    else:
        return jsonify({'error': message}), 500


@zones_api.route('/<zone_name>/sync', methods=['POST'])
@token_required
@operator_required
def sync_zone(current_user, zone_name):
    """Reload/sync zone on DNS server"""
    dns = DNSService()
    success, message = dns.reload_zone(zone_name)

    if success:
        return jsonify({
            'success': True,
            'message': f'Zone {zone_name} synchronized'
        })
    else:
        return jsonify({'error': message}), 500


# ==================== RECORDS ====================

@zones_api.route('/<zone_name>/records', methods=['GET'])
@token_required
def list_records(current_user, zone_name):
    """List all records in a zone"""
    dns = DNSService()
    records = dns.get_zone_records(zone_name)

    return jsonify({
        'records': records,
        'total': len(records)
    })


@zones_api.route('/<zone_name>/records', methods=['POST'])
@token_required
@operator_required
def create_record(current_user, zone_name):
    """Add a new record to a zone"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    required_fields = ['name', 'type', 'value']
    for field in required_fields:
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    dns = DNSService()

    record_data = {
        'name': data['name'],
        'ttl': data.get('ttl', 3600),
        'type': data['type'].upper(),
        'value': data['value'],
        'priority': data.get('priority')
    }

    success, message = dns.add_record_from_data(zone_name, record_data)

    if success:
        audit_log(
            'create',
            'dns_record',
            f"{zone_name}/{record_data['name']}",
            new_value=record_data,
            user=current_user
        )
        return jsonify({
            'success': True,
            'message': 'Record created successfully',
            'record': record_data
        }), 201
    else:
        return jsonify({'error': message}), 500


@zones_api.route('/<zone_name>/records/<record_name>/<record_type>', methods=['PUT'])
@token_required
@operator_required
def update_record(current_user, zone_name, record_name, record_type):
    """Update an existing record"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    dns = DNSService()

    record_data = {
        'name': data.get('name', record_name),
        'ttl': data.get('ttl', 3600),
        'type': data.get('type', record_type).upper(),
        'value': data['value'],
        'priority': data.get('priority')
    }

    success, message = dns.update_record(
        zone_name,
        record_name,
        record_type,
        record_data
    )

    if success:
        audit_log(
            'update',
            'dns_record',
            f"{zone_name}/{record_name}",
            old_value={'name': record_name, 'type': record_type},
            new_value=record_data,
            user=current_user
        )
        return jsonify({
            'success': True,
            'message': 'Record updated successfully'
        })
    else:
        return jsonify({'error': message}), 500


@zones_api.route('/<zone_name>/records/<record_name>/<record_type>', methods=['DELETE'])
@token_required
@operator_required
def delete_record(current_user, zone_name, record_name, record_type):
    """Delete a record from a zone"""
    # Get value from query parameter to allow deleting specific record
    # when multiple records have same name and type
    value = request.args.get('value')

    dns = DNSService()
    success, message = dns.delete_record(zone_name, record_name, record_type, value)

    if success:
        audit_log(
            'delete',
            'dns_record',
            f"{zone_name}/{record_name}",
            old_value={'name': record_name, 'type': record_type, 'value': value},
            user=current_user
        )
        return jsonify({
            'success': True,
            'message': 'Record deleted successfully'
        })
    else:
        return jsonify({'error': message}), 500

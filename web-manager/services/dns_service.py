"""
DNS Service - BIND9 management via RNDC and shared volumes
Replaces SSH/Paramiko with direct RNDC commands and file access
"""
import os
import re
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from flask import current_app


class DNSService:
    """Service for managing BIND9 DNS server"""

    def __init__(self):
        self.zones_path = current_app.config.get('ZONES_PATH', '/etc/bind/zones')
        self.rndc_key = current_app.config.get('RNDC_KEY_PATH', '/etc/bind/rndc.key')
        self.dns_master = current_app.config.get('DNS_MASTER_HOST', 'dns-master')
        self.dns_master_ip = current_app.config.get('DNS_MASTER_IP', '172.25.0.10')
        self.dns_slave = current_app.config.get('DNS_SLAVE_HOST', 'dns-slave')
        self.dns_slave_ip = current_app.config.get('DNS_SLAVE_IP', '172.25.0.11')
        self.named_conf_local = current_app.config.get('NAMED_CONF_LOCAL', '/etc/bind/named.conf.local')

    def _run_rndc(self, *args) -> Tuple[bool, str]:
        """Execute RNDC command"""
        cmd = ['/usr/sbin/rndc', '-s', self.dns_master, '-k', self.rndc_key] + list(args)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "RNDC command timed out"
        except Exception as e:
            return False, str(e)

    def check_status(self, server: str = 'master') -> bool:
        """Check if DNS server is running"""
        if server == 'slave':
            # Check slave via DNS query or ping
            return self._check_server_reachable(self.dns_slave_ip)
        else:
            # Check master via RNDC
            success, _ = self._run_rndc('status')
            return success

    def _check_server_reachable(self, host: str, port: int = 53) -> bool:
        """Check if a DNS server is reachable"""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def get_server_status(self) -> dict:
        """Get status of DNS servers (master + registered slaves)"""
        import socket

        # Get master info
        master_status = self.check_status('master')

        # Try to get actual hostname
        try:
            master_hostname = socket.gethostname()
        except:
            master_hostname = self.dns_master

        # Get master IP (real network IP, not loopback)
        try:
            # Use UDP socket trick to get the real IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(('8.8.8.8', 80))
            master_ip = s.getsockname()[0]
            s.close()
        except:
            # Fallback: try gethostbyname but skip loopback addresses
            try:
                master_ip = socket.gethostbyname(socket.gethostname())
                if master_ip.startswith('127.'):
                    master_ip = self.dns_master_ip
            except:
                master_ip = self.dns_master_ip

        result = {
            'master': {
                'name': master_hostname,
                'ip': master_ip,
                'status': 'online' if master_status else 'offline'
            },
            'slaves': []
        }

        # Get registered slaves from database
        try:
            from models import Slave
            slaves = Slave.get_all()
            for slave in slaves:
                slave_online = self._check_server_reachable(slave.ip_address)
                result['slaves'].append({
                    'name': slave.hostname or f'slave-{slave.id}',
                    'ip': slave.ip_address,
                    'status': 'online' if slave_online else 'offline'
                })
        except Exception as e:
            current_app.logger.warning(f"Could not get slaves from DB: {e}")

        # For backwards compatibility, also include 'slave' key if there's at least one slave
        if result['slaves']:
            result['slave'] = result['slaves'][0]
        else:
            result['slave'] = {
                'name': '',
                'ip': '',
                'status': 'offline'
            }

        return result

    def reload_zone(self, zone_name: str) -> Tuple[bool, str]:
        """Reload a specific zone"""
        return self._run_rndc('reload', zone_name)

    def reload_all(self) -> Tuple[bool, str]:
        """Reload all zones"""
        return self._run_rndc('reload')

    def get_zones(self) -> Dict[str, dict]:
        """Get all zones from named.conf.local"""
        zones = {}
        try:
            if os.path.exists(self.named_conf_local):
                with open(self.named_conf_local, 'r') as f:
                    content = f.read()

                # Remove single-line comments before parsing
                content_no_comments = re.sub(r'//.*$', '', content, flags=re.MULTILINE)

                # Parse zones using regex
                zone_pattern = r'zone\s+"([^"]+)"\s*\{[^}]*?type\s+master[^}]*?file\s+"([^"]+)"'
                matches = re.findall(zone_pattern, content_no_comments, re.DOTALL | re.IGNORECASE)

                for zone_name, zone_file in matches:
                    # Get the filename from the path
                    if zone_file.startswith('/'):
                        file_path = zone_file
                        file_name = os.path.basename(zone_file)
                    else:
                        file_name = zone_file
                        file_path = os.path.join(self.zones_path, zone_file)

                    zones[zone_name] = {
                        'name': zone_name,
                        'file': file_name,
                        'path': file_path,
                        'exists': os.path.exists(file_path)
                    }
        except Exception as e:
            current_app.logger.error(f"Error reading zones: {e}")

        return zones

    def get_zone_content(self, zone_name: str) -> Optional[str]:
        """Read zone file content"""
        zones = self.get_zones()
        if zone_name not in zones:
            return None

        zone_path = zones[zone_name]['path']
        try:
            with open(zone_path, 'r') as f:
                return f.read()
        except Exception as e:
            current_app.logger.error(f"Error reading zone {zone_name}: {e}")
            return None

    def parse_zone_records(self, content: str) -> List[dict]:
        """Parse zone file content into records"""
        records = []
        for line in content.split('\n'):
            line = line.strip()
            # Skip comments, empty lines, TTL, and SOA block
            if not line or line.startswith(';') or line.startswith('$'):
                continue
            if line.startswith('@') and 'SOA' in line:
                continue

            # Parse record line: hostname IN TYPE value
            match = re.match(r'^(\S+)\s+(?:(\d+)\s+)?IN\s+(\w+)\s+(.+)$', line)
            if match:
                records.append({
                    'hostname': match.group(1),
                    'ttl': match.group(2),
                    'type': match.group(3),
                    'value': match.group(4).strip()
                })

        return records

    def validate_zone(self, zone_name: str, content: str) -> Tuple[bool, str]:
        """Validate zone content using named-checkzone"""
        # Write to temp file
        temp_file = f'/tmp/zone-check-{zone_name}.tmp'
        try:
            with open(temp_file, 'w') as f:
                f.write(content)

            result = subprocess.run(
                ['/usr/bin/named-checkzone', zone_name, temp_file],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0 and 'OK' in result.stdout:
                return True, "Zone is valid"
            return False, result.stderr or result.stdout

        except Exception as e:
            return False, str(e)
        finally:
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def increment_serial(self, serial: int) -> int:
        """Increment DNS serial (YYYYMMDDNN format)"""
        today = datetime.now().strftime('%Y%m%d')

        if str(serial).startswith(today):
            # Same day, increment sequence
            seq = int(str(serial)[-2:]) + 1
            if seq > 99:
                seq = 99  # Max 99 per day
            return int(f"{today}{seq:02d}")
        else:
            # Different day, start at 01
            return int(f"{today}01")

    def update_zone_content(self, zone_name: str, content: str) -> Tuple[bool, str]:
        """Update zone file content"""
        zones = self.get_zones()
        if zone_name not in zones:
            return False, f"Zone {zone_name} not found"

        zone_path = zones[zone_name]['path']

        # Update serial
        serial_match = re.search(r'(\d{10})\s*;\s*Serial', content)
        if serial_match:
            old_serial = int(serial_match.group(1))
            new_serial = self.increment_serial(old_serial)
            content = content.replace(
                serial_match.group(0),
                f'{new_serial} ; Serial'
            )

        # Validate before writing
        valid, msg = self.validate_zone(zone_name, content)
        if not valid:
            return False, f"Validation failed: {msg}"

        try:
            # Write zone file
            with open(zone_path, 'w') as f:
                f.write(content)

            # Set permissions
            os.chmod(zone_path, 0o644)

            # Reload zone
            success, msg = self.reload_zone(zone_name)
            if not success:
                return False, f"Zone updated but reload failed: {msg}"

            return True, "Zone updated successfully"

        except Exception as e:
            return False, str(e)

    def add_record(self, zone_name: str, hostname: str, record_type: str, value: str) -> Tuple[bool, str]:
        """Add a DNS record to zone"""
        content = self.get_zone_content(zone_name)
        if content is None:
            return False, f"Zone {zone_name} not found"

        # Create new record line
        new_record = f"{hostname:<16} IN  {record_type:<6} {value}\n"

        # Find position to insert (after last record of same type, or at end)
        lines = content.split('\n')
        insert_pos = len(lines) - 1

        for i in range(len(lines) - 1, -1, -1):
            if f'IN  {record_type}' in lines[i] or 'IN A' in lines[i]:
                insert_pos = i + 1
                break

        lines.insert(insert_pos, new_record.rstrip())
        content = '\n'.join(lines)

        return self.update_zone_content(zone_name, content)

    def delete_record(self, zone_name: str, hostname: str, record_type: str, value: str = None) -> Tuple[bool, str]:
        """Delete a DNS record from zone"""
        content = self.get_zone_content(zone_name)
        if content is None:
            return False, f"Zone {zone_name} not found"

        lines = content.split('\n')
        new_lines = []
        removed = False

        for line in lines:
            # Normalize for comparison
            normalized = ' '.join(line.split()).upper()

            # Check if this line matches the record to delete
            matches = False
            if hostname.upper() in normalized and f"IN {record_type.upper()}" in normalized:
                if value:
                    # If value provided, match exactly
                    if value.upper() in normalized:
                        matches = True
                else:
                    # No value provided, match by name and type only
                    matches = True

            if matches and not line.strip().startswith(';'):
                removed = True
                continue  # Skip this line (delete)

            new_lines.append(line)

        if not removed:
            return False, "Record not found"

        content = '\n'.join(new_lines)
        return self.update_zone_content(zone_name, content)

    def create_zone(self, zone_name: str, nameserver_ip: str, admin_email: str = None) -> Tuple[bool, str]:
        """Create a new DNS zone"""
        # Check if zone already exists
        zones = self.get_zones()
        if zone_name in zones:
            return False, f"Zone {zone_name} already exists"

        # Generate zone file content
        serial = datetime.now().strftime('%Y%m%d') + '01'
        admin = admin_email.replace('@', '.') if admin_email else f'admin.{zone_name}'

        content = f"""$TTL 86400
@   IN  SOA     ns1.{zone_name}. {admin}. (
                {serial} ; Serial
                3600       ; Refresh (1 hour)
                1800       ; Retry (30 minutes)
                604800     ; Expire (1 week)
                86400 )    ; Minimum TTL (24 hours)

; Nameservers
@               IN  NS      ns1.{zone_name}.

; Nameserver A record
ns1             IN  A       {nameserver_ip}

; Add your records below
"""

        # Validate zone content
        valid, msg = self.validate_zone(zone_name, content)
        if not valid:
            return False, f"Zone validation failed: {msg}"

        # Write zone file
        zone_file = f"db.{zone_name}"
        zone_path = os.path.join(self.zones_path, zone_file)

        try:
            with open(zone_path, 'w') as f:
                f.write(content)
            os.chmod(zone_path, 0o644)

            # Add to named.conf.local
            zone_config = f'''
zone "{zone_name}" {{
    type master;
    file "{zone_path}";
    allow-transfer {{ slaves; }};
    allow-update {{ none; }};
    notify yes;
}};
'''
            with open(self.named_conf_local, 'a') as f:
                f.write(zone_config)

            # Reload BIND
            success, msg = self.reload_all()
            if not success:
                return False, f"Zone created but reload failed: {msg}"

            return True, f"Zone {zone_name} created successfully"

        except Exception as e:
            # Cleanup on failure
            if os.path.exists(zone_path):
                os.remove(zone_path)
            return False, str(e)

    def delete_zone(self, zone_name: str) -> Tuple[bool, str]:
        """Delete a DNS zone"""
        zones = self.get_zones()
        if zone_name not in zones:
            return False, f"Zone {zone_name} not found"

        zone_path = zones[zone_name]['path']

        try:
            # Remove from named.conf.local
            with open(self.named_conf_local, 'r') as f:
                config_content = f.read()

            # Remove zone block using regex
            pattern = rf'\n*zone\s+"{re.escape(zone_name)}"\s*\{{[\s\S]*?^\}};\s*'
            new_content = re.sub(pattern, '\n', config_content, flags=re.MULTILINE)

            # Verify zone was removed
            if f'zone "{zone_name}"' in new_content:
                return False, "Failed to remove zone from configuration"

            with open(self.named_conf_local, 'w') as f:
                f.write(new_content)

            # Delete zone file
            if os.path.exists(zone_path):
                os.remove(zone_path)

            # Reload BIND
            success, msg = self.reload_all()
            if not success:
                return False, f"Zone deleted but reload failed: {msg}"

            return True, f"Zone {zone_name} deleted successfully"

        except Exception as e:
            return False, str(e)

    def flush_cache(self) -> Tuple[bool, str]:
        """Flush DNS cache"""
        return self._run_rndc('flush')

    # ==================== API COMPATIBILITY METHODS ====================

    def list_zones(self) -> List[dict]:
        """List all zones as a list (API compatible)"""
        zones_dict = self.get_zones()
        zones_list = []

        for zone_name, zone_data in zones_dict.items():
            # Get serial from zone file
            serial = None
            if zone_data.get('exists'):
                content = self.get_zone_content(zone_name)
                if content:
                    serial_match = re.search(r'(\d{10})\s*;\s*Serial', content)
                    if serial_match:
                        serial = serial_match.group(1)

            zones_list.append({
                'name': zone_name,
                'type': 'master',
                'file': zone_data.get('file'),
                'serial': serial,
                'status': 'active' if zone_data.get('exists') else 'error'
            })

        return zones_list

    def get_zone(self, zone_name: str) -> Optional[dict]:
        """Get a single zone by name"""
        zones = self.get_zones()
        if zone_name not in zones:
            return None

        zone_data = zones[zone_name]
        serial = None
        ttl = 86400
        refresh = 7200
        retry = 3600
        expire = 1209600
        minimum = 3600
        primary_ns = None
        admin_email = None

        content = self.get_zone_content(zone_name)

        if content:
            # Extract Serial
            serial_match = re.search(r'(\d{10})\s*;\s*Serial', content)
            if serial_match:
                serial = serial_match.group(1)

            # Extract TTL from $TTL directive
            ttl_match = re.search(r'\$TTL\s+(\d+)', content)
            if ttl_match:
                ttl = int(ttl_match.group(1))

            # Extract SOA record info
            # Format: @ IN SOA ns1.domain. admin.domain. ( serial refresh retry expire minimum )
            soa_match = re.search(r'@\s+IN\s+SOA\s+(\S+)\s+(\S+)\s*\(', content)
            if soa_match:
                primary_ns = soa_match.group(1).rstrip('.')
                admin_email = soa_match.group(2).rstrip('.').replace('.', '@', 1)

            # Extract SOA timing values
            refresh_match = re.search(r'(\d+)\s*;\s*Refresh', content)
            if refresh_match:
                refresh = int(refresh_match.group(1))

            retry_match = re.search(r'(\d+)\s*;\s*Retry', content)
            if retry_match:
                retry = int(retry_match.group(1))

            expire_match = re.search(r'(\d+)\s*;\s*Expire', content)
            if expire_match:
                expire = int(expire_match.group(1))

            minimum_match = re.search(r'(\d+)\s*;\s*(?:Minimum|Negative)', content)
            if minimum_match:
                minimum = int(minimum_match.group(1))

        return {
            'name': zone_name,
            'type': 'master',
            'file': zone_data.get('file'),
            'path': zone_data.get('path'),
            'serial': serial,
            'ttl': ttl,
            'refresh': refresh,
            'retry': retry,
            'expire': expire,
            'minimum': minimum,
            'primary_ns': primary_ns,
            'admin_email': admin_email,
            'status': 'active' if zone_data.get('exists') else 'error'
        }

    def get_zone_records(self, zone_name: str) -> List[dict]:
        """Get all records for a zone"""
        content = self.get_zone_content(zone_name)
        if not content:
            return []

        records = []
        record_id = 1

        for line in content.split('\n'):
            line = line.strip()
            # Skip comments, empty lines, directives
            if not line or line.startswith(';') or line.startswith('$'):
                continue

            # Skip SOA records (multiline)
            if 'SOA' in line:
                continue

            # Parse record: hostname [TTL] IN TYPE value
            # Pattern handles optional TTL
            match = re.match(r'^(\S+)\s+(?:(\d+)\s+)?(?:IN\s+)?(\w+)\s+(.+)$', line)
            if match:
                hostname = match.group(1)
                ttl = match.group(2) or '3600'
                rec_type = match.group(3)
                value = match.group(4).strip()

                # Skip NS records pointing to self
                if rec_type == 'NS' and hostname == '@':
                    continue

                records.append({
                    'id': record_id,
                    'name': hostname,
                    'ttl': int(ttl),
                    'type': rec_type,
                    'value': value
                })
                record_id += 1

        return records

    def create_zone_from_data(self, zone_data: dict) -> Tuple[bool, str]:
        """Create zone from dictionary data (API compatible)"""
        zone_name = zone_data['name']
        primary_ns = zone_data.get('primary_ns', f'ns1.{zone_name}')
        admin_email = zone_data.get('admin_email', f'admin.{zone_name}')
        ttl = zone_data.get('ttl', 86400)
        refresh = zone_data.get('refresh', 3600)
        retry = zone_data.get('retry', 1800)
        expire = zone_data.get('expire', 604800)
        minimum = zone_data.get('minimum', 86400)

        # Check if zone already exists
        zones = self.get_zones()
        if zone_name in zones:
            return False, f"Zone {zone_name} already exists"

        # Generate zone file content
        serial = datetime.now().strftime('%Y%m%d') + '01'
        admin = admin_email.replace('@', '.')

        # Ensure primary_ns ends with a dot
        if not primary_ns.endswith('.'):
            primary_ns = f'{primary_ns}.'

        # Ensure admin ends with a dot (but only one)
        if not admin.endswith('.'):
            admin = f'{admin}.'

        # Get the nameserver hostname without trailing dot
        ns_hostname = primary_ns.rstrip('.')
        if '.' in ns_hostname:
            ns_short = ns_hostname.split('.')[0]  # e.g., ns1
        else:
            ns_short = ns_hostname

        content = f"""$TTL {ttl}
@   IN  SOA     {primary_ns} {admin} (
                {serial} ; Serial
                {refresh}       ; Refresh
                {retry}       ; Retry
                {expire}     ; Expire
                {minimum} )    ; Minimum TTL

; Nameservers
@               IN  NS      {ns_short}

; Nameserver A record
{ns_short}            IN  A       {self.dns_master_ip}

; Add your records below
"""

        # Validate zone content
        valid, msg = self.validate_zone(zone_name, content)
        if not valid:
            return False, f"Zone validation failed: {msg}"

        # Write zone file
        zone_file = f"db.{zone_name}"
        zone_path = os.path.join(self.zones_path, zone_file)

        try:
            with open(zone_path, 'w') as f:
                f.write(content)
            os.chmod(zone_path, 0o644)

            # Add to named.conf.local
            zone_config = f'''
zone "{zone_name}" {{
    type master;
    file "{zone_path}";
    allow-transfer {{ slaves; }};
    allow-update {{ none; }};
    notify yes;
}};
'''
            with open(self.named_conf_local, 'a') as f:
                f.write(zone_config)

            # Reload BIND
            success, msg = self.reload_all()
            if not success:
                return False, f"Zone created but reload failed: {msg}"

            return True, f"Zone {zone_name} created successfully"

        except Exception as e:
            # Cleanup on failure
            if os.path.exists(zone_path):
                os.remove(zone_path)
            return False, str(e)

    def add_record_from_data(self, zone_name: str, record_data: dict) -> Tuple[bool, str]:
        """Add record from dictionary data (API compatible)"""
        hostname = record_data['name']
        record_type = record_data['type']
        value = record_data['value']
        ttl = record_data.get('ttl', 3600)
        priority = record_data.get('priority')

        # Handle MX priority
        if record_type == 'MX' and priority:
            value = f"{priority} {value}"

        return self.add_record(zone_name, hostname, record_type, value)

    def update_record(self, zone_name: str, old_name: str, old_type: str, new_data: dict) -> Tuple[bool, str]:
        """Update an existing record"""
        content = self.get_zone_content(zone_name)
        if content is None:
            return False, f"Zone {zone_name} not found"

        # Find and replace the record
        lines = content.split('\n')
        new_lines = []
        found = False

        new_name = new_data.get('name', old_name)
        new_type = new_data.get('type', old_type)
        new_value = new_data['value']
        new_ttl = new_data.get('ttl', 3600)
        priority = new_data.get('priority')

        if new_type == 'MX' and priority:
            new_value = f"{priority} {new_value}"

        for line in lines:
            # Skip comments and empty lines
            stripped = line.strip()
            if not stripped or stripped.startswith(';') or stripped.startswith('$'):
                new_lines.append(line)
                continue

            # Skip SOA records
            if 'SOA' in stripped:
                new_lines.append(line)
                continue

            # Parse the record line: hostname [TTL] IN TYPE value
            match = re.match(r'^(\S+)\s+(?:(\d+)\s+)?(?:IN\s+)?(\w+)\s+(.+)$', stripped)
            if match:
                rec_name = match.group(1)
                rec_type = match.group(3)

                # Check if this is the record to update (case-insensitive)
                if rec_name.upper() == old_name.upper() and rec_type.upper() == old_type.upper():
                    # Replace with new record
                    new_line = f"{new_name:<16} {new_ttl}  IN  {new_type:<6} {new_value}"
                    new_lines.append(new_line)
                    found = True
                    continue

            new_lines.append(line)

        if not found:
            return False, "Record not found"

        content = '\n'.join(new_lines)
        return self.update_zone_content(zone_name, content)

    def update_zone_soa(self, zone_name: str, soa_data: dict) -> Tuple[bool, str]:
        """Update zone SOA settings"""
        content = self.get_zone_content(zone_name)
        if content is None:
            return False, f"Zone {zone_name} not found"

        # Update SOA values
        if 'ttl' in soa_data:
            content = re.sub(r'\$TTL\s+\d+', f"$TTL {soa_data['ttl']}", content)

        if 'refresh' in soa_data:
            content = re.sub(r'(\d+)\s*;\s*Refresh', f"{soa_data['refresh']}       ; Refresh", content)

        if 'retry' in soa_data:
            content = re.sub(r'(\d+)\s*;\s*Retry', f"{soa_data['retry']}       ; Retry", content)

        if 'expire' in soa_data:
            content = re.sub(r'(\d+)\s*;\s*Expire', f"{soa_data['expire']}     ; Expire", content)

        if 'minimum' in soa_data:
            content = re.sub(r'(\d+)\s*\)\s*;\s*Minimum', f"{soa_data['minimum']} )    ; Minimum", content)

        return self.update_zone_content(zone_name, content)

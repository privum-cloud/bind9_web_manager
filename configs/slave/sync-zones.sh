#!/bin/bash
#===============================================================================
# DNS Manager - Slave Zone Sync Script
# Automatically syncs zones from master to slave
# Run via cron: */2 * * * * /usr/local/bin/dns-manager-sync-zones.sh
#===============================================================================

# Configuration (overridden by /opt/dns-manager/slave.conf set during install)
MASTER_IP="${MASTER_IP:-}"
MASTER_URL="${MASTER_URL:-http://${MASTER_IP}}"
SLAVE_TOKEN="${SLAVE_TOKEN:-}"
NAMED_CONF_LOCAL="${NAMED_CONF_LOCAL:-/etc/bind/named.conf.local}"
ZONES_DIR="${ZONES_DIR:-/var/lib/bind/zones}"
LOG_FILE="${LOG_FILE:-/var/log/dns-manager/sync.log}"

# Load config file if exists
CONFIG_FILE="/opt/dns-manager/slave.conf"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
fi

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# Check required variables
if [ -z "$MASTER_IP" ]; then
    log "ERROR: MASTER_IP not configured"
    exit 1
fi

# Get zones from master
log "Fetching zones from master ${MASTER_IP}..."

# Public endpoint for slave sync (no auth, only returns names/types/files)
MASTER_ZONES=$(curl -s --connect-timeout 10 "${MASTER_URL}/api/slaves/zones" 2>/dev/null)

if [ -z "$MASTER_ZONES" ]; then
    log "ERROR: Could not fetch zones from master"
    exit 1
fi

# Parse zone names and files from JSON response (name<TAB>file)
ZONE_LIST=$(echo "$MASTER_ZONES" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    zones = data.get('zones', [])
    for z in zones:
        if z.get('type') == 'master':
            name = z.get('name', '')
            f = z.get('file') or f'db.{name}'
            print(f'{name}\t{f}')
except:
    pass
" 2>/dev/null)
ZONE_NAMES=$(echo "$ZONE_LIST" | awk -F'\t' '{print $1}')

if [ -z "$ZONE_NAMES" ]; then
    log "No master zones found or error parsing response"
    exit 0
fi

# Get currently configured zones on slave
CURRENT_ZONES=$(grep -oP 'zone\s+"\K[^"]+' "$NAMED_CONF_LOCAL" 2>/dev/null || echo "")

# Track if changes were made
CHANGES=0

# Check each master zone
while IFS=$'\t' read -r ZONE ZONE_FILE; do
    [ -z "$ZONE" ] && continue
    # Skip if zone already configured
    if echo "$CURRENT_ZONES" | grep -q "^${ZONE}$"; then
        continue
    fi

    log "Adding new zone: ${ZONE}"

    # Add zone configuration to named.conf.local
    # NOTE: 'primaries' is the modern keyword (BIND 9.18+). 'masters' is deprecated.
    cat >> "$NAMED_CONF_LOCAL" << EOF

zone "${ZONE}" {
    type slave;
    primaries { ${MASTER_IP}; };
    file "${ZONES_DIR}/${ZONE_FILE}";
    allow-notify { ${MASTER_IP}; };
    allow-transfer { none; };
};
EOF

    CHANGES=$((CHANGES + 1))
done <<< "$ZONE_LIST"

# Check for zones that were deleted on master (optional cleanup)
for LOCAL_ZONE in $CURRENT_ZONES; do
    # Skip system zones
    case "$LOCAL_ZONE" in
        localhost|127.in-addr.arpa|0.in-addr.arpa|255.in-addr.arpa)
            continue
            ;;
    esac

    # Check if zone still exists on master
    if ! echo "$ZONE_NAMES" | grep -q "^${LOCAL_ZONE}$"; then
        log "WARNING: Zone ${LOCAL_ZONE} exists locally but not on master (manual cleanup may be needed)"
    fi
done

# Reload BIND if changes were made
if [ $CHANGES -gt 0 ]; then
    log "Reloading BIND (${CHANGES} zones added)..."

    # Validate configuration first
    if named-checkconf "$NAMED_CONF_LOCAL" 2>/dev/null; then
        rndc reload 2>/dev/null
        if [ $? -eq 0 ]; then
            log "BIND reloaded successfully"

            # Send heartbeat to master with sync status
            if [ -n "$SLAVE_TOKEN" ]; then
                curl -s -X POST "${MASTER_URL}/api/slaves/heartbeat" \
                    -H "Content-Type: application/json" \
                    -d "{\"last_sync\": true}" \
                    --connect-timeout 5 2>/dev/null
            fi
        else
            log "ERROR: Failed to reload BIND"
        fi
    else
        log "ERROR: BIND configuration validation failed"
        # Try to recover by removing the last added zones
        log "Attempting to recover..."
    fi
else
    log "No new zones to sync"
fi

# Cleanup old log entries (keep last 1000 lines)
if [ -f "$LOG_FILE" ]; then
    tail -n 1000 "$LOG_FILE" > "${LOG_FILE}.tmp" && mv "${LOG_FILE}.tmp" "$LOG_FILE"
fi

exit 0

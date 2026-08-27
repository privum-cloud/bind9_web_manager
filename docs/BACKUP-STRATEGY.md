# Backup Strategy - DNS Web Manager

> **Updated:** 2025-12

## Overview

Native backup system using shell scripts and cron for automation.

## What is Backed Up

| Component | Location | Importance |
|-----------|----------|------------|
| Zone Files | `/var/lib/bind/zones/` | Critical |
| BIND Configuration | `/etc/bind/` | High |
| SQLite Database | `/opt/dns-manager/data/` | Critical |
| API Configuration | `/opt/dns-manager/.env` | High |

## Backup Structure

```
/opt/dns-manager/backups/
├── daily/
│   ├── backup-2025-12-20.tar.gz
│   ├── backup-2025-12-19.tar.gz
│   └── ...
├── weekly/
│   ├── backup-week-51.tar.gz
│   └── ...
└── monthly/
    ├── backup-2025-12.tar.gz
    └── ...
```

## Backup Script

**Location:** `/opt/dns-manager/backup-script.sh`

```bash
#!/bin/bash

BACKUP_DIR="/opt/dns-manager/backups"
DATE=$(date +%Y-%m-%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create directories
mkdir -p $BACKUP_DIR/{daily,weekly,monthly}

# Backup zones
tar -czf $BACKUP_DIR/daily/zones-$DATE.tar.gz /var/lib/bind/zones/

# Backup database
cp /opt/dns-manager/data/dns_manager.db $BACKUP_DIR/daily/db-$DATE.sqlite

# Backup configuration
tar -czf $BACKUP_DIR/daily/config-$DATE.tar.gz /etc/bind/ /opt/dns-manager/.env

# Clean old backups (keep 7 days)
find $BACKUP_DIR/daily -type f -mtime +7 -delete

# Weekly backup (Sunday)
if [ $(date +%u) -eq 7 ]; then
    cp $BACKUP_DIR/daily/zones-$DATE.tar.gz $BACKUP_DIR/weekly/
fi

# Monthly backup (day 1)
if [ $(date +%d) -eq 01 ]; then
    cp $BACKUP_DIR/daily/zones-$DATE.tar.gz $BACKUP_DIR/monthly/
fi
```

## Scheduling (Cron)

```cron
# Daily backup at 2:00 AM
0 2 * * * /opt/dns-manager/backup-script.sh

# Integrity check at 3:00 AM
0 3 * * * /opt/dns-manager/verify-backup.sh
```

## Backup via Web Interface

The API also allows manual backup:

**Endpoint:** `POST /api/backup/run`

**Features:**
- Create backup on demand
- List existing backups
- Download backup
- Restore backup

## Restore

### Via Script

```bash
# Restore zones
tar -xzf /opt/dns-manager/backups/daily/zones-2025-12-20.tar.gz -C /

# Restore database
cp /opt/dns-manager/backups/daily/db-2025-12-20.sqlite /opt/dns-manager/data/dns_manager.db

# Restart services
systemctl restart named
systemctl restart dns-manager-api
```

### Via Web Interface

1. Access Settings > Backup
2. Select desired backup
3. Click "Restore"
4. Confirm action

## Retention

| Type | Retention | Frequency |
|------|-----------|-----------|
| Daily | 7 days | Every day |
| Weekly | 4 weeks | Sundays |
| Monthly | 12 months | Day 1 |

## Integrity Verification

**Script:** `/opt/dns-manager/verify-backup.sh`

```bash
#!/bin/bash

BACKUP_DIR="/opt/dns-manager/backups/daily"
LATEST=$(ls -t $BACKUP_DIR/zones-*.tar.gz | head -1)

# Check if backup exists
if [ ! -f "$LATEST" ]; then
    echo "ERROR: Backup not found"
    exit 1
fi

# Verify tar integrity
tar -tzf "$LATEST" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "ERROR: Backup corrupted"
    exit 1
fi

echo "OK: Backup verified successfully"
```

## Recommendations

1. **External backup:** Copy backups to external storage (S3, NFS, etc)
2. **Restore testing:** Test restore periodically in a staging environment
3. **Monitoring:** Configure alerts for backup failures
4. **Encryption:** Consider encrypting sensitive backups

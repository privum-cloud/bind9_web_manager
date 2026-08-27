# Operations

Day-to-day running of a PRIVUM DNS Manager install: services, logs, where things live, and how to
get out of trouble.

## Services

| Service | What it is |
|---|---|
| `dns-manager-api` | The Flask API under gunicorn, bound to `127.0.0.1:5000` |
| `named` | BIND 9 itself |
| `nginx` | Serves the web UI and reverse-proxies `/api` |

```bash
sudo systemctl status dns-manager-api named nginx
sudo systemctl restart dns-manager-api
sudo systemctl restart named
sudo systemctl restart nginx
```

On a secondary server only `named` runs, plus the zone-sync agent (`slave-agent`).

## Logs

```bash
# API
journalctl -u dns-manager-api -f
tail -f /var/log/dns-manager/error.log

# BIND 9
tail -f /var/log/named/named.log

# nginx
tail -f /var/log/nginx/access.log
```

## File locations

| Path | What's there |
|---|---|
| `/opt/dns-manager/` | Application install |
| `/opt/dns-manager/.env` | Configuration |
| `/opt/dns-manager/data/` | SQLite database |
| `/opt/dns-manager/backups/` | Backups |
| `/opt/dns-manager/admin-password.txt` | Admin password from install time |
| `/opt/dns-manager/slave-token.txt` | Secondary-server token from install time |
| `/var/www/dns-manager/` | Built web UI |
| `/var/lib/bind/zones/` | Zone files (Ubuntu/Debian) |
| `/var/named/zones/` | Zone files (RHEL/Rocky) |
| `/etc/bind/` | BIND 9 config (Ubuntu/Debian) |
| `/etc/named/` | BIND 9 config (RHEL/Rocky) |

The database is at `/opt/dns-manager/data/dns_manager.db` on a default install. **Back it up
before any manual change.**

## Secondary-server tokens

The master installer generates a 24-hour token and writes it to
`/opt/dns-manager/slave-token.txt`. To mint another one later, call the API as an admin:

```bash
curl -X POST http://<primary-ip>/api/slaves/tokens \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json"
```

Tokens are single-use and expire. List or revoke them with `GET` and
`DELETE /api/slaves/tokens/<id>`.

## Troubleshooting

### Zone changes aren't reaching the secondary

Check, in order:

1. `rndc reload` succeeded on the primary — the API reports "updated but reload failed" if not.
2. The zone's serial actually incremented (`dig @<primary> <zone> SOA`).
3. The secondary has the zone in its `named.conf.local`.
4. AXFR is permitted: the secondary's IP is in `allow-transfer` on the primary.

```bash
# Ask the secondary what it thinks the serial is
dig @<secondary-ip> <zone> SOA +short

# Force a transfer
sudo rndc retransfer <zone>
```

### Reset a user's 2FA

If someone loses access to their authenticator app:

```bash
sudo /opt/dns-manager/venv/bin/python3 -c "
import sys
sys.path.insert(0, '/opt/dns-manager')
from app import app
from models import User, db
with app.app_context():
    user = User.get_by_username('USERNAME')
    user.totp_enabled = False
    user.totp_secret = None
    user.backup_codes = None
    db.session.commit()
    print('2FA reset for user:', user.username)
"
```

### Reset the admin password

```bash
sudo /opt/dns-manager/venv/bin/python3 -c "
import sys
sys.path.insert(0, '/opt/dns-manager')
from app import app
from models import User, db
with app.app_context():
    user = User.get_by_username('admin')
    user.set_password('NEW_PASSWORD')
    db.session.commit()
    print('Password reset for admin')
"
```

### The API won't start

```bash
journalctl -u dns-manager-api -n 50 --no-pager
```

Most common causes: a missing or too-short `FLASK_SECRET_KEY` in `/opt/dns-manager/.env`, a
database file the `dns-manager` user can't write, or port 5000 already taken.

### Health check

```bash
curl -s http://127.0.0.1:5000/health
```

Returns `healthy` when the API is up and BIND responds, `degraded` otherwise. It always returns
HTTP 200 — read the body, not the status code.

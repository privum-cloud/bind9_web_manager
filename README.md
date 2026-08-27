# PRIVUM DNS Manager

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)]()

**PRIVUM DNS Manager** is a modern, **free and open-source web GUI for BIND 9** — a self-hosted web interface (web UI) for managing BIND9 DNS servers with a Master/Slave architecture. It provides a user-friendly interface for managing DNS zones and records, server replication, Keycloak SSO, role-based access control (RBAC), and a full audit trail.

> 🌐 **Product page & docs:** [privum.cloud/dns-manager](https://privum.cloud/dns-manager/)

## Features

- **Web-Based Management** - Modern React frontend with dark theme
- **Master/Slave Architecture** - Automatic zone replication between servers
- **Multi-User Support** - Role-based access control (Admin, Operator, Viewer)
- **Two-Factor Authentication** - TOTP-based 2FA support
- **SSO Integration** - Optional Keycloak/OIDC authentication
- **Full DNS Record Support** - A, AAAA, CNAME, MX, TXT, NS, SRV, PTR
- **Backup & Restore** - Automated backup with retention policies
- **Audit Logging** - Track all changes with detailed logs
- **RESTful API** - Complete API for automation

## Architecture

```
MASTER SERVER
┌────────────────────────────────────────────────────┐
│  BIND9 (:53)  │  Flask API (:5000)  │  Nginx (:80) │
│    (DNS)      │   + SQLite/PostgreSQL│   + React   │
└────────────────────────────────────────────────────┘
        │ AXFR (Zone Transfer)
        ▼
SLAVE SERVER(S)
┌────────────────────────────────────────────────────┐
│  BIND9 (:53) - Receives zone updates from Master   │
└────────────────────────────────────────────────────┘
```

## Requirements

- **Operating System**: Ubuntu 22.04/24.04 LTS or Rocky Linux 8/9
- **Python**: 3.9+
- **Node.js**: 20 LTS
- **BIND9**: 9.16+

## Quick Start

### Master Server Installation

```bash
curl -fsSL https://get.privum.cloud/dns | sudo bash -s -- --master
```

The installer will:
1. Install BIND9, Python, Node.js, and Nginx
2. Configure BIND9 as the master DNS server
3. Set up the Flask API with SQLite database
4. Build and deploy the React frontend
5. Create an admin user with a random password

After installation, access the web interface at `http://<server-ip>` and log in with the credentials shown at the end of installation.

### Slave Server Installation

```bash
curl -fsSL https://get.privum.cloud/dns | sudo bash -s -- --slave --master-ip=<IP> --token=<TOKEN>
```

Generate the token from **Settings > Slaves** in the master web interface.

## Configuration

### Environment Variables

Key configuration options in `/opt/dns-manager/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | JWT signing key (required) | - |
| `FLASK_ENV` | Environment mode | `production` |
| `CORS_ORIGINS` | Allowed CORS origins (comma-separated) | localhost |
| `KEYCLOAK_ENABLED` | Enable SSO | `false` |
| `DNS_MASTER_HOST` | Master DNS hostname | `localhost` |

### SSO Configuration (Keycloak)

PRIVUM DNS Manager supports Single Sign-On via Keycloak (or any OIDC-compatible provider).

#### Step 1: Configure Keycloak

1. **Create a Realm** (or use existing):
   - Name: `dns-manager`

2. **Create a Client**:
   - Client ID: `dns-web-manager`
   - Client Type: `public`
   - Valid Redirect URIs: `https://your-dns-manager.com/*`
   - Web Origins: `https://your-dns-manager.com`

3. **Enable Groups in Token**:
   - Go to Client Scopes → `dns-web-manager-dedicated` → Add mapper
   - Mapper type: `Group Membership`
   - Name: `groups`
   - Token Claim Name: `groups`
   - Full group path: `OFF`

4. **Create Groups** for role mapping:
   - `dns-admin` → Full administrative access
   - `dns-operator` → Manage zones and records
   - `dns-viewer` → Read-only access

5. **Assign Users** to appropriate groups

#### Step 2: Configure DNS Manager

Edit `/opt/dns-manager/.env`:

```bash
# Enable Keycloak SSO
KEYCLOAK_ENABLED=true

# Keycloak server URL (no trailing slash)
KEYCLOAK_SERVER_URL=https://keycloak.example.com

# Realm name
KEYCLOAK_REALM=dns-manager

# Client ID (must match Keycloak client)
KEYCLOAK_CLIENT_ID=dns-web-manager

# Group to role mapping (JSON format)
KEYCLOAK_GROUP_MAPPING={"dns-admin":"admin","dns-operator":"operator","dns-viewer":"viewer"}

# Keep local admin login as fallback (recommended)
LOCAL_ADMIN_ENABLED=true

# SSL verification (set to true in production)
KEYCLOAK_VERIFY_SSL=true
```

#### Step 3: Restart the service

```bash
sudo systemctl restart dns-manager-api
```

#### Authentication Flow

1. User clicks **"Login with SSO"** on the login page
2. Browser redirects to Keycloak for authentication
3. After successful login, Keycloak redirects back with authorization code
4. DNS Manager exchanges code for token and validates it
5. User is automatically created/updated based on Keycloak profile
6. Role is assigned based on group membership

#### Roles and Permissions

| Role | Permissions |
|------|-------------|
| `admin` | Full access: users, zones, settings, backups |
| `operator` | Manage zones and records, view settings |
| `viewer` | Read-only access to zones and records |

## Development

### Backend (Flask API)

```bash
cd web-manager
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

### Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

## API Documentation

The API is available at `/api` with the following endpoints:

| Endpoint | Description |
|----------|-------------|
| `POST /api/auth/login` | User authentication |
| `GET /api/zones` | List all zones |
| `POST /api/zones` | Create a new zone |
| `GET /api/zones/<id>/records` | Get zone records |
| `POST /api/zones/<id>/records` | Add DNS record |
| `GET /api/dashboard/stats` | Dashboard statistics |
| `GET /api/backup/list` | List backups |

## Service Management

```bash
# API Service
sudo systemctl status dns-manager-api
sudo systemctl restart dns-manager-api

# BIND9 DNS
sudo systemctl status named
sudo systemctl restart named

# Nginx Web Server
sudo systemctl status nginx
sudo systemctl restart nginx
```

## Logs

```bash
# API logs
journalctl -u dns-manager-api -f

# BIND9 logs
tail -f /var/log/named/named.log

# Nginx logs
tail -f /var/log/nginx/access.log
```

## File Locations

| Path | Description |
|------|-------------|
| `/opt/dns-manager/` | Application installation |
| `/opt/dns-manager/data/` | SQLite database |
| `/var/lib/bind/zones/` | Zone files (Ubuntu/Debian) |
| `/var/named/zones/` | Zone files (RHEL/Rocky) |
| `/etc/bind/` | BIND9 config (Ubuntu/Debian) |
| `/etc/named/` | BIND9 config (RHEL/Rocky) |

## Security Considerations

- Change the default admin password immediately after installation
- Use HTTPS in production (configure SSL in Nginx)
- Configure firewall rules to restrict DNS access
- Enable 2FA for all admin accounts
- Regularly backup your zones and database
- See [SECURITY.md](SECURITY.md) for detailed security guidelines

## Troubleshooting

### Reset User 2FA

If a user loses access to their authenticator app:

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

### Reset Admin Password

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

### Check Service Status

```bash
# Check all services
sudo systemctl status dns-manager-api named nginx

# View API logs
sudo journalctl -u dns-manager-api -f

# View BIND9 logs
sudo tail -f /var/log/named/named.log
```

### Database Location

- SQLite: `/opt/dns-manager/data/dns_manager.db`
- Backup before any manual changes!

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

Copyright (C) 2024-2026 PRIVUM

PRIVUM DNS Manager is free software: you can redistribute it and/or modify it
under the terms of the **GNU Affero General Public License** as published by the
Free Software Foundation, either version 3 of the License, or (at your option)
any later version. See the [LICENSE](LICENSE) file for the full text.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU Affero General Public License for more details.

**What AGPLv3 means in practice for this project:** because DNS Manager is a web
application, section 13 applies - if you run a *modified* version and let other
people use it over a network, you must offer those users the corresponding
source code of your modified version. Running it unmodified, or modifying it for
purely internal use with no network users other than yourself, creates no such
obligation.

> Releases up to and including v2.0.0 were published under the MIT License and
> remain available under those terms; the change to AGPLv3 applies from this
> point forward.

## Support

- **Issues**: [GitLab Issues](https://gitlab.com/privum_public/dns_manager/-/issues)
- **Documentation**: [docs/](docs/)
- **Product page**: [BIND 9 Web GUI — Privum DNS Manager](https://privum.cloud/dns-manager/)
- **Website**: [https://privum.cloud](https://privum.cloud)

---

Made with care by the PRIVUM team.

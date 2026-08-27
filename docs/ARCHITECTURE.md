# DNS Web Manager Architecture (v2.0 - Native)

> **Updated:** 2025-12

## Overview

DNS management system for BIND9 with native installation via shell scripts. No Docker, no Kubernetes - just native operating system services.

## Architecture Diagram

```
                    MASTER SERVER
    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
    │  │   BIND9     │  │  Flask API  │  │     Nginx       │ │
    │  │   (DNS)     │  │  (Gunicorn) │  │  (Reverse Proxy)│ │
    │  │   :53       │  │   :5000     │  │     :80/:443    │ │
    │  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘ │
    │         │                │                   │          │
    │         │         ┌──────┴──────┐           │          │
    │         │         │   SQLite    │           │          │
    │         │         │  (database) │           │          │
    │         │         └─────────────┘           │          │
    │         │                                    │          │
    │  ┌──────┴────────────────────────────────────┴───────┐ │
    │  │              /opt/dns-manager/                     │ │
    │  │  - Flask Backend (REST API)                       │ │
    │  │  - React Frontend (static files)                  │ │
    │  │  - SQLite database                                │ │
    │  └───────────────────────────────────────────────────┘ │
    └─────────────────────────────────────────────────────────┘
                            │
                            │ AXFR/NOTIFY (Zone Transfer)
                            │ RNDC Key Authentication
                            ▼
                    SLAVE SERVER(S)
    ┌─────────────────────────────────────────────────────────┐
    │                                                         │
    │  ┌─────────────────────────────────────────────────┐   │
    │  │                    BIND9                         │   │
    │  │              (DNS Slave Only)                    │   │
    │  │                    :53                           │   │
    │  └─────────────────────────────────────────────────┘   │
    │                                                         │
    │  - Receives zones via AXFR from Master                 │
    │  - Automatic synchronization                           │
    │  - DNS failover                                        │
    │                                                         │
    └─────────────────────────────────────────────────────────┘
```

## Components

### 1. BIND9 (DNS Server)

**Purpose:** Authoritative DNS server

**Configuration:**
- Master: Manages zones, allows AXFR to slaves
- Slave: Receives zones via zone transfer

**Files:**
```
/etc/bind/                    # Debian/Ubuntu
/etc/named/                   # RHEL/Rocky
├── named.conf
├── named.conf.options
├── named.conf.local          # Zone definitions
└── rndc.key                  # Authentication key

/var/lib/bind/zones/          # Debian/Ubuntu
/var/named/zones/             # RHEL/Rocky
└── *.zone                    # Zone files
```

### 2. Flask API (Backend)

**Purpose:** REST API for management

**Stack:**
- Python 3.9+
- Flask 3.0 + Blueprints
- SQLAlchemy 2.0 (ORM)
- SQLite (database)
- Gunicorn (WSGI server)
- JWT (authentication)

**Files:**
```
/opt/dns-manager/
├── app.py                    # Flask application
├── config.py                 # Configuration
├── requirements.txt
├── api/                      # REST Endpoints
│   ├── auth.py              # Login, JWT, 2FA
│   ├── zones.py             # Zone CRUD
│   ├── users.py             # User CRUD
│   ├── settings.py          # Settings
│   ├── backup.py            # Backup/Restore
│   └── dashboard.py         # Statistics
├── models/                   # SQLAlchemy models
│   ├── user.py
│   ├── audit.py
│   └── settings.py
├── services/
│   └── dns_service.py       # BIND9/RNDC communication
└── data/
    └── dns_manager.db       # SQLite database
```

### 3. React Frontend

**Purpose:** Modern web interface

**Stack:**
- React 18 + TypeScript
- Vite 5 (build tool)
- Tailwind CSS 3
- React Query (data fetching)
- Axios (HTTP client)

**Files:**
```
/opt/dns-manager/static/      # Build output (production)
├── index.html
└── assets/
    ├── index-*.js
    └── index-*.css
```

### 4. Nginx (Reverse Proxy)

**Purpose:** Serve frontend + proxy to API

**Configuration:**
```nginx
server {
    listen 80;

    # React Frontend (static)
    location / {
        root /opt/dns-manager/static;
        try_files $uri $uri/ /index.html;
    }

    # Flask API (proxy)
    location /api {
        proxy_pass http://127.0.0.1:5000;
    }
}
```

### 5. Systemd Services

**dns-manager-api.service:**
```ini
[Unit]
Description=DNS Manager API Server

[Service]
User=dns-manager
WorkingDirectory=/opt/dns-manager
ExecStart=/opt/dns-manager/venv/bin/gunicorn \
    --workers 4 \
    --bind 127.0.0.1:5000 \
    app:app

[Install]
WantedBy=multi-user.target
```

## Data Flow

```
┌──────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│  Browser │────►│  Nginx  │────►│  Flask  │────►│ SQLite  │
│          │◄────│  :80    │◄────│  :5000  │◄────│   DB    │
└──────────┘     └─────────┘     └────┬────┘     └─────────┘
                                      │
                                      │ RNDC
                                      ▼
                                 ┌─────────┐
                                 │  BIND9  │
                                 │   :53   │
                                 └─────────┘
```

## Security

1. **Authentication:** JWT with configurable expiration
2. **2FA:** TOTP (Google Authenticator)
3. **Rate Limiting:** 5 attempts/minute on login
4. **RBAC:** Admin, Operator, Viewer roles
5. **Audit Log:** All actions are recorded
6. **RNDC Key:** Secure communication with BIND9

## Ports

| Service | Port | Protocol | Access |
|---------|------|----------|--------|
| DNS | 53 | TCP/UDP | Public |
| HTTP | 80 | TCP | Public |
| HTTPS | 443 | TCP | Public |
| API | 5000 | TCP | Localhost only |

## Supported Operating Systems

- Ubuntu 22.04 / 24.04
- Debian 11 / 12
- RHEL 8 / 9
- Rocky Linux 8 / 9
- AlmaLinux 8 / 9

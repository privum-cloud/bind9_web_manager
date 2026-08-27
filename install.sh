#!/bin/bash
#===============================================================================
# PRIVUM DNS Manager - Unified Installation Script
#
# Usage:
#   Master: curl -fsSL https://get.privum.cloud/dns | sudo bash -s -- --master
#   Slave:  curl -fsSL https://get.privum.cloud/dns | sudo bash -s -- --slave --master-ip=<IP> --token=<TOKEN>
#
# Project: https://gitlab.com/privum_public/dns_manager
# License: MIT
# Version: 2.0.0
#===============================================================================

set -e

# Version and URLs
VERSION="2.0.0"
REPO_URL="https://gitlab.com/privum_public/dns_manager.git"
RELEASE_URL="https://gitlab.com/privum_public/dns_manager/-/archive/v${VERSION}/dns_manager-v${VERSION}.tar.gz"
RAW_URL="https://gitlab.com/privum_public/dns_manager/-/raw/main"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Installation mode
MODE=""
MASTER_IP=""
MASTER_TOKEN=""

# Configuration
INSTALL_DIR="/opt/dns-manager"
DATA_DIR="${INSTALL_DIR}/data"
LOG_DIR="/var/log/dns-manager"
WEB_DIR="/var/www/dns-manager"
SERVICE_USER="dns-manager"
TEMP_DIR="/tmp/dns-manager-install"

#===============================================================================
# Helper Functions
#===============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║     ██████╗ ██████╗ ██╗██╗   ██╗██╗   ██╗███╗   ███╗          ║"
    echo "║     ██╔══██╗██╔══██╗██║██║   ██║██║   ██║████╗ ████║          ║"
    echo "║     ██████╔╝██████╔╝██║██║   ██║██║   ██║██╔████╔██║          ║"
    echo "║     ██╔═══╝ ██╔══██╗██║╚██╗ ██╔╝██║   ██║██║╚██╔╝██║          ║"
    echo "║     ██║     ██║  ██║██║ ╚████╔╝ ╚██████╔╝██║ ╚═╝ ██║          ║"
    echo "║     ╚═╝     ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═════╝ ╚═╝     ╚═╝          ║"
    echo "║                                                               ║"
    echo "║                 DNS Manager v.2.0.0                           ║"
    echo "║                   https://privum.cloud                        ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    echo "PRIVUM DNS Manager - Installation Script v${VERSION}"
    echo ""
    echo "Usage:"
    echo "  Master server:"
    echo "    curl -fsSL https://get.privum.cloud/dns | sudo bash -s -- --master"
    echo ""
    echo "  Slave server:"
    echo "    curl -fsSL https://get.privum.cloud/dns | sudo bash -s -- --slave --master-ip=<IP> --token=<TOKEN>"
    echo ""
    echo "Options:"
    echo "  --master              Install as master server (API + Frontend + BIND9)"
    echo "  --slave               Install as slave server (BIND9 only)"
    echo "  --master-ip=<IP>      Master server IP (required for slave)"
    echo "  --token=<TOKEN>       Integration token from master (required for slave)"
    echo "  --help, -h            Show this help message"
    echo ""
    echo "Examples:"
    echo "  sudo bash install.sh --master"
    echo "  sudo bash install.sh --slave --master-ip=192.168.1.10 --token=abc123"
    echo ""
    exit 0
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

parse_arguments() {
    if [ $# -eq 0 ]; then
        show_usage
    fi

    for arg in "$@"; do
        case $arg in
            --master)
                MODE="master"
                ;;
            --slave)
                MODE="slave"
                ;;
            --master-ip=*)
                MASTER_IP="${arg#*=}"
                ;;
            --token=*)
                MASTER_TOKEN="${arg#*=}"
                ;;
            --help|-h)
                show_usage
                ;;
            *)
                log_error "Unknown argument: $arg"
                show_usage
                ;;
        esac
    done

    # Validate arguments
    if [ -z "$MODE" ]; then
        log_error "Please specify --master or --slave"
        show_usage
    fi

    if [ "$MODE" == "slave" ]; then
        if [ -z "$MASTER_IP" ]; then
            log_error "Master IP is required for slave installation (--master-ip=<IP>)"
            exit 1
        fi
        if [ -z "$MASTER_TOKEN" ]; then
            log_error "Integration token is required for slave installation (--token=<TOKEN>)"
            exit 1
        fi
    fi
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO=$ID
        DISTRO_VERSION=$VERSION_ID
        DISTRO_FAMILY=""

        case $DISTRO in
            ubuntu|debian|linuxmint)
                DISTRO_FAMILY="debian"
                PKG_MANAGER="apt-get"
                PKG_UPDATE="apt-get update"
                PKG_INSTALL="apt-get install -y"
                BIND_SERVICE="named"
                BIND_USER="bind"
                BIND_GROUP="bind"
                BIND_CONFIG_DIR="/etc/bind"
                BIND_ZONES_DIR="/var/lib/bind/zones"
                NGINX_SITES_DIR="/etc/nginx/sites-enabled"
                ;;
            centos|rhel|rocky|almalinux|fedora)
                DISTRO_FAMILY="rhel"
                PKG_MANAGER="dnf"
                PKG_UPDATE="dnf check-update || true"
                PKG_INSTALL="dnf install -y"
                BIND_SERVICE="named"
                BIND_USER="named"
                BIND_GROUP="named"
                BIND_CONFIG_DIR="/etc/named"
                BIND_ZONES_DIR="/var/named/zones"
                NGINX_SITES_DIR="/etc/nginx/conf.d"

                if [[ "$DISTRO" == "centos" && "${DISTRO_VERSION%%.*}" -le 7 ]]; then
                    PKG_MANAGER="yum"
                    PKG_UPDATE="yum check-update || true"
                    PKG_INSTALL="yum install -y"
                fi
                ;;
            *)
                log_error "Unsupported distribution: $DISTRO"
                log_error "Supported: Ubuntu, Debian, CentOS, RHEL, Rocky, AlmaLinux"
                exit 1
                ;;
        esac

        log_info "Detected: $DISTRO $DISTRO_VERSION ($DISTRO_FAMILY family)"
    else
        log_error "Cannot detect distribution"
        exit 1
    fi
}

generate_secret_key() {
    python3 -c "import secrets; print(secrets.token_hex(32))"
}

generate_admin_password() {
    python3 -c "import secrets; import string; chars = string.ascii_letters + string.digits; print(''.join(secrets.choice(chars) for _ in range(16)))"
}

#===============================================================================
# Master Installation Functions
#===============================================================================

download_source() {
    log_info "Downloading PRIVUM DNS Manager v${VERSION}..."

    mkdir -p "$TEMP_DIR"
    cd "$TEMP_DIR"

    # Try to download release tarball
    if curl -fsSL "$RELEASE_URL" -o dns-manager.tar.gz 2>/dev/null; then
        tar -xzf dns-manager.tar.gz
        mv dns-manager-*/* . 2>/dev/null || mv dns-manager-${VERSION}/* . 2>/dev/null || true
        rm -f dns-manager.tar.gz
        log_success "Downloaded release v${VERSION}"
    else
        # Fallback: clone from git
        log_info "Downloading from git repository..."
        if command -v git &> /dev/null; then
            git clone --depth 1 "$REPO_URL" .
            log_success "Cloned repository"
        else
            log_error "Could not download source. Please install git."
            exit 1
        fi
    fi
}

install_dependencies_master() {
    log_info "Installing dependencies..."

    $PKG_UPDATE

    if [ "$DISTRO_FAMILY" == "debian" ]; then
        $PKG_INSTALL \
            bind9 \
            bind9utils \
            bind9-dnsutils \
            python3 \
            python3-pip \
            python3-venv \
            nginx \
            curl \
            git \
            build-essential \
            libffi-dev \
            libssl-dev
    else
        $PKG_INSTALL epel-release || true
        $PKG_INSTALL \
            bind \
            bind-utils \
            python3 \
            python3-pip \
            python3-devel \
            nginx \
            curl \
            git \
            gcc \
            libffi-devel \
            openssl-devel
    fi

    # Install Node.js 20 LTS
    if ! command -v node &> /dev/null; then
        log_info "Installing Node.js 20..."
        if [ "$DISTRO_FAMILY" == "debian" ]; then
            curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
        else
            curl -fsSL https://rpm.nodesource.com/setup_20.x | bash -
        fi
        $PKG_INSTALL nodejs
    fi

    log_success "Dependencies installed"
}

configure_bind_master() {
    log_info "Configuring BIND9 as master..."

    mkdir -p "$BIND_ZONES_DIR"
    mkdir -p /var/log/named

    chown -R ${BIND_USER}:${BIND_GROUP} "$BIND_ZONES_DIR"
    chown -R ${BIND_USER}:${BIND_GROUP} /var/log/named

    # Generate RNDC key
    RNDC_KEY_PATH="${BIND_CONFIG_DIR}/rndc.key"
    if [ ! -f "$RNDC_KEY_PATH" ]; then
        log_info "Generating RNDC key..."
        rndc-confgen -a -k rndc-key -c "$RNDC_KEY_PATH"
        chown root:${BIND_GROUP} "$RNDC_KEY_PATH"
        chmod 640 "$RNDC_KEY_PATH"
    fi

    cp "$RNDC_KEY_PATH" /etc/rndc.key
    chown root:${BIND_GROUP} /etc/rndc.key
    chmod 640 /etc/rndc.key

    # Copy configuration files
    if [ "$DISTRO_FAMILY" == "rhel" ]; then
        sed "s|/var/cache/bind|/var/named|g" \
            "${TEMP_DIR}/configs/bind/named.conf.options.master" > "${BIND_CONFIG_DIR}/named.conf.options"
    else
        cp "${TEMP_DIR}/configs/bind/named.conf.options.master" "${BIND_CONFIG_DIR}/named.conf.options"
    fi

    NAMED_CONF_LOCAL="${BIND_CONFIG_DIR}/named.conf.local"
    sed "s|{{RNDC_KEY_PATH}}|${RNDC_KEY_PATH}|g" \
        "${TEMP_DIR}/configs/bind/named.conf.local.master.template" > "$NAMED_CONF_LOCAL"

    chown root:${BIND_GROUP} "${BIND_CONFIG_DIR}/named.conf.options"
    chmod 644 "${BIND_CONFIG_DIR}/named.conf.options"

    # For RHEL, rewrite main named.conf
    if [ "$DISTRO_FAMILY" == "rhel" ]; then
        NAMED_CONF="/etc/named.conf"
        cp "$NAMED_CONF" "${NAMED_CONF}.original" 2>/dev/null || true

        cat > "$NAMED_CONF" << 'NAMEDCONF'
// named.conf - DNS Manager Configuration
include "/etc/named/named.conf.options";
include "/etc/named/named.conf.local";
zone "." IN { type hint; file "named.ca"; };
include "/etc/named.rfc1912.zones";
include "/etc/named.root.key";
NAMEDCONF

        chown root:${BIND_GROUP} "$NAMED_CONF"
        chmod 644 "$NAMED_CONF"
    fi

    chown root:${BIND_GROUP} "$NAMED_CONF_LOCAL"
    chmod 664 "$NAMED_CONF_LOCAL"

    log_info "Validating BIND configuration..."
    named-checkconf || {
        log_error "BIND configuration validation failed"
        exit 1
    }

    systemctl enable $BIND_SERVICE
    systemctl restart $BIND_SERVICE

    sleep 2
    if systemctl is-active --quiet $BIND_SERVICE; then
        log_success "BIND9 master configured and running"
    else
        log_error "BIND9 failed to start"
        journalctl -u $BIND_SERVICE --no-pager -n 20
        exit 1
    fi
}

install_api() {
    log_info "Installing DNS Manager API..."

    if ! id "$SERVICE_USER" &>/dev/null; then
        useradd -r -s /bin/false -d "$INSTALL_DIR" "$SERVICE_USER"
    fi

    mkdir -p "$INSTALL_DIR"
    mkdir -p "$DATA_DIR"
    mkdir -p "$LOG_DIR"

    cp -r "${TEMP_DIR}/web-manager/"* "$INSTALL_DIR/"

    # Shared secret used for master <-> slave-agent push. Generated once on
    # master install, served to slaves via /api/slaves/config so all nodes
    # share the same token. Re-using avoids the file getting rewritten on
    # upgrade.
    if [ ! -f "${INSTALL_DIR}/slave-agent.token" ]; then
        openssl rand -hex 32 > "${INSTALL_DIR}/slave-agent.token"
        chown root:${SERVICE_USER} "${INSTALL_DIR}/slave-agent.token"
        chmod 640 "${INSTALL_DIR}/slave-agent.token"
        log_success "Generated slave-agent shared token"
    fi

    log_info "Creating Python virtual environment..."
    python3 -m venv "${INSTALL_DIR}/venv"

    log_info "Installing Python dependencies..."
    "${INSTALL_DIR}/venv/bin/pip" install --upgrade pip
    "${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/requirements.txt"

    SECRET_KEY=$(generate_secret_key)

    cat > "${INSTALL_DIR}/.env" << EOF
FLASK_ENV=production
FLASK_SECRET_KEY=${SECRET_KEY}
DNS_MASTER_HOST=localhost
ZONES_PATH=${BIND_ZONES_DIR}
RNDC_KEY_PATH=${BIND_CONFIG_DIR}/rndc.key
NAMED_CONF_LOCAL=${BIND_CONFIG_DIR}/named.conf.local
BIND_CONFIG_DIR=${BIND_CONFIG_DIR}
BACKUP_PATH=${INSTALL_DIR}/backups
EOF

    mkdir -p "${INSTALL_DIR}/backups"

    chown -R ${SERVICE_USER}:${SERVICE_USER} "$INSTALL_DIR"
    chown -R ${SERVICE_USER}:${SERVICE_USER} "$DATA_DIR"
    chown -R ${SERVICE_USER}:${SERVICE_USER} "$LOG_DIR"
    chmod 600 "${INSTALL_DIR}/.env"

    usermod -aG ${BIND_GROUP} ${SERVICE_USER}
    chmod 775 "$BIND_ZONES_DIR"
    chmod g+s "$BIND_ZONES_DIR"

    NAMED_CONF_LOCAL="${BIND_CONFIG_DIR}/named.conf.local"
    chown ${SERVICE_USER}:${BIND_GROUP} "$NAMED_CONF_LOCAL"
    chmod 664 "$NAMED_CONF_LOCAL"

    log_info "Installing systemd service..."
    sed "s|{{SECRET_KEY}}|${SECRET_KEY}|g" \
        "${TEMP_DIR}/configs/systemd/dns-manager-api.service" > /etc/systemd/system/dns-manager-api.service

    if [ "$DISTRO_FAMILY" == "rhel" ]; then
        sed -i "s|/var/lib/bind/zones|${BIND_ZONES_DIR}|g" /etc/systemd/system/dns-manager-api.service
        sed -i "s|/etc/bind|${BIND_CONFIG_DIR}|g" /etc/systemd/system/dns-manager-api.service
    fi

    systemctl daemon-reload
    systemctl enable dns-manager-api
    systemctl start dns-manager-api

    sleep 3
    if systemctl is-active --quiet dns-manager-api; then
        log_success "DNS Manager API installed and running"
    else
        log_error "DNS Manager API failed to start"
        journalctl -u dns-manager-api --no-pager -n 20
        exit 1
    fi
}

create_admin_user() {
    log_info "Creating admin user..."

    ADMIN_PASSWORD=$(generate_admin_password)

    cd "${INSTALL_DIR}"
    # Run as dns-manager user to ensure database is created with correct ownership
    sudo -u ${SERVICE_USER} "${INSTALL_DIR}/venv/bin/python" << EOF
import sys
sys.path.insert(0, '${INSTALL_DIR}')
from app import app
from models import db, User

with app.app_context():
    existing = User.query.filter_by(username='admin').first()
    if existing:
        existing.set_password('${ADMIN_PASSWORD}')
        db.session.commit()
    else:
        admin = User(
            username='admin',
            email='admin@localhost',
            role='admin',
            is_active=True
        )
        admin.set_password('${ADMIN_PASSWORD}')
        db.session.add(admin)
        db.session.commit()
EOF

    echo "${ADMIN_PASSWORD}" > "${INSTALL_DIR}/admin-password.txt"
    chmod 600 "${INSTALL_DIR}/admin-password.txt"
    chown root:root "${INSTALL_DIR}/admin-password.txt"

    log_success "Admin user created"
}

build_frontend() {
    log_info "Building frontend..."

    cd "${TEMP_DIR}/frontend"

    log_info "Installing npm dependencies..."
    npm install

    log_info "Building production bundle..."
    npm run build

    mkdir -p "$WEB_DIR"
    cp -r dist/* "$WEB_DIR/"

    chown -R root:root "$WEB_DIR"
    chmod -R 755 "$WEB_DIR"

    log_success "Frontend built and installed"
}

configure_nginx() {
    log_info "Configuring Nginx..."

    if [ "$DISTRO_FAMILY" == "debian" ]; then
        cp "${TEMP_DIR}/configs/nginx/dns-manager.conf" /etc/nginx/sites-available/dns-manager
        ln -sf /etc/nginx/sites-available/dns-manager /etc/nginx/sites-enabled/
        rm -f /etc/nginx/sites-enabled/default
    else
        cp "${TEMP_DIR}/configs/nginx/dns-manager.conf" /etc/nginx/conf.d/dns-manager.conf

        cat > /etc/nginx/nginx.conf << 'NGINXCONF'
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;
include /usr/share/nginx/modules/*.conf;
events { worker_connections 1024; }
http {
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent"';
    access_log /var/log/nginx/access.log main;
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 4096;
    include /etc/nginx/mime.types;
    default_type application/octet-stream;
    include /etc/nginx/conf.d/*.conf;
}
NGINXCONF
    fi

    if command -v getenforce &> /dev/null && [ "$(getenforce)" != "Disabled" ]; then
        log_info "Configuring SELinux..."
        chcon -R -t httpd_sys_content_t "$WEB_DIR" 2>/dev/null || true
        setsebool -P httpd_can_network_connect 1 2>/dev/null || true
    fi

    nginx -t || {
        log_error "Nginx configuration test failed"
        exit 1
    }

    systemctl enable nginx
    systemctl restart nginx

    log_success "Nginx configured"
}

configure_firewall() {
    log_info "Configuring firewall..."

    if command -v ufw &> /dev/null; then
        ufw allow 53/tcp comment "DNS TCP" 2>/dev/null || true
        ufw allow 53/udp comment "DNS UDP" 2>/dev/null || true
        ufw allow 80/tcp comment "HTTP" 2>/dev/null || true
        ufw allow 443/tcp comment "HTTPS" 2>/dev/null || true
        log_success "UFW rules added"
    elif command -v firewall-cmd &> /dev/null; then
        firewall-cmd --permanent --add-service=dns 2>/dev/null || true
        firewall-cmd --permanent --add-service=http 2>/dev/null || true
        firewall-cmd --permanent --add-service=https 2>/dev/null || true
        firewall-cmd --reload 2>/dev/null || true
        log_success "firewalld rules added"
    else
        log_warn "No firewall detected"
    fi
}

cleanup_temp() {
    log_info "Cleaning up temporary files..."
    rm -rf "$TEMP_DIR"
}

generate_slave_token() {
    # Generate a slave token via Python and save it
    log_info "Generating slave installation token..."

    cd "${INSTALL_DIR}"
    # Run as dns-manager user to ensure correct database permissions
    SLAVE_TOKEN=$(sudo -u ${SERVICE_USER} "${INSTALL_DIR}/venv/bin/python" << 'EOF'
import sys
sys.path.insert(0, '/opt/dns-manager')
from app import app
from models import db, SlaveToken
from datetime import datetime, timedelta

with app.app_context():
    # Generate token using the model's method
    slave_token = SlaveToken.generate(user_id=None, expiry_minutes=1440)  # 24 hours
    print(slave_token.token)
EOF
)

    if [ -n "$SLAVE_TOKEN" ]; then
        echo "${SLAVE_TOKEN}" > "${INSTALL_DIR}/slave-token.txt"
        chmod 600 "${INSTALL_DIR}/slave-token.txt"
        chown root:root "${INSTALL_DIR}/slave-token.txt"
        log_success "Slave token generated"
    else
        log_warn "Could not generate slave token automatically"
        SLAVE_TOKEN="<generate in web interface>"
    fi
}

print_master_summary() {
    SERVER_IP=$(hostname -I | awk '{print $1}')
    ADMIN_PASS=$(cat "${INSTALL_DIR}/admin-password.txt" 2>/dev/null || echo "See ${INSTALL_DIR}/admin-password.txt")
    SLAVE_TOKEN=$(cat "${INSTALL_DIR}/slave-token.txt" 2>/dev/null || echo "<generate in web interface>")

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}        PRIVUM DNS Manager - Installation Complete!            ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Access Information:${NC}"
    echo "  Web Interface: http://${SERVER_IP}"
    echo "  API Endpoint:  http://${SERVER_IP}/api"
    echo ""
    echo -e "${CYAN}Admin Credentials:${NC}"
    echo "  Username: admin"
    echo "  Password: ${ADMIN_PASS}"
    echo ""
    echo -e "${YELLOW}  ⚠ Delete ${INSTALL_DIR}/admin-password.txt after noting the password!${NC}"
    echo ""
    echo -e "${CYAN}══════════════════════════════════════════════════════════════=${NC}"
    echo -e "${CYAN}  SLAVE INSTALLATION COMMAND (copy & run on slave server):${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════════════=${NC}"
    echo ""
    echo -e "  ${GREEN}curl -fsSL https://get.privum.cloud/dns | sudo bash -s -- --slave \\\\${NC}"
    echo -e "  ${GREEN}    --master-ip=${SERVER_IP} \\\\${NC}"
    echo -e "  ${GREEN}    --token=${SLAVE_TOKEN}${NC}"
    echo ""
    echo -e "${YELLOW}  ⚠ Token saved to: ${INSTALL_DIR}/slave-token.txt${NC}"
    echo -e "${YELLOW}  ⚠ Generate new tokens in: Settings > Slaves${NC}"
    echo ""
    echo -e "${CYAN}Service Management:${NC}"
    echo "  systemctl {start|stop|restart|status} dns-manager-api"
    echo "  systemctl {start|stop|restart|status} ${BIND_SERVICE}"
    echo "  systemctl {start|stop|restart|status} nginx"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

#===============================================================================
# Slave Installation Functions
#===============================================================================

install_dependencies_slave() {
    log_info "Installing dependencies..."

    $PKG_UPDATE

    if [ "$DISTRO_FAMILY" == "debian" ]; then
        $PKG_INSTALL bind9 bind9utils bind9-dnsutils curl jq
    else
        $PKG_INSTALL bind bind-utils curl jq
    fi

    log_success "Dependencies installed"
}

fetch_master_config() {
    log_info "Fetching configuration from master server..."

    MASTER_URL="http://${MASTER_IP}"

    if ! curl -s --connect-timeout 5 "${MASTER_URL}/health" > /dev/null; then
        log_error "Cannot connect to master server at ${MASTER_URL}"
        exit 1
    fi

    log_info "Validating integration token..."
    CONFIG_RESPONSE=$(curl -s "${MASTER_URL}/api/slaves/config?token=${MASTER_TOKEN}")

    if echo "$CONFIG_RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
        ERROR_MSG=$(echo "$CONFIG_RESPONSE" | jq -r '.error')
        log_error "Failed to get configuration: $ERROR_MSG"
        exit 1
    fi

    RNDC_KEY_CONTENT=$(echo "$CONFIG_RESPONSE" | jq -r '.rndc_key')
    ZONES_JSON=$(echo "$CONFIG_RESPONSE" | jq -r '.zones')
    SLAVE_AGENT_TOKEN=$(echo "$CONFIG_RESPONSE" | jq -r '.slave_agent_token // empty')

    if [ -z "$RNDC_KEY_CONTENT" ] || [ "$RNDC_KEY_CONTENT" == "null" ]; then
        log_error "Failed to get RNDC key from master"
        exit 1
    fi

    if [ -z "$SLAVE_AGENT_TOKEN" ]; then
        log_warn "Master did not return slave-agent token — slave-agent will be disabled."
        log_warn "Re-run on the master: 'openssl rand -hex 32 > /opt/dns-manager/slave-agent.token' and restart the API."
    fi

    log_success "Configuration received from master"
}

configure_bind_slave() {
    log_info "Configuring BIND9 as slave..."

    mkdir -p "$BIND_ZONES_DIR"
    mkdir -p /var/log/named

    chown -R ${BIND_USER}:${BIND_GROUP} "$BIND_ZONES_DIR"
    chown -R ${BIND_USER}:${BIND_GROUP} /var/log/named

    RNDC_KEY_PATH="${BIND_CONFIG_DIR}/rndc.key"
    echo "$RNDC_KEY_CONTENT" > "$RNDC_KEY_PATH"
    chown root:${BIND_GROUP} "$RNDC_KEY_PATH"
    chmod 640 "$RNDC_KEY_PATH"

    cp "$RNDC_KEY_PATH" /etc/rndc.key
    chown root:${BIND_GROUP} /etc/rndc.key
    chmod 640 /etc/rndc.key

    if [ "$DISTRO_FAMILY" == "rhel" ]; then
        BIND_CACHE_DIR="/var/named"
    else
        BIND_CACHE_DIR="/var/cache/bind"
    fi

    cat > "${BIND_CONFIG_DIR}/named.conf.options" << EOF
options {
    directory "${BIND_CACHE_DIR}";
    recursion no;
    allow-query { any; };
    allow-transfer { none; };
    notify no;
    dnssec-validation auto;
    listen-on { any; };
    listen-on-v6 { any; };
    querylog yes;
    version "PRIVUM DNS Manager Slave";
};
logging {
    channel default_log {
        file "/var/log/named/named.log" versions 3 size 5m;
        severity info;
        print-time yes;
        print-severity yes;
    };
    channel transfer_log {
        file "/var/log/named/transfer.log" versions 3 size 5m;
        severity info;
        print-time yes;
    };
    category default { default_log; };
    category xfer-in { transfer_log; };
    category xfer-out { transfer_log; };
    category notify { transfer_log; };
};
EOF

    NAMED_CONF_LOCAL="${BIND_CONFIG_DIR}/named.conf.local"

    cat > "$NAMED_CONF_LOCAL" << EOF
controls {
    inet 127.0.0.1 port 953 allow { 127.0.0.1; } keys { "rndc-key"; };
};
include "${RNDC_KEY_PATH}";
acl "masters" { ${MASTER_IP}; };
EOF

    ZONE_COUNT=$(echo "$ZONES_JSON" | jq 'length')
    log_info "Configuring $ZONE_COUNT zones..."

    for i in $(seq 0 $((ZONE_COUNT - 1))); do
        ZONE_NAME=$(echo "$ZONES_JSON" | jq -r ".[$i].name")
        ZONE_FILE=$(echo "$ZONES_JSON" | jq -r ".[$i].file")

        cat >> "$NAMED_CONF_LOCAL" << EOF

zone "${ZONE_NAME}" {
    type slave;
    file "${BIND_ZONES_DIR}/${ZONE_FILE}";
    primaries { ${MASTER_IP}; };
    allow-notify { ${MASTER_IP}; };
};
EOF
    done

    chown root:${BIND_GROUP} "${BIND_CONFIG_DIR}/named.conf.options"
    chown root:${BIND_GROUP} "$NAMED_CONF_LOCAL"
    chmod 644 "${BIND_CONFIG_DIR}/named.conf.options"
    chmod 644 "$NAMED_CONF_LOCAL"

    if [ "$DISTRO_FAMILY" == "rhel" ]; then
        cat > /etc/named.conf << 'NAMEDCONF'
include "/etc/named/named.conf.options";
include "/etc/named/named.conf.local";
zone "." IN { type hint; file "named.ca"; };
include "/etc/named.rfc1912.zones";
include "/etc/named.root.key";
NAMEDCONF
        chown root:${BIND_GROUP} /etc/named.conf
        chmod 644 /etc/named.conf
    fi

    log_info "Validating BIND configuration..."
    named-checkconf || {
        log_error "BIND configuration validation failed"
        exit 1
    }

    log_success "BIND slave configuration complete"
}

start_bind_slave() {
    log_info "Starting BIND..."

    systemctl enable $BIND_SERVICE
    systemctl restart $BIND_SERVICE

    sleep 3

    if ! systemctl is-active --quiet $BIND_SERVICE; then
        log_error "BIND failed to start"
        journalctl -u $BIND_SERVICE --no-pager -n 20
        exit 1
    fi

    log_success "BIND started successfully"
}

register_slave() {
    log_info "Registering slave with master..."

    SLAVE_IP=$(hostname -I | awk '{print $1}')
    SLAVE_HOSTNAME=$(hostname -f 2>/dev/null || hostname)

    curl -s -X POST "http://${MASTER_IP}/api/slaves/register" \
        -H "Content-Type: application/json" \
        -d "{\"token\": \"${MASTER_TOKEN}\", \"ip_address\": \"${SLAVE_IP}\", \"hostname\": \"${SLAVE_HOSTNAME}\"}" > /dev/null 2>&1 || true

    log_success "Slave registered"
}

setup_slave_agent() {
    log_info "Setting up slave-agent (push from master) and heartbeat..."

    mkdir -p "$INSTALL_DIR"
    mkdir -p /var/log/dns-manager

    cat > "${INSTALL_DIR}/slave.conf" << EOF
MASTER_IP="${MASTER_IP}"
MASTER_URL="http://${MASTER_IP}"
NAMED_CONF_LOCAL="${BIND_CONFIG_DIR}/named.conf.local"
ZONES_DIR="${BIND_ZONES_DIR}"
AGENT_BIND="0.0.0.0"
AGENT_PORT="5001"
LOG_FILE="/var/log/dns-manager/sync.log"
EOF
    chmod 600 "${INSTALL_DIR}/slave.conf"

    # Shared token for master <-> slave-agent push.
    # If master didn't provide one (older master), agent will refuse to start
    # and the user can drop the token manually + restart the unit.
    if [ -n "${SLAVE_AGENT_TOKEN:-}" ]; then
        echo "${SLAVE_AGENT_TOKEN}" > "${INSTALL_DIR}/slave-agent.token"
        chmod 600 "${INSTALL_DIR}/slave-agent.token"
    fi

    # Heartbeat script (still useful for "last seen" in master UI)
    cat > /usr/local/bin/dns-manager-heartbeat.sh << 'EOF'
#!/bin/bash
source /opt/dns-manager/slave.conf
SLAVE_IP=$(hostname -I | awk '{print $1}')
curl -s -X POST "${MASTER_URL}/api/slaves/heartbeat" \
    -H "Content-Type: application/json" \
    -d "{\"ip_address\": \"${SLAVE_IP}\"}" > /dev/null 2>&1
EOF
    chmod +x /usr/local/bin/dns-manager-heartbeat.sh

    # Drop any legacy zone-sync cron from previous installs — agent replaces it.
    (crontab -l 2>/dev/null \
        | grep -v dns-manager-heartbeat \
        | grep -v dns-manager-sync-zones \
        ; echo "*/5 * * * * /usr/local/bin/dns-manager-heartbeat.sh") | crontab -

    rm -f /usr/local/bin/dns-manager-sync-zones.sh

    # Deploy the slave-agent (HTTP service that receives push from master)
    if [ -d "${TEMP_DIR}/slave-agent" ]; then
        mkdir -p "${INSTALL_DIR}/slave-agent"
        cp -r "${TEMP_DIR}/slave-agent/"* "${INSTALL_DIR}/slave-agent/"

        # Reuse master's venv if available; otherwise create a minimal one
        if [ ! -x "${INSTALL_DIR}/venv/bin/python" ]; then
            python3 -m venv "${INSTALL_DIR}/venv"
        fi
        "${INSTALL_DIR}/venv/bin/pip" install --upgrade pip > /dev/null
        "${INSTALL_DIR}/venv/bin/pip" install flask requests > /dev/null

        install -m 644 "${TEMP_DIR}/configs/slave/slave-agent.service" \
            /etc/systemd/system/slave-agent.service

        systemctl daemon-reload
        systemctl enable slave-agent.service
        systemctl restart slave-agent.service
        sleep 2
        if systemctl is-active --quiet slave-agent.service; then
            log_success "slave-agent running on :5001 (reconciles with master on boot)"
        else
            log_warn "slave-agent failed to start — check 'journalctl -u slave-agent'"
        fi
    else
        log_warn "slave-agent source missing in repo — skipping push setup"
    fi
}

print_slave_summary() {
    SLAVE_IP=$(hostname -I | awk '{print $1}')

    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}        PRIVUM DNS Manager Slave - Installation Complete!      ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${CYAN}Slave Information:${NC}"
    echo "  Slave IP:  ${SLAVE_IP}"
    echo "  Master IP: ${MASTER_IP}"
    echo "  Status:    Active"
    echo ""
    echo -e "${CYAN}Service Management:${NC}"
    echo "  systemctl {start|stop|restart|status} ${BIND_SERVICE}"
    echo ""
    echo -e "${CYAN}Log Files:${NC}"
    echo "  BIND:     /var/log/named/named.log"
    echo "  Transfer: /var/log/named/transfer.log"
    echo ""
    echo -e "${CYAN}Verify Zone Transfer:${NC}"
    echo "  dig @localhost <zone-name> SOA"
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

#===============================================================================
# Main
#===============================================================================

main() {
    print_banner
    check_root
    parse_arguments "$@"
    detect_distro

    if [ "$MODE" == "master" ]; then
        log_info "Installing PRIVUM DNS Manager (Master)..."
        install_dependencies_master
        download_source
        configure_bind_master
        install_api
        create_admin_user
        build_frontend
        configure_nginx
        configure_firewall
        cleanup_temp
        generate_slave_token
        print_master_summary
    else
        log_info "Installing PRIVUM DNS Manager (Slave)..."
        install_dependencies_slave
        download_source
        fetch_master_config
        configure_bind_slave
        start_bind_slave
        register_slave
        configure_firewall
        setup_slave_agent
        cleanup_temp
        print_slave_summary
    fi
}

main "$@"

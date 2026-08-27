"""
DNS Web Manager - Configuration
Supports both Docker and native installation
"""
import os
import json
from datetime import timedelta

# Detect installation type
IS_DOCKER = os.path.exists('/.dockerenv') or os.environ.get('DOCKER_CONTAINER', False)

# Keycloak SSO Configuration
KEYCLOAK_ENABLED = os.environ.get('KEYCLOAK_ENABLED', 'false').lower() == 'true'
KEYCLOAK_SERVER_URL = os.environ.get('KEYCLOAK_SERVER_URL', 'https://keycloak.example.com')
KEYCLOAK_REALM = os.environ.get('KEYCLOAK_REALM', 'dns-manager')
KEYCLOAK_CLIENT_ID = os.environ.get('KEYCLOAK_CLIENT_ID', 'dns-web-manager')
KEYCLOAK_JWKS_URL = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"

# Local admin fallback (emergency access)
LOCAL_ADMIN_ENABLED = os.environ.get('LOCAL_ADMIN_ENABLED', 'true').lower() == 'true'

# Group to Role Mapping (default mapping)
_default_group_mapping = {
    'dns-admin': 'admin',
    'dns-operator': 'operator',
    'dns-viewer': 'viewer'
}
try:
    KEYCLOAK_GROUP_MAPPING = json.loads(os.environ.get('KEYCLOAK_GROUP_MAPPING', '{}')) or _default_group_mapping
except json.JSONDecodeError:
    KEYCLOAK_GROUP_MAPPING = _default_group_mapping

# Base paths for native installation
NATIVE_BASE_PATH = '/opt/dns-manager'
NATIVE_DATA_PATH = os.path.join(NATIVE_BASE_PATH, 'data')


def detect_bind_paths():
    """Detect BIND9 paths based on distro"""
    # Debian/Ubuntu paths
    if os.path.exists('/etc/bind'):
        return {
            'config_dir': '/etc/bind',
            'zones_dir': '/var/lib/bind/zones',
            'named_conf_local': '/etc/bind/named.conf.local',
            'rndc_key': '/etc/bind/rndc.key'
        }
    # RHEL/CentOS paths
    elif os.path.exists('/etc/named'):
        return {
            'config_dir': '/etc/named',
            'zones_dir': '/var/named/zones',
            'named_conf_local': '/etc/named/named.conf.local',
            'rndc_key': '/etc/named/rndc.key'
        }
    # Default (Docker)
    return {
        'config_dir': '/etc/bind',
        'zones_dir': '/etc/bind/zones',
        'named_conf_local': '/etc/bind/named.conf.local',
        'rndc_key': '/etc/bind/rndc.key'
    }


BIND_PATHS = detect_bind_paths()


# Default insecure secrets that must be changed in production
INSECURE_SECRETS = [
    'change-me-in-production-please',
    'change-me-in-production',
    'secret-key',
    'default-secret',
    'changeme',
    'your-secret-key',
    'development-key',
]


def validate_secret_key(secret_key):
    """Validate that secret key is not a default/insecure value"""
    if not secret_key or len(secret_key) < 32:
        return False
    if secret_key.lower() in [s.lower() for s in INSECURE_SECRETS]:
        return False
    return True


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'change-me-in-production-please')

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # DNS Settings - Auto-detect paths
    DNS_MASTER_HOST = os.environ.get('DNS_MASTER_HOST', 'localhost' if not IS_DOCKER else 'dns-master')
    DNS_MASTER_IP = os.environ.get('DNS_MASTER_IP', '127.0.0.1' if not IS_DOCKER else '172.25.0.10')
    DNS_SLAVE_HOST = os.environ.get('DNS_SLAVE_HOST', '')
    DNS_SLAVE_IP = os.environ.get('DNS_SLAVE_IP', '' if not IS_DOCKER else '172.25.0.11')
    ZONES_PATH = os.environ.get('ZONES_PATH', BIND_PATHS['zones_dir'])
    RNDC_KEY_PATH = os.environ.get('RNDC_KEY_PATH', BIND_PATHS['rndc_key'])
    NAMED_CONF_LOCAL = os.environ.get('NAMED_CONF_LOCAL', BIND_PATHS['named_conf_local'])
    BIND_CONFIG_DIR = os.environ.get('BIND_CONFIG_DIR', BIND_PATHS['config_dir'])

    # Auth
    AUTH_USERNAME = os.environ.get('AUTH_USERNAME', 'admin')
    AUTH_PASSWORD_HASH = os.environ.get('AUTH_PASSWORD_HASH', None)

    # Keycloak SSO
    KEYCLOAK_ENABLED = KEYCLOAK_ENABLED
    KEYCLOAK_SERVER_URL = KEYCLOAK_SERVER_URL
    KEYCLOAK_REALM = KEYCLOAK_REALM
    KEYCLOAK_CLIENT_ID = KEYCLOAK_CLIENT_ID
    KEYCLOAK_JWKS_URL = KEYCLOAK_JWKS_URL
    KEYCLOAK_GROUP_MAPPING = KEYCLOAK_GROUP_MAPPING
    LOCAL_ADMIN_ENABLED = LOCAL_ADMIN_ENABLED

    # Backup
    BACKUP_PATH = os.environ.get('BACKUP_PATH', '/var/lib/dns-manager/backups' if not IS_DOCKER else '/backup')
    BACKUP_RETENTION_DAILY = int(os.environ.get('RETENTION_DAILY', 7))
    BACKUP_RETENTION_WEEKLY = int(os.environ.get('RETENTION_WEEKLY', 4))
    BACKUP_RETENTION_MONTHLY = int(os.environ.get('RETENTION_MONTHLY', 12))

    # Database - SQLite by default for native, PostgreSQL for Docker
    DATABASE_URL = os.environ.get('DATABASE_URL', None)

    # If no DATABASE_URL, use SQLite
    if not DATABASE_URL:
        if IS_DOCKER:
            # Docker without PostgreSQL - use local SQLite
            SQLALCHEMY_DATABASE_URI = 'sqlite:///dns_manager.db'
        else:
            # Native installation - use data directory
            os.makedirs(NATIVE_DATA_PATH, exist_ok=True)
            SQLALCHEMY_DATABASE_URI = f'sqlite:///{NATIVE_DATA_PATH}/dns_manager.db'

    # Slave integration settings
    SLAVE_TOKEN_EXPIRY_MINUTES = int(os.environ.get('SLAVE_TOKEN_EXPIRY', 10))

    # Installation info
    INSTALL_TYPE = 'docker' if IS_DOCKER else 'native'


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

    def __init__(self):
        super().__init__()
        # Validate secret key in production
        if not validate_secret_key(self.SECRET_KEY):
            import warnings
            warnings.warn(
                "\n" + "=" * 60 + "\n"
                "SECURITY WARNING: Insecure SECRET_KEY detected!\n"
                "Set FLASK_SECRET_KEY environment variable to a secure value.\n"
                "Generate one with: python3 -c \"import secrets; print(secrets.token_hex(32))\"\n"
                + "=" * 60 + "\n",
                RuntimeWarning
            )


# Config selector
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])

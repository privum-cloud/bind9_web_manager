#!/usr/bin/env python3
"""
DNS Web Manager - API Server
REST API for managing BIND9 DNS servers

Copyright (C) 2024-2026 PRIVUM
SPDX-License-Identifier: AGPL-3.0-or-later
"""
import os

from dotenv import load_dotenv
load_dotenv()  # Load .env before any other imports

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import get_config
from models import init_db

# Rate limiter instance (initialized in create_app)
limiter = None


def create_app():
    """Application factory"""
    global limiter

    app = Flask(__name__)

    # Load configuration
    app.config.from_object(get_config())

    # Initialize database
    init_db(app)

    # Initialize Rate Limiter
    # Protege contra brute-force e DDoS
    # Usa memcached-style storage em arquivo para funcionar com múltiplos workers
    storage_uri = os.environ.get('RATELIMIT_STORAGE_URI', 'memory://')

    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=["200 per minute", "1000 per hour"],
        storage_uri=storage_uri,
        strategy="fixed-window"
    )

    # Log rate limit configuration
    app.logger.info(f"Rate limiter initialized with storage: {storage_uri}")

    # Handler para quando limite é excedido
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            'error': 'Rate limit exceeded',
            'message': str(e.description),
            'retry_after': e.get_response().headers.get('Retry-After', 60)
        }), 429

    # Enable CORS for React frontend
    # Configure allowed origins via CORS_ORIGINS env variable (comma-separated)
    cors_origins_env = os.environ.get('CORS_ORIGINS', '')
    if cors_origins_env:
        cors_origins = [origin.strip() for origin in cors_origins_env.split(',')]
    else:
        # Default development origins (no wildcard for security)
        cors_origins = ["http://localhost:3000", "http://localhost:5173", "http://localhost:8080"]

    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True
        }
    })

    # Register API blueprints
    from api.auth import auth_api
    from api.dashboard import dashboard_api
    from api.zones import zones_api
    from api.users import users_api
    from api.backup import backup_api
    from api.settings import settings_api
    from api.slaves import slaves_api

    app.register_blueprint(auth_api)
    app.register_blueprint(dashboard_api)
    app.register_blueprint(zones_api)
    app.register_blueprint(users_api)
    app.register_blueprint(backup_api)
    app.register_blueprint(settings_api)
    app.register_blueprint(slaves_api)

    # Apply specific rate limits to critical endpoints
    # Login: 5 attempts per minute (anti brute-force)
    limiter.limit("5 per minute")(app.view_functions['auth_api.login'])

    # Backup run: 5 per hour (resource intensive)
    limiter.limit("5 per hour")(app.view_functions['backup_api.run_backup'])

    # Zone creation: 10 per minute (prevent spam)
    limiter.limit("10 per minute")(app.view_functions['zones_api.create_zone'])

    # Health check endpoint (always returns 200 for Docker)
    @app.route('/health')
    def health():
        from services.dns_service import DNSService
        try:
            dns = DNSService()
            server_status = dns.get_server_status()

            status = {
                'status': 'healthy',
                'service': 'dns-web-manager-api',
                'dns_master': server_status['master']['status'] == 'online',
                'dns_slave': server_status['slave']['status'] == 'online'
            }

            if not status['dns_master']:
                status['status'] = 'degraded'
        except Exception as e:
            status = {
                'status': 'degraded',
                'service': 'dns-web-manager-api',
                'error': str(e)
            }

        # Always return 200 for Docker health check
        return jsonify(status), 200

    # API root info
    @app.route('/api')
    def api_info():
        return jsonify({
            'name': 'PRIVUM DNS Manager API',
            'version': '2.0.0',
            # AGPLv3 section 13: users interacting with this service over a
            # network must be offered the Corresponding Source. If you deploy a
            # MODIFIED version, point 'source' at your own published sources.
            'license': 'AGPL-3.0-or-later',
            'source': os.environ.get(
                'SOURCE_URL', 'https://gitlab.com/privum_public/dns_manager'
            ),
            'endpoints': {
                'auth': '/api/auth',
                'dashboard': '/api/dashboard',
                'zones': '/api/zones',
                'users': '/api/users',
                'backup': '/api/backup',
                'settings': '/api/settings'
            }
        })

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500

    return app


# Create app instance
app = create_app()


if __name__ == '__main__':
    print("=" * 50)
    print("PRIVUM DNS Manager API Server v2.0.0")
    print("=" * 50)
    print(f"Zones path: {app.config['ZONES_PATH']}")
    print(f"DNS Master: {app.config['DNS_MASTER_HOST']}")
    print(f"Running on: http://0.0.0.0:5000")
    print("=" * 50)

    app.run(host='0.0.0.0', port=5000, debug=True)

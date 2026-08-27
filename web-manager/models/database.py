"""
DNS Web Manager - Database Configuration
SQLAlchemy setup with Flask integration
Supports both PostgreSQL and SQLite
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3
import os

# Initialize SQLAlchemy
db = SQLAlchemy()


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enable foreign keys for SQLite"""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def init_db(app):
    """Initialize database with Flask app"""
    # Configure SQLAlchemy
    database_url = app.config.get('DATABASE_URL')

    if database_url:
        # Fix Heroku-style postgres:// URLs
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
    elif not app.config.get('SQLALCHEMY_DATABASE_URI'):
        # Fallback to SQLite for development without PostgreSQL
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dns_manager.db'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Configure engine options based on database type
    if 'sqlite' in app.config['SQLALCHEMY_DATABASE_URI']:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}
    else:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
        }

    # Initialize with app
    db.init_app(app)

    # Create tables and initial data
    with app.app_context():
        create_tables()
        seed_initial_data()

    return db


def create_tables():
    """Create all database tables"""
    db.create_all()


def seed_initial_data():
    """Seed initial data if tables are empty (race-condition safe)"""
    from .user import User
    from .settings import Settings
    from sqlalchemy.exc import IntegrityError

    # Create admin user if not exists (with race condition protection)
    try:
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@localhost',
                role='admin',
                active=True
            )
            admin.set_password('admin')
            db.session.add(admin)
            db.session.commit()
            print("[DB] Created default admin user (admin/admin)")
    except IntegrityError:
        # Another worker already created the admin user
        db.session.rollback()

    # Create default settings if not exist
    default_settings = [
        ('dns_default_ttl', 3600, 'TTL padrão para novos registros'),
        ('dns_default_refresh', 86400, 'Refresh padrão para SOA'),
        ('dns_default_retry', 7200, 'Retry padrão para SOA'),
        ('dns_default_expire', 3600000, 'Expire padrão para SOA'),
        ('dns_default_minimum', 86400, 'Minimum padrão para SOA'),
        ('session_timeout', 30, 'Timeout de sessão em minutos'),
        ('max_login_attempts', 5, 'Tentativas máximas de login'),
        ('lockout_duration', 15, 'Duração do bloqueio em minutos'),
    ]

    for key, value, description in default_settings:
        try:
            if not Settings.query.get(key):
                setting = Settings(key=key, value=value, description=description)
                db.session.add(setting)
                db.session.commit()
        except IntegrityError:
            # Another worker already created this setting
            db.session.rollback()


def get_db():
    """Get database session"""
    return db.session


def reset_db():
    """Reset database - USE WITH CAUTION"""
    db.drop_all()
    db.create_all()
    seed_initial_data()

"""
DNS Web Manager - Settings Model
SQLAlchemy model for system settings
"""
from datetime import datetime
from .database import db


class Settings(db.Model):
    """Settings model for system configuration"""
    __tablename__ = 'settings'

    key = db.Column(db.String(100), primary_key=True)
    value = db.Column(db.JSON, nullable=False)
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    def __repr__(self):
        return f'<Settings {self.key}={self.value}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get(cls, key, default=None):
        """Get a setting value by key"""
        setting = cls.query.get(key)
        if setting:
            return setting.value
        return default

    @classmethod
    def set(cls, key, value, description=None, user_id=None):
        """Set a setting value"""
        setting = cls.query.get(key)
        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.updated_by = user_id
        else:
            setting = cls(
                key=key,
                value=value,
                description=description,
                updated_by=user_id
            )
            db.session.add(setting)
        db.session.commit()
        return setting

    @classmethod
    def get_all(cls):
        """Get all settings"""
        return {s.key: s.value for s in cls.query.all()}

    @classmethod
    def get_all_detailed(cls):
        """Get all settings with metadata"""
        return [s.to_dict() for s in cls.query.all()]

    @classmethod
    def delete(cls, key):
        """Delete a setting"""
        setting = cls.query.get(key)
        if setting:
            db.session.delete(setting)
            db.session.commit()
            return True
        return False

    @classmethod
    def get_dns_settings(cls):
        """Get DNS-related settings"""
        return {
            'default_ttl': cls.get('dns_default_ttl', 3600),
            'default_refresh': cls.get('dns_default_refresh', 86400),
            'default_retry': cls.get('dns_default_retry', 7200),
            'default_expire': cls.get('dns_default_expire', 3600000),
            'default_minimum': cls.get('dns_default_minimum', 86400)
        }

    @classmethod
    def set_dns_settings(cls, settings_dict, user_id=None):
        """Set DNS-related settings"""
        mapping = {
            'default_ttl': 'dns_default_ttl',
            'default_refresh': 'dns_default_refresh',
            'default_retry': 'dns_default_retry',
            'default_expire': 'dns_default_expire',
            'default_minimum': 'dns_default_minimum'
        }
        for key, db_key in mapping.items():
            if key in settings_dict:
                cls.set(db_key, settings_dict[key], user_id=user_id)

    @classmethod
    def get_security_settings(cls):
        """Get security-related settings"""
        return {
            'session_timeout': cls.get('session_timeout', 30),
            'max_login_attempts': cls.get('max_login_attempts', 5),
            'lockout_duration': cls.get('lockout_duration', 15)
        }

    @classmethod
    def set_security_settings(cls, settings_dict, user_id=None):
        """Set security-related settings"""
        keys = ['session_timeout', 'max_login_attempts', 'lockout_duration']
        for key in keys:
            if key in settings_dict:
                cls.set(key, settings_dict[key], user_id=user_id)


class ZoneVersion(db.Model):
    """Zone version history model"""
    __tablename__ = 'zone_versions'

    id = db.Column(db.Integer, primary_key=True)
    zone_name = db.Column(db.String(255), nullable=False)
    serial = db.Column(db.BigInteger, nullable=False)
    content = db.Column(db.Text, nullable=False)
    changed_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    change_type = db.Column(db.String(20), nullable=False)
    change_summary = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ZoneVersion {self.zone_name} serial={self.serial}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'zone_name': self.zone_name,
            'serial': self.serial,
            'change_type': self.change_type,
            'change_summary': self.change_summary,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def save_version(cls, zone_name, serial, content, change_type, user_id=None, change_summary=None):
        """Save a new zone version"""
        version = cls(
            zone_name=zone_name,
            serial=serial,
            content=content,
            changed_by=user_id,
            change_type=change_type,
            change_summary=change_summary
        )
        db.session.add(version)
        db.session.commit()
        return version

    @classmethod
    def get_versions(cls, zone_name, limit=10):
        """Get version history for a zone"""
        return cls.query.filter_by(zone_name=zone_name).order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_version(cls, version_id):
        """Get a specific version"""
        return cls.query.get(version_id)

    @classmethod
    def get_latest(cls, zone_name):
        """Get the latest version of a zone"""
        return cls.query.filter_by(zone_name=zone_name).order_by(cls.created_at.desc()).first()

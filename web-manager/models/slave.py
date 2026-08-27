"""
DNS Web Manager - Slave Model
SQLAlchemy model for DNS slave server management
"""
from datetime import datetime, timedelta
from .database import db
import secrets


class Slave(db.Model):
    """Slave DNS server model"""
    __tablename__ = 'slaves'

    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=True)
    ip_address = db.Column(db.String(45), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, active, inactive, error
    registered_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, nullable=True)
    last_sync = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Slave {self.ip_address} ({self.status})>'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'status': self.status,
            'registered_at': self.registered_at.isoformat() if self.registered_at else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'last_sync': self.last_sync.isoformat() if self.last_sync else None,
            'notes': self.notes
        }

    def update_last_seen(self):
        """Update last seen timestamp"""
        self.last_seen = datetime.utcnow()
        db.session.commit()

    def update_last_sync(self):
        """Update last sync timestamp"""
        self.last_sync = datetime.utcnow()
        db.session.commit()

    def set_status(self, status):
        """Update slave status"""
        self.status = status
        db.session.commit()

    @classmethod
    def get_by_ip(cls, ip_address):
        """Get slave by IP address"""
        return cls.query.filter_by(ip_address=ip_address).first()

    @classmethod
    def get_all(cls):
        """Get all slaves"""
        return cls.query.order_by(cls.registered_at.desc()).all()

    @classmethod
    def get_active(cls):
        """Get all active slaves"""
        return cls.query.filter_by(status='active').all()

    @classmethod
    def create(cls, ip_address, hostname=None, notes=None):
        """Create a new slave"""
        slave = cls(
            ip_address=ip_address,
            hostname=hostname,
            notes=notes,
            status='active'
        )
        db.session.add(slave)
        db.session.commit()
        return slave

    def delete(self):
        """Delete slave"""
        db.session.delete(self)
        db.session.commit()


class SlaveToken(db.Model):
    """Integration token for slave registration"""
    __tablename__ = 'slave_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)
    used_at = db.Column(db.DateTime, nullable=True)
    used_by_ip = db.Column(db.String(45), nullable=True)

    def __repr__(self):
        return f'<SlaveToken {self.token[:8]}... expires={self.expires_at}>'

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'token': self.token,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'used': self.used,
            'used_at': self.used_at.isoformat() if self.used_at else None,
            'used_by_ip': self.used_by_ip
        }

    def is_valid(self):
        """Check if token is still valid"""
        if self.used:
            return False
        if datetime.utcnow() > self.expires_at:
            return False
        return True

    def mark_used(self, ip_address):
        """Mark token as used"""
        self.used = True
        self.used_at = datetime.utcnow()
        self.used_by_ip = ip_address
        db.session.commit()

    @classmethod
    def generate(cls, user_id, expiry_minutes=10):
        """Generate a new integration token"""
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(minutes=expiry_minutes)

        slave_token = cls(
            token=token,
            created_by=user_id,
            expires_at=expires_at
        )
        db.session.add(slave_token)
        db.session.commit()
        return slave_token

    @classmethod
    def get_by_token(cls, token):
        """Get token by value"""
        return cls.query.filter_by(token=token).first()

    @classmethod
    def cleanup_expired(cls):
        """Remove expired tokens"""
        expired = cls.query.filter(cls.expires_at < datetime.utcnow()).all()
        for token in expired:
            db.session.delete(token)
        db.session.commit()
        return len(expired)

    @classmethod
    def get_active(cls):
        """Get all active (unused, not expired) tokens"""
        return cls.query.filter(
            cls.used == False,
            cls.expires_at > datetime.utcnow()
        ).all()

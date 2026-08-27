"""
DNS Web Manager - User Model
SQLAlchemy model for user management
"""
from datetime import datetime
from .database import db
import bcrypt


class User(db.Model):
    """User model for authentication and authorization"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='viewer')
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Security fields
    must_change_password = db.Column(db.Boolean, default=True)  # Force password change on first login

    # 2FA/TOTP fields
    totp_secret = db.Column(db.String(32), nullable=True)
    totp_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.JSON, nullable=True)

    # SSO/Keycloak fields
    keycloak_id = db.Column(db.String(255), unique=True, nullable=True, index=True)
    auth_source = db.Column(db.String(20), default='local')  # 'local' or 'keycloak'
    is_local_admin = db.Column(db.Boolean, default=False)  # Emergency local admin flag

    # Relationships
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        """Hash and set password"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    def check_password(self, password):
        """Verify password against hash"""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()

    def to_dict(self, include_email=False):
        """Convert to dictionary for API responses"""
        data = {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'active': self.active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
            'totp_enabled': self.totp_enabled or False,
            'must_change_password': self.must_change_password or False,
            'auth_source': self.auth_source or 'local',
            'is_local_admin': self.is_local_admin or False
        }
        if include_email:
            data['email'] = self.email
        return data

    def generate_totp_secret(self):
        """Generate a new TOTP secret"""
        import pyotp
        self.totp_secret = pyotp.random_base32()
        self.totp_enabled = False  # Not enabled until verified
        db.session.commit()
        return self.totp_secret

    def get_totp_uri(self):
        """Get the TOTP URI for QR code generation"""
        import pyotp
        if not self.totp_secret:
            return None
        totp = pyotp.TOTP(self.totp_secret)
        return totp.provisioning_uri(name=self.email, issuer_name="DNS Web Manager")

    def verify_totp(self, code):
        """Verify a TOTP code"""
        import pyotp
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code, valid_window=1)  # Allow 1 window tolerance

    def enable_totp(self):
        """Enable TOTP after verification"""
        self.totp_enabled = True
        self.generate_backup_codes()
        db.session.commit()

    def disable_totp(self):
        """Disable TOTP"""
        self.totp_enabled = False
        self.totp_secret = None
        self.backup_codes = None
        db.session.commit()

    def generate_backup_codes(self):
        """Generate backup codes for account recovery"""
        import secrets
        codes = [secrets.token_hex(4).upper() for _ in range(8)]
        self.backup_codes = codes
        db.session.commit()
        return codes

    def verify_backup_code(self, code):
        """Verify and consume a backup code"""
        if not self.backup_codes:
            return False
        code = code.upper().replace('-', '').replace(' ', '')
        if code in self.backup_codes:
            # Create a new list to force SQLAlchemy to detect the change
            codes = list(self.backup_codes)
            codes.remove(code)
            self.backup_codes = codes
            db.session.commit()
            return True
        return False

    def has_permission(self, action):
        """Check if user has permission for action"""
        permissions = {
            'admin': ['create', 'edit', 'delete', 'view', 'manage_users', 'backup', 'settings'],
            'operator': ['create', 'edit', 'view', 'backup'],
            'viewer': ['view']
        }
        return action in permissions.get(self.role, [])

    def is_admin(self):
        """Check if user is admin"""
        return self.role == 'admin'

    @classmethod
    def get_by_id(cls, user_id):
        """Get user by ID"""
        return cls.query.get(user_id)

    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        return cls.query.filter_by(username=username).first()

    @classmethod
    def get_by_email(cls, email):
        """Get user by email"""
        return cls.query.filter_by(email=email).first()

    @classmethod
    def get_all_active(cls):
        """Get all active users"""
        return cls.query.filter_by(active=True).all()

    @classmethod
    def get_all(cls):
        """Get all users"""
        return cls.query.order_by(cls.created_at.desc()).all()

    @classmethod
    def create(cls, username, email, password, role='viewer'):
        """Create a new user"""
        user = cls(
            username=username,
            email=email,
            role=role
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return user

    def update(self, **kwargs):
        """Update user fields"""
        allowed_fields = ['username', 'email', 'role', 'active']
        for field in allowed_fields:
            if field in kwargs:
                setattr(self, field, kwargs[field])
        if 'password' in kwargs and kwargs['password']:
            self.set_password(kwargs['password'])
        db.session.commit()
        return self

    def delete(self):
        """Soft delete - deactivate user"""
        self.active = False
        db.session.commit()

    def hard_delete(self):
        """Permanently delete user"""
        db.session.delete(self)
        db.session.commit()

    @classmethod
    def get_by_keycloak_id(cls, keycloak_id):
        """Get user by Keycloak subject ID"""
        if not keycloak_id:
            return None  # Don't search for NULL keycloak_id
        return cls.query.filter_by(keycloak_id=keycloak_id).first()

    @classmethod
    def create_from_keycloak(cls, keycloak_id, username, email, role='viewer'):
        """Create a new user from Keycloak authentication"""
        user = cls(
            keycloak_id=keycloak_id,
            username=username,
            email=email,
            role=role,
            auth_source='keycloak',
            password_hash='',  # No password for SSO users
            must_change_password=False,
            active=True
        )
        db.session.add(user)
        db.session.commit()
        return user

"""
DNS Web Manager - Audit Log Model
SQLAlchemy model for audit logging
"""
from datetime import datetime
from flask import request, g
from .database import db
import json


class AuditLog(db.Model):
    """Audit log model for tracking system changes"""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    username = db.Column(db.String(50))
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_name = db.Column(db.String(255), nullable=False)
    old_value = db.Column(db.JSON, nullable=True)
    new_value = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AuditLog {self.action} {self.target_type}:{self.target_name}>'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'user': self.username or 'system',
            'action': f"{self.action} {self.target_type}",
            'type': self.action,
            'target': self.target_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'ip_address': self.ip_address,
            'timestamp': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def log(cls, action, target_type, target_name, old_value=None, new_value=None, user=None):
        """
        Create an audit log entry

        Args:
            action: The action performed (create, update, delete, login, etc.)
            target_type: Type of target (zone, record, user, system, etc.)
            target_name: Name/identifier of the target
            old_value: Previous value (for updates/deletes)
            new_value: New value (for creates/updates)
            user: User object (optional, will try to get from g.current_user)
        """
        # Get user from context if not provided
        if user is None:
            user = getattr(g, 'current_user', None)

        # Get request info
        ip_address = None
        user_agent = None
        try:
            ip_address = request.remote_addr
            user_agent = request.headers.get('User-Agent', '')[:500]
        except RuntimeError:
            # Outside of request context
            pass

        log_entry = cls(
            user_id=user.id if user and hasattr(user, 'id') else None,
            username=user.username if user and hasattr(user, 'username') else 'system',
            action=action,
            target_type=target_type,
            target_name=str(target_name),
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent
        )

        db.session.add(log_entry)
        db.session.commit()
        return log_entry

    @classmethod
    def get_recent(cls, limit=50):
        """Get recent audit logs"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_by_user(cls, user_id, limit=50):
        """Get audit logs for a specific user"""
        return cls.query.filter_by(user_id=user_id).order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_by_target(cls, target_type, target_name=None, limit=50):
        """Get audit logs for a specific target"""
        query = cls.query.filter_by(target_type=target_type)
        if target_name:
            query = query.filter_by(target_name=target_name)
        return query.order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_by_action(cls, action, limit=50):
        """Get audit logs for a specific action"""
        return cls.query.filter_by(action=action).order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def search(cls, query_str, limit=50):
        """Search audit logs"""
        search_pattern = f'%{query_str}%'
        return cls.query.filter(
            db.or_(
                cls.action.ilike(search_pattern),
                cls.target_type.ilike(search_pattern),
                cls.target_name.ilike(search_pattern),
                cls.username.ilike(search_pattern)
            )
        ).order_by(cls.created_at.desc()).limit(limit).all()

    @classmethod
    def get_stats(cls):
        """Get audit log statistics"""
        from sqlalchemy import func

        total = cls.query.count()

        by_action = db.session.query(
            cls.action,
            func.count(cls.id)
        ).group_by(cls.action).all()

        by_type = db.session.query(
            cls.target_type,
            func.count(cls.id)
        ).group_by(cls.target_type).all()

        return {
            'total': total,
            'by_action': {action: count for action, count in by_action},
            'by_type': {target_type: count for target_type, count in by_type}
        }


# Helper function for easy logging
def audit_log(action, target_type, target_name, old_value=None, new_value=None, user=None):
    """Shortcut function for creating audit logs"""
    return AuditLog.log(action, target_type, target_name, old_value, new_value, user)

"""User model for authentication and authorization."""
from app import db
from datetime import datetime, timezone
from flask_login import UserMixin


class User(UserMixin, db.Model):
    """User model representing system users (admins and pausalci)."""

    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.Enum('admin', 'pausalac', name='user_role'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    firma_id = db.Column(db.Integer, db.ForeignKey('pausaln_firma.id', ondelete='SET NULL'), nullable=True, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    firma = db.relationship('PausalnFirma', back_populates='users')
    fakture = db.relationship('Faktura', back_populates='user')

    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.email}>'

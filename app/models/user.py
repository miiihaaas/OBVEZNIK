"""User model for authentication and authorization."""
from app import db, bcrypt
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
    fakture = db.relationship('Faktura', foreign_keys='Faktura.user_id', back_populates='user')

    def is_admin(self):
        """Check if user has admin role."""
        return self.role == 'admin'

    def set_password(self, password):
        """
        Hash password using bcrypt with cost factor 12.

        Args:
            password: Plain text password to hash
        """
        self.password_hash = bcrypt.generate_password_hash(password, rounds=12).decode('utf-8')

    def check_password(self, password):
        """
        Verify password against stored hash.

        Args:
            password: Plain text password to verify

        Returns:
            bool: True if password matches, False otherwise
        """
        return bcrypt.check_password_hash(self.password_hash, password)

    def update_last_login(self):
        """Update last_login timestamp to current UTC time."""
        self.last_login = datetime.now(timezone.utc)
        db.session.commit()

    def __repr__(self):
        return f'<User {self.email}>'

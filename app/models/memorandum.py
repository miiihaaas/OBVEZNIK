"""Memorandum model (placeholder for future implementation)."""
from app import db
from datetime import datetime, timezone


class Memorandum(db.Model):
    """Model representing a memorandum (placeholder for Epic 4)."""

    __tablename__ = 'memorandumi'

    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('pausaln_firma.id', ondelete='CASCADE'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    firma = db.relationship('PausalnFirma')

    # TODO: Full implementation in Epic 4
    # This is a placeholder model for future development

    def __repr__(self):
        return f'<Memorandum {self.id}>'

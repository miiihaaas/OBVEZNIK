"""Memorandum model for internal documentation notes."""
from app import db
from datetime import datetime, timezone, date


class Memorandum(db.Model):
    """Model representing an internal memorandum (documentation note)."""

    __tablename__ = 'memorandumi'

    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('pausaln_firma.id', ondelete='CASCADE'), nullable=False, index=True)

    # Core fields (AC: 3)
    naslov = db.Column(db.String(255), nullable=False)
    sadrzaj = db.Column(db.Text, nullable=False)
    datum = db.Column(db.Date, nullable=False, default=lambda: date.today())

    # Optional linking (AC: 3)
    komitent_id = db.Column(db.Integer, db.ForeignKey('komitenti.id', ondelete='SET NULL'), nullable=True, index=True)
    faktura_id = db.Column(db.Integer, db.ForeignKey('fakture.id', ondelete='SET NULL'), nullable=True, index=True)

    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    firma = db.relationship('PausalnFirma')
    komitent = db.relationship('Komitent', foreign_keys=[komitent_id])
    faktura = db.relationship('Faktura', foreign_keys=[faktura_id])

    def __repr__(self):
        return f'<Memorandum {self.naslov[:50]}>'

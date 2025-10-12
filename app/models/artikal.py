"""Artikal model for products/services."""
from app import db
from datetime import datetime, timezone


class Artikal(db.Model):
    """Model representing a product or service (artikal)."""

    __tablename__ = 'artikli'

    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('pausaln_firma.id', ondelete='CASCADE'), nullable=False, index=True)

    # Product/service information
    naziv = db.Column(db.String(255), nullable=False)
    opis = db.Column(db.Text, nullable=True)
    podrazumevana_cena = db.Column(db.Numeric(10, 2), nullable=True)
    jedinica_mere = db.Column(db.String(20), nullable=False)

    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    firma = db.relationship('PausalnFirma', back_populates='artikli')
    faktura_stavke = db.relationship('FakturaStavka', back_populates='artikal')

    def __repr__(self):
        return f'<Artikal {self.naziv}>'

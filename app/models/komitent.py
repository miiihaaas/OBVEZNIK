"""Komitent model for invoice recipients (clients)."""
from app import db
from datetime import datetime, timezone


class Komitent(db.Model):
    """Model representing a client (komitent) who receives invoices."""

    __tablename__ = 'komitenti'

    id = db.Column(db.Integer, primary_key=True)
    firma_id = db.Column(db.Integer, db.ForeignKey('pausaln_firma.id', ondelete='CASCADE'), nullable=False, index=True)

    # Company identification
    pib = db.Column(db.String(9), nullable=False, index=True)
    maticni_broj = db.Column(db.String(8), nullable=False)
    naziv = db.Column(db.String(255), nullable=False)

    # Address information
    adresa = db.Column(db.String(255), nullable=False)
    broj = db.Column(db.String(20), nullable=False)
    postanski_broj = db.Column(db.String(10), nullable=False)
    mesto = db.Column(db.String(100), nullable=False)
    drzava = db.Column(db.String(50), nullable=False)

    # Contact information
    email = db.Column(db.String(120), nullable=False)
    kontakt_osoba = db.Column(db.String(255), nullable=True)  # Optional contact person
    napomene = db.Column(db.Text, nullable=True)  # Optional notes

    # Banking information (required for foreign currency invoices)
    iban = db.Column(db.String(34), nullable=True)  # IBAN format for international payments
    swift = db.Column(db.String(11), nullable=True)  # SWIFT/BIC code

    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    firma = db.relationship('PausalnFirma', back_populates='komitenti')
    fakture = db.relationship('Faktura', back_populates='komitent')

    # Composite index for tenant isolation and efficient queries
    __table_args__ = (
        db.Index('idx_firma_pib', 'firma_id', 'pib'),
    )

    def __repr__(self):
        return f'<Komitent {self.naziv} (PIB: {self.pib})>'

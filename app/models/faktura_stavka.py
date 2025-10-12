"""FakturaStavka model for invoice line items."""
from app import db


class FakturaStavka(db.Model):
    """Model representing a single line item on an invoice."""

    __tablename__ = 'faktura_stavke'

    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys
    faktura_id = db.Column(db.Integer, db.ForeignKey('fakture.id', ondelete='CASCADE'), nullable=False, index=True)
    artikal_id = db.Column(db.Integer, db.ForeignKey('artikli.id', ondelete='SET NULL'), nullable=True)

    # Line item details
    naziv = db.Column(db.String(255), nullable=False)
    kolicina = db.Column(db.Numeric(10, 2), nullable=False)
    jedinica_mere = db.Column(db.String(20), nullable=False)
    cena = db.Column(db.Numeric(10, 2), nullable=False)
    ukupno = db.Column(db.Numeric(12, 2), nullable=False)

    # Ordering
    redni_broj = db.Column(db.Integer, nullable=False)

    # Relationships
    faktura = db.relationship('Faktura', back_populates='stavke')
    artikal = db.relationship('Artikal', back_populates='faktura_stavke')

    def calculate_ukupno(self):
        """Calculate total amount (quantity * price)."""
        self.ukupno = self.kolicina * self.cena

    def __repr__(self):
        return f'<FakturaStavka {self.naziv} ({self.kolicina} x {self.cena})>'

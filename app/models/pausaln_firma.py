"""PausalnFirma model for lump-sum taxpayer companies."""
from app import db
from datetime import datetime, timezone
from sqlalchemy.dialects.mysql import JSON


class PausalnFirma(db.Model):
    """Model representing a lump-sum taxpayer company (paušalna firma)."""

    __tablename__ = 'pausaln_firma'

    id = db.Column(db.Integer, primary_key=True)
    pib = db.Column(db.String(9), unique=True, nullable=False, index=True)
    maticni_broj = db.Column(db.String(8), nullable=False)
    naziv = db.Column(db.String(255), nullable=False)
    adresa = db.Column(db.String(255), nullable=False)
    broj = db.Column(db.String(20), nullable=False)
    postanski_broj = db.Column(db.String(10), nullable=False)
    mesto = db.Column(db.String(100), nullable=False)
    drzava = db.Column(db.String(50), default='Srbija', nullable=False)
    telefon = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(120), nullable=False)

    # Bank account information stored as JSON
    dinarski_racuni = db.Column(JSON, nullable=False)
    devizni_racuni = db.Column(JSON, nullable=True)

    # Invoice numbering configuration
    prefiks_fakture = db.Column(db.String(10), nullable=True)
    sufiks_fakture = db.Column(db.String(10), nullable=True)
    brojac_fakture = db.Column(db.Integer, default=1, nullable=False)
    brojac_profakture = db.Column(db.Integer, default=1, nullable=False)
    brojac_avansne = db.Column(db.Integer, default=1, nullable=False)

    # Tax information
    pdv_kategorija = db.Column(db.String(10), default='SS', nullable=False)
    sifra_osnova = db.Column(db.String(20), default='PDV-RS-33', nullable=False)

    # Status and timestamps
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    users = db.relationship('User', back_populates='firma')
    komitenti = db.relationship('Komitent', back_populates='firma', cascade='all, delete-orphan')
    artikli = db.relationship('Artikal', back_populates='firma', cascade='all, delete-orphan')
    fakture = db.relationship('Faktura', back_populates='firma', cascade='all, delete-orphan')

    def get_next_broj_fakture(self):
        """Generate next invoice number based on prefix, counter, and suffix."""
        return f"{self.prefiks_fakture or ''}{self.brojac_fakture}{self.sufiks_fakture or ''}"

    def __repr__(self):
        return f'<PausalnFirma {self.naziv} (PIB: {self.pib})>'

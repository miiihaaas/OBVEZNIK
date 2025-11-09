"""Faktura model for invoices."""
from app import db
from datetime import datetime, timedelta, timezone


class Faktura(db.Model):
    """Model representing an invoice (faktura)."""

    __tablename__ = 'fakture'

    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys
    firma_id = db.Column(db.Integer, db.ForeignKey('pausaln_firma.id', ondelete='CASCADE'), nullable=False, index=True)
    komitent_id = db.Column(db.Integer, db.ForeignKey('komitenti.id', ondelete='RESTRICT'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False)

    # Invoice identification and type
    broj_fakture = db.Column(db.String(50), nullable=False, index=True)
    tip_fakture = db.Column(
        db.Enum('standardna', 'profaktura', 'avansna', 'devizna', name='tip_fakture'),
        nullable=False
    )
    valuta_fakture = db.Column(
        db.Enum('RSD', 'EUR', 'USD', 'GBP', 'CHF', name='valuta_fakture'),
        nullable=False
    )
    jezik = db.Column(
        db.Enum('sr', 'en', name='jezik_fakture'),
        default='sr',
        nullable=False
    )

    # Date fields
    datum_prometa = db.Column(db.Date, nullable=False)
    valuta_placanja = db.Column(db.Integer, nullable=False)  # Days until payment due
    datum_dospeca = db.Column(db.Date, nullable=False)

    # Optional reference fields
    broj_ugovora = db.Column(db.String(100), nullable=True)
    broj_odluke = db.Column(db.String(100), nullable=True)
    broj_narudzbenice = db.Column(db.String(100), nullable=True)
    poziv_na_broj = db.Column(db.String(50), nullable=True)
    model = db.Column(db.String(10), nullable=True)

    # Amount fields (using Decimal for precision)
    ukupan_iznos_rsd = db.Column(db.Numeric(12, 2), nullable=False)
    ukupan_iznos_originalna_valuta = db.Column(db.Numeric(12, 2), nullable=True)
    srednji_kurs = db.Column(db.Numeric(10, 4), nullable=True)

    # Status and references
    status = db.Column(
        db.Enum('draft', 'izdata', 'stornirana', 'konvertovana', 'zatvorena', name='status_fakture'),
        default='draft',
        nullable=False
    )
    avansna_faktura_id = db.Column(db.Integer, db.ForeignKey('fakture.id'), nullable=True)

    # Profaktura conversion linking (self-referential)
    konvertovana_iz_profakture_id = db.Column(
        db.Integer,
        db.ForeignKey('fakture.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    konvertovana_u_fakturu_id = db.Column(
        db.Integer,
        db.ForeignKey('fakture.id', ondelete='SET NULL'),
        nullable=True
    )

    # PDF storage
    pdf_url = db.Column(db.String(500), nullable=True)
    status_pdf = db.Column(
        db.Enum('pending', 'generating', 'generated', 'failed', name='status_pdf_fakture'),
        default='pending',
        nullable=False
    )

    # Email sending status
    email_status = db.Column(
        db.Enum('not_sent', 'sending', 'sent', 'failed', name='email_status_fakture'),
        default='not_sent',
        nullable=False
    )
    email_sent_at = db.Column(db.DateTime, nullable=True)
    email_recipient = db.Column(db.String(120), nullable=True)
    email_error_message = db.Column(db.Text, nullable=True)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    finalized_at = db.Column(db.DateTime, nullable=True)


    # Storniranje audit trail (optional fields)
    razlog_storniranja = db.Column(db.String(500), nullable=True)
    stornirana_at = db.Column(db.DateTime, nullable=True)
    stornirana_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    firma = db.relationship('PausalnFirma', back_populates='fakture')
    komitent = db.relationship('Komitent', back_populates='fakture')
    user = db.relationship('User', foreign_keys=[user_id], back_populates='fakture')
    stavke = db.relationship('FakturaStavka', back_populates='faktura', cascade='all, delete-orphan')

    # Self-referential relationships for profaktura conversion
    konvertovana_iz_profakture = db.relationship(
        'Faktura',
        remote_side=[id],
        foreign_keys=[konvertovana_iz_profakture_id],
        backref='konvertovana_u_fakturu_ref',
        uselist=False
    )

    # Constraints and indexes
    __table_args__ = (
        db.UniqueConstraint('firma_id', 'broj_fakture', name='uq_firma_broj'),
        db.Index('idx_firma_status', 'firma_id', 'status'),
    )

    def calculate_datum_dospeca(self):
        """Calculate due date based on transaction date and payment term."""
        self.datum_dospeca = self.datum_prometa + timedelta(days=self.valuta_placanja)

    def __repr__(self):
        return f'<Faktura {self.broj_fakture} ({self.status})>'

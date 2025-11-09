"""KPO Entry model for automatic invoice registration in KPO book."""
from app import db
from datetime import datetime, timezone


class KPOEntry(db.Model):
    """Model representing a KPO (Knjiga Prometa Obveznika) entry."""

    __tablename__ = 'kpo_entries'

    id = db.Column(db.Integer, primary_key=True)

    # Foreign keys - tenant isolation
    firma_id = db.Column(
        db.Integer,
        db.ForeignKey('pausaln_firma.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    faktura_id = db.Column(
        db.Integer,
        db.ForeignKey('fakture.id', ondelete='RESTRICT'),
        nullable=False,
        index=True
    )

    # KPO fields
    redni_broj = db.Column(db.Integer, nullable=False)
    broj_fakture = db.Column(db.String(50), nullable=False)
    datum_prometa = db.Column(db.Date, nullable=False)
    datum_dospeca = db.Column(db.Date, nullable=False)

    # Denormalized komitent data for performance
    komitent_naziv = db.Column(db.String(255), nullable=False)
    komitent_pib = db.Column(db.String(8), nullable=False)

    # Description and amounts
    opis = db.Column(db.Text, nullable=True)
    iznos_rsd = db.Column(db.Numeric(12, 2), nullable=False)
    valuta = db.Column(
        db.Enum('RSD', 'EUR', 'USD', 'GBP', 'CHF', name='valuta_fakture'),
        nullable=False
    )

    # Status tracking
    status_fakture = db.Column(
        db.Enum('izdata', 'stornirana', name='status_kpo'),
        nullable=False
    )

    # Godina field for partitioning and indexing
    godina = db.Column(db.Integer, nullable=False, index=True)

    # Timestamp
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    firma = db.relationship(
        'PausalnFirma',
        backref=db.backref('kpo_entries', lazy='dynamic')
    )
    faktura = db.relationship(
        'Faktura',
        backref=db.backref('kpo_entries', lazy='dynamic')
    )

    # Constraints
    __table_args__ = (
        db.UniqueConstraint(
            'firma_id',
            'redni_broj',
            'godina',
            name='uq_kpo_redni_broj_per_firma_godina'
        ),
        db.Index('idx_firma_godina', 'firma_id', 'godina'),
    )

    def __repr__(self):
        """String representation of KPO Entry."""
        return (
            f'<KPOEntry {self.redni_broj}/{self.godina} - '
            f'Faktura {self.broj_fakture} - {self.iznos_rsd} RSD>'
        )

"""Integration tests for automatic KPO entry creation and management."""
import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal

from app import db
from app.models import User, PausalnFirma, Komitent, Faktura, FakturaStavka, KPOEntry
from app.services import faktura_service


class TestKPOAutoEvidentiranje:
    """Tests for automatic KPO entry creation during faktura finalization."""

    def test_finalize_faktura_creates_kpo_entry(self, app):
        """Test finalizacija fakture kreira KPO entry automatski."""
        with app.app_context():
            # Setup: Create firma, komitent, user
            firma = PausalnFirma(
                pib='12345678', maticni_broj='87654321', naziv='Test Firma',
                adresa='Test', broj='1', postanski_broj='11000',
                mesto='Beograd', drzava='Srbija', telefon='011123456',
                email='test@test.rs', dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id, naziv='Komitent d.o.o.', pib='87654321',
                maticni_broj='12345678', adresa='Adresa 1', broj='1',
                postanski_broj='11000', mesto='Beograd', drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            user = User(
                email='user@test.rs', password_hash='hash',
                full_name='Test User', role='pausalac', firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create draft faktura directly
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='DRAFT-TMP',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 1, 15) + timedelta(days=30),
                ukupan_iznos_rsd=Decimal('10000.00'),
                status='draft'
            )
            db.session.add(faktura)
            db.session.commit()

            # Verify KPO entry doesn't exist yet
            kpo_before = KPOEntry.query.filter_by(faktura_id=faktura.id).first()
            assert kpo_before is None

            # Finalize faktura - should create KPO entry automatically
            finalized = faktura_service.finalize_faktura(faktura.id)
            assert finalized.status == 'izdata'

            # Verify KPO entry was created
            kpo_entry = KPOEntry.query.filter_by(faktura_id=faktura.id).first()
            assert kpo_entry is not None
            assert kpo_entry.redni_broj == 1
            assert kpo_entry.iznos_rsd == Decimal('10000.00')
            assert kpo_entry.status_fakture == 'izdata'
            assert kpo_entry.godina == 2025

    def test_storniraj_fakturu_updates_kpo_status(self, app, client):
        """Test storniranje fakture ažurira KPO status."""
        with app.app_context():
            # Setup
            firma = PausalnFirma(
                pib='12345678', maticni_broj='87654321', naziv='Test Firma',
                adresa='Test', broj='1', postanski_broj='11000',
                mesto='Beograd', drzava='Srbija', telefon='011123456',
                email='test@test.rs', dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id, naziv='Komitent d.o.o.', pib='87654321',
                maticni_broj='12345678', adresa='Adresa 1', broj='1',
                postanski_broj='11000', mesto='Beograd', drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            user = User(
                email='user@test.rs', password_hash='hash',
                full_name='Test User', role='pausalac', firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create and finalize faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='DRAFT-TMP2',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('5000.00'),
                status='draft'
            )
            db.session.add(faktura)
            db.session.commit()

            faktura_service.finalize_faktura(faktura.id)

            # Verify KPO entry exists with status 'izdata'
            kpo_entry = KPOEntry.query.filter_by(faktura_id=faktura.id).first()
            assert kpo_entry.status_fakture == 'izdata'

            # Mock current_user for storniraj_fakturu
            with client:
                with client.session_transaction() as sess:
                    sess['_user_id'] = str(user.id)

                from flask_login import login_user
                login_user(user)

                # Stornirati fakturu
                stornirana = faktura_service.storniraj_fakturu(faktura.id, razlog='Test storniranje')
                assert stornirana.status == 'stornirana'

                # Verify KPO entry status updated to 'stornirana'
                db.session.refresh(kpo_entry)
                assert kpo_entry.status_fakture == 'stornirana'

    def test_profaktura_finalization_does_not_create_kpo_entry(self, app):
        """Test profaktura ne kreira KPO entry (AC: 4)."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678', maticni_broj='87654321', naziv='Test Firma',
                adresa='Test', broj='1', postanski_broj='11000',
                mesto='Beograd', drzava='Srbija', telefon='011123456',
                email='test@test.rs', dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id, naziv='Komitent d.o.o.', pib='87654321',
                maticni_broj='12345678', adresa='Adresa 1', broj='1',
                postanski_broj='11000', mesto='Beograd', drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            user = User(
                email='user@test.rs', password_hash='hash',
                full_name='Test User', role='pausalac', firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create profaktura
            profaktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='DRAFT-PRO',
                tip_fakture='profaktura',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('8000.00'),
                status='draft'
            )
            db.session.add(profaktura)
            db.session.commit()

            # Finalize profaktura
            finalized = faktura_service.finalize_faktura(profaktura.id)
            assert finalized.status == 'izdata'
            assert finalized.tip_fakture == 'profaktura'

            # Verify NO KPO entry was created for profaktura
            kpo_entry = KPOEntry.query.filter_by(faktura_id=profaktura.id).first()
            assert kpo_entry is None

    def test_avansna_faktura_creates_kpo_entry(self, app):
        """Test avansna faktura kreira KPO entry (AC: 5)."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678', maticni_broj='87654321', naziv='Test Firma',
                adresa='Test', broj='1', postanski_broj='11000',
                mesto='Beograd', drzava='Srbija', telefon='011123456',
                email='test@test.rs', dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id, naziv='Komitent d.o.o.', pib='87654321',
                maticni_broj='12345678', adresa='Adresa 1', broj='1',
                postanski_broj='11000', mesto='Beograd', drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            user = User(
                email='user@test.rs', password_hash='hash',
                full_name='Test User', role='pausalac', firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create avansna faktura
            avansna = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='DRAFT-AVN',
                tip_fakture='avansna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 10),
                valuta_placanja=15,
                datum_dospeca=date(2025, 1, 25),
                ukupan_iznos_rsd=Decimal('3000.00'),
                status='draft'
            )
            db.session.add(avansna)
            db.session.commit()

            # Finalize avansna faktura
            finalized = faktura_service.finalize_faktura(avansna.id)
            assert finalized.status == 'izdata'
            assert finalized.tip_fakture == 'avansna'

            # Verify KPO entry WAS created for avansna faktura
            kpo_entry = KPOEntry.query.filter_by(faktura_id=avansna.id).first()
            assert kpo_entry is not None
            assert kpo_entry.iznos_rsd == Decimal('3000.00')
            assert kpo_entry.status_fakture == 'izdata'

    def test_kpo_entry_has_correct_data_from_faktura(self, app):
        """Test KPO entry sadrži ispravne podatke iz fakture."""
        with app.app_context():
            firma = PausalnFirma(
                pib='12345678', maticni_broj='87654321', naziv='Test Firma',
                adresa='Test', broj='1', postanski_broj='11000',
                mesto='Beograd', drzava='Srbija', telefon='011123456',
                email='test@test.rs', dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id, naziv='Komitent d.o.o.', pib='87654321',
                maticni_broj='12345678', adresa='Adresa 1', broj='1',
                postanski_broj='11000', mesto='Beograd', drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            user = User(
                email='user@test.rs', password_hash='hash',
                full_name='Test User', role='pausalac', firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='DRAFT-DATA',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 3, 20),
                valuta_placanja=45,
                datum_dospeca=date(2025, 5, 4),
                ukupan_iznos_rsd=Decimal('12500.00'),
                status='draft'
            )
            db.session.add(faktura)
            db.session.commit()

            finalized = faktura_service.finalize_faktura(faktura.id)

            # Verify KPO entry has correct data
            kpo_entry = KPOEntry.query.filter_by(faktura_id=faktura.id).first()
            assert kpo_entry.firma_id == firma.id
            assert kpo_entry.faktura_id == faktura.id
            assert kpo_entry.broj_fakture == finalized.broj_fakture
            assert kpo_entry.datum_prometa == date(2025, 3, 20)
            assert kpo_entry.komitent_naziv == 'Komitent d.o.o.'
            assert kpo_entry.komitent_pib == '87654321'
            assert kpo_entry.iznos_rsd == Decimal('12500.00')
            assert kpo_entry.valuta == 'RSD'
            assert kpo_entry.godina == 2025

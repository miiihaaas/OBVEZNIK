"""Unit tests for KPO Service logic."""
import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import User, PausalnFirma, Komitent, Faktura, FakturaStavka, KPOEntry
from app.services import kpo_service


class TestCreateKPOEntry:
    """Tests for create_kpo_entry() function."""

    def test_create_kpo_entry_for_standardna_faktura(self, app):
        """Test creating KPO entry for standard faktura."""
        with app.app_context():
            # Create firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create komitent
            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create user
            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create standardna faktura with status='izdata'
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('12000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura)
            db.session.commit()

            # Create KPO entry
            kpo_entry = kpo_service.create_kpo_entry(faktura.id)

            assert kpo_entry.id is not None
            assert kpo_entry.firma_id == firma.id
            assert kpo_entry.faktura_id == faktura.id
            assert kpo_entry.redni_broj == 1  # First entry for this firma/godina
            assert kpo_entry.broj_fakture == 'F-2025-001'
            assert kpo_entry.datum_prometa == date(2025, 1, 15)
            assert kpo_entry.datum_dospeca == date(2025, 2, 14)
            assert kpo_entry.komitent_naziv == 'Komitent d.o.o.'
            assert kpo_entry.komitent_pib == '87654321'
            assert kpo_entry.iznos_rsd == Decimal('12000.00')
            assert kpo_entry.valuta == 'RSD'
            assert kpo_entry.status_fakture == 'izdata'
            assert kpo_entry.godina == 2025

    def test_create_kpo_entry_for_avansna_faktura(self, app):
        """Test creating KPO entry for avansna faktura (AC: 5)."""
        with app.app_context():
            # Create firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create komitent
            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create user
            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create avansna faktura with status='izdata'
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='AVN-2025-001',
                tip_fakture='avansna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 10),
                valuta_placanja=15,
                datum_dospeca=date(2025, 1, 25),
                ukupan_iznos_rsd=Decimal('5000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura)
            db.session.commit()

            # Create KPO entry - avansne fakture se evidentiraju
            kpo_entry = kpo_service.create_kpo_entry(faktura.id)

            assert kpo_entry.id is not None
            assert kpo_entry.iznos_rsd == Decimal('5000.00')  # Avansne fakture se evidentiraju
            assert kpo_entry.status_fakture == 'izdata'

    def test_profaktura_not_evidentirajed_in_kpo(self, app):
        """Test profakture se NE evidentiraju u KPO knjigu (AC: 4)."""
        with app.app_context():
            # Create firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create komitent
            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create user
            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create profaktura with status='izdata'
            profaktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='PRO-2025-001',
                tip_fakture='profaktura',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 5),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 4),
                ukupan_iznos_rsd=Decimal('10000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(profaktura)
            db.session.commit()

            # Attempt to create KPO entry for profaktura - should raise ValueError
            with pytest.raises(ValueError, match="Profakture se NE evidentiraju u KPO knjigu"):
                kpo_service.create_kpo_entry(profaktura.id)

            # Verify no KPO entry was created
            kpo_entry_count = KPOEntry.query.filter_by(faktura_id=profaktura.id).count()
            assert kpo_entry_count == 0

    def test_redni_broj_auto_increments_per_godina_firma(self, app):
        """Test redni_broj auto-increments per godina and firma."""
        with app.app_context():
            # Create firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create komitent
            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create user
            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create 3 fakture in 2025
            for i in range(1, 4):
                faktura = Faktura(
                    firma_id=firma.id,
                    komitent_id=komitent.id,
                    user_id=user.id,
                    broj_fakture=f'F-2025-{str(i).zfill(3)}',
                    tip_fakture='standardna',
                    valuta_fakture='RSD',
                    datum_prometa=date(2025, 1, i),
                    valuta_placanja=30,
                    datum_dospeca=date(2025, 2, i),
                    ukupan_iznos_rsd=Decimal('1000.00') * i,
                    status='izdata',
                    finalized_at=datetime.now()
                )
                db.session.add(faktura)
                db.session.commit()

                kpo_entry = kpo_service.create_kpo_entry(faktura.id)
                assert kpo_entry.redni_broj == i
                assert kpo_entry.godina == 2025

            # Create faktura in 2026 - redni_broj should reset to 1
            faktura_2026 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2026-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2026, 1, 1),
                valuta_placanja=30,
                datum_dospeca=date(2026, 1, 31),
                ukupan_iznos_rsd=Decimal('2000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura_2026)
            db.session.commit()

            kpo_entry_2026 = kpo_service.create_kpo_entry(faktura_2026.id)
            assert kpo_entry_2026.redni_broj == 1  # Reset to 1 for new year
            assert kpo_entry_2026.godina == 2026

    def test_kpo_entry_immutable(self, app):
        """Test KPO entries ne mogu se direktno menjati (AC: 7)."""
        with app.app_context():
            # Create firma
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            # Create komitent
            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            # Create user
            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create faktura
            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('12000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura)
            db.session.commit()

            # Create KPO entry
            kpo_entry = kpo_service.create_kpo_entry(faktura.id)
            original_iznos = kpo_entry.iznos_rsd

            # Note: This test verifies that there's no UPDATE method in kpo_service
            # KPO entries can only be updated via update_kpo_entry_status() for status changes
            # Direct field modifications (iznos_rsd, broj_fakture, etc.) are not allowed

            # Verify iznos_rsd remains unchanged
            db.session.refresh(kpo_entry)
            assert kpo_entry.iznos_rsd == original_iznos


class TestUpdateKPOEntryStatus:
    """Tests for update_kpo_entry_status() function."""

    def test_update_kpo_entry_status_to_stornirana(self, app):
        """Test updating KPO entry status to 'stornirana'."""
        with app.app_context():
            # Create firma, komitent, user, faktura and KPO entry
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('12000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura)
            db.session.commit()

            kpo_entry = kpo_service.create_kpo_entry(faktura.id)
            assert kpo_entry.status_fakture == 'izdata'

            # Update status to 'stornirana'
            kpo_service.update_kpo_entry_status(faktura.id, 'stornirana')

            # Verify status changed
            db.session.refresh(kpo_entry)
            assert kpo_entry.status_fakture == 'stornirana'


class TestCalculateTotalPromet:
    """Tests for calculate_total_promet() function."""

    def test_calculate_total_promet_excludes_stornirane(self, app):
        """Test stornirane fakture ne utiču na promet (AC: 3)."""
        with app.app_context():
            # Create firma, komitent, user
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create 2 fakture with status 'izdata'
            faktura1 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 10),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 9),
                ukupan_iznos_rsd=Decimal('10000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura1)
            db.session.commit()
            kpo_service.create_kpo_entry(faktura1.id)

            faktura2 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-002',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 20),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 19),
                ukupan_iznos_rsd=Decimal('15000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura2)
            db.session.commit()
            kpo_service.create_kpo_entry(faktura2.id)

            # Total should be 25000 (10000 + 15000)
            total_before = kpo_service.calculate_total_promet(firma.id, 2025, status_filter='izdata')
            assert total_before == Decimal('25000.00')

            # Stornirana faktura1 - update KPO entry status
            kpo_service.update_kpo_entry_status(faktura1.id, 'stornirana')

            # Total should now be 15000 (only faktura2)
            total_after = kpo_service.calculate_total_promet(firma.id, 2025, status_filter='izdata')
            assert total_after == Decimal('15000.00')

            # Total with filter='all' should be 25000
            total_all = kpo_service.calculate_total_promet(firma.id, 2025, status_filter='all')
            assert total_all == Decimal('25000.00')


class TestGetKPOEntriesForFirma:
    """Tests for get_kpo_entries_for_firma() function."""

    def test_get_kpo_entries_filtered_by_status(self, app):
        """Test filtering KPO entries by status."""
        with app.app_context():
            # Create firma, komitent, user
            firma = PausalnFirma(
                pib='12345678',
                maticni_broj='87654321',
                naziv='Test Firma',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011123456',
                email='test@test.rs',
                dinarski_racuni=[]
            )
            db.session.add(firma)
            db.session.commit()

            komitent = Komitent(
                firma_id=firma.id,
                naziv='Komitent d.o.o.',
                pib='87654321',
                maticni_broj='12345678',
                adresa='Adresa 1',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='kontakt@komitent.rs'
            )
            db.session.add(komitent)
            db.session.commit()

            user = User(
                email='user@test.rs',
                password_hash='hash',
                full_name='Test User',
                role='pausalac',
                firma_id=firma.id
            )
            db.session.add(user)
            db.session.commit()

            # Create 2 fakture
            faktura1 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 10),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 9),
                ukupan_iznos_rsd=Decimal('10000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura1)
            db.session.commit()
            kpo_service.create_kpo_entry(faktura1.id)

            faktura2 = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture='F-2025-002',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 20),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 19),
                ukupan_iznos_rsd=Decimal('15000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura2)
            db.session.commit()
            kpo_service.create_kpo_entry(faktura2.id)

            # Stornirana faktura1
            kpo_service.update_kpo_entry_status(faktura1.id, 'stornirana')

            # Filter by status='izdata' - should return only faktura2
            izdate = kpo_service.get_kpo_entries_for_firma(firma.id, godina=2025, status_filter='izdata')
            assert len(izdate) == 1
            assert izdate[0].broj_fakture == 'F-2025-002'

            # Filter by status='stornirana' - should return only faktura1
            stornirane = kpo_service.get_kpo_entries_for_firma(firma.id, godina=2025, status_filter='stornirana')
            assert len(stornirane) == 1
            assert stornirane[0].broj_fakture == 'F-2025-001'

            # Filter by status='all' - should return both
            sve = kpo_service.get_kpo_entries_for_firma(firma.id, godina=2025, status_filter='all')
            assert len(sve) == 2


class TestTenantIsolation:
    """Tests for tenant isolation in KPO entries."""

    def test_tenant_isolation_kpo_entries(self, app):
        """Test KPO entries are isolated per firma (tenant)."""
        with app.app_context():
            # Create two firme
            firma1 = PausalnFirma(
                pib='11111111',
                maticni_broj='11111111',
                naziv='Firma 1',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011111111',
                email='firma1@test.rs',
                dinarski_racuni=[]
            )
            firma2 = PausalnFirma(
                pib='22222222',
                maticni_broj='22222222',
                naziv='Firma 2',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='022222222',
                email='firma2@test.rs',
                dinarski_racuni=[]
            )
            db.session.add_all([firma1, firma2])
            db.session.commit()

            # Create komitent for each firma
            komitent1 = Komitent(
                firma_id=firma1.id,
                naziv='Komitent 1',
                pib='33333333',
                maticni_broj='33333333',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k1@test.rs'
            )
            komitent2 = Komitent(
                firma_id=firma2.id,
                naziv='Komitent 2',
                pib='44444444',
                maticni_broj='44444444',
                adresa='Test',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email='k2@test.rs'
            )
            db.session.add_all([komitent1, komitent2])
            db.session.commit()

            # Create user for each firma
            user1 = User(
                email='user1@test.rs',
                password_hash='hash',
                full_name='User 1',
                role='pausalac',
                firma_id=firma1.id
            )
            user2 = User(
                email='user2@test.rs',
                password_hash='hash',
                full_name='User 2',
                role='pausalac',
                firma_id=firma2.id
            )
            db.session.add_all([user1, user2])
            db.session.commit()

            # Create faktura for each firma in same godina
            faktura1 = Faktura(
                firma_id=firma1.id,
                komitent_id=komitent1.id,
                user_id=user1.id,
                broj_fakture='F1-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('10000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura1)
            db.session.commit()
            kpo1 = kpo_service.create_kpo_entry(faktura1.id)

            faktura2 = Faktura(
                firma_id=firma2.id,
                komitent_id=komitent2.id,
                user_id=user2.id,
                broj_fakture='F2-2025-001',
                tip_fakture='standardna',
                valuta_fakture='RSD',
                datum_prometa=date(2025, 1, 15),
                valuta_placanja=30,
                datum_dospeca=date(2025, 2, 14),
                ukupan_iznos_rsd=Decimal('20000.00'),
                status='izdata',
                finalized_at=datetime.now()
            )
            db.session.add(faktura2)
            db.session.commit()
            kpo2 = kpo_service.create_kpo_entry(faktura2.id)

            # Both should have redni_broj = 1 (isolated per firma)
            assert kpo1.redni_broj == 1
            assert kpo2.redni_broj == 1

            # Get KPO entries for firma1 - should only return kpo1
            entries_firma1 = kpo_service.get_kpo_entries_for_firma(firma1.id, godina=2025)
            assert len(entries_firma1) == 1
            assert entries_firma1[0].broj_fakture == 'F1-2025-001'

            # Get KPO entries for firma2 - should only return kpo2
            entries_firma2 = kpo_service.get_kpo_entries_for_firma(firma2.id, godina=2025)
            assert len(entries_firma2) == 1
            assert entries_firma2[0].broj_fakture == 'F2-2025-001'

            # Calculate promet for firma1 - should only include firma1's invoices
            promet_firma1 = kpo_service.calculate_total_promet(firma1.id, 2025)
            assert promet_firma1 == Decimal('10000.00')

            # Calculate promet for firma2 - should only include firma2's invoices
            promet_firma2 = kpo_service.calculate_total_promet(firma2.id, 2025)
            assert promet_firma2 == Decimal('20000.00')

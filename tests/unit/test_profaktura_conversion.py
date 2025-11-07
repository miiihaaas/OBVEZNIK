"""Unit tests for Profaktura Conversion."""
import pytest
from datetime import date
from decimal import Decimal

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.services.faktura_service import (
    create_faktura,
    finalize_faktura,
    convert_profaktura_to_faktura
)


@pytest.fixture
def pausalac_with_firma(app):
    """Create a test pausalac user with firma."""
    with app.app_context():
        firma = PausalnFirma(
            pib='123456789',
            maticni_broj='12345678',
            naziv='Test Firma',
            adresa='Test Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011111111',
            email='firma@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '123-456789-00'}],
            prefiks_fakture='TF-',
            sufiks_fakture='/2025',
            brojac_fakture=1,
            brojac_profakture=1
        )
        db.session.add(firma)
        db.session.commit()

        user = User(
            email='pausalac@test.com',
            full_name='Test Pausalac',
            role='pausalac',
            firma_id=firma.id
        )
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        yield user, firma


@pytest.fixture
def komitent(pausalac_with_firma):
    """Create a test komitent for the pausalac's firma."""
    user, firma = pausalac_with_firma
    komitent = Komitent(
        firma_id=firma.id,
        pib='87654321',
        maticni_broj='12345678',
        naziv='Test Komitent',
        adresa='Komitent Adresa',
        broj='2',
        postanski_broj='11000',
        mesto='Beograd',
        drzava='Srbija',
        email='komitent@test.rs'
    )
    db.session.add(komitent)
    db.session.commit()
    return komitent


class TestConvertProfakturaToFaktura:
    """Tests for converting profaktura to standard faktura."""

    def test_convert_profaktura_to_faktura_success(self, pausalac_with_firma, komitent):
        """Test successful conversion of profaktura to faktura."""
        user, firma = pausalac_with_firma

        # 1. Create and finalize profaktura
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga 1', 'kolicina': 2, 'jedinica_mere': 'h', 'cena': Decimal('100.00')},
                {'naziv': 'Usluga 2', 'kolicina': 1, 'jedinica_mere': 'kom', 'cena': Decimal('50.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        # 2. Convert profaktura
        nova_faktura = convert_profaktura_to_faktura(profaktura.id)

        # 3. Assertions
        assert nova_faktura.tip_fakture == 'standardna'
        assert nova_faktura.status == 'draft'
        assert nova_faktura.komitent_id == profaktura.komitent_id
        assert nova_faktura.datum_prometa == date.today()
        assert nova_faktura.ukupan_iznos_rsd == Decimal('250.00')
        assert len(nova_faktura.stavke) == 2
        assert 'PRO' not in nova_faktura.broj_fakture  # Not profaktura broj
        assert 'DRAFT' in nova_faktura.broj_fakture  # Draft status

    def test_convert_profaktura_copies_all_data(self, pausalac_with_firma, komitent):
        """Test that all profaktura data is copied correctly."""
        user, firma = pausalac_with_firma

        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 10),
            'valuta_placanja': 14,
            'broj_ugovora': 'UG-123',
            'broj_odluke': 'OD-456',
            'broj_narudzbenice': 'NAR-789',
            'poziv_na_broj': '12345',
            'model': '97',
            'stavke': [
                {'naziv': 'Proizvod A', 'kolicina': 5, 'jedinica_mere': 'kom', 'cena': Decimal('200.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        nova_faktura = convert_profaktura_to_faktura(profaktura.id)

        # Check all optional fields are copied
        assert nova_faktura.broj_ugovora == 'UG-123'
        assert nova_faktura.broj_odluke == 'OD-456'
        assert nova_faktura.broj_narudzbenice == 'NAR-789'
        assert nova_faktura.poziv_na_broj == '12345'
        assert nova_faktura.model == '97'
        assert nova_faktura.valuta_placanja == 14
        assert nova_faktura.komitent_id == komitent.id

    def test_convert_profaktura_creates_new_broj_fakture(self, pausalac_with_firma, komitent):
        """Test that new faktura gets standard brojac, not profaktura brojac."""
        user, firma = pausalac_with_firma

        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        nova_faktura = convert_profaktura_to_faktura(profaktura.id)

        # New faktura should NOT have 'PRO' in broj (draft for now)
        assert 'PRO' not in nova_faktura.broj_fakture
        assert 'DRAFT' in nova_faktura.broj_fakture

    def test_convert_profaktura_updates_datum_prometa(self, pausalac_with_firma, komitent):
        """Test that new faktura has today's datum_prometa, not profaktura's date."""
        user, firma = pausalac_with_firma

        # Profaktura with old date
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2024, 12, 1),  # Old date
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        nova_faktura = convert_profaktura_to_faktura(profaktura.id)

        # New faktura should have today's date
        assert nova_faktura.datum_prometa == date.today()
        assert nova_faktura.datum_prometa != profaktura.datum_prometa

    def test_convert_profaktura_links_bidirectionally(self, pausalac_with_firma, komitent):
        """Test bidirectional linking between profaktura and faktura."""
        user, firma = pausalac_with_firma

        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        nova_faktura = convert_profaktura_to_faktura(profaktura.id)

        # Refresh profaktura from DB
        db.session.refresh(profaktura)

        # Check bidirectional linking
        assert profaktura.konvertovana_u_fakturu_id == nova_faktura.id
        assert nova_faktura.konvertovana_iz_profakture_id == profaktura.id

    def test_convert_profaktura_changes_status_to_konvertovana(self, pausalac_with_firma, komitent):
        """Test that profaktura status changes to 'konvertovana'."""
        user, firma = pausalac_with_firma

        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        assert profaktura.status == 'izdata'

        convert_profaktura_to_faktura(profaktura.id)

        # Refresh profaktura from DB
        db.session.refresh(profaktura)

        assert profaktura.status == 'konvertovana'

    def test_convert_profaktura_new_faktura_is_draft(self, pausalac_with_firma, komitent):
        """Test that new faktura is created as draft."""
        user, firma = pausalac_with_firma

        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        nova_faktura = convert_profaktura_to_faktura(profaktura.id)

        assert nova_faktura.status == 'draft'

    def test_convert_profaktura_copies_all_stavke(self, pausalac_with_firma, komitent):
        """Test that all stavke are copied with correct data."""
        user, firma = pausalac_with_firma

        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga 1', 'kolicina': 2, 'jedinica_mere': 'h', 'cena': Decimal('100.00')},
                {'naziv': 'Usluga 2', 'kolicina': 5, 'jedinica_mere': 'kom', 'cena': Decimal('50.00')},
                {'naziv': 'Usluga 3', 'kolicina': 1, 'jedinica_mere': 'dan', 'cena': Decimal('300.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        nova_faktura = convert_profaktura_to_faktura(profaktura.id)

        # Check all stavke copied
        assert len(nova_faktura.stavke) == 3

        # Check stavka details
        stavke_sorted = sorted(nova_faktura.stavke, key=lambda s: s.redni_broj)
        assert stavke_sorted[0].naziv == 'Usluga 1'
        assert stavke_sorted[0].kolicina == Decimal('2')
        assert stavke_sorted[0].cena == Decimal('100.00')
        assert stavke_sorted[0].ukupno == Decimal('200.00')

    def test_convert_profaktura_validates_tip_fakture(self, pausalac_with_firma, komitent):
        """Test error if trying to convert non-profaktura."""
        user, firma = pausalac_with_firma

        # Create standard faktura (not profaktura)
        faktura_data = {
            'tip_fakture': 'standardna',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        faktura = create_faktura(faktura_data, user)
        finalize_faktura(faktura.id)

        # Try to convert - should raise error
        with pytest.raises(ValueError, match="Samo profakture mogu biti konvertovane"):
            convert_profaktura_to_faktura(faktura.id)

    def test_convert_profaktura_validates_status_izdata(self, pausalac_with_firma, komitent):
        """Test error if trying to convert draft profaktura."""
        user, firma = pausalac_with_firma

        # Create profaktura but DON'T finalize it (keep as draft)
        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        # Do NOT finalize - keep as draft

        # Try to convert - should raise error
        with pytest.raises(ValueError, match="Samo izdate profakture mogu biti konvertovane"):
            convert_profaktura_to_faktura(profaktura.id)

    def test_convert_profaktura_prevents_duplicate_conversion(self, pausalac_with_firma, komitent):
        """Test error if trying to convert already converted profaktura."""
        user, firma = pausalac_with_firma

        profaktura_data = {
            'tip_fakture': 'profaktura',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 1, 15),
            'valuta_placanja': 7,
            'stavke': [
                {'naziv': 'Usluga', 'kolicina': 1, 'jedinica_mere': 'h', 'cena': Decimal('100.00')}
            ]
        }

        profaktura = create_faktura(profaktura_data, user)
        finalize_faktura(profaktura.id)

        # First conversion - should work
        convert_profaktura_to_faktura(profaktura.id)

        # Second conversion attempt - should raise error
        with pytest.raises(ValueError, match="Profaktura je već konvertovana"):
            convert_profaktura_to_faktura(profaktura.id)

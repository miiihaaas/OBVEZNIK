"""Integration tests for Profaktura flow (Story 4.1)."""
import pytest
from datetime import date
from decimal import Decimal
from app import db
from app.models.faktura import Faktura
from app.models.komitent import Komitent
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.services.faktura_service import create_faktura, finalize_faktura
from flask_login import login_user


@pytest.fixture
def pausalac_user_with_firma(app):
    """Create pausalac user with firma for testing profaktura."""
    # Create firma
    firma = PausalnFirma(
        pib='12345678',
        maticni_broj='87654321',
        naziv='Test Firma',
        adresa='Test Adresa',
        broj='1',
        postanski_broj='11000',
        mesto='Beograd',
        telefon='011234567',
        email='test@firma.rs',
        dinarski_racuni=[{'banka': 'Test Banka', 'broj': '123-456789-10'}],
        prefiks_fakture='MK-',
        sufiks_fakture='/2025-PS',
        brojac_fakture=1,
        brojac_profakture=1
    )
    db.session.add(firma)
    db.session.flush()

    # Create pausalac user
    user = User(
        email='pausalac@test.com',
        full_name='Test Pausalac',
        role='pausalac',
        firma_id=firma.id
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    return user, firma


@pytest.fixture
def komitent(pausalac_user_with_firma):
    """Create komitent for testing."""
    user, firma = pausalac_user_with_firma

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


class TestProfakturaFlow:
    """Integration tests for profaktura creation, finalization, and validation (AC 1-10)."""

    def test_pausalac_can_create_domestic_profaktura(self, client, pausalac_user_with_firma, komitent):
        """Test that pausalac can create domestic profaktura in RSD (AC 1, 2, 3)."""
        user, firma = pausalac_user_with_firma

        # Set brojac
        firma.prefiks_fakture = 'MK-'
        firma.sufiks_fakture = '/2025-PS'
        firma.brojac_profakture = 1
        db.session.commit()

        # Create profaktura
        data = {
            'tip_fakture': 'profaktura',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Konsultantske usluge',
                    'kolicina': Decimal('10.00'),
                    'jedinica_mere': 'h',
                    'cena': Decimal('5000.00')
                }
            ]
        }

        profaktura = create_faktura(data, user)

        assert profaktura.tip_fakture == 'profaktura'
        assert profaktura.valuta_fakture == 'RSD'
        assert profaktura.status == 'draft'
        assert profaktura.broj_fakture == f'DRAFT-{profaktura.id}'
        assert profaktura.ukupan_iznos_rsd == Decimal('50000.00')
        assert 'PRO' not in profaktura.broj_fakture  # Draft doesn't have final number yet

    def test_finalize_profaktura_increments_brojac_profakture(self, client, pausalac_user_with_firma, komitent):
        """Test that finalizing profaktura increments brojac_profakture (AC 2, 4)."""
        user, firma = pausalac_user_with_firma

        # Set initial brojaci
        firma.prefiks_fakture = 'MK-'
        firma.sufiks_fakture = '/2025-PS'
        firma.brojac_profakture = 5
        db.session.commit()

        # Create profaktura
        data = {
            'tip_fakture': 'profaktura',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1.00'), 'jedinica_mere': 'h', 'cena': Decimal('100.00')}]
        }
        profaktura = create_faktura(data, user)

        # Finalize
        finalized = finalize_faktura(profaktura.id)

        # Reload firma
        db.session.refresh(firma)

        # Profaktura brojac should be incremented to 6
        assert firma.brojac_profakture == 6
        assert finalized.status == 'izdata'
        assert 'PRO' in finalized.broj_fakture
        assert finalized.broj_fakture == 'MK-PRO0005/2025-PS'

    def test_profaktura_and_standardna_have_separate_counters(self, client, pausalac_user_with_firma, komitent):
        """Test that profakture and standardne fakture have independent counters (AC 2)."""
        user, firma = pausalac_user_with_firma

        # Set initial brojaci
        firma.prefiks_fakture = 'MK-'
        firma.sufiks_fakture = '/2025'
        firma.brojac_fakture = 10
        firma.brojac_profakture = 5
        db.session.commit()

        # Create and finalize standardna faktura
        data_std = {
            'tip_fakture': 'standardna',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1.00'), 'jedinica_mere': 'h', 'cena': Decimal('100.00')}]
        }
        std = create_faktura(data_std, user)
        finalize_faktura(std.id)

        db.session.refresh(firma)
        assert firma.brojac_fakture == 11
        assert firma.brojac_profakture == 5  # Should NOT change

        # Create and finalize profaktura
        data_pro = {
            'tip_fakture': 'profaktura',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1.00'), 'jedinica_mere': 'h', 'cena': Decimal('100.00')}]
        }
        pro = create_faktura(data_pro, user)
        finalize_faktura(pro.id)

        db.session.refresh(firma)
        assert firma.brojac_fakture == 11  # Should NOT change
        assert firma.brojac_profakture == 6  # Should increment

    def test_profaktura_pdf_template_selection(self, client, pausalac_user_with_firma, komitent):
        """Test that profaktura uses correct PDF template (AC 5)."""
        user, firma = pausalac_user_with_firma

        # Create profaktura
        firma.brojac_profakture = 1
        db.session.commit()

        data = {
            'tip_fakture': 'profaktura',
            'komitent_id': komitent.id,
            'datum_prometa': date.today(),
            'valuta_placanja': 7,
            'stavke': [{'naziv': 'Usluga', 'kolicina': Decimal('1.00'), 'jedinica_mere': 'h', 'cena': Decimal('100.00')}]
        }
        profaktura = create_faktura(data, user)
        finalized = finalize_faktura(profaktura.id)

        # Verify template selection
        from app.services.pdf_service import get_template
        template = get_template(finalized)

        assert template == 'pdf/profaktura_sr.html'
        assert finalized.jezik == 'sr'

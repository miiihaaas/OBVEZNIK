"""Integration tests for storniranje (cancelling) fakture (Story 4.5)."""
import pytest
from datetime import date
from decimal import Decimal
from flask import url_for
from app import create_app, db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura
from app.services.faktura_service import create_faktura, finalize_faktura


@pytest.fixture
def app():
    """Create test app with test config."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def pausalac_with_firma(app):
    """Create pausalac user with firma for testing."""
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
            brojac_fakture=1
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

        return user, firma


@pytest.fixture
def admin_user(app):
    """Create admin user for testing."""
    with app.app_context():
        user = User(email='admin@test.com', full_name='Admin Test', role='admin')
        user.set_password('admin123')
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def komitent(pausalac_with_firma):
    """Create test komitent for the pausalac's firma."""
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


def login_user(client, email, password):
    """Helper function to login a user."""
    return client.post('/login', data={
        'email': email,
        'password': password
    }, follow_redirects=True)


def test_pausalac_can_stornirati_own_faktura(client, pausalac_with_firma, komitent, app):
    """Test that pausalac can stornirati their own issued faktura."""
    user, firma = pausalac_with_firma

    with app.app_context():
        # Login as pausalac
        login_user(client, 'pausalac@test.com', 'password123')

        # Create and finalize faktura
        faktura_data = {
            'tip_fakture': 'standardna',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 9),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Usluga 1',
                    'kolicina': Decimal('1.00'),
                    'jedinica_mere': 'kom',
                    'cena': Decimal('100.00')
                }
            ]
        }

        faktura = create_faktura(faktura_data, user)
        finalize_faktura(faktura.id)
        db.session.commit()

        faktura_id = faktura.id

    # Stornirati fakturu preko POST request
    response = client.post(
        f'/fakture/{faktura_id}/storniraj',
        data={'razlog': 'Greška u unosu'},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert 'uspešno stornirana' in response.data.decode('utf-8')

    # Verify status changed
    with app.app_context():
        faktura = db.session.get(Faktura, faktura_id)
        assert faktura.status == 'stornirana'


def test_admin_can_stornirati_any_faktura(client, admin_user, pausalac_with_firma, komitent, app):
    """Test that admin can stornirati any faktura (god mode)."""
    user, firma = pausalac_with_firma

    with app.app_context():
        # Create and finalize faktura as pausalac
        faktura_data = {
            'tip_fakture': 'standardna',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 9),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Usluga 1',
                    'kolicina': Decimal('1.00'),
                    'jedinica_mere': 'kom',
                    'cena': Decimal('100.00')
                }
            ]
        }

        faktura = create_faktura(faktura_data, user)
        finalize_faktura(faktura.id)
        db.session.commit()

        faktura_id = faktura.id

    # Login as admin and stornirati
    login_user(client, 'admin@test.com', 'admin123')

    response = client.post(
        f'/fakture/{faktura_id}/storniraj',
        data={'razlog': 'Admin correction'},
        follow_redirects=True
    )

    assert response.status_code == 200
    assert 'uspešno stornirana' in response.data.decode('utf-8')

    # Verify status changed
    with app.app_context():
        faktura = db.session.get(Faktura, faktura_id)
        assert faktura.status == 'stornirana'


def test_pausalac_cannot_stornirati_other_firma_faktura(client, app):
    """Test tenant isolation - pausalac cannot stornirati faktura from another firma."""
    with app.app_context():
        # Create first firma and user
        firma1 = PausalnFirma(
            pib='111111111',
            maticni_broj='11111111',
            naziv='Firma 1',
            adresa='Adresa 1',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='011111111',
            email='firma1@test.com',
            dinarski_racuni=[{'banka': 'Banka 1', 'racun': '111-111111-11'}],
            prefiks_fakture='F1-',
            sufiks_fakture='/2025',
            brojac_fakture=1
        )
        db.session.add(firma1)
        db.session.commit()

        user1 = User(
            email='user1@test.com',
            full_name='User 1',
            role='pausalac',
            firma_id=firma1.id
        )
        user1.set_password('password123')
        db.session.add(user1)
        db.session.commit()

        # Create second firma and user
        firma2 = PausalnFirma(
            pib='222222222',
            maticni_broj='22222222',
            naziv='Firma 2',
            adresa='Adresa 2',
            broj='2',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon='022222222',
            email='firma2@test.com',
            dinarski_racuni=[{'banka': 'Banka 2', 'racun': '222-222222-22'}],
            prefiks_fakture='F2-',
            sufiks_fakture='/2025',
            brojac_fakture=1
        )
        db.session.add(firma2)
        db.session.commit()

        user2 = User(
            email='user2@test.com',
            full_name='User 2',
            role='pausalac',
            firma_id=firma2.id
        )
        user2.set_password('password123')
        db.session.add(user2)
        db.session.commit()

        # Create komitent for firma2
        komitent2 = Komitent(
            firma_id=firma2.id,
            pib='33333333',
            maticni_broj='33333333',
            naziv='Komitent 2',
            adresa='Adresa',
            broj='3',
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            email='komitent2@test.rs'
        )
        db.session.add(komitent2)
        db.session.commit()

        # Create and finalize faktura for firma2
        faktura_data = {
            'tip_fakture': 'standardna',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent2.id,
            'datum_prometa': date(2025, 11, 9),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Usluga',
                    'kolicina': Decimal('1.00'),
                    'jedinica_mere': 'kom',
                    'cena': Decimal('100.00')
                }
            ]
        }

        faktura = create_faktura(faktura_data, user2)
        finalize_faktura(faktura.id)
        db.session.commit()

        faktura_id = faktura.id

    # Login as user1 and attempt to stornirati user2's faktura
    login_user(client, 'user1@test.com', 'password123')

    response = client.post(
        f'/fakture/{faktura_id}/storniraj',
        data={'razlog': 'Should fail'},
        follow_redirects=True
    )

    # Should get error due to tenant isolation (404 or error message)
    assert response.status_code == 404 or 'Greška' in response.data.decode('utf-8')


def test_pausalac_cannot_stornirati_faktura_created_by_other_user(client, pausalac_with_firma, komitent, app):
    """Test authorization - pausalac cannot stornirati faktura created by another user in same firma."""
    user, firma = pausalac_with_firma

    with app.app_context():
        # Create second user in SAME firma
        user2 = User(
            email='user2@test.com',
            full_name='User 2',
            role='pausalac',
            firma_id=firma.id
        )
        user2.set_password('password123')
        db.session.add(user2)
        db.session.commit()

        # Create and finalize faktura as first user
        faktura_data = {
            'tip_fakture': 'standardna',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 9),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Usluga',
                    'kolicina': Decimal('1.00'),
                    'jedinica_mere': 'kom',
                    'cena': Decimal('100.00')
                }
            ]
        }

        faktura = create_faktura(faktura_data, user)
        finalize_faktura(faktura.id)
        db.session.commit()

        faktura_id = faktura.id

    # Login as user2 and attempt to stornirati user1's faktura
    login_user(client, 'user2@test.com', 'password123')

    response = client.post(
        f'/fakture/{faktura_id}/storniraj',
        data={'razlog': 'Should fail'},
        follow_redirects=True
    )

    # Should get permission error
    assert 'Greška' in response.data.decode('utf-8')


def test_cannot_stornirati_draft_faktura(client, pausalac_with_firma, komitent, app):
    """Test that draft fakture cannot be stornirana."""
    user, firma = pausalac_with_firma

    with app.app_context():
        # Login as pausalac
        login_user(client, 'pausalac@test.com', 'password123')

        # Create draft faktura (not finalized)
        faktura_data = {
            'tip_fakture': 'standardna',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 9),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Usluga 1',
                    'kolicina': Decimal('1.00'),
                    'jedinica_mere': 'kom',
                    'cena': Decimal('100.00')
                }
            ]
        }

        faktura = create_faktura(faktura_data, user)
        db.session.commit()

        faktura_id = faktura.id

    # Attempt to stornirati draft faktura
    response = client.post(
        f'/fakture/{faktura_id}/storniraj',
        data={'razlog': 'Should fail'},
        follow_redirects=True
    )

    # Should get error message
    assert 'Greška' in response.data.decode('utf-8')
    assert 'Samo izdate fakture' in response.data.decode('utf-8')


def test_storniraj_redirects_to_lista(client, pausalac_with_firma, komitent, app):
    """Test that successful storniranje redirects to lista."""
    user, firma = pausalac_with_firma

    with app.app_context():
        # Login as pausalac
        login_user(client, 'pausalac@test.com', 'password123')

        # Create and finalize faktura
        faktura_data = {
            'tip_fakture': 'standardna',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 9),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Usluga 1',
                    'kolicina': Decimal('1.00'),
                    'jedinica_mere': 'kom',
                    'cena': Decimal('100.00')
                }
            ]
        }

        faktura = create_faktura(faktura_data, user)
        finalize_faktura(faktura.id)
        db.session.commit()

        faktura_id = faktura.id

    # Stornirati fakturu
    response = client.post(
        f'/fakture/{faktura_id}/storniraj',
        data={'razlog': 'Test'},
        follow_redirects=False
    )

    # Should redirect to lista
    assert response.status_code == 302
    assert '/fakture' in response.location


def test_storniraj_shows_success_message(client, pausalac_with_firma, komitent, app):
    """Test that storniranje shows success flash message."""
    user, firma = pausalac_with_firma

    with app.app_context():
        # Login as pausalac
        login_user(client, 'pausalac@test.com', 'password123')

        # Create and finalize faktura
        faktura_data = {
            'tip_fakture': 'standardna',
            'valuta_fakture': 'RSD',
            'komitent_id': komitent.id,
            'datum_prometa': date(2025, 11, 9),
            'valuta_placanja': 7,
            'stavke': [
                {
                    'naziv': 'Usluga 1',
                    'kolicina': Decimal('1.00'),
                    'jedinica_mere': 'kom',
                    'cena': Decimal('100.00')
                }
            ]
        }

        faktura = create_faktura(faktura_data, user)
        finalize_faktura(faktura.id)
        db.session.commit()

        faktura_id = faktura.id

    # Stornirati fakturu
    response = client.post(
        f'/fakture/{faktura_id}/storniraj',
        data={'razlog': 'Test reason'},
        follow_redirects=True
    )

    # Should show success message
    assert response.status_code == 200
    assert 'uspešno stornirana' in response.data.decode('utf-8')

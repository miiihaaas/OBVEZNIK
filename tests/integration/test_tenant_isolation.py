"""Integration tests for tenant isolation and role-based access control."""
import pytest
from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.faktura import Faktura
from app.models.komitent import Komitent
from app.models.artikal import Artikal
from datetime import datetime, timezone, timedelta


@pytest.fixture
def setup_two_firmas_with_data(app):
    """
    Setup fixture: Create 2 pausaln firmas with users and data.

    Returns:
        dict with firma1, firma2, admin, pausalac1, pausalac2, fakture, komitenti, artikli
    """
    with app.app_context():
        # Create two pausaln firmas
        firma1 = PausalnFirma(
            pib='111111111',
            naziv='Firma 1',
            adresa='Adresa 1',
            broj='1',
            mesto='Beograd',
            postanski_broj='11000',
            maticni_broj='11111111',
            telefon='011111111',
            email='firma1@test.rs',
            dinarski_racuni=[{'racun': '111-111-111', 'banka': 'Banka 1'}]
        )
        firma2 = PausalnFirma(
            pib='222222222',
            naziv='Firma 2',
            adresa='Adresa 2',
            broj='2',
            mesto='Novi Sad',
            postanski_broj='21000',
            maticni_broj='22222222',
            telefon='021222222',
            email='firma2@test.rs',
            dinarski_racuni=[{'racun': '222-222-222', 'banka': 'Banka 2'}]
        )
        db.session.add_all([firma1, firma2])
        db.session.commit()

        # Create admin user
        admin = User(
            email='admin@test.com',
            full_name='Admin User',
            role='admin',
            firma_id=None
        )
        admin.set_password('admin123')

        # Create pausalac user for firma1
        pausalac1 = User(
            email='pausalac1@test.com',
            full_name='Pausalac 1',
            role='pausalac',
            firma_id=firma1.id
        )
        pausalac1.set_password('pausalac123')

        # Create pausalac user for firma2
        pausalac2 = User(
            email='pausalac2@test.com',
            full_name='Pausalac 2',
            role='pausalac',
            firma_id=firma2.id
        )
        pausalac2.set_password('pausalac123')

        db.session.add_all([admin, pausalac1, pausalac2])
        db.session.commit()

        # Create komitenti for both firmas
        komitent1 = Komitent(
            firma_id=firma1.id,
            pib='333333333',
            maticni_broj='33333333',
            naziv='Komitent Firma 1',
            adresa='Komitent Adresa 1',
            broj='10',
            mesto='Beograd',
            postanski_broj='11000',
            drzava='Srbija',
            email='komitent1@test.rs'
        )
        komitent2 = Komitent(
            firma_id=firma2.id,
            pib='444444444',
            maticni_broj='44444444',
            naziv='Komitent Firma 2',
            adresa='Komitent Adresa 2',
            broj='20',
            mesto='Novi Sad',
            postanski_broj='21000',
            drzava='Srbija',
            email='komitent2@test.rs'
        )
        db.session.add_all([komitent1, komitent2])
        db.session.commit()

        # Create artikli for both firmas
        artikal1 = Artikal(
            firma_id=firma1.id,
            naziv='Artikal Firma 1',
            jedinica_mere='kom',
            podrazumevana_cena=100.00
        )
        artikal2 = Artikal(
            firma_id=firma2.id,
            naziv='Artikal Firma 2',
            jedinica_mere='kom',
            podrazumevana_cena=200.00
        )
        db.session.add_all([artikal1, artikal2])
        db.session.commit()

        # Create fakture for both firmas
        faktura1 = Faktura(
            firma_id=firma1.id,
            user_id=pausalac1.id,
            komitent_id=komitent1.id,
            broj_fakture='F1-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=datetime.now(timezone.utc).date(),
            valuta_placanja=15,
            datum_dospeca=datetime.now(timezone.utc).date() + timedelta(days=15),
            status='izdata',
            ukupan_iznos_rsd=100.00
        )
        faktura2 = Faktura(
            firma_id=firma2.id,
            user_id=pausalac2.id,
            komitent_id=komitent2.id,
            broj_fakture='F2-001',
            tip_fakture='standardna',
            valuta_fakture='RSD',
            datum_prometa=datetime.now(timezone.utc).date(),
            valuta_placanja=15,
            datum_dospeca=datetime.now(timezone.utc).date() + timedelta(days=15),
            status='izdata',
            ukupan_iznos_rsd=200.00
        )
        db.session.add_all([faktura1, faktura2])
        db.session.commit()

        yield {
            'firma1': firma1,
            'firma2': firma2,
            'admin': admin,
            'pausalac1': pausalac1,
            'pausalac2': pausalac2,
            'komitent1': komitent1,
            'komitent2': komitent2,
            'artikal1': artikal1,
            'artikal2': artikal2,
            'faktura1': faktura1,
            'faktura2': faktura2
        }


def test_pausalac_sees_only_own_fakture(client, app, setup_two_firmas_with_data):
    """Test that pausalac user can only see fakture from their own firma."""
    data = setup_two_firmas_with_data

    # Login as pausalac1
    response = client.post('/login', data={
        'email': 'pausalac1@test.com',
        'password': 'pausalac123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Query fakture with tenant isolation
    with app.app_context():
        from flask_login import login_user, current_user
        from app.utils.query_helpers import filter_by_firma

        # Manually login for query test
        pausalac1 = User.query.filter_by(email='pausalac1@test.com').first()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(pausalac1.id)

        with app.test_request_context():
            login_user(pausalac1)

            # Apply tenant isolation filter
            fakture = filter_by_firma(Faktura.query).all()

            # Pausalac1 should only see fakture from firma1
            assert len(fakture) == 1
            assert fakture[0].broj_fakture == 'F1-001'
            assert fakture[0].firma_id == data['firma1'].id


def test_admin_sees_all_fakture(client, app, setup_two_firmas_with_data):
    """Test that admin user can see fakture from all firmas."""
    data = setup_two_firmas_with_data

    # Login as admin
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Query fakture with tenant isolation
    with app.app_context():
        from flask_login import login_user
        from app.utils.query_helpers import filter_by_firma

        # Manually login for query test
        admin = User.query.filter_by(email='admin@test.com').first()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)

        with app.test_request_context():
            login_user(admin)

            # Apply tenant isolation filter
            fakture = filter_by_firma(Faktura.query).all()

            # Admin should see all fakture from both firmas
            assert len(fakture) == 2
            faktura_brojevi = [f.broj_fakture for f in fakture]
            assert 'F1-001' in faktura_brojevi
            assert 'F2-001' in faktura_brojevi


def test_pausalac_sees_only_own_komitenti(client, app, setup_two_firmas_with_data):
    """Test that pausalac user can only see komitenti from their own firma."""
    data = setup_two_firmas_with_data

    # Login as pausalac1
    response = client.post('/login', data={
        'email': 'pausalac1@test.com',
        'password': 'pausalac123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Query komitenti with tenant isolation
    with app.app_context():
        from flask_login import login_user
        from app.utils.query_helpers import filter_by_firma

        # Manually login for query test
        pausalac1 = User.query.filter_by(email='pausalac1@test.com').first()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(pausalac1.id)

        with app.test_request_context():
            login_user(pausalac1)

            # Apply tenant isolation filter
            komitenti = filter_by_firma(Komitent.query).all()

            # Pausalac1 should only see komitenti from firma1
            assert len(komitenti) == 1
            assert komitenti[0].naziv == 'Komitent Firma 1'
            assert komitenti[0].firma_id == data['firma1'].id


def test_admin_sees_all_komitenti(client, app, setup_two_firmas_with_data):
    """Test that admin user can see komitenti from all firmas."""
    data = setup_two_firmas_with_data

    # Login as admin
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'admin123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Query komitenti with tenant isolation
    with app.app_context():
        from flask_login import login_user
        from app.utils.query_helpers import filter_by_firma

        # Manually login for query test
        admin = User.query.filter_by(email='admin@test.com').first()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)

        with app.test_request_context():
            login_user(admin)

            # Apply tenant isolation filter
            komitenti = filter_by_firma(Komitent.query).all()

            # Admin should see all komitenti from both firmas
            assert len(komitenti) == 2
            komitent_nazivi = [k.naziv for k in komitenti]
            assert 'Komitent Firma 1' in komitent_nazivi
            assert 'Komitent Firma 2' in komitent_nazivi


def test_pausalac_sees_only_own_artikli(client, app, setup_two_firmas_with_data):
    """Test that pausalac user can only see artikli from their own firma."""
    data = setup_two_firmas_with_data

    # Login as pausalac1
    response = client.post('/login', data={
        'email': 'pausalac1@test.com',
        'password': 'pausalac123'
    }, follow_redirects=True)
    assert response.status_code == 200

    # Query artikli with tenant isolation
    with app.app_context():
        from flask_login import login_user
        from app.utils.query_helpers import filter_by_firma

        # Manually login for query test
        pausalac1 = User.query.filter_by(email='pausalac1@test.com').first()

        with client.session_transaction() as sess:
            sess['_user_id'] = str(pausalac1.id)

        with app.test_request_context():
            login_user(pausalac1)

            # Apply tenant isolation filter
            artikli = filter_by_firma(Artikal.query).all()

            # Pausalac1 should only see artikli from firma1
            assert len(artikli) == 1
            assert artikli[0].naziv == 'Artikal Firma 1'
            assert artikli[0].firma_id == data['firma1'].id


def test_admin_sees_all_artikli(app, setup_two_firmas_with_data):
    """Test that admin user can see artikli from all firmas."""
    data = setup_two_firmas_with_data

    # Query artikli with tenant isolation (no HTTP client needed)
    with app.app_context():
        from flask_login import login_user
        from app.utils.query_helpers import filter_by_firma

        # Get admin user
        admin = User.query.filter_by(email='admin@test.com').first()

        with app.test_request_context():
            login_user(admin)

            # Apply tenant isolation filter
            artikli = filter_by_firma(Artikal.query).all()

            # Admin should see all artikli from both firmas
            assert len(artikli) == 2
            artikal_nazivi = [a.naziv for a in artikli]
            assert 'Artikal Firma 1' in artikal_nazivi
            assert 'Artikal Firma 2' in artikal_nazivi


def test_pausalac_cannot_access_admin_routes(client, app, setup_two_firmas_with_data):
    """Test that pausalac user cannot access admin-only routes."""
    # Login as pausalac1 - need to follow redirects to complete login
    with client:
        response = client.post('/login', data={
            'email': 'pausalac1@test.com',
            'password': 'pausalac123'
        }, follow_redirects=True)

        # Verify login was successful
        assert response.status_code == 200

        # Try to access admin users route
        response = client.get('/admin/users', follow_redirects=False)

        # Should return 403 Forbidden
        assert response.status_code == 403


def test_unauthenticated_cannot_access_admin_routes(client, app):
    """Test that unauthenticated user is redirected from admin routes."""
    # Try to access admin users route without authentication
    response = client.get('/admin/users', follow_redirects=False)

    # Should redirect to login page
    assert response.status_code == 302
    assert '/login' in response.location


def test_admin_can_access_admin_routes(client, app, setup_two_firmas_with_data):
    """Test that admin user can access admin-only routes."""
    # Login as admin - need to follow redirects to complete login
    with client:
        response = client.post('/login', data={
            'email': 'admin@test.com',
            'password': 'admin123'
        }, follow_redirects=True)

        # Verify login was successful
        assert response.status_code == 200

        # Try to access admin users route
        response = client.get('/admin/users', follow_redirects=False)

        # Should return 200 OK
        assert response.status_code == 200

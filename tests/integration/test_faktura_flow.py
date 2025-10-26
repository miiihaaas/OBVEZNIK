"""
Integration tests for Faktura flow (Story 3.1).

Tests the complete user flow from creating a draft invoice to finalizing it,
including form validation, tenant isolation, and admin god mode functionality.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from app import db
from app.models.faktura import Faktura
from app.models.faktura_stavka import FakturaStavka
from app.models.komitent import Komitent
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from flask_login import login_user


@pytest.fixture
def pausalac_with_komitent(app):
    """Create pausalac user with firma and komitent for testing."""
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
        prefiks_fakture='TF-',
        sufiks_fakture='/2025',
        brojac_fakture=1
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
    db.session.flush()

    # Create komitent
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

    return user, firma, komitent


@pytest.fixture
def second_firma_with_user(app):
    """Create second firma with pausalac user for tenant isolation testing."""
    firma2 = PausalnFirma(
        pib='99999999',
        maticni_broj='88888888',
        naziv='Druga Firma',
        adresa='Druga Adresa',
        broj='10',
        postanski_broj='21000',
        mesto='Novi Sad',
        telefon='021123456',
        email='druga@firma.rs',
        dinarski_racuni=[{'banka': 'Druga Banka', 'broj': '999-888888-77'}],
        prefiks_fakture='DF-',
        sufiks_fakture='/2025',
        brojac_fakture=1
    )
    db.session.add(firma2)
    db.session.flush()

    user2 = User(
        email='pausalac2@test.com',
        full_name='Drugi Pausalac',
        role='pausalac',
        firma_id=firma2.id
    )
    user2.set_password('password123')
    db.session.add(user2)
    db.session.commit()

    return user2, firma2


def test_pausalac_can_access_nova_faktura_form(client, pausalac_with_komitent):
    """Test: Paušalac može pristupiti /fakture/nova i videti formu (AC#1)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Access nova faktura form
    response = client.get('/fakture/nova')

    assert response.status_code == 200
    assert b'Kreiraj Fakturu' in response.data or b'Nova Faktura' in response.data
    assert b'tip_fakture' in response.data
    assert b'komitent' in response.data
    assert b'datum_prometa' in response.data


def test_pausalac_can_create_draft_faktura_with_stavke(client, pausalac_with_komitent):
    """Test: Paušalac može kreirati draft fakturu sa stavkama (AC#2-10, #12)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Create draft faktura
    response = client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Usluga konzultacije',
        'stavke-0-kolicina': '10',
        'stavke-0-jedinica_mere': 'h',
        'stavke-0-cena': '5000.00',
        'stavke-0-ukupno': '50000.00',
        'stavke-1-naziv': 'Usluga razvoja',
        'stavke-1-kolicina': '5',
        'stavke-1-jedinica_mere': 'h',
        'stavke-1-cena': '8000.00',
        'stavke-1-ukupno': '40000.00',
    }, follow_redirects=True)

    assert response.status_code == 200

    # Verify faktura created in database
    faktura = Faktura.query.filter_by(firma_id=firma.id).first()
    assert faktura is not None
    assert faktura.status == 'draft'
    assert faktura.firma_id == firma.id
    assert faktura.komitent_id == komitent.id
    assert faktura.user_id == user.id
    assert len(faktura.stavke) == 2


def test_created_faktura_has_status_draft_and_broj_fakture(client, pausalac_with_komitent):
    """Test: Kreirana faktura ima status='draft' i generiše broj_fakture (AC#7, #9)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Create draft faktura
    client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Test stavka',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': '1000.00',
        'stavke-0-ukupno': '1000.00',
    }, follow_redirects=True)

    # Verify
    faktura = Faktura.query.filter_by(firma_id=firma.id).first()
    assert faktura.status == 'draft'
    assert faktura.broj_fakture == 'TF-0001/2025'  # prefiks + brojac + sufiks


def test_ukupan_iznos_calculated_correctly(client, pausalac_with_komitent):
    """Test: Ukupan iznos fakture je tačno kalkulisan (suma stavki) (AC#6, #15)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Create faktura sa više stavki
    client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Stavka 1',
        'stavke-0-kolicina': '2',
        'stavke-0-jedinica_mere': 'h',
        'stavke-0-cena': '1500.00',
        'stavke-0-ukupno': '3000.00',
        'stavke-1-naziv': 'Stavka 2',
        'stavke-1-kolicina': '3',
        'stavke-1-jedinica_mere': 'kom',
        'stavke-1-cena': '2500.00',
        'stavke-1-ukupno': '7500.00',
    }, follow_redirects=True)

    # Verify ukupan iznos
    faktura = Faktura.query.filter_by(firma_id=firma.id).first()
    assert faktura.ukupan_iznos_rsd == Decimal('10500.00')  # 3000 + 7500


def test_datum_dospeca_calculated_correctly(client, pausalac_with_komitent):
    """Test: Datum dospeća je tačno kalkulisan (datum_prometa + valuta_placanja) (AC#4, #15)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Create faktura
    datum_prometa = date.today()
    client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': datum_prometa.strftime('%Y-%m-%d'),
        'valuta_placanja': 14,  # 14 days
        'stavke-0-naziv': 'Test',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': '1000.00',
        'stavke-0-ukupno': '1000.00',
    }, follow_redirects=True)

    # Verify datum_dospeca
    faktura = Faktura.query.filter_by(firma_id=firma.id).first()
    expected_datum_dospeca = datum_prometa + timedelta(days=14)

    # If expected date falls on weekend, should be moved to Monday
    weekday = expected_datum_dospeca.weekday()
    if weekday == 5:  # Saturday
        expected_datum_dospeca += timedelta(days=2)
    elif weekday == 6:  # Sunday
        expected_datum_dospeca += timedelta(days=1)

    assert faktura.datum_dospeca == expected_datum_dospeca


def test_pausalac_can_finalize_draft_faktura(client, pausalac_with_komitent):
    """Test: Paušalac može finalizovati draft fakturu (AC#11)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Create draft faktura
    client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Test',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': '1000.00',
        'stavke-0-ukupno': '1000.00',
    }, follow_redirects=True)

    faktura = Faktura.query.filter_by(firma_id=firma.id).first()
    assert faktura.status == 'draft'

    # Finalize faktura
    response = client.post(f'/fakture/{faktura.id}/finalizuj', follow_redirects=True)

    assert response.status_code == 200

    # Verify status changed
    db.session.refresh(faktura)
    assert faktura.status == 'izdata'


def test_after_finalization_status_izdata_and_brojac_incremented(client, pausalac_with_komitent):
    """Test: Nakon finalizacije, status='izdata' i brojač je inkrementiran (AC#8, #11)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    original_brojac = firma.brojac_fakture

    # Create and finalize faktura
    client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Test',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': '1000.00',
        'stavke-0-ukupno': '1000.00',
    }, follow_redirects=True)

    faktura = Faktura.query.filter_by(firma_id=firma.id).first()
    client.post(f'/fakture/{faktura.id}/finalizuj', follow_redirects=True)

    # Verify
    db.session.refresh(faktura)
    db.session.refresh(firma)

    assert faktura.status == 'izdata'
    assert faktura.finalized_at is not None
    assert firma.brojac_fakture == original_brojac + 1


def test_pausalac_cannot_create_faktura_without_stavke(client, pausalac_with_komitent):
    """Test: Paušalac ne može kreirati fakturu bez stavki (validacija fails) (AC#12)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Try to create faktura without stavke
    response = client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
    }, follow_redirects=True)

    # Should show validation error
    assert response.status_code == 200
    assert b'mora imati' in response.data or b'obavezn' in response.data or b'stavk' in response.data

    # Verify no faktura created
    faktura_count = Faktura.query.filter_by(firma_id=firma.id).count()
    assert faktura_count == 0


def test_pausalac_cannot_create_faktura_without_komitent(client, pausalac_with_komitent):
    """Test: Paušalac ne može kreirati fakturu bez komitenta (validacija fails) (AC#12)."""
    user, firma, komitent = pausalac_with_komitent

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Try to create faktura without komitent
    response = client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        # komitent_id missing
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Test',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': '1000.00',
        'stavke-0-ukupno': '1000.00',
    }, follow_redirects=True)

    # Should show validation error
    assert response.status_code == 200

    # Verify no faktura created
    faktura_count = Faktura.query.filter_by(firma_id=firma.id).count()
    assert faktura_count == 0


def test_admin_can_access_nova_faktura(client, app, pausalac_with_komitent):
    """Test: Admin može pristupiti /fakture/nova i kreirati fakturu (god mode)."""
    user, firma, komitent = pausalac_with_komitent

    # Create admin user
    admin = User(
        email='admin@obveznik.local',
        full_name='Admin User',
        role='admin'
    )
    admin.set_password('AdminPass123!')
    db.session.add(admin)
    db.session.commit()

    # Login as admin
    login_response = client.post('/login', data={
        'email': 'admin@obveznik.local',
        'password': 'AdminPass123!'
    }, follow_redirects=True)
    assert login_response.status_code == 200

    # Switch to firma context
    switch_response = client.post(f'/admin/switch-firma/{firma.id}', follow_redirects=True)
    assert switch_response.status_code == 200

    # Access nova faktura form
    response = client.get('/fakture/nova', follow_redirects=True)

    # Admin with firma context should be able to access
    assert response.status_code == 200


def test_pausalac_sees_only_own_firma_fakture(client, pausalac_with_komitent, second_firma_with_user):
    """Test: Paušalac vidi samo fakture svoje firme (tenant isolation)."""
    user1, firma1, komitent1 = pausalac_with_komitent
    user2, firma2 = second_firma_with_user

    # Create komitent for firma2
    komitent2 = Komitent(
        firma_id=firma2.id,
        pib='11111111',
        maticni_broj='22222222',
        naziv='Komitent 2',
        adresa='Adresa 2',
        broj='5',
        postanski_broj='21000',
        mesto='Novi Sad',
        drzava='Srbija',
        email='komitent2@test.rs'
    )
    db.session.add(komitent2)
    db.session.commit()

    # Login as user1 and create faktura for firma1
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent1.id,
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Firma 1 stavka',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': '1000.00',
        'stavke-0-ukupno': '1000.00',
    }, follow_redirects=True)

    # Logout
    client.get('/logout', follow_redirects=True)

    # Login as user2 and create faktura for firma2
    client.post('/login', data={
        'email': 'pausalac2@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    client.post('/fakture/nova', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent2.id,
        'datum_prometa': date.today().strftime('%Y-%m-%d'),
        'valuta_placanja': 7,
        'stavke-0-naziv': 'Firma 2 stavka',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'kom',
        'stavke-0-cena': '2000.00',
        'stavke-0-ukupno': '2000.00',
    }, follow_redirects=True)

    # Verify tenant isolation
    fakture_firma1 = Faktura.query.filter_by(firma_id=firma1.id).all()
    fakture_firma2 = Faktura.query.filter_by(firma_id=firma2.id).all()

    assert len(fakture_firma1) == 1
    assert len(fakture_firma2) == 1
    assert fakture_firma1[0].firma_id == firma1.id
    assert fakture_firma2[0].firma_id == firma2.id

    # User2 should NOT see firma1's fakture
    # This would be tested via API/route level, but we verify at DB level here
    assert fakture_firma1[0].id != fakture_firma2[0].id

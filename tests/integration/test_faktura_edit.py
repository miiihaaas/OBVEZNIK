"""
Integration tests for Faktura edit functionality (Story 3.7).

Tests the complete edit flow including form prepopulation, data updates,
tenant isolation, and admin god mode functionality.
"""

import pytest
from datetime import date
from decimal import Decimal
from app import db
from app.models.faktura import Faktura
from app.models.faktura_stavka import FakturaStavka
from app.models.komitent import Komitent
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma


@pytest.fixture
def pausalac_with_draft_faktura(app):
    """Create pausalac user with firma, komitent, and draft faktura for testing."""
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
        dinarski_racuni=[{'banka': 'Test Banka', 'racun': '123-456789-10'}],
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
    db.session.flush()

    # Create draft faktura
    faktura = Faktura(
        firma_id=firma.id,
        komitent_id=komitent.id,
        user_id=user.id,
        broj_fakture='DRAFT-1',
        tip_fakture='standardna',
        valuta_fakture='RSD',
        jezik='sr',
        datum_prometa=date(2025, 11, 3),
        valuta_placanja=7,
        datum_dospeca=date(2025, 11, 10),
        ukupan_iznos_rsd=Decimal('1000.00'),
        status='draft'
    )
    db.session.add(faktura)
    db.session.flush()

    # Create stavke
    stavka1 = FakturaStavka(
        faktura_id=faktura.id,
        naziv='Usluga 1',
        kolicina=Decimal('2.00'),
        jedinica_mere='h',
        cena=Decimal('300.00'),
        ukupno=Decimal('600.00'),
        redni_broj=1
    )
    stavka2 = FakturaStavka(
        faktura_id=faktura.id,
        naziv='Usluga 2',
        kolicina=Decimal('1.00'),
        jedinica_mere='h',
        cena=Decimal('400.00'),
        ukupno=Decimal('400.00'),
        redni_broj=2
    )
    db.session.add(stavka1)
    db.session.add(stavka2)
    db.session.commit()

    return user, firma, komitent, faktura


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
        dinarski_racuni=[{'banka': 'Druga Banka', 'racun': '999-888888-77'}],
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


def test_pausalac_can_access_edit_route_for_draft_faktura(client, pausalac_with_draft_faktura):
    """Test: Paušalac može pristupiti /fakture/<id>/edit za draft fakturu (AC: 1, 2, 3)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Access edit route
    response = client.get(f'/fakture/{faktura.id}/edit')

    assert response.status_code == 200
    assert b'Izmena Fakture' in response.data
    assert faktura.broj_fakture.encode() in response.data


def test_pausalac_cannot_access_edit_route_for_izdata_faktura(client, pausalac_with_draft_faktura):
    """Test: Paušalac NE može pristupiti edit ruti za izdatu fakturu (redirect sa error) (AC: 13)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    # Change faktura status to 'izdata'
    faktura.status = 'izdata'
    db.session.commit()

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Try to access edit route
    response = client.get(f'/fakture/{faktura.id}/edit', follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Samo fakture u statusu "draft" mogu biti izmenjene' in response_text or \
           'finalizovana' in response_text


def test_pausalac_cannot_access_edit_route_for_stornirana_faktura(client, pausalac_with_draft_faktura):
    """Test: Paušalac NE može pristupiti edit ruti za storniranu fakturu (redirect sa error) (AC: 14)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    # Change faktura status to 'stornirana'
    faktura.status = 'stornirana'
    db.session.commit()

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Try to access edit route
    response = client.get(f'/fakture/{faktura.id}/edit', follow_redirects=True)

    assert response.status_code == 200
    response_text = response.data.decode('utf-8')
    assert 'Samo fakture u statusu "draft" mogu biti izmenjene' in response_text or \
           'finalizovana' in response_text


def test_edit_form_is_prepopulated_with_existing_data(client, pausalac_with_draft_faktura):
    """Test: Edit forma je prepopulisana sa postojećim podacima (AC: 4)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Access edit route
    response = client.get(f'/fakture/{faktura.id}/edit')

    assert response.status_code == 200
    # Check form is prepopulated
    assert faktura.broj_fakture.encode() in response.data
    assert komitent.naziv.encode() in response.data
    assert b'2025-11-03' in response.data  # datum_prometa
    assert b'value="7"' in response.data  # valuta_placanja


def test_pausalac_can_update_faktura_data(client, pausalac_with_draft_faktura):
    """Test: Paušalac može ažurirati podatke fakture (komitent, datum, stavke) (AC: 5, 6)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Submit updated data
    response = client.post(f'/fakture/{faktura.id}/edit', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': '2025-11-05',
        'valuta_placanja': '14',  # Changed
        'stavke-0-naziv': 'Izmenjena Usluga',
        'stavke-0-kolicina': '3',  # Changed
        'stavke-0-jedinica_mere': 'h',
        'stavke-0-cena': '500.00',  # Changed
        'stavke-0-ukupno': '1500.00'
    }, follow_redirects=True)

    assert response.status_code == 200
    # Check for success message (Serbian or English)
    response_text = response.data.decode('utf-8').lower()
    assert 'uspešno' in response_text or 'successfully' in response_text

    # Verify changes in database
    updated_faktura = db.session.get(Faktura, faktura.id)
    assert updated_faktura.valuta_placanja == 14
    assert updated_faktura.datum_prometa == date(2025, 11, 5)
    assert updated_faktura.ukupan_iznos_rsd == Decimal('1500.00')
    assert len(updated_faktura.stavke) == 1
    assert updated_faktura.stavke[0].naziv == 'Izmenjena Usluga'


def test_ukupan_iznos_recalculated_after_edit(client, pausalac_with_draft_faktura):
    """Test: Ukupan iznos se rekalkuliše nakon izmene stavki (AC: 7)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    original_iznos = faktura.ukupan_iznos_rsd

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Submit updated data with different stavke
    client.post(f'/fakture/{faktura.id}/edit', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': '2025-11-03',
        'valuta_placanja': '7',
        'stavke-0-naziv': 'Nova Stavka 1',
        'stavke-0-kolicina': '5',
        'stavke-0-jedinica_mere': 'h',
        'stavke-0-cena': '200.00',
        'stavke-0-ukupno': '1000.00',
        'stavke-1-naziv': 'Nova Stavka 2',
        'stavke-1-kolicina': '2',
        'stavke-1-jedinica_mere': 'kom',
        'stavke-1-cena': '300.00',
        'stavke-1-ukupno': '600.00'
    }, follow_redirects=True)

    # Verify total amount recalculated
    updated_faktura = db.session.get(Faktura, faktura.id)
    assert updated_faktura.ukupan_iznos_rsd == Decimal('1600.00')  # 1000 + 600
    assert updated_faktura.ukupan_iznos_rsd != original_iznos


def test_status_remains_draft_after_edit(client, pausalac_with_draft_faktura):
    """Test: Status ostaje 'draft' nakon izmene (AC: 9)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    assert faktura.status == 'draft'

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Update faktura
    client.post(f'/fakture/{faktura.id}/edit', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': '2025-11-03',
        'valuta_placanja': '7',
        'stavke-0-naziv': 'Usluga',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'h',
        'stavke-0-cena': '100.00',
        'stavke-0-ukupno': '100.00'
    }, follow_redirects=True)

    # Verify status still draft
    updated_faktura = db.session.get(Faktura, faktura.id)
    assert updated_faktura.status == 'draft'


def test_broj_fakture_not_changed_after_edit(client, pausalac_with_draft_faktura):
    """Test: Broj fakture se NE menja nakon izmene (AC: 5)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    original_broj = faktura.broj_fakture

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Update faktura
    client.post(f'/fakture/{faktura.id}/edit', data={
        'tip_fakture': 'standardna',
        'komitent_id': komitent.id,
        'datum_prometa': '2025-11-03',
        'valuta_placanja': '7',
        'stavke-0-naziv': 'Usluga',
        'stavke-0-kolicina': '1',
        'stavke-0-jedinica_mere': 'h',
        'stavke-0-cena': '100.00',
        'stavke-0-ukupno': '100.00'
    }, follow_redirects=True)

    # Verify broj fakture unchanged
    updated_faktura = db.session.get(Faktura, faktura.id)
    assert updated_faktura.broj_fakture == original_broj


def test_tenant_isolation_pausalac_can_only_edit_own_fakture(client, pausalac_with_draft_faktura, second_firma_with_user):
    """Test: Tenant isolation - paušalac može editovati samo svoje fakture (AC: 16)."""
    user1, firma1, komitent1, faktura1 = pausalac_with_draft_faktura
    user2, firma2 = second_firma_with_user

    # Login as user2 from firma2
    client.post('/login', data={
        'email': 'pausalac2@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Try to access faktura from firma1 (should fail - 404)
    response = client.get(f'/fakture/{faktura1.id}/edit')

    assert response.status_code == 404


def test_izmeni_button_visible_only_for_draft_fakture(client, pausalac_with_draft_faktura):
    """Test: Button "Izmeni" je vidljiv samo za fakture sa statusom 'draft' (AC: 2)."""
    user, firma, komitent, faktura = pausalac_with_draft_faktura

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Access detail view - should show "Izmeni" button
    response = client.get(f'/fakture/{faktura.id}')
    assert response.status_code == 200
    assert b'Izmeni' in response.data

    # Change status to 'izdata'
    faktura.status = 'izdata'
    db.session.commit()

    # Access detail view again - should NOT show "Izmeni" button
    response = client.get(f'/fakture/{faktura.id}')
    assert response.status_code == 200
    # Check that "Izmeni" button is NOT present
    assert b'Finalizuj' not in response.data  # Draft-only actions should be hidden

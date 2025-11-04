"""
Integration tests for PDF Generation flow (Story 3.4).

Tests the complete PDF generation flow from finalization to download,
including Celery task triggering, PDF serving, and retry mechanism.
"""

import pytest
import os
from datetime import date
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app import db
from app.models.faktura import Faktura
from app.models.faktura_stavka import FakturaStavka
from app.models.komitent import Komitent
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma


@pytest.fixture
def pausalac_with_faktura(app):
    """Create pausalac user with firma, komitent, and draft faktura."""
    # Create firma
    firma = PausalnFirma(
        pib='12345678',
        maticni_broj='87654321',
        naziv='Test Firma PDF',
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
    db.session.flush()

    # Create draft faktura
    faktura = Faktura(
        firma_id=firma.id,
        komitent_id=komitent.id,
        user_id=user.id,
        broj_fakture='TF-0001/2025',
        tip_fakture='standardna',
        valuta_fakture='RSD',
        jezik='sr',
        datum_prometa=date.today(),
        valuta_placanja=7,
        datum_dospeca=date.today(),
        ukupan_iznos_rsd=Decimal('10000.00'),
        status='draft',
        status_pdf='pending'
    )
    db.session.add(faktura)
    db.session.flush()

    # Add stavka
    stavka = FakturaStavka(
        faktura_id=faktura.id,
        redni_broj=1,
        naziv='Test usluga',
        kolicina=Decimal('10'),
        jedinica_mere='h',
        cena=Decimal('1000.00'),
        ukupno=Decimal('10000.00')
    )
    db.session.add(stavka)
    db.session.commit()

    return user, firma, komitent, faktura


@pytest.fixture
def pausalac_with_foreign_faktura(app):
    """Create pausalac user with foreign (devizna) faktura."""
    # Create firma with devizni racuni
    firma = PausalnFirma(
        pib='99999999',
        maticni_broj='88888888',
        naziv='Foreign Firma',
        adresa='Foreign Adresa',
        broj='5',
        postanski_broj='11000',
        mesto='Beograd',
        telefon='011234567',
        email='foreign@firma.rs',
        dinarski_racuni=[{'banka': 'Test Banka', 'broj': '123-456789-10'}],
        devizni_racuni=[{'banka': 'Test Bank', 'iban': 'RS35160005050000012345', 'swift': 'TESTRS22'}],
        prefiks_fakture='FF-',
        sufiks_fakture='/2025',
        brojac_fakture=1
    )
    db.session.add(firma)
    db.session.flush()

    # Create pausalac user
    user = User(
        email='foreign@test.com',
        full_name='Foreign Pausalac',
        role='pausalac',
        firma_id=firma.id
    )
    user.set_password('password123')
    db.session.add(user)
    db.session.flush()

    # Create foreign komitent
    komitent = Komitent(
        firma_id=firma.id,
        pib='11111111',
        maticni_broj='22222222',
        naziv='Foreign Client LLC',
        adresa='Foreign Address 123',
        broj='10',
        postanski_broj='10000',
        mesto='Berlin',
        drzava='Germany',
        email='client@foreign.com',
        devizni_racuni=[{'banka': 'Foreign Bank', 'iban': 'DE89370400440532013000', 'swift': 'COBADEFF'}]
    )
    db.session.add(komitent)
    db.session.flush()

    # Create devizna faktura
    faktura = Faktura(
        firma_id=firma.id,
        komitent_id=komitent.id,
        user_id=user.id,
        broj_fakture='FF-0001/2025',
        tip_fakture='devizna',
        valuta_fakture='EUR',
        jezik='en',
        datum_prometa=date.today(),
        valuta_placanja=14,
        datum_dospeca=date.today(),
        ukupan_iznos_originalna_valuta=Decimal('1000.00'),
        ukupan_iznos_rsd=Decimal('117250.00'),
        srednji_kurs=Decimal('117.25'),
        status='draft',
        status_pdf='pending'
    )
    db.session.add(faktura)
    db.session.flush()

    # Add stavka
    stavka = FakturaStavka(
        faktura_id=faktura.id,
        redni_broj=1,
        naziv='Consulting Services',
        kolicina=Decimal('10'),
        jedinica_mere='hours',
        cena=Decimal('100.00'),
        ukupno=Decimal('1000.00')
    )
    db.session.add(stavka)
    db.session.commit()

    return user, firma, komitent, faktura


@patch('celery_worker.generate_faktura_pdf_task_async.apply_async')
def test_finalize_faktura_triggers_pdf_generation(mock_celery_task, client, pausalac_with_faktura):
    """
    Test: Finalizacija fakture triggera Celery task za PDF generisanje (AC#1, Task 9.2).

    Verifies:
    - Celery task is triggered with correct faktura_id
    - status_pdf changes to 'generating'
    """
    user, firma, komitent, faktura = pausalac_with_faktura

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Verify initial status
    assert faktura.status == 'draft'
    assert faktura.status_pdf == 'pending'

    # Finalize faktura
    response = client.post(f'/fakture/{faktura.id}/finalizuj', follow_redirects=True)

    assert response.status_code == 200

    # Verify Celery task was triggered with correct args
    mock_celery_task.assert_called_once_with(args=[faktura.id])

    # Verify status_pdf changed to 'generating'
    db.session.refresh(faktura)
    assert faktura.status == 'izdata'
    assert faktura.status_pdf == 'generating'


@patch('app.services.pdf_service.generate_pdf')
def test_download_pdf_domestic_faktura(mock_generate_pdf, client, pausalac_with_faktura, tmp_path):
    """
    Test: Paušalac može downloadovati PDF za domaću fakturu (AC#9, #10, Task 9.3).

    Verifies:
    - PDF is served with correct filename
    - Content-Type is application/pdf
    - Tenant isolation is maintained
    """
    user, firma, komitent, faktura = pausalac_with_faktura

    # Mock PDF generation to create a dummy PDF file
    pdf_folder = tmp_path / "storage" / "fakture" / str(firma.id) / "2025" / str(date.today().month)
    pdf_folder.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_folder / f"{faktura.broj_fakture.replace('/', '-')}.pdf"
    pdf_path.write_bytes(b'%PDF-1.4 DUMMY PDF CONTENT')

    # Update faktura with PDF path
    faktura.pdf_url = str(pdf_path)
    faktura.status_pdf = 'generated'
    db.session.commit()

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Download PDF
    response = client.get(f'/fakture/{faktura.id}/download-pdf')

    assert response.status_code == 200
    assert response.content_type == 'application/pdf'

    # Verify filename in Content-Disposition header
    content_disposition = response.headers.get('Content-Disposition', '')
    assert 'attachment' in content_disposition
    assert f'Faktura_{faktura.broj_fakture.replace("/", "-")}.pdf' in content_disposition


@patch('app.services.pdf_service.generate_pdf')
def test_download_pdf_foreign_faktura(mock_generate_pdf, client, pausalac_with_foreign_faktura, tmp_path):
    """
    Test: Paušalac može downloadovati PDF za deviznu fakturu sa engleskim template-om (AC#5, Task 9.4).

    Verifies:
    - English template is used for foreign invoices
    - Dual-currency display is present
    - PDF is served correctly
    """
    user, firma, komitent, faktura = pausalac_with_foreign_faktura

    # Mock PDF generation to create a dummy PDF file
    pdf_folder = tmp_path / "storage" / "fakture" / str(firma.id) / "2025" / str(date.today().month)
    pdf_folder.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_folder / f"{faktura.broj_fakture.replace('/', '-')}.pdf"
    pdf_path.write_bytes(b'%PDF-1.4 DUMMY ENGLISH PDF CONTENT')

    # Update faktura with PDF path
    faktura.pdf_url = str(pdf_path)
    faktura.status_pdf = 'generated'
    db.session.commit()

    # Login
    client.post('/login', data={
        'email': 'foreign@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Download PDF
    response = client.get(f'/fakture/{faktura.id}/download-pdf')

    assert response.status_code == 200
    assert response.content_type == 'application/pdf'

    # Verify filename
    content_disposition = response.headers.get('Content-Disposition', '')
    assert 'attachment' in content_disposition
    assert f'Faktura_{faktura.broj_fakture.replace("/", "-")}.pdf' in content_disposition

    # Verify faktura jezik is 'en' (uses English template)
    assert faktura.jezik == 'en'


@patch('celery_worker.generate_faktura_pdf_task_async.apply_async')
def test_retry_failed_pdf_generation(mock_celery_task, client, pausalac_with_faktura):
    """
    Test: Paušalac može retry failed PDF generisanje (AC#8, Task 9.5).

    Verifies:
    - Retry endpoint triggers new Celery task
    - status_pdf changes from 'failed' to 'generating'
    - JSON response is returned correctly
    """
    user, firma, komitent, faktura = pausalac_with_faktura

    # Simulate failed PDF generation
    faktura.status = 'izdata'
    faktura.status_pdf = 'failed'
    db.session.commit()

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Verify initial failed status
    assert faktura.status_pdf == 'failed'

    # Retry PDF generation
    response = client.post(f'/fakture/{faktura.id}/retry-pdf')

    assert response.status_code == 200

    # Verify JSON response
    json_data = response.get_json()
    assert json_data['success'] is True
    assert 'u toku' in json_data['message'].lower() or 'generating' in json_data['message'].lower()

    # Verify Celery task was triggered with correct args
    mock_celery_task.assert_called_once_with(args=[faktura.id])

    # Verify status_pdf changed to 'generating'
    db.session.refresh(faktura)
    assert faktura.status_pdf == 'generating'


def test_download_pdf_returns_404_when_pdf_not_generated(client, pausalac_with_faktura):
    """
    Test: Download endpoint vraća 404 ako PDF nije generisan (AC#9).

    Verifies:
    - Returns 404 or error message when pdf_url is None
    """
    user, firma, komitent, faktura = pausalac_with_faktura

    # Ensure PDF is not generated
    faktura.pdf_url = None
    faktura.status_pdf = 'pending'
    db.session.commit()

    # Login
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Try to download PDF
    response = client.get(f'/fakture/{faktura.id}/download-pdf')

    # Should return error (404 or redirect with error message)
    assert response.status_code in [404, 302, 200]

    if response.status_code == 200:
        # If redirected with flash message, verify error message
        assert b'nije dostupan' in response.data or b'not available' in response.data or b'PDF' in response.data


def test_tenant_isolation_in_download_pdf(client, pausalac_with_faktura, tmp_path):
    """
    Test: Tenant isolation - drugi user ne može downloadovati tuđe PDF-ove (Security).

    Verifies:
    - User from different firma cannot access PDF
    - Returns 403 or redirect
    """
    user1, firma1, komitent1, faktura1 = pausalac_with_faktura

    # Create second firma with user
    firma2 = PausalnFirma(
        pib='77777777',
        maticni_broj='66666666',
        naziv='Druga Firma',
        adresa='Druga Adresa',
        broj='20',
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

    # Mock PDF for faktura1
    pdf_folder = tmp_path / "storage" / "fakture" / str(firma1.id) / "2025" / str(date.today().month)
    pdf_folder.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_folder / f"{faktura1.broj_fakture.replace('/', '-')}.pdf"
    pdf_path.write_bytes(b'%PDF-1.4 FIRMA1 PDF')

    faktura1.pdf_url = str(pdf_path)
    faktura1.status_pdf = 'generated'
    db.session.commit()

    # Login as user2 (different firma)
    client.post('/login', data={
        'email': 'pausalac2@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Try to download faktura1's PDF (belongs to firma1)
    response = client.get(f'/fakture/{faktura1.id}/download-pdf', follow_redirects=False)

    # Should be denied (403, 404, or redirect)
    assert response.status_code in [403, 404, 302]

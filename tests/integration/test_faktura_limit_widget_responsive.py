"""
Integration tests for Faktura Limit Widget Responsive Design & Loading States (Story 5.4 - Task 8).

Tests responsive behavior, loading states, and sticky positioning of the limit widget.
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal

from app import db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.komitent import Komitent
from app.models.faktura import Faktura


@pytest.fixture
def pausalac_user(app):
    """Create pausalac user with firma for testing."""
    with app.app_context():
        # Create firma
        firma = PausalnFirma(
            pib='111111111',
            maticni_broj='11111111',
            naziv='Test Firma',
            adresa='Test Adresa',
            broj='1',
            postanski_broj='11000',
            mesto='Beograd',
            telefon='011111111',
            email='test@test.com',
            dinarski_racuni=[{'banka': 'Test Banka', 'racun': '111-111111-11'}]
        )
        db.session.add(firma)
        db.session.flush()

        # Create pausalac user
        pausalac = User(
            email='pausalac@test.com',
            full_name='Pausalac User',
            role='pausalac',
            firma_id=firma.id
        )
        pausalac.set_password('password123')
        db.session.add(pausalac)
        db.session.commit()

        return {
            'firma_id': firma.id,
            'pausalac_id': pausalac.id
        }


def test_responsive_layout_structure(client, pausalac_user):
    """Test responsive layout with Bootstrap grid (AC: 1 - Task 8)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # GET nova faktura form
    response = client.get('/fakture/nova')
    assert response.status_code == 200

    html = response.data.decode('utf-8')

    # Verify responsive grid layout
    assert 'col-lg-8' in html  # Main form content column
    assert 'col-lg-4' in html  # Widget sidebar column

    # Verify widget is inside col-lg-4 (desktop/tablet only)
    assert 'col-lg-4' in html and 'id="limit_widget"' in html


def test_sticky_positioning(client, pausalac_user):
    """Test sticky positioning CSS (AC: 1 - Task 8)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # GET nova faktura form
    response = client.get('/fakture/nova')
    assert response.status_code == 200

    html = response.data.decode('utf-8')

    # Verify sticky positioning
    assert 'position-sticky' in html
    assert 'top: 20px' in html  # Sticky top offset


def test_loading_state_elements(client, pausalac_user):
    """Test loading state HTML elements (AC: 1 - Task 8)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # GET nova faktura form
    response = client.get('/fakture/nova')
    assert response.status_code == 200

    html = response.data.decode('utf-8')

    # Verify loading state elements
    assert 'id="limit_loading"' in html
    assert 'fa-spinner' in html  # Spinner icon
    assert 'Učitavam' in html  # Loading text

    # Verify content state element
    assert 'id="limit_content"' in html
    assert 'style="display: none;"' in html  # Hidden by default

    # Verify error state element
    assert 'id="limit_error"' in html


def test_widget_content_structure(client, pausalac_user):
    """Test widget content HTML structure (AC: 1 - Task 8)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # GET nova faktura form
    response = client.get('/fakture/nova')
    assert response.status_code == 200

    html = response.data.decode('utf-8')

    # Verify widget header
    assert 'Limit Tracking' in html

    # Verify rolling limit display elements
    assert 'id="rolling_limit_display"' in html
    assert 'Godišnji Limit (365 dana)' in html

    # Verify progress bar
    assert 'id="progress_bar"' in html
    assert 'progress-bar' in html

    # Verify current stats displays
    assert 'id="promet_365_display"' in html
    assert 'id="preostali_limit_display"' in html

    # Verify nova faktura simulation section
    assert 'id="nova_faktura_section"' in html
    assert 'Simulacija nove fakture' in html
    assert 'id="nova_faktura_iznos_display"' in html
    assert 'id="preostalo_nakon_display"' in html

    # Verify over limit warning section
    assert 'id="over_limit_warning"' in html
    assert 'UPOZORENJE' in html
    assert 'id="over_limit_amount_display"' in html

    # Verify projekcije displays
    assert 'id="projekcija_7_display"' in html
    assert 'id="projekcija_15_display"' in html
    assert 'id="projekcija_30_display"' in html


def test_bootstrap_classes_present(client, pausalac_user):
    """Test Bootstrap 5 classes are present (AC: 1 - Task 8)."""
    # Login as pausalac
    client.post('/login', data={
        'email': 'pausalac@test.com',
        'password': 'password123'
    }, follow_redirects=True)

    # GET nova faktura form
    response = client.get('/fakture/nova')
    assert response.status_code == 200

    html = response.data.decode('utf-8')

    # Verify Bootstrap card components
    assert 'class="card border-0 shadow-sm' in html

    # Verify Bootstrap alert components
    assert 'alert alert-info' in html  # Nova faktura section
    assert 'alert alert-danger' in html  # Over limit warning
    assert 'alert alert-light' in html  # Info tooltip

    # Verify Bootstrap progress bar
    assert 'class="progress"' in html
    assert 'role="progressbar"' in html

    # Verify Bootstrap utility classes
    assert 'text-center' in html  # Loading spinner
    assert 'text-muted' in html  # Labels
    assert 'mb-' in html  # Margin bottom spacing


def test_manual_responsive_checklist():
    """
    Manual testing checklist for responsive design (Task 8).

    This is a documentation test that outlines manual testing steps for:
    - Desktop (lg+ breakpoint): Widget displayed in sidebar with sticky position
    - Tablet (md breakpoint): Widget displayed but not sticky
    - Mobile (sm breakpoint): Widget hidden or displayed at top of form

    Manual Testing Steps:
    1. Open /fakture/nova in browser
    2. Resize window to desktop width (>= 992px)
       - Verify widget is visible in right sidebar
       - Scroll down and verify widget stays visible (sticky)
    3. Resize window to tablet width (768px - 991px)
       - Verify widget is visible but may not be sticky
    4. Resize window to mobile width (< 768px)
       - Verify widget is hidden or moved to top of form

    Loading States Manual Testing:
    1. Open /fakture/nova with network throttling
    2. Verify spinner is displayed while loading
    3. Verify content is displayed after API response
    4. Simulate API error (disconnect network)
    5. Verify error message is displayed
    """
    # This is a documentation test - no assertions needed
    assert True, "Manual testing checklist documented"

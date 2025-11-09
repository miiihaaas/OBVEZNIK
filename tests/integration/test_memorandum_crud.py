"""Integration tests for Memorandum CRUD operations."""
import pytest
from datetime import date
from app import create_app, db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma
from app.models.memorandum import Memorandum
from app.models.komitent import Komitent


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
            dinarski_racuni=[]
        )
        db.session.add(firma)
        db.session.commit()

        user = User(
            email='pausalac@test.com',
            full_name='Test Pausalac',
            role='pausalac',
            firma_id=firma.id
        )
        user.set_password('TestPass123!')
        db.session.add(user)
        db.session.commit()

        yield user, firma


@pytest.fixture
def firma2(app):
    """Create second firma for tenant isolation testing."""
    with app.app_context():
        firma = PausalnFirma(
            pib='987654321',
            maticni_broj='87654321',
            naziv='Druga Firma',
            adresa='Druga Adresa',
            broj='2',
            postanski_broj='21000',
            mesto='Novi Sad',
            drzava='Srbija',
            telefon='022222222',
            email='firma2@test.com',
            dinarski_racuni=[]
        )
        db.session.add(firma)
        db.session.commit()
        yield firma


class TestMemorandumCRUD:
    """Integration tests for Memorandum CRUD operations with tenant isolation."""

    def test_pausalac_can_create_memorandum(self, client, pausalac_with_firma):
        """Test that pausalac can create a memorandum."""
        user, firma = pausalac_with_firma

        # Login
        client.post('/login', data={'email': user.email, 'password': 'TestPass123!'}, follow_redirects=True)

        # Create memorandum
        response = client.post('/memorandumi/novi', data={
            'naslov': 'Test memorandum',
            'sadrzaj': 'Ovo je test memorandum sa dovoljno karaktera za validaciju.',
            'datum': date.today().isoformat(),
            'komitent_id': '',
            'faktura_id': ''
        }, follow_redirects=True)

        assert response.status_code == 200
        memo = db.session.query(Memorandum).filter_by(naslov='Test memorandum').first()
        assert memo is not None
        assert memo.firma_id == firma.id
        assert memo.sadrzaj == 'Ovo je test memorandum sa dovoljno karaktera za validaciju.'

    def test_pausalac_can_view_own_memorandum(self, client, pausalac_with_firma):
        """Test that pausalac can view their own memorandum."""
        user, firma = pausalac_with_firma

        # Create memorandum
        memo = Memorandum(
            firma_id=firma.id,
            naslov='Testni memorandum',
            sadrzaj='Sadrzaj testnog memoranduma',
            datum=date.today()
        )
        db.session.add(memo)
        db.session.commit()

        # Login
        client.post('/login', data={'email': user.email, 'password': 'TestPass123!'}, follow_redirects=True)

        # View memorandum
        response = client.get(f'/memorandumi/{memo.id}')
        assert response.status_code == 200
        assert b'Testni memorandum' in response.data

    def test_pausalac_cannot_view_other_firma_memorandum(self, client, pausalac_with_firma, firma2):
        """Test tenant isolation: pausalac cannot view other firma's memorandumi."""
        user, firma = pausalac_with_firma

        # Create memorandum for firma2
        memo_other = Memorandum(
            firma_id=firma2.id,
            naslov='Memorandum druge firme',
            sadrzaj='Sadrzaj memoranduma druge firme',
            datum=date.today()
        )
        db.session.add(memo_other)
        db.session.commit()

        # Login as pausalac from firma1
        client.post('/login', data={'email': user.email, 'password': 'TestPass123!'}, follow_redirects=True)

        # Try to view firma2's memorandum (should get 404)
        response = client.get(f'/memorandumi/{memo_other.id}')
        assert response.status_code == 404

    def test_pausalac_can_edit_own_memorandum(self, client, pausalac_with_firma):
        """Test that pausalac can edit their own memorandum."""
        user, firma = pausalac_with_firma

        # Create memorandum
        memo = Memorandum(
            firma_id=firma.id,
            naslov='Originalni naslov',
            sadrzaj='Originalni sadrzaj memoranduma',
            datum=date.today()
        )
        db.session.add(memo)
        db.session.commit()

        # Login
        client.post('/login', data={'email': user.email, 'password': 'TestPass123!'}, follow_redirects=True)

        # Edit memorandum
        response = client.post(f'/memorandumi/{memo.id}/izmeni', data={
            'naslov': 'Izmenjeni naslov',
            'sadrzaj': 'Izmenjeni sadrzaj memoranduma',
            'datum': date.today().isoformat(),
            'komitent_id': '',
            'faktura_id': ''
        }, follow_redirects=True)

        assert response.status_code == 200
        db.session.refresh(memo)
        assert memo.naslov == 'Izmenjeni naslov'
        assert memo.sadrzaj == 'Izmenjeni sadrzaj memoranduma'

    def test_pausalac_can_delete_own_memorandum(self, client, pausalac_with_firma):
        """Test that pausalac can delete their own memorandum."""
        user, firma = pausalac_with_firma

        # Create memorandum
        memo = Memorandum(
            firma_id=firma.id,
            naslov='Memorandum za brisanje',
            sadrzaj='Ovaj memorandum ce biti obrisan',
            datum=date.today()
        )
        db.session.add(memo)
        db.session.commit()
        memo_id = memo.id

        # Login
        client.post('/login', data={'email': user.email, 'password': 'TestPass123!'}, follow_redirects=True)

        # Delete memorandum
        response = client.post(f'/memorandumi/{memo_id}/obrisi', follow_redirects=True)
        assert response.status_code == 200

        # Verify deleted
        deleted_memo = db.session.query(Memorandum).filter_by(id=memo_id).first()
        assert deleted_memo is None

    def test_lista_memoranduma_search_by_naslov(self, client, pausalac_with_firma):
        """Test search functionality by naslov."""
        user, firma = pausalac_with_firma

        # Create multiple memorandumi
        memo1 = Memorandum(firma_id=firma.id, naslov='Python Development', sadrzaj='Razvoj u Python-u', datum=date.today())
        memo2 = Memorandum(firma_id=firma.id, naslov='JavaScript Coding', sadrzaj='Kodiranje u JavaScript-u', datum=date.today())
        db.session.add_all([memo1, memo2])
        db.session.commit()

        # Login
        client.post('/login', data={'email': user.email, 'password': 'TestPass123!'}, follow_redirects=True)

        # Search for "Python"
        response = client.get('/memorandumi/?search=Python')
        assert response.status_code == 200
        assert b'Python Development' in response.data
        assert b'JavaScript Coding' not in response.data

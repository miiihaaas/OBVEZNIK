"""
Seed script for creating test users.

Usage:
    python tests/seed_users.py

This script creates:
- Admin user: admin@example.com / admin123
- Pausalac user: pausalac@example.com / pausalac123
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.user import User
from app.models.pausaln_firma import PausalnFirma


def seed_users():
    """Create test users in the database."""
    app = create_app('development')

    with app.app_context():
        print("Starting user seeding...")

        # Check if users already exist
        admin_exists = User.query.filter_by(email='admin@example.com').first()
        pausalac_exists = User.query.filter_by(email='pausalac@example.com').first()

        if admin_exists and pausalac_exists:
            print("Test users already exist. Skipping seed.")
            return

        # Create admin user
        if not admin_exists:
            admin = User(
                email='admin@example.com',
                full_name='Admin User',
                role='admin',
                is_active=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("✓ Created admin user: admin@example.com / admin123")
        else:
            print("✓ Admin user already exists")

        # Create test firma for pausalac
        test_firma = PausalnFirma.query.filter_by(pib='123456789').first()
        if not test_firma:
            test_firma = PausalnFirma(
                pib='123456789',
                maticni_broj='87654321',
                naziv='Test Paušalna Firma',
                adresa='Testna ulica',
                broj='1',
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                telefon='011/1234567',
                email='test@firma.rs',
                dinarski_racuni='[]',
                is_active=True
            )
            db.session.add(test_firma)
            db.session.flush()  # Get firma ID
            print("✓ Created test firma: Test Paušalna Firma (PIB: 123456789)")

        # Create pausalac user
        if not pausalac_exists:
            pausalac = User(
                email='pausalac@example.com',
                full_name='Paušalac User',
                role='pausalac',
                is_active=True,
                firma_id=test_firma.id
            )
            pausalac.set_password('pausalac123')
            db.session.add(pausalac)
            print("✓ Created pausalac user: pausalac@example.com / pausalac123")
        else:
            print("✓ Pausalac user already exists")

        # Commit all changes
        db.session.commit()
        print("\n✅ Seeding completed successfully!")
        print("\nTest credentials:")
        print("  Admin: admin@example.com / admin123")
        print("  Paušalac: pausalac@example.com / pausalac123")


if __name__ == '__main__':
    seed_users()

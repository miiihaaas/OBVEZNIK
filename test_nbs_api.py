"""Test script for NBS SOAP API integration."""
import os
import sys
from datetime import date

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from app.services.nbs_kursna_service import fetch_kursna_lista_soap

# Create Flask app context
app = create_app()

with app.app_context():
    print("=" * 60)
    print("Testing NBS SOAP API Integration")
    print("=" * 60)

    # Check credentials
    nbs_user = app.config.get('NBS_USERNAME')
    nbs_pass = app.config.get('NBS_PASSWORD')
    nbs_licence = app.config.get('NBS_LICENCE_ID')

    print(f"\nNBS Username: {'SET' if nbs_user else 'NOT SET'}")
    print(f"NBS Password: {'SET' if nbs_pass else 'NOT SET'}")
    print(f"NBS Licence ID: {'SET' if nbs_licence else 'NOT SET'}")

    if not (nbs_user and nbs_pass and nbs_licence):
        print("\n[ERROR] NBS credentials are NOT configured in .env file!")
        print("   Please set NBS_USERNAME, NBS_PASSWORD, and NBS_LICENCE_ID")
        sys.exit(1)

    print("\n[OK] NBS credentials are configured")
    print("\nCalling NBS SOAP API...")

    try:
        today = date.today()
        kursevi = fetch_kursna_lista_soap(today)

        print(f"\n[SUCCESS] Fetched {len(kursevi)} exchange rates:")
        print("-" * 60)
        for valuta, kurs in kursevi.items():
            print(f"  {valuta}: {kurs} RSD")
        print("-" * 60)

    except Exception as e:
        print(f"\n[FAILED] Error: {e}")
        print("\nPossible reasons:")
        print("  1. Invalid NBS credentials")
        print("  2. NBS service is unavailable")
        print("  3. Network connection issue")
        print("  4. SOAP API endpoint changed")
        sys.exit(1)

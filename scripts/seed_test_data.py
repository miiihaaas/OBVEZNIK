#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Seed script to populate database with test data for development.

Creates:
- 10 paušalnih firmi
- 2-3 korisnika po firmi (pausalac role)
- 5-10 komitenata po firmi
- 3-5 artikala po firmi
- 10-50 faktura po firmi (poslednja 2-3 meseca)
"""
import random
import sys
import os
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models.pausaln_firma import PausalnFirma
from app.models.user import User
from app.models.komitent import Komitent
from app.models.artikal import Artikal
from app.models.faktura import Faktura
from app.models.faktura_stavka import FakturaStavka


# Test data constants
FIRMA_NAMES = [
    'Digital Solutions DOO',
    'Marketing Pro Paušal',
    'Web Design Studio',
    'Consulting Group',
    'IT Innovations',
    'Creative Agency',
    'Business Partners',
    'Tech Services',
    'Smart Solutions',
    'Professional Hub'
]

KOMITENT_NAMES = [
    'Komercijalna Banka AD',
    'Energoprojekt Holding',
    'Telecom Srbija DOO',
    'AutoMoto Plus',
    'MegaMarket Chain',
    'Gradnja Invest',
    'Tehnomanija Retail',
    'HealthCare Systems',
    'EduTech Solutions',
    'Transport Logistics'
]

ARTIKAL_NAMES = [
    ('Web Development', 'Izrada web aplikacija', 'sat'),
    ('Grafički dizajn', 'Kreiranje grafičkih rešenja', 'sat'),
    ('SEO optimizacija', 'Optimizacija za pretraživače', 'usluga'),
    ('Konsultantske usluge', 'Biznis konsalting', 'sat'),
    ('Copywriting', 'Pisanje marketinških tekstova', 'sat'),
    ('Social Media Management', 'Upravljanje društvenim mrežama', 'mesec'),
    ('Email Marketing', 'Email kampanje', 'kampanja'),
    ('Logo Design', 'Kreiranje logotipa', 'komad'),
    ('Maintenance', 'Održavanje sistema', 'mesec'),
    ('Training', 'Obuka zaposlenih', 'dan')
]

USER_NAMES = [
    'Marko Marković',
    'Jovana Jovanović',
    'Stefan Stefanović',
    'Ana Anić',
    'Petar Petrović',
    'Milica Milić',
    'Nikola Nikolić',
    'Jelena Jelenić'
]


def generate_pib():
    """Generate random 9-digit PIB."""
    return str(random.randint(100000000, 999999999))


def generate_maticni_broj():
    """Generate random 8-digit matični broj."""
    return str(random.randint(10000000, 99999999))


def create_firme(count=10):
    """Create test paušalnih firmi."""
    print(f"\nKreiram {count} paušalnih firmi...")
    firme = []

    for i in range(count):
        firma = PausalnFirma(
            pib=generate_pib(),
            maticni_broj=generate_maticni_broj(),
            naziv=FIRMA_NAMES[i],
            adresa=f'Bulevar Kralja Aleksandra',
            broj=str(random.randint(1, 200)),
            postanski_broj='11000',
            mesto='Beograd',
            drzava='Srbija',
            telefon=f'011/{random.randint(1000000, 9999999)}',
            email=f'info@{FIRMA_NAMES[i].lower().replace(" ", "")}.rs',
            dinarski_racuni='[{"banka": "Komercijalna Banka", "racun": "160-12345-67"}]',
            prefiks_fakture=f'F{i+1}',
            sufiks_fakture=str(datetime.now().year),
            brojac_fakture=random.randint(100, 200),
            is_active=True
        )
        db.session.add(firma)
        firme.append(firma)

    db.session.flush()
    print(f"[OK] Kreirano {count} firmi")
    return firme


def create_users(firme):
    """Create 2-3 pausalac users per firma."""
    print("\nKreiram korisnike...")
    users_created = 0

    for firma in firme:
        num_users = random.randint(2, 3)
        # Use different names from USER_NAMES to avoid duplicates
        selected_names = random.sample(USER_NAMES, min(num_users, len(USER_NAMES)))

        for i, user_name in enumerate(selected_names, 1):
            # Add index to ensure unique email
            email = f'{user_name.lower().replace(" ", ".")}.{i}@{firma.naziv.lower().replace(" ", "")}.rs'

            user = User(
                email=email,
                full_name=user_name,
                role='pausalac',
                firma_id=firma.id,
                is_active=True
            )
            user.set_password('password123')
            db.session.add(user)
            users_created += 1

    db.session.flush()
    print(f"[OK] Kreirano {users_created} korisnika")


def create_komitenti(firme):
    """Create 5-10 komitenti per firma."""
    print("\nKreiram komitente...")
    komitenti_created = 0
    firma_komitenti = {}

    for firma in firme:
        num_komitenti = random.randint(5, 10)
        firma_komitenti[firma.id] = []

        for i in range(num_komitenti):
            komitent_name = random.choice(KOMITENT_NAMES)

            komitent = Komitent(
                firma_id=firma.id,
                pib=generate_pib(),
                maticni_broj=generate_maticni_broj(),
                naziv=f'{komitent_name} {i+1}',
                adresa=f'Kralja Petra',
                broj=str(random.randint(1, 100)),
                postanski_broj='11000',
                mesto='Beograd',
                drzava='Srbija',
                email=f'office@{komitent_name.lower().replace(" ", "")}{i+1}.rs',
                dinarski_racuni='[{"banka": "Raiffeisen Banka", "racun": "265-98765-43"}]'
            )
            db.session.add(komitent)
            firma_komitenti[firma.id].append(komitent)
            komitenti_created += 1

    db.session.flush()
    print(f"[OK] Kreirano {komitenti_created} komitenata")
    return firma_komitenti


def create_artikli(firme):
    """Create 3-5 artikli per firma."""
    print("\nKreiram artikle...")
    artikli_created = 0
    firma_artikli = {}

    for firma in firme:
        num_artikli = random.randint(3, 5)
        firma_artikli[firma.id] = []

        selected_artikli = random.sample(ARTIKAL_NAMES, num_artikli)
        for naziv, opis, jedinica in selected_artikli:
            artikal = Artikal(
                firma_id=firma.id,
                naziv=naziv,
                opis=opis,
                jedinica_mere=jedinica,
                podrazumevana_cena=Decimal(random.randint(5000, 50000))
            )
            db.session.add(artikal)
            firma_artikli[firma.id].append(artikal)
            artikli_created += 1

    db.session.flush()
    print(f"[OK] Kreirano {artikli_created} artikala")
    return firma_artikli


def create_fakture(firme, firma_komitenti, firma_artikli):
    """Create 10-50 fakture per firma with random dates in last 2-3 months."""
    print("\nKreiram fakture...")
    fakture_created = 0

    # Date range: last 2-3 months
    today = date.today()
    start_date = today - timedelta(days=random.randint(60, 90))

    for firma in firme:
        # Get users for this firma
        firma_users = User.query.filter_by(firma_id=firma.id).all()
        if not firma_users:
            continue

        num_fakture = random.randint(10, 50)

        for i in range(num_fakture):
            # Random date in range
            days_offset = random.randint(0, (today - start_date).days)
            datum_prometa = start_date + timedelta(days=days_offset)
            valuta_placanja = random.choice([7, 15, 30, 45])
            datum_dospeca = datum_prometa + timedelta(days=valuta_placanja)

            # Random komitent from firma's komitenti
            komitent = random.choice(firma_komitenti[firma.id])
            user = random.choice(firma_users)

            # Generate invoice number
            broj_fakture = f'{firma.prefiks_fakture or ""}{firma.brojac_fakture + i}{firma.sufiks_fakture or ""}'

            faktura = Faktura(
                firma_id=firma.id,
                komitent_id=komitent.id,
                user_id=user.id,
                broj_fakture=broj_fakture,
                tip_fakture='standardna',
                valuta_fakture='RSD',
                jezik='sr',
                datum_prometa=datum_prometa,
                valuta_placanja=valuta_placanja,
                datum_dospeca=datum_dospeca,
                ukupan_iznos_rsd=Decimal(0),  # Will be calculated from stavke
                status='izdata',
                finalized_at=datetime.combine(datum_prometa, datetime.min.time()).replace(tzinfo=timezone.utc)
            )
            db.session.add(faktura)
            db.session.flush()  # Get faktura.id

            # Create faktura stavke (1-5 items per invoice)
            num_stavke = random.randint(1, 5)
            ukupan_iznos = Decimal(0)

            for j in range(num_stavke):
                artikal = random.choice(firma_artikli[firma.id])
                kolicina = Decimal(random.randint(1, 20))
                cena = artikal.podrazumevana_cena or Decimal(random.randint(5000, 50000))
                ukupno = kolicina * cena
                ukupan_iznos += ukupno

                stavka = FakturaStavka(
                    faktura_id=faktura.id,
                    artikal_id=artikal.id,
                    naziv=artikal.naziv,
                    kolicina=kolicina,
                    jedinica_mere=artikal.jedinica_mere,
                    cena=cena,
                    ukupno=ukupno,
                    redni_broj=j + 1
                )
                db.session.add(stavka)

            # Update faktura with total amount
            faktura.ukupan_iznos_rsd = ukupan_iznos
            fakture_created += 1

    db.session.flush()
    print(f"[OK] Kreirano {fakture_created} faktura")


def seed_database():
    """Main function to seed database with test data."""
    print("=" * 60)
    print("SEED TEST DATA SCRIPT")
    print("=" * 60)

    # Create application context
    app = create_app('development')

    with app.app_context():
        print("\n[!] WARNING: Ova skripta ce kreirati TEST PODATKE u bazi!")
        print("Nastavite samo ako zelite da dodate test podatke.\n")

        response = input("Da li zelite da nastavite? (y/N): ")
        if response.lower() != 'y':
            print("Odustao. Skripta prekinuta.")
            return

        try:
            # Create test data
            firme = create_firme(10)
            create_users(firme)
            firma_komitenti = create_komitenti(firme)
            firma_artikli = create_artikli(firme)
            create_fakture(firme, firma_komitenti, firma_artikli)

            # Commit all changes
            db.session.commit()

            print("\n" + "=" * 60)
            print("[OK] SVE PODATKE SU USPESNO KREIRANI!")
            print("=" * 60)
            print("\nStatistika:")
            print(f"  - Firme: {PausalnFirma.query.count()}")
            print(f"  - Korisnici: {User.query.filter_by(role='pausalac').count()}")
            print(f"  - Komitenti: {Komitent.query.count()}")
            print(f"  - Artikli: {Artikal.query.count()}")
            print(f"  - Fakture: {Faktura.query.count()}")
            print(f"  - Stavke: {FakturaStavka.query.count()}")

            print("\n[INFO] Korisnici za login (svi sa password: 'password123'):")
            users = User.query.filter_by(role='pausalac').limit(5).all()
            for user in users:
                print(f"  - {user.email} ({user.firma.naziv})")

        except Exception as e:
            db.session.rollback()
            print(f"\n[ERROR] GRESKA: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    seed_database()

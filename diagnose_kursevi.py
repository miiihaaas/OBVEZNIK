"""
Dijagnostički script za debug problema sa kursevima.
Koristi se na serveru da se identifikuje problem.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app
from datetime import date
from decimal import Decimal

app = create_app()

with app.app_context():
    print("=" * 60)
    print("DIJAGNOSTIKA KURSEVI PROBLEMA")
    print("=" * 60)

    # 1. Check Redis connection
    print("\n1. Redis Konekcija:")
    redis_client = app.extensions.get('redis')
    if redis_client:
        try:
            redis_client.ping()
            print("   [OK] Redis je aktivan")
        except Exception as e:
            print(f"   [ERROR] Redis ping failed: {e}")
    else:
        print("   [ERROR] Redis client nije inicijalizovan")

    # 2. Test write to Redis
    print("\n2. Test pisanja u Redis:")
    from app.services.nbs_kursna_service import cache_kurs
    test_datum = date.today()
    test_kurs = Decimal('123.4567')

    try:
        cache_kurs('EUR', test_datum, test_kurs)
        print(f"   [OK] Uspešno zapisano: EUR/{test_datum} = {test_kurs}")
    except Exception as e:
        print(f"   [ERROR] Neuspešno pisanje: {e}")

    # 3. Test read from Redis
    print("\n3. Test čitanja iz Redis-a:")
    from app.services.nbs_kursna_service import get_kurs

    try:
        kurs = get_kurs('EUR', test_datum)
        if kurs:
            print(f"   [OK] Uspešno pročitano: EUR/{test_datum} = {kurs}")
            if kurs == test_kurs:
                print("   [OK] Vrednost se poklapa sa zapisanom!")
            else:
                print(f"   [WARNING] Vrednost se NE poklapa! Očekivano: {test_kurs}, Dobijeno: {kurs}")
        else:
            print(f"   [ERROR] Kurs nije pronađen (None)")
    except Exception as e:
        print(f"   [ERROR] Neuspešno čitanje: {e}")

    # 4. Check all cached keys
    print("\n4. Svi keširani kursevi danas:")
    if redis_client:
        try:
            pattern = f"nbs_kurs_*_{test_datum}"
            keys = redis_client.keys(pattern)
            if keys:
                print(f"   Pronađeno {len(keys)} ključeva:")
                for key in keys:
                    value = redis_client.get(key)
                    if value:
                        print(f"     - {key.decode('utf-8')}: {value.decode('utf-8')}")
            else:
                print(f"   Nema keširanih kurseva za {test_datum}")
        except Exception as e:
            print(f"   [ERROR] {e}")

    # 5. Check kursevi view
    print("\n5. Provera kursevi view-a:")
    try:
        from app.routes.admin import kursevi
        print("   [OK] Route 'admin.kursevi' postoji")
    except Exception as e:
        print(f"   [ERROR] {e}")

    # 6. Environment check
    print("\n6. Environment:")
    print(f"   REDIS_URL: {app.config.get('REDIS_URL', 'NOT SET')}")
    print(f"   FLASK_ENV: {os.environ.get('FLASK_ENV', 'NOT SET')}")

    print("\n" + "=" * 60)
    print("DIJAGNOSTIKA ZAVRŠENA")
    print("=" * 60)

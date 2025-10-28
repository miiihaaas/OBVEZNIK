# 🔍 Kursevi Debug Guide - Rešavanje Problema na Serveru

## Problem
Na serveru, kada ažuriram kurs (manual override), dobijam flash poruku o uspešnom ažuriranju, ali se izmene ne prikazuju na stranici.

---

## Kako Funkcioniše Sistem (za početnike sa Redis-om)

### Šta je Redis?
Redis je **in-memory key-value baza** - ultra brz cache sistem. Zamišljaj ga kao gigantski Python dictionary u memoriji:

```python
redis_cache = {
    "nbs_kurs_EUR_2025-10-28": "117.2516",  # Expires after 24h
    "nbs_kurs_USD_2025-10-28": "100.5157",
    # ...
}
```

### 🔄 Tok Ručnog Ažuriranja Kursa

```
1. Uneseš kurs u formu i klikneš "Sačuvaj Kurs"
   ↓
2. POST /admin/kursevi/override
   (app/routes/admin.py:648)
   ↓
3. cache_kurs(valuta, datum, kurs)
   (app/services/nbs_kursna_service.py:215)
   ↓
4. Redis: SETEX "nbs_kurs_EUR_2025-10-28" 86400 "117.2516"
          └────────┬────────┘ └──┬──┘ └────┬────┘
              KEY (string)   TTL    VALUE (string)
                           (24h)
   ↓
5. Redirect → GET /admin/kursevi
   ↓
6. get_kurs(valuta, today)
   (app/services/nbs_kursna_service.py:145)
   ↓
7. Redis: GET "nbs_kurs_EUR_2025-10-28"
   └─→ Vraća: "117.2516" ✓
```

### 🤖 Tok Automatskog Ažuriranja (Celery)

```
1. Celery Beat (cron scheduler)
   └─→ Svaki dan u 14:00
   (celery_worker.py:40-44)
   ↓
2. Celery Worker pokreće task
   └─→ update_daily_kursna_lista()
   (app/tasks/nbs_kursna_tasks.py:7)
   ↓
3. NBS SOAP API poziv
   └─→ fetch_kursna_lista_soap()
   ↓
4. Redis: SETEX za sve valute (EUR, USD, GBP, CHF)
```

---

## 🛠️ Korak-po-Korak Dijagnostika

### KORAK 1: Pokreni dijagnostički script

**NA SERVERU:**
```bash
python diagnose_kursevi.py
```

**Šta da tražiš:**

✅ **AKO VIDIŠ:**
```
[OK] Redis je aktivan
[OK] Uspešno zapisano: EUR/2025-10-28 = 123.4567
[OK] Uspešno pročitano: EUR/2025-10-28 = 123.4567
[OK] Vrednost se poklapa sa zapisanom!
```
→ **Redis radi! Problem je drugde (vidi KORAK 2)**

❌ **AKO VIDIŠ:**
```
[ERROR] Redis ping failed: Connection refused
```
→ **REŠENJE: Pokreni Redis**
```bash
# Ubuntu/Debian
sudo systemctl start redis
sudo systemctl status redis

# Ili ručno
redis-server
```

---

### KORAK 2: Proveri da li Redis URL u .env fajlu odgovara serveru

**Otvori .env fajl na serveru:**
```bash
cat .env | grep REDIS_URL
```

**Trebalo bi:**
```
REDIS_URL=redis://localhost:6379/0
```

**AKO JE DRUGAČIJE** (npr. `redis://some-cloud-server:6379`), proveri da li taj server radi.

---

### KORAK 3: Proveri logove

**Proveri Flask logove:**
```bash
tail -f logs/app.log | grep -i kurs
```

**Šta tražiš:**
```
INFO: Cached nbs_kurs_EUR_2025-10-28 = 117.2516  ✓ DOBRO
WARNING: Redis cache write error: ...            ❌ PROBLEM!
```

---

### KORAK 4: Ručno testiraj Redis na serveru

```bash
redis-cli

# U Redis CLI-ju:
> PING
PONG  # ← Trebalo bi da vidiš ovo

> SET nbs_kurs_TEST_2025-10-28 "999.9999" EX 3600
OK

> GET nbs_kurs_TEST_2025-10-28
"999.9999"  # ← Trebalo bi da vidiš ovo

> EXIT
```

**Ako bilo šta od ovoga ne radi**, Redis nije pravilno pokrenut.

---

## 🐛 Mogući Problemi i Rešenja

### Problem 1: Redis nije pokrenut
**Simptomi:**
- `[ERROR] Redis ping failed`

**Rešenje:**
```bash
sudo systemctl start redis
```

---

### Problem 2: Browser Cache
**Simptomi:**
- Flash poruka se prikazuje
- Ali vrednosti se ne menjaju

**Rešenje:**
Dodao sam `Cache-Control` header u `app/routes/admin.py:640-643`:
```python
response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
```

**Dodatno: Hard refresh u browseru**
- Chrome/Firefox: `Ctrl + Shift + R` (Windows) ili `Cmd + Shift + R` (Mac)

---

### Problem 3: Redis permissions
**Simptomi:**
- Redis radi ali ne može da piše

**Rešenje:**
```bash
# Proveri ko pokreće Redis
ps aux | grep redis

# Proveri permissions
ls -la /var/lib/redis
```

---

### Problem 4: Različite Redis instance (development vs production)
**Simptomi:**
- Lokalno radi, na serveru ne

**Proveri:**
```bash
# Na serveru:
echo $REDIS_URL
# Ili
cat .env | grep REDIS_URL
```

**Treba biti:**
```
REDIS_URL=redis://localhost:6379/0
```

---

## 📋 Checklist za Proveru

- [ ] Redis je pokrenut (`sudo systemctl status redis`)
- [ ] Redis odgovara na PING (`redis-cli PING`)
- [ ] REDIS_URL u .env je ispravan
- [ ] Flask aplikacija se konektuje na Redis (proveri logove)
- [ ] Browser cache je očišćen (Hard refresh: Ctrl+Shift+R)
- [ ] `diagnose_kursevi.py` prolazi sve provere

---

## 🚀 Finalno Testiranje

**Nakon što Redis radi:**

1. Otvori `/admin/kursevi`
2. Unesi novi kurs (npr. EUR = 999.9999)
3. Klikni "Sačuvaj Kurs"
4. **Hard refresh** (Ctrl+Shift+R)
5. Proveri da li se prikazuje novi kurs

**Ako i dalje ne radi**, pošalji output od `diagnose_kursevi.py` i logove.

---

## 📞 Kontakt za Podršku

Ako problem persista, pošalji:
1. Output od `python diagnose_kursevi.py`
2. Output od `redis-cli PING`
3. Screenshot Flash poruke
4. Screenshot stranice posle refresh-a
5. Flask logove: `tail -100 logs/app.log`

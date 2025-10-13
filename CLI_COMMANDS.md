# Flask CLI Komande

Flask aplikacija pruža nekoliko korisnih CLI komandi za upravljanje korisnicima i firmama.

## Podešavanje

Postavite `FLASK_APP` environment promenljivu:

```bash
# Windows CMD
set FLASK_APP=run.py

# Windows PowerShell
$env:FLASK_APP="run.py"

# Linux/Mac
export FLASK_APP=run.py
```

## Dostupne Komande

### 1. Kreiranje Admin Korisnika

Kreira novog admin korisnika sa interaktivnim promptovima:

```bash
flask create-admin
```

Ili direktno sa parametrima:

```bash
flask create-admin --email admin@example.com --full-name "Admin User"
```

**Šta radi:**
- Traži email i puno ime
- Traži lozinku (hidden input sa potvr dom)
- Kreira admin korisnika u bazi
- Prikazuje detalje kreiranog korisnika

### 2. Kreiranje Paušalac Korisnika

Kreira novog paušalac korisnika:

```bash
flask create-pausalac
```

Ili sa parametrima:

```bash
flask create-pausalac --email pausalac@example.com --full-name "Pausalac User" --firma-id 1
```

**Napomena:** Morate imati kreирану paušalnu firmu pre nego što možete kreirati paušalac korisnika.

### 3. Lista Svih Korisnika

Prikazuje listu svih korisnika u sistemu:

```bash
flask list-users
```

**Prikazuje:**
- ID korisnika
- Email
- Tip korisnika (ADMIN/PAUSALAC)
- Puno ime
- Povezanu firmu (za paušalce)
- Datum kreiranja
- Status (aktivan/neaktivan)

### 4. Lista Svih Firmi

Prikazuje listu svih paušalnih firmi:

```bash
flask list-firme
```

**Prikazuje:**
- ID firme
- Naziv
- PIB
- Matični broj
- Email
- Telefon
- Status

## Primeri Korišćenja

### Prvi Admin Korisnik (Bootstrap)

Kada prvi put podižeš aplikaciju i nemaš nijedan korisnika:

```bash
set FLASK_APP=run.py
flask create-admin
```

Prompt će tražiti:
```
Admin Email: admin@obveznik.com
Full Name: Administrator
Password: ********
Repeat for confirmation: ********
```

Output:
```
[SUCCESS] Admin korisnik admin@obveznik.com uspesno kreiran!
   ID: 1
   Email: admin@obveznik.com
   Full Name: Administrator
   Role: admin
```

### Provera Korisnika

```bash
flask list-users
```

Output:
```
[INFO] Ukupno korisnika: 1

[OK] ID: 1 | admin@obveznik.com | ADMIN
   Ime: Administrator
   Kreiran: 13.10.2025 14:30
```

## Dodatne Flask Komande

Flask takođe pruža standardne komande:

```bash
flask run                # Pokreni development server
flask shell              # Otvori Python shell sa app kontekstom
flask routes             # Prikaži sve route-ove
flask db upgrade         # Pokreni database migracije
flask db migrate         # Kreiraj novu migraciju
```

## Greške i Troubleshooting

**Greška: "Korisnik vec postoji"**
```
[ERROR] Korisnik sa email-om admin@test.com vec postoji!
```
Rešenje: Koristi drugi email ili obriši postojećeg korisnika kroz web interfejs.

**Greška: "Firma ne postoji"**
```
[ERROR] Pausalna firma sa ID 1 ne postoji!
```
Rešenje: Prvo kreiraj paušalnu firmu kroz web interfejs, ili proveri postojeće firme sa `flask list-firme`.

**Greška: "No such command"**
```
Error: No such command 'create-admin'
```
Rešenje: Proveri da li si postavio `FLASK_APP=run.py` i da li je aplikacija pravilno instalirana.

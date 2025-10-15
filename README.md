# maj-sbirka - Databáze rozhodnutí NSS

Web aplikace pro stahování a správu rozhodnutí Nejvyššího správního soudu ČR.

## 🎯 Funkce

- **Web GUI** - Moderní webové rozhraní na http://localhost:5001
- **Vyhledávání** - Fulltextové vyhledávání v rozhodnutích NSS
- **Multi-source** - Stahování z NSS sbírky + NSS Open Data
- **Automatické stahování** - Hromadné stahování plných textů
- **Job monitoring** - Sledování průběhu stahování v reálném čase
- **SQLite FTS5** - Rychlé fulltextové vyhledávání

## 📊 Statistiky (k 15.10.2025)

- **654 rozhodnutí** celkem
- **165 s plným textem** (25%)
- **489 zbývá stáhnout** (75%)

## 🚀 Spuštění

```bash
# Aktivace virtuálního prostředí
source venv/bin/activate

# Spuštění web serveru
python3 web_app.py

# Web rozhraní
open http://localhost:5001
```

## 📁 Struktura projektu

```
maj-sbirka/
├── web_app.py              # Flask web server + REST API
├── downloader.py           # Selenium scraper pro NSS sbírku
├── search_nss.py           # Import z NSS Open Data (xlsx)
├── storage.py              # SQLite databáze + FTS5
├── job_manager.py          # Správa background jobů
├── models.py               # Data modely
├── config.py               # Konfigurace
├── templates/
│   └── index.html          # Web GUI (HTML + JS)
└── data/
    ├── nss_decisions.db    # SQLite databáze
    └── pdfs/               # Stažené PDF soubory
```

## 🔧 Klíčové komponenty

### REST API Endpointy

- `GET /` - Web GUI
- `GET /api/stats` - Statistiky databáze
- `GET /api/decisions` - Seznam rozhodnutí (paginace, filtry)
- `POST /api/search_nss` - Vyhledávání v NSS sbírce
- `POST /api/download_all_without_text` - Hromadné stahování textů
- `POST /api/download_single` - Stažení jednoho textu
- `GET /api/jobs` - Seznam běžících jobů

### Databáze (SQLite + FTS5)

```sql
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    ecli TEXT UNIQUE,
    title TEXT,
    date TEXT,
    url TEXT,
    full_text TEXT,
    metadata TEXT -- JSON
)
```

### Zdroje dat

1. **NSS Sbírka** (sbirka.nssoud.cz) - S plnými texty
2. **NSS Open Data** (xlsx) - Metadata bez textů

## 🔍 Použití

### Vyhledávání v NSS sbírce
1. Zadej klíčová slova (např. "dotace EU")
2. Nastav limit (10-100)
3. Klikni "🔍 Vyhledat v NSS"
4. Sleduj progress bar

### Hromadné stahování textů
1. Nastav limit (max 200)
2. Klikni "📥 Stáhnout všechny bez textu"
3. Sleduj progress a počet stažených
4. Případně zruš tlačítkem "❌ Zrušit"

## 🐛 Opravy (15.10.2025)

- ✅ Opraveny statistiky v GUI
- ✅ Přidána podpora pro URL formát `?q=` 
- ✅ Hromadné stahování nyní funguje pro všechny zdroje

## 👤 Autor

M.A.J. Puzik - 14.-15.10.2025

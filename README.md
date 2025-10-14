# 🏛️ NSS Crawler

Automatický crawler pro judikaturu Nejvyššího správního soudu ČR s pokročilou funkcionalitou.

## 🎯 Stav projektu

**Verze:** 2.0.0
**Stav:** ✅ Plně funkční

### ✅ Implementováno

- ✅ Modulární architektura
- ✅ Web scraping NSS webu (vyhledavac.nssoud.cz)
- ✅ Paralelní stahování PDF (ThreadPoolExecutor)
- ✅ OCR konverze (Tesseract, pdf2image)
- ✅ SQLite databáze s FTS5 (fulltextové vyhledávání)
- ✅ Kompletní indexace
- ✅ Komplexní testy (test_pipeline.py)
- ✅ Konfigurovatelné parametry
- ✅ Detailní logování

## 📦 Struktura projektu

```
nss-crawler/
├── main.py              # Hlavní orchestrátor
├── config.py            # Konfigurace
├── models.py            # Datové modely
├── search_nss.py        # Web scraping NSS
├── download_nss.py      # Paralelní stahování
├── convert_ocr.py       # OCR konverze
├── storage.py           # SQLite databáze s FTS5
├── indexer.py           # Wrapper pro indexaci
├── test_pipeline.py     # Testy
├── requirements.txt     # Python závislosti
└── data/                # Datové adresáře
    ├── pdf/            # Stažené PDF
    ├── pdf_ocr/        # PDF s OCR
    ├── exports/        # Exporty
    ├── logs/           # Logy
    └── nss_decisions.db # SQLite databáze
```

## 🚀 Rychlý start

### 1. Instalace závislostí

```bash
cd /Users/majpuzik/apps/nss-crawler
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Systémové závislosti (macOS)

```bash
# Tesseract OCR s českým jazykem
brew install tesseract tesseract-lang

# Poppler pro pdf2image
brew install poppler
```

### 2. Konfigurace

Edituj `config.py`:

```python
# Režim běhu
DEBUG_MODE = True  # False pro produkci

# Klíčová slova
KEYWORDS = [
    "nezastavitelná plocha",
    "územní plán",
    "větrná elektrárna"
]

# Limity
MAX_RESULTS_PER_KEYWORD = 50

# Paralelizace
MAX_WORKERS_DOWNLOAD = 6  # Počet vláken pro stahování
MAX_WORKERS_OCR = 2       # Počet procesů pro OCR
```

### 3. Spuštění

```bash
# Demo režim (mock data)
python3 main.py

# Produkční režim (reálné stahování)
# Změň DEBUG_MODE = False v config.py
python3 main.py
```

### 4. Testy

```bash
python3 test_pipeline.py
```

## 📊 Pipeline crawleru

Crawler má 4 hlavní fáze:

### 1️⃣ Vyhledávání
- Crawling NSS webu (vyhledavac.nssoud.cz)
- Extrakce ECLI, názvu, data, URL
- Odstranění duplicit

### 2️⃣ Stahování
- Paralelní download PDF (ThreadPoolExecutor)
- Retry mechanika s exponenciálním backoffem
- Validace stažených PDF

### 3️⃣ OCR zpracování
- Detekce textu v PDF
- OCR pro skeny (Tesseract)
- Vytvoření searchable PDF
- Paralelní zpracování (ProcessPoolExecutor)

### 4️⃣ Indexace
- Uložení do SQLite databáze
- Fulltextová indexace (FTS5)
- Podpora Elasticsearch (připraveno)

## 🔍 Použití databáze

```python
from storage import DecisionStorage

# Připojení
storage = DecisionStorage()

# Fulltextové vyhledávání
results = storage.search_fulltext("územní plán", limit=10)

for decision in results:
    print(f"{decision.ecli}: {decision.title}")
    print(f"Text: {decision.full_text[:100]}...")

# Statistiky
stats = storage.get_stats()
print(f"Celkem: {stats['total']} rozhodnutí")
print(f"S OCR: {stats['with_ocr']}")

storage.close()
```

## ⚙️ Konfigurace

### Parametry v `config.py`

| Parametr | Popis | Výchozí |
|----------|-------|---------|
| `DEBUG_MODE` | Testovací režim | `True` |
| `MAX_RESULTS_PER_KEYWORD` | Max výsledků na slovo | `50` |
| `MAX_WORKERS_DOWNLOAD` | Paralelní stahování | `6` |
| `MAX_WORKERS_OCR` | Paralelní OCR | `2` |
| `OCR_LANGUAGE` | Jazyk pro Tesseract | `ces` |
| `OCR_DPI` | DPI pro OCR | `300` |
| `USE_ELASTICSEARCH` | Použít Elasticsearch | `False` |

### Cesty

| Cesta | Popis |
|-------|-------|
| `DATA_PATH` | `data/` |
| `PDF_STORAGE_PATH` | `data/pdf/` |
| `PDF_OCR_PATH` | `data/pdf_ocr/` |
| `DB_PATH` | `data/nss_decisions.db` |

## 🧪 Testování

```bash
# Spuštění všech testů
python3 test_pipeline.py

# Test jednotlivých modulů
python3 search_nss.py
python3 download_nss.py
python3 convert_ocr.py
python3 storage.py
python3 indexer.py
```

## 📈 Výkon

### Rychlost
- **Vyhledávání:** ~2-5s na klíčové slovo
- **Stahování:** 6 PDF paralelně (~10-30s celkem)
- **OCR:** 2 PDF paralelně (~30-60s na PDF)
- **Indexace:** ~0.1s na rozhodnutí

### Doporučení
- `MAX_WORKERS_DOWNLOAD = 6` (dobrý poměr rychlost/zátěž)
- `MAX_WORKERS_OCR = 2` (CPU-bound operace)
- `OCR_DPI = 300` (dobrý poměr kvalita/rychlost)

## 🛠️ Technologie

- **Python 3.9+**
- **Scraping:** requests, BeautifulSoup4
- **OCR:** pytesseract, pdf2image
- **Databáze:** SQLite s FTS5
- **Paralelizace:** ThreadPoolExecutor, ProcessPoolExecutor
- **PDF:** PyPDF2, reportlab

## 📝 Formát dat

### Decision objekt

```python
@dataclass
class Decision:
    ecli: str                    # ECLI identifikátor
    title: str                   # Název rozhodnutí
    date: Optional[datetime]     # Datum rozhodnutí
    url: Optional[str]           # URL na NSS webu
    pdf_path: Optional[str]      # Cesta k originálnímu PDF
    ocr_pdf_path: Optional[str]  # Cesta k PDF s OCR
    full_text: Optional[str]     # Plný text z OCR
    keywords: List[str]          # Klíčová slova
```

## 🐛 Známé problémy

1. **OCR kvalita:** Závisí na kvalitě skenů v PDF
2. **Rate limiting:** NSS web může blokovat příliš časté požadavky
3. **Memory:** OCR velkých PDF může spotřebovat hodně RAM

## 🔮 Plány do budoucna

- [ ] Elasticsearch integrace (připraveno)
- [ ] Export do PDF (připraveno v config)
- [ ] Web UI pro vyhledávání
- [ ] API endpoint
- [ ] Docker kontejner
- [ ] Inkrementální aktualizace

## 👨‍💻 Autor

**Majpuzik**
Vytvořeno s pomocí Claude Code

## 📜 Licence

MIT License

## 🙏 Poděkování

- Nejvyšší správní soud ČR za veřejně dostupná data
- Tesseract OCR projekt
- Python community

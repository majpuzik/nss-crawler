# 🏛️ NSS Crawler

Automatický crawler pro judikaturu Nejvyššího správního soudu ČR.

## 🎯 Současný stav

**Verze:** 1.0.0 (Demonstrační - zjednodušená)
**Stav:** Základní struktura připravena

### ✅ Implementováno
- ✅ Modulární architektura
- ✅ Konfigurace (config.py)
- ✅ Datové modely (models.py)
- ✅ Hlavní orchestrátor (main.py)
- ✅ Fázová struktura (5 fází)
- ✅ Logování a statistiky

### 🔨 K dokončení
- ⏳ search_nss.py - Reálný scraping NSS webu
- ⏳ download_nss.py - Paralelní stahování
- ⏳ convert_ocr.py - OCR konverze
- ⏳ storage.py - Databáze
- ⏳ indexer.py - Fulltextová indexace
- ⏳ exporter.py - Export do PDF

## 🚀 Rychlý start

### Instalace závislostí
```bash
pip3 install -r requirements.txt
```

### Spuštění (demo režim)
```bash
python3 main.py
```

## 📁 Struktura

```
nss-crawler/
├── main.py              # Hlavní orchestrátor
├── config.py            # Konfigurace
├── models.py            # Datové struktury
├── requirements.txt     # Python závislosti
└── data/                # Datové adresáře
    ├── pdf/            # Stažené PDF
    ├── pdf_ocr/        # PDF s OCR
    ├── exports/        # Exporty
    └── logs/           # Logy
```

## ⚙️ Konfigurace

Edituj `config.py`:

```python
# Klíčová slova
KEYWORDS = [
    "nezastavitelná plocha",
    "územní plán",
    "větrná elektrárna"
]

# Debug režim
DEBUG_MODE = True  # False pro produkci

# Paralelizace
MAX_WORKERS_DOWNLOAD = 6
MAX_WORKERS_OCR = 2
```

## 📊 Fáze crawleru

1. **Vyhledávání** - Crawling NSS webu
2. **Stahování** - Paralelní download
3. **OCR** - Konverze do PDF s OCR
4. **Indexace** - Fulltextová indexace
5. **Export** - Export do PDF (POVINNÝ)

## 👨‍💻 Autor

**Majpuzik** - Vytvořeno s pomocí Claude Code

## 📜 Licence

MIT License

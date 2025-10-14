"""
config.py
Konfigurace NSS crawleru
"""

import os
from pathlib import Path

# Režim běhu
DEBUG_MODE = True  # True = testovací režim s mock daty
MAX_RESULTS_PER_KEYWORD = 50  # Maximální výsledků na klíčové slovo

# Klíčová slova pro vyhledávání
KEYWORDS = [
    "nezastavitelná plocha",
    "územní plán",
    "větrná elektrárna"
]

# Cesty k adresářům
BASE_PATH = Path(__file__).parent
DATA_PATH = BASE_PATH / "data"
PDF_STORAGE_PATH = DATA_PATH / "pdf"
PDF_OCR_PATH = DATA_PATH / "pdf_ocr"
EXPORT_PATH = DATA_PATH / "exports"
LOG_PATH = DATA_PATH / "logs"
DB_PATH = DATA_PATH / "nss_decisions.db"

# HTTP nastavení
REQUEST_TIMEOUT = 30  # sekundy
MAX_RETRIES = 3
RETRY_DELAY = 2  # sekundy
USER_AGENT = "Mozilla/5.0 (NSS-Crawler/2.0)"

# Paralelizace
MAX_WORKERS_DOWNLOAD = 6  # Počet vláken pro stahování
MAX_WORKERS_OCR = 2  # Počet procesů pro OCR

# OCR nastavení
OCR_LANGUAGE = "ces"  # Český jazyk pro Tesseract
OCR_DPI = 300
PDF_OCR_ENABLED = True  # POVINNÉ - nelze vypnout

# Export nastavení
EXPORT_FORMAT = "pdf"  # POVINNÉ
EXPORT_METADATA = True
EXPORT_SINGLE_FILE = True  # True = jeden PDF, False = samostatné soubory
EXPORT_SEPARATOR_PAGES = True  # Prázdné stránky mezi rozhodnutími

# Elasticsearch
USE_ELASTICSEARCH = False  # True = použít ES, False = SQLite
ELASTICSEARCH_HOST = "localhost"
ELASTICSEARCH_PORT = 9200
ELASTICSEARCH_INDEX = "nss_decisions"

# NSS URL
NSS_SEARCH_URL = "https://vyhledavac.nssoud.cz/"

# Vytvoření adresářů
for path in [PDF_STORAGE_PATH, PDF_OCR_PATH, EXPORT_PATH, LOG_PATH]:
    path.mkdir(parents=True, exist_ok=True)

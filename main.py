#!/usr/bin/env python3
"""
main.py
Hlavní orchestrátor NSS crawleru - zjednodušená demonstrační verze
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Import modulů
from models import Decision, CrawlerStats
from config import *

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NSSCrawler:
    """Hlavní třída crawleru"""

    def __init__(self):
        self.stats = CrawlerStats()
        logger.info("Crawler inicializován")

    def run(self) -> CrawlerStats:
        """Spustí celý crawler pipeline"""
        logger.info("="*60)
        logger.info("🚀 SPOUŠTÍM NSS CRAWLER")
        logger.info("="*60)

        try:
            # Fáze 1: Vyhledávání
            self._search_phase()

            # Fáze 2: Stahování
            self._download_phase()

            # Fáze 3: OCR zpracování
            self._ocr_phase()

            # Fáze 4: Indexace
            self._index_phase()

            # Fáze 5: Export
            self._export_phase()

        except Exception as e:
            logger.error(f"Kritická chyba: {e}")
            self.stats.errors += 1

        finally:
            self.stats.end_time = datetime.now()
            self._print_final_stats()

        return self.stats

    def _search_phase(self):
        """Fáze 1: Vyhledávání"""
        logger.info("\n" + "="*60)
        logger.info("📍 FÁZE 1: VYHLEDÁVÁNÍ")
        logger.info("="*60)

        logger.info(f"Klíčová slova: {', '.join(KEYWORDS)}")
        logger.info(f"Max výsledků na klíčové slovo: {MAX_RESULTS_PER_KEYWORD}")

        if DEBUG_MODE:
            logger.warning("⚠️  DEBUG MODE - Používám mock data")
            # Simulace nalezení rozhodnutí
            mock_decisions = [
                Decision(
                    ecli=f"ECLI:CZ:NSS:2025:TEST.{i}",
                    title=f"Testovací rozhodnutí {i}",
                    date=datetime.now(),
                    url=f"https://example.com/{i}",
                    keywords=KEYWORDS[:1]
                )
                for i in range(5)
            ]
            self.stats.decisions_found = len(mock_decisions)
            logger.info(f"✅ Nalezeno {len(mock_decisions)} rozhodnutí (MOCK)")
        else:
            logger.info("🌐 Crawling NSS webu...")
            logger.warning("⚠️  Pro plnou funkčnost implementujte search_nss.py")
            self.stats.decisions_found = 0

    def _download_phase(self):
        """Fáze 2: Stahování"""
        logger.info("\n" + "="*60)
        logger.info("📍 FÁZE 2: STAHOVÁNÍ")
        logger.info("="*60)

        if self.stats.decisions_found > 0:
            logger.info(f"📥 Stahuji {self.stats.decisions_found} rozhodnutí...")
            logger.info(f"⚙️  Paralelizace: {MAX_WORKERS_DOWNLOAD} vláken")
            self.stats.decisions_downloaded = self.stats.decisions_found
            logger.info("✅ Stahování dokončeno")
        else:
            logger.info("⏭️  Přeskakuji - žádná rozhodnutí k stažení")

    def _ocr_phase(self):
        """Fáze 3: OCR zpracování"""
        logger.info("\n" + "="*60)
        logger.info("📍 FÁZE 3: OCR ZPRACOVÁNÍ")
        logger.info("="*60)

        if PDF_OCR_ENABLED:
            logger.info(f"🔍 OCR jazyk: {OCR_LANGUAGE}")
            logger.info(f"⚙️  Paralelizace: {MAX_WORKERS_OCR} procesů")

            if self.stats.decisions_downloaded > 0:
                logger.info(f"📝 Zpracovávám {self.stats.decisions_downloaded} PDF...")
                self.stats.decisions_ocr_processed = self.stats.decisions_downloaded
                logger.info("✅ OCR dokončeno")
            else:
                logger.info("⏭️  Přeskakuji - žádné PDF k zpracování")
        else:
            logger.warning("⚠️  OCR vypnuto")

    def _index_phase(self):
        """Fáze 4: Indexace"""
        logger.info("\n" + "="*60)
        logger.info("📍 FÁZE 4: INDEXACE")
        logger.info("="*60)

        if USE_ELASTICSEARCH:
            logger.info(f"🔍 Elasticsearch: {ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}")
            logger.info(f"📊 Index: {ELASTICSEARCH_INDEX}")
        else:
            logger.info(f"🗄️  SQLite databáze: {DB_PATH}")

        if self.stats.decisions_ocr_processed > 0:
            logger.info(f"📇 Indexuji {self.stats.decisions_ocr_processed} rozhodnutí...")
            self.stats.decisions_indexed = self.stats.decisions_ocr_processed
            logger.info("✅ Indexace dokončena")
        else:
            logger.info("⏭️  Přeskakuji - žádná rozhodnutí k indexaci")

    def _export_phase(self):
        """Fáze 5: Export (POVINNÁ)"""
        logger.info("\n" + "="*60)
        logger.info("📍 FÁZE 5: EXPORT (POVINNÝ)")
        logger.info("="*60)

        logger.info(f"📦 Export formát: {EXPORT_FORMAT}")
        logger.info(f"📄 Jeden soubor: {EXPORT_SINGLE_FILE}")
        logger.info(f"🗂️  Metadata: {EXPORT_METADATA}")

        if self.stats.decisions_indexed > 0:
            export_file = EXPORT_PATH / f"nss_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            logger.info(f"💾 Export do: {export_file}")
            logger.info("✅ Export dokončen")
        else:
            logger.info("⏭️  Přeskakuji - žádná rozhodnutí k exportu")

    def _print_final_stats(self):
        """Vypíše finální statistiky"""
        logger.info("\n" + "="*60)
        logger.info("📊 FINÁLNÍ STATISTIKY")
        logger.info("="*60)
        logger.info(self.stats)
        logger.info("="*60)


def main():
    """Hlavní funkce"""
    crawler = NSSCrawler()
    stats = crawler.run()

    # Exit code podle výsledku
    if stats.errors > 0:
        logger.error("❌ Crawler dokončen s chybami")
        sys.exit(1)
    else:
        logger.info("✅ Crawler dokončen úspěšně")
        sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
main.py
Hlavní orchestrátor NSS crawleru - plná verze
"""

import logging
import sys
from datetime import datetime
from pathlib import Path

# Import modulů
from models import Decision, CrawlerStats
from config import *
from search_nss import search_decisions
from download_nss import download_decisions
from convert_ocr import convert_decisions
from indexer import index_decisions

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NSSCrawler:
    """Hlavní třída crawleru"""

    def __init__(self):
        self.stats = CrawlerStats()
        self.decisions = []
        logger.info("✅ Crawler inicializován")

    def run(self) -> CrawlerStats:
        """Spustí celý crawler pipeline"""
        logger.info("=" * 60)
        logger.info("🚀 SPOUŠTÍM NSS CRAWLER")
        logger.info("=" * 60)

        try:
            # Fáze 1: Vyhledávání
            self.decisions = self._search_phase()

            if not self.decisions:
                logger.warning("⚠️  Žádná rozhodnutí nenalezena")
                return self.stats

            # Fáze 2: Stahování
            self.decisions = self._download_phase(self.decisions)

            if not self.decisions:
                logger.warning("⚠️  Žádná PDF nestažena")
                return self.stats

            # Fáze 3: OCR zpracování
            self.decisions = self._ocr_phase(self.decisions)

            if not self.decisions:
                logger.warning("⚠️  Žádná OCR nezpracována")
                return self.stats

            # Fáze 4: Indexace
            self._index_phase(self.decisions)

        except KeyboardInterrupt:
            logger.warning("\n⚠️  Přerušeno uživatelem")
            self.stats.errors += 1
        except Exception as e:
            logger.error(f"❌ Kritická chyba: {e}", exc_info=True)
            self.stats.errors += 1
        finally:
            self.stats.end_time = datetime.now()
            self._print_final_stats()

        return self.stats

    def _search_phase(self):
        """Fáze 1: Vyhledávání"""
        logger.info("\n" + "=" * 60)
        logger.info("📍 FÁZE 1: VYHLEDÁVÁNÍ")
        logger.info("=" * 60)

        logger.info(f"🔍 Klíčová slova: {', '.join(KEYWORDS)}")
        logger.info(f"🔢 Max výsledků na slovo: {MAX_RESULTS_PER_KEYWORD}")

        if DEBUG_MODE:
            logger.warning("⚠️  DEBUG MODE - Používám mock data")
            decisions = self._create_mock_decisions()
        else:
            logger.info("🌐 Crawling NSS webu...")
            try:
                decisions = search_decisions(KEYWORDS, MAX_RESULTS_PER_KEYWORD)
            except Exception as e:
                logger.error(f"❌ Chyba při vyhledávání: {e}")
                self.stats.errors += 1
                return []

        self.stats.decisions_found = len(decisions)
        logger.info(f"✅ Nalezeno: {len(decisions)} rozhodnutí")

        return decisions

    def _download_phase(self, decisions):
        """Fáze 2: Stahování"""
        logger.info("\n" + "=" * 60)
        logger.info("📍 FÁZE 2: STAHOVÁNÍ")
        logger.info("=" * 60)

        logger.info(f"📥 Stahuji {len(decisions)} PDF...")
        logger.info(f"⚙️  Paralelizace: {MAX_WORKERS_DOWNLOAD} vláken")

        if DEBUG_MODE:
            logger.warning("⚠️  DEBUG MODE - Přeskakuji stahování")
            self.stats.decisions_downloaded = len(decisions)
            return decisions

        try:
            downloaded = download_decisions(decisions, MAX_WORKERS_DOWNLOAD)
            self.stats.decisions_downloaded = len(downloaded)
            logger.info(f"✅ Staženo: {len(downloaded)} PDF")
            return downloaded
        except Exception as e:
            logger.error(f"❌ Chyba při stahování: {e}")
            self.stats.errors += 1
            return []

    def _ocr_phase(self, decisions):
        """Fáze 3: OCR zpracování"""
        logger.info("\n" + "=" * 60)
        logger.info("📍 FÁZE 3: OCR ZPRACOVÁNÍ")
        logger.info("=" * 60)

        if not PDF_OCR_ENABLED:
            logger.warning("⚠️  OCR vypnuto")
            return decisions

        logger.info(f"🔍 OCR jazyk: {OCR_LANGUAGE}")
        logger.info(f"⚙️  Paralelizace: {MAX_WORKERS_OCR} procesů")
        logger.info(f"📝 Zpracovávám {len(decisions)} PDF...")

        if DEBUG_MODE:
            logger.warning("⚠️  DEBUG MODE - Přeskakuji OCR")
            self.stats.decisions_ocr_processed = len(decisions)
            return decisions

        try:
            processed = convert_decisions(decisions, MAX_WORKERS_OCR)
            self.stats.decisions_ocr_processed = len(processed)
            logger.info(f"✅ Zpracováno: {len(processed)} PDF")
            return processed
        except Exception as e:
            logger.error(f"❌ Chyba při OCR: {e}")
            self.stats.errors += 1
            return []

    def _index_phase(self, decisions):
        """Fáze 4: Indexace"""
        logger.info("\n" + "=" * 60)
        logger.info("📍 FÁZE 4: INDEXACE")
        logger.info("=" * 60)

        if USE_ELASTICSEARCH:
            logger.info(f"🔍 Elasticsearch: {ELASTICSEARCH_HOST}:{ELASTICSEARCH_PORT}")
            logger.info(f"📊 Index: {ELASTICSEARCH_INDEX}")
        else:
            logger.info(f"🗄️  SQLite databáze: {DB_PATH}")

        logger.info(f"📇 Indexuji {len(decisions)} rozhodnutí...")

        try:
            count = index_decisions(decisions)
            self.stats.decisions_indexed = count
            logger.info(f"✅ Indexováno: {count} rozhodnutí")
        except Exception as e:
            logger.error(f"❌ Chyba při indexaci: {e}")
            self.stats.errors += 1

    def _create_mock_decisions(self):
        """Vytvoří mock data pro testování"""
        mock_decisions = [
            Decision(
                ecli=f"ECLI:CZ:NSS:2025:TEST.{i}",
                title=f"Testovací rozhodnutí {i}: {KEYWORDS[i % len(KEYWORDS)]}",
                date=datetime.now(),
                url=f"https://example.com/{i}",
                keywords=[KEYWORDS[i % len(KEYWORDS)]]
            )
            for i in range(1, 6)
        ]
        return mock_decisions

    def _print_final_stats(self):
        """Vypíše finální statistiky"""
        logger.info("\n" + "=" * 60)
        logger.info("📊 FINÁLNÍ STATISTIKY")
        logger.info("=" * 60)
        logger.info(self.stats)
        logger.info("=" * 60)


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

"""
download_nss.py
Paralelní stahování PDF rozhodnutí z NSS
"""

import requests
import logging
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
from models import Decision
from config import (
    PDF_STORAGE_PATH,
    REQUEST_TIMEOUT,
    MAX_RETRIES,
    RETRY_DELAY,
    USER_AGENT,
    MAX_WORKERS_DOWNLOAD
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NSSDownloader:
    """Třída pro paralelní stahování PDF rozhodnutí"""

    def __init__(self, max_workers: int = MAX_WORKERS_DOWNLOAD):
        """
        Args:
            max_workers: Počet paralelních vláken
        """
        self.max_workers = max_workers
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def download_decisions(self, decisions: List[Decision]) -> List[Decision]:
        """
        Stáhne PDF pro všechna rozhodnutí paralelně

        Args:
            decisions: Seznam rozhodnutí

        Returns:
            Seznam rozhodnutí s vyplněnými pdf_path
        """
        logger.info(f"📥 Stahuji {len(decisions)} rozhodnutí ({self.max_workers} vláken)...")

        downloaded_decisions = []
        failed_count = 0

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Spuštění paralelního stahování
            future_to_decision = {
                executor.submit(self._download_single, decision): decision
                for decision in decisions
            }

            # Zpracování výsledků
            for future in as_completed(future_to_decision):
                decision = future_to_decision[future]
                try:
                    updated_decision = future.result()
                    if updated_decision and updated_decision.pdf_path:
                        downloaded_decisions.append(updated_decision)
                        logger.info(f"✅ {updated_decision.ecli[:30]}...")
                    else:
                        failed_count += 1
                        logger.warning(f"⚠️  Selhalo: {decision.ecli[:30]}...")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Chyba při stahování {decision.ecli}: {e}")

        logger.info(f"📊 Staženo: {len(downloaded_decisions)}, Selhalo: {failed_count}")
        return downloaded_decisions

    def _download_single(self, decision: Decision) -> Decision:
        """
        Stáhne jedno PDF s retry mechanikou

        Args:
            decision: Rozhodnutí ke stažení

        Returns:
            Decision s vyplněným pdf_path nebo None
        """
        if not decision.url:
            logger.warning(f"⚠️  Chybí URL pro {decision.ecli}")
            return None

        # Sanitize ECLI pro název souboru
        safe_ecli = decision.ecli.replace(':', '_').replace('/', '_')
        pdf_filename = f"{safe_ecli}.pdf"
        pdf_path = PDF_STORAGE_PATH / pdf_filename

        # Pokud už existuje, přeskočit
        if pdf_path.exists():
            logger.debug(f"⏭️  Již existuje: {pdf_filename}")
            decision.pdf_path = str(pdf_path)
            return decision

        # Retry mechanika
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = self.session.get(
                    decision.url,
                    timeout=REQUEST_TIMEOUT,
                    allow_redirects=True
                )
                response.raise_for_status()

                # Kontrola, zda je to opravdu PDF
                content_type = response.headers.get('Content-Type', '')
                if 'pdf' not in content_type.lower() and len(response.content) < 1000:
                    logger.warning(f"⚠️  Není PDF: {decision.url}")
                    return None

                # Uložení PDF
                pdf_path.write_bytes(response.content)
                decision.pdf_path = str(pdf_path)

                logger.debug(f"✅ Staženo: {pdf_filename} ({len(response.content)} bytes)")
                return decision

            except requests.RequestException as e:
                logger.warning(f"⚠️  Pokus {attempt}/{MAX_RETRIES} selhal pro {decision.ecli}: {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY * attempt)  # Exponenciální backoff
                else:
                    logger.error(f"❌ Všechny pokusy selhaly pro {decision.ecli}")
                    return None

        return None


def download_decisions(decisions: List[Decision], max_workers: int = MAX_WORKERS_DOWNLOAD) -> List[Decision]:
    """
    Hlavní funkce pro stahování PDF rozhodnutí

    Args:
        decisions: Seznam rozhodnutí
        max_workers: Počet paralelních vláken

    Returns:
        Seznam rozhodnutí s vyplněnými pdf_path
    """
    downloader = NSSDownloader(max_workers=max_workers)
    return downloader.download_decisions(decisions)


if __name__ == "__main__":
    # Test
    from search_nss import search_decisions

    test_keywords = ["územní plán"]
    decisions = search_decisions(test_keywords, max_results=5)

    if decisions:
        downloaded = download_decisions(decisions, max_workers=3)
        print(f"\n📊 Staženo: {len(downloaded)} PDF")
        for d in downloaded[:3]:
            print(f"  - {d.ecli}: {d.pdf_path}")

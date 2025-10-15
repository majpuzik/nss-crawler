#!/usr/bin/env python3
"""
downloader.py
Stahování plných textů rozhodnutí ze sbírky NSS pomocí Selenium
"""

import logging
import time
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from models import Decision
from storage import DecisionStorage
from config import DB_PATH, PDF_STORAGE_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NSSSbirkaDownloader:
    """Stahování z veřejné sbírky NSS"""

    def __init__(self):
        self.storage = DecisionStorage(DB_PATH)

        # Selenium setup
        options = Options()
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--headless')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)

    def search_and_download(self, keywords, limit=10, job_status=None):
        """
        Vyhledá rozhodnutí v NSS sbírce a stáhne plné texty

        Args:
            keywords: Seznam klíčových slov
            limit: Maximální počet výsledků
            job_status: JobStatus objekt pro sledování progress

        Returns:
            Seznam stažených rozhodnutí
        """
        logger.info(f"🔍 Vyhledávám: {', '.join(keywords)}")

        if job_status:
            job_status.update(0, limit, "Připojování k NSS sbírce...")

        try:
            # Připravit search query
            if len(keywords) == 1:
                search_query = keywords[0]
            else:
                search_query = " ".join(keywords)

            # Otevřít přímo vyhledávací stránku s parametrem
            import urllib.parse
            encoded_query = urllib.parse.quote(search_query)
            search_url = f"http://sbirka.nssoud.cz/cz/vyhledavani?q={encoded_query}"

            logger.info(f"   URL: {search_url}")
            self.driver.get(search_url)
            time.sleep(3)

            try:
                # Počkat na výsledky
                results = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".list-item"))
                )

                logger.info(f"✅ Nalezeno {len(results)} výsledků")

                decisions = []
                for i, result in enumerate(results[:limit], 1):
                    # Kontrola zrušení
                    if job_status and job_status.cancel_requested:
                        logger.info("❌ Stahování zrušeno uživatelem")
                        if job_status:
                            job_status.status = "cancelled"
                            job_status.complete()
                        return decisions

                    try:
                        logger.info(f"\n📄 Výsledek {i}/{min(limit, len(results))}")

                        if job_status:
                            job_status.update(i, limit, f"Stahuji rozhodnutí {i}/{limit}...")

                        # Najít odkaz
                        link = result.find_element(By.CSS_SELECTOR, "a")
                        title = link.text.strip()
                        url = link.get_attribute("href")

                        if not url or len(title) < 10:
                            continue

                        logger.info(f"   {title[:80]}...")

                        # Otevřít detail v novém tabu
                        self.driver.execute_script("window.open(arguments[0], '_blank');", url)
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        time.sleep(2)

                        # Extrahovat text
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        full_text = body.text

                        if len(full_text) > 500:
                            # Zkontrolovat duplicitu podle URL
                            if self.storage.decision_exists_by_url(url):
                                logger.info(f"   ⚠️  Již existuje v databázi, přeskakuji")
                                continue

                            ecli = f"CZ:NSS:SBIRKA:{int(time.time())}:{i}"

                            decision = Decision(
                                ecli=ecli,
                                title=title,
                                url=url,
                                full_text=full_text,
                                keywords=keywords
                            )

                            decision.metadata = {
                                'court': 'NSS',
                                'source': 'sbirka.nssoud.cz',
                                'search_keywords': ', '.join(keywords)
                            }

                            # Uložit do databáze
                            if self.storage.save_decision(decision):
                                logger.info(f"   ✅ Uloženo: {len(full_text)} znaků")
                                decisions.append(decision)

                                if job_status:
                                    job_status.add_result(decision)

                                # Uložit do textového souboru
                                safe_name = ecli.replace(':', '_').replace('/', '_')
                                text_file = PDF_STORAGE_PATH / f"{safe_name}.txt"
                                text_file.write_text(full_text, encoding='utf-8')

                        # Zavřít tab
                        self.driver.close()
                        self.driver.switch_to.window(self.driver.window_handles[0])

                    except Exception as e:
                        logger.error(f"❌ Chyba u výsledku {i}: {e}")
                        if len(self.driver.window_handles) > 1:
                            self.driver.close()
                            self.driver.switch_to.window(self.driver.window_handles[0])
                        continue

                return decisions

            except Exception as e:
                logger.error(f"❌ Chyba při vyhledávání: {e}")
                self.driver.save_screenshot("error_screenshot.png")
                return []

        finally:
            pass  # Nezavírat driver, použít close() explicitně

    def download_by_spisova_znacka(self, spisova_znacka):
        """
        Stáhne rozhodnutí podle spisové značky

        Args:
            spisova_znacka: Spisová značka (např. "8 Afs 141/2025")

        Returns:
            Decision nebo None
        """
        logger.info(f"🔍 Stahuji: {spisova_znacka}")

        try:
            # Vyhledat na vyhledavac.nssoud.cz
            search_url = f"https://vyhledavac.nssoud.cz/?q={spisova_znacka.replace(' ', '+')}"
            self.driver.get(search_url)
            time.sleep(3)

            # Zkusit najít odkaz na detail
            try:
                detail_link = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='detail']"))
                )

                detail_link.click()
                time.sleep(2)

                # Extrahovat text
                body = self.driver.find_element(By.TAG_NAME, "body")
                full_text = body.text

                if len(full_text) > 500:
                    ecli = f"CZ:NSS:{spisova_znacka.replace(' ', '-')}"

                    decision = Decision(
                        ecli=ecli,
                        title=f"Rozhodnutí {spisova_znacka}",
                        url=self.driver.current_url,
                        full_text=full_text,
                        keywords=[]
                    )

                    decision.metadata = {
                        'court': 'NSS',
                        'source': 'vyhledavac.nssoud.cz',
                        'spisova_znacka': spisova_znacka
                    }

                    if self.storage.save_decision(decision):
                        logger.info(f"✅ Staženo: {len(full_text)} znaků")
                        return decision

            except Exception as e:
                logger.warning(f"⚠️  Nenalezeno ve vyhledávači: {e}")

        except Exception as e:
            logger.error(f"❌ Chyba při stahování: {e}")

        return None

    def close(self):
        """Zavře prohlížeč"""
        if self.driver:
            self.driver.quit()
        if self.storage:
            self.storage.close()


if __name__ == "__main__":
    downloader = NSSSbirkaDownloader()

    try:
        # Test vyhledávání
        decisions = downloader.search_and_download(["dotace", "eu"], limit=3)
        logger.info(f"\n✅ Celkem staženo: {len(decisions)} rozhodnutí")

    finally:
        downloader.close()

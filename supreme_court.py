"""
supreme_court.py
Crawler pro Nejvyšší soud ČR - https://sbirka.nsoud.cz
"""

import requests
import logging
import time
import random
from typing import List, Optional
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from models import Decision
from config import DATA_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User-Agent rotace
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
]


class SupremeCourtSearcher:
    """Crawler pro Nejvyšší soud ČR"""

    BASE_URL = "https://sbirka.nsoud.cz"
    SEARCH_URL = f"{BASE_URL}/rozsirene-vyhledavani-ve-sbirce/"
    RSS_URL = f"{BASE_URL}/feed/"

    def __init__(self, delay: float = 2.0, use_selenium: bool = True):
        """
        Args:
            delay: Prodleva mezi požadavky (v sekundách)
            use_selenium: Použít Selenium pro získání textů
        """
        self.delay = delay
        self.use_selenium = use_selenium
        self.driver = None

        if use_selenium:
            self._init_selenium()

    def _init_selenium(self):
        """Inicializuje Selenium driver"""
        logger.info("🚀 Inicializuji Selenium pro NS...")

        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        logger.info("✅ Selenium připraven")

    def search_decisions(self, keywords: List[str], max_results: int = 100) -> List[Decision]:
        """
        Vyhledá rozhodnutí podle klíčových slov

        Args:
            keywords: Seznam klíčových slov
            max_results: Maximální počet výsledků

        Returns:
            Seznam objektů Decision
        """
        logger.info(f"🔍 Vyhledávám v Nejvyšším soudu...")
        logger.info(f"📌 Klíčová slova: {', '.join(keywords)}")

        if not self.use_selenium:
            logger.error("❌ Nejvyšší soud vyžaduje Selenium (dynamický obsah)")
            return []

        decisions = []

        try:
            # Připravit search query
            search_query = " ".join(keywords)

            # Navigovat na vyhledávání
            self.driver.get(self.SEARCH_URL)
            time.sleep(self.delay)

            # Najít vyhledávací pole "V odůvodnění" (In Reasoning)
            try:
                search_input = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.NAME, "v_oduvodneni"))
                )
                search_input.clear()
                search_input.send_keys(search_query)
                logger.info(f"✅ Vyhledávací dotaz: {search_query}")

                # Odeslat formulář
                search_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                search_button.click()

                time.sleep(self.delay + random.uniform(-0.5, 0.5))

                # Parsovat výsledky
                decisions = self._parse_results_page(keywords, max_results)

            except Exception as e:
                logger.error(f"❌ Chyba při vyhledávání: {e}")

        except Exception as e:
            logger.error(f"❌ Chyba při načítání stránky: {e}")

        logger.info(f"✅ Nalezeno {len(decisions)} rozhodnutí")
        return decisions

    def _parse_results_page(self, keywords: List[str], max_results: int) -> List[Decision]:
        """Parsuje stránku s výsledky"""
        decisions = []

        try:
            # Počkat na výsledky
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "search-result-item"))
            )

            # Najít všechny výsledky
            result_items = self.driver.find_elements(By.CLASS_NAME, "search-result-item")

            for item in result_items[:max_results]:
                try:
                    # Extrakce dat
                    title_elem = item.find_element(By.CSS_SELECTOR, "h3 a")
                    title = title_elem.text.strip()
                    url = title_elem.get_attribute("href")

                    # ECLI
                    ecli = ""
                    try:
                        ecli_elem = item.find_element(By.CLASS_NAME, "ecli")
                        ecli = ecli_elem.text.strip()
                    except:
                        pass

                    # Spisová značka
                    case_number = ""
                    try:
                        case_elem = item.find_element(By.CLASS_NAME, "case-number")
                        case_number = case_elem.text.strip()
                    except:
                        pass

                    # Datum
                    date = None
                    try:
                        date_elem = item.find_element(By.CLASS_NAME, "decision-date")
                        date_str = date_elem.text.strip()
                        date = self._parse_date(date_str)
                    except:
                        pass

                    # Vytvoření Decision objektu
                    decision = Decision(
                        ecli=ecli or f"CZ:NS:{case_number.replace(' ', '-')}",
                        title=title or "Bez názvu",
                        date=date,
                        url=url,
                        keywords=keywords
                    )

                    decision.metadata = {
                        'court': 'Nejvyšší soud',
                        'case_number': case_number,
                        'source': 'sbirka.nsoud.cz'
                    }

                    decisions.append(decision)
                    logger.info(f"  ✅ {ecli or case_number}")

                except Exception as e:
                    logger.warning(f"  ⚠️  Chyba při parsování položky: {e}")
                    continue

        except Exception as e:
            logger.error(f"❌ Chyba při parsování výsledků: {e}")

        return decisions

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parsuje datum"""
        try:
            # Formát: "12. 1. 2025"
            return datetime.strptime(date_str.strip(), "%d. %m. %Y")
        except:
            try:
                # Formát: "2025-01-12"
                return datetime.strptime(date_str.strip(), "%Y-%m-%d")
            except:
                return None

    def get_rss_feed(self) -> List[Decision]:
        """Získá nejnovější rozhodnutí z RSS"""
        logger.info("📡 Získávám RSS feed...")

        decisions = []

        try:
            response = requests.get(self.RSS_URL, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')

            for item in items:
                try:
                    title = item.find('title').text
                    link = item.find('link').text
                    pub_date = item.find('pubDate').text

                    # Parsovat datum
                    date = None
                    try:
                        date = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
                    except:
                        pass

                    decision = Decision(
                        ecli=f"CZ:NS:RSS:{link.split('/')[-2]}",
                        title=title,
                        date=date,
                        url=link,
                        keywords=[]
                    )

                    decision.metadata = {
                        'court': 'Nejvyšší soud',
                        'source': 'RSS feed'
                    }

                    decisions.append(decision)

                except Exception as e:
                    logger.warning(f"  ⚠️  Chyba při parsování RSS položky: {e}")
                    continue

            logger.info(f"✅ RSS: {len(decisions)} nových rozhodnutí")

        except Exception as e:
            logger.error(f"❌ Chyba při načítání RSS: {e}")

        return decisions

    def __del__(self):
        """Cleanup Selenium driveru"""
        if self.driver:
            self.driver.quit()


def search_decisions(keywords: List[str], max_results: int = 100, use_selenium: bool = True) -> List[Decision]:
    """
    Hlavní funkce pro vyhledávání rozhodnutí NS

    Args:
        keywords: Seznam klíčových slov
        max_results: Maximální počet výsledků
        use_selenium: Použít Selenium

    Returns:
        Seznam objektů Decision
    """
    searcher = SupremeCourtSearcher(delay=2.0, use_selenium=use_selenium)
    return searcher.search_decisions(keywords, max_results)


def get_latest_from_rss() -> List[Decision]:
    """Získá nejnovější rozhodnutí z RSS"""
    searcher = SupremeCourtSearcher(use_selenium=False)
    return searcher.get_rss_feed()


if __name__ == "__main__":
    # Test
    test_keywords = ["územní plán"]
    results = search_decisions(test_keywords, max_results=5)

    print(f"\n📊 Nalezeno: {len(results)} rozhodnutí")
    for i, decision in enumerate(results, 1):
        print(f"\n{i}. {decision.title}")
        print(f"   ECLI: {decision.ecli}")
        print(f"   URL: {decision.url}")
        print(f"   Datum: {decision.date}")

    # Test RSS
    print("\n" + "="*60)
    print("📡 RSS Feed Test")
    print("="*60)
    rss_results = get_latest_from_rss()
    print(f"\n📊 RSS: {len(rss_results)} nejnovějších rozhodnutí")

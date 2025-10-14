"""
regional_courts.py
Crawler pro krajské soudy ČR
"""

import requests
import logging
import time
import random
from typing import List, Dict, Optional
from datetime import datetime
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from models import Decision

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# User-Agent rotace
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0',
]

# Seznam krajských soudů
REGIONAL_COURTS = {
    'KSOS': {
        'name': 'Krajský soud v Ostravě',
        'url': 'https://www.ksos.justice.cz',
        'search_url': 'https://www.ksos.justice.cz/rozhodnuti/',
    },
    'KSPH': {
        'name': 'Krajský soud v Praze',
        'url': 'https://www.ksph.justice.cz',
        'search_url': 'https://www.ksph.justice.cz/rozhodnuti/',
    },
    'KSBR': {
        'name': 'Krajský soud v Brně',
        'url': 'https://www.ksbr.justice.cz',
        'search_url': 'https://www.ksbr.justice.cz/rozhodnuti/',
    },
    'KSUL': {
        'name': 'Krajský soud v Ústí nad Labem',
        'url': 'https://www.ksul.justice.cz',
        'search_url': 'https://www.ksul.justice.cz/rozhodnuti/',
    },
    'KSHK': {
        'name': 'Krajský soud v Hradci Králové',
        'url': 'https://www.kshk.justice.cz',
        'search_url': 'https://www.kshk.justice.cz/rozhodnuti/',
    },
    'KSCB': {
        'name': 'Krajský soud v Českých Budějovicích',
        'url': 'https://www.kscb.justice.cz',
        'search_url': 'https://www.kscb.justice.cz/rozhodnuti/',
    },
    'KSPL': {
        'name': 'Krajský soud v Plzni',
        'url': 'https://www.kspl.justice.cz',
        'search_url': 'https://www.kspl.justice.cz/rozhodnuti/',
    },
}


class RegionalCourtSearcher:
    """Crawler pro krajské soudy"""

    def __init__(self, delay: float = 2.0, use_selenium: bool = True):
        """
        Args:
            delay: Prodleva mezi požadavky (v sekundách)
            use_selenium: Použít Selenium
        """
        self.delay = delay
        self.use_selenium = use_selenium
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': random.choice(USER_AGENTS)
        })

        if use_selenium:
            self._init_selenium()

    def _init_selenium(self):
        """Inicializuje Selenium driver"""
        logger.info("🚀 Inicializuji Selenium pro krajské soudy...")

        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument(f'user-agent={random.choice(USER_AGENTS)}')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        logger.info("✅ Selenium připraven")

    def search_all_courts(self, keywords: List[str], max_results_per_court: int = 20) -> List[Decision]:
        """
        Vyhledá ve všech krajských soudech

        Args:
            keywords: Seznam klíčových slov
            max_results_per_court: Max výsledků na soud

        Returns:
            Seznam objektů Decision
        """
        logger.info(f"🔍 Vyhledávám ve {len(REGIONAL_COURTS)} krajských soudech...")
        logger.info(f"📌 Klíčová slova: {', '.join(keywords)}")

        all_decisions = []

        for court_code, court_info in REGIONAL_COURTS.items():
            logger.info(f"\n📍 {court_info['name']} ({court_code})")

            try:
                decisions = self._search_court(
                    court_code,
                    court_info,
                    keywords,
                    max_results_per_court
                )
                all_decisions.extend(decisions)
                logger.info(f"  ✅ Nalezeno: {len(decisions)} rozhodnutí")

                # Pauza mezi soudy
                time.sleep(self.delay + random.uniform(-0.5, 0.5))

            except Exception as e:
                logger.error(f"  ❌ Chyba při vyhledávání v {court_code}: {e}")
                continue

        logger.info(f"\n✅ Celkem nalezeno {len(all_decisions)} rozhodnutí")
        return all_decisions

    def _search_court(
        self,
        court_code: str,
        court_info: Dict[str, str],
        keywords: List[str],
        max_results: int
    ) -> List[Decision]:
        """Vyhledá v jednom krajském soudu"""

        # Zkusit různé metody
        decisions = []

        # 1. Zkusit rozhodnuti.justice.cz (centrální portál)
        try:
            decisions = self._search_via_justice_portal(court_code, keywords, max_results)
            if decisions:
                return decisions
        except Exception as e:
            logger.debug(f"  rozhodnuti.justice.cz selhal: {e}")

        # 2. Zkusit Selenium na webu soudu
        if self.use_selenium:
            try:
                decisions = self._search_via_selenium(court_info, keywords, max_results)
                if decisions:
                    return decisions
            except Exception as e:
                logger.debug(f"  Selenium selhal: {e}")

        # 3. Zkusit RSS feed (pokud existuje)
        try:
            decisions = self._search_via_rss(court_info)
            if decisions:
                return decisions[:max_results]
        except Exception as e:
            logger.debug(f"  RSS selhal: {e}")

        return decisions

    def _search_via_justice_portal(
        self,
        court_code: str,
        keywords: List[str],
        max_results: int
    ) -> List[Decision]:
        """Vyhledá přes centrální portál rozhodnuti.justice.cz"""

        decisions = []
        search_query = " ".join(keywords)

        url = f"https://rozhodnuti.justice.cz/search?q={search_query}&court={court_code}"

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Parsovat výsledky (přizpůsobit skutečné struktuře)
            result_items = soup.select('.search-result-item')

            for item in result_items[:max_results]:
                try:
                    title = item.select_one('h3').text.strip()
                    link = item.select_one('a')['href']
                    ecli = item.select_one('.ecli').text.strip() if item.select_one('.ecli') else ""

                    decision = Decision(
                        ecli=ecli or f"CZ:{court_code}:{datetime.now().year}:TEMP",
                        title=title,
                        url=link if link.startswith('http') else f"https://rozhodnuti.justice.cz{link}",
                        keywords=keywords
                    )

                    decision.metadata = {
                        'court': court_code,
                        'source': 'rozhodnuti.justice.cz'
                    }

                    decisions.append(decision)

                except Exception as e:
                    logger.debug(f"  Chyba při parsování položky: {e}")
                    continue

        except Exception as e:
            logger.debug(f"Justice portál chyba: {e}")

        return decisions

    def _search_via_selenium(
        self,
        court_info: Dict[str, str],
        keywords: List[str],
        max_results: int
    ) -> List[Decision]:
        """Vyhledá pomocí Selenium na webu soudu"""

        decisions = []
        search_url = court_info.get('search_url', court_info['url'])

        try:
            self.driver.get(search_url)
            time.sleep(self.delay)

            # Zkusit najít vyhledávací formulář
            try:
                search_input = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='search'], input[name='q'], input[name='search']"))
                )

                search_query = " ".join(keywords)
                search_input.clear()
                search_input.send_keys(search_query)

                # Najít submit tlačítko
                submit_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
                submit_button.click()

                time.sleep(self.delay)

                # Parsovat výsledky (obecný pokus)
                result_items = self.driver.find_elements(By.CSS_SELECTOR, ".result-item, .decision-item, article")

                for item in result_items[:max_results]:
                    try:
                        title_elem = item.find_element(By.CSS_SELECTOR, "h2, h3, .title")
                        title = title_elem.text.strip()

                        link_elem = item.find_element(By.CSS_SELECTOR, "a")
                        link = link_elem.get_attribute("href")

                        decision = Decision(
                            ecli=f"CZ:{court_info['name'].split()[2].upper()}:{datetime.now().year}:TEMP",
                            title=title,
                            url=link,
                            keywords=keywords
                        )

                        decision.metadata = {
                            'court': court_info['name'],
                            'source': 'court website'
                        }

                        decisions.append(decision)

                    except Exception as e:
                        logger.debug(f"  Chyba při parsování Selenium položky: {e}")
                        continue

            except Exception as e:
                logger.debug(f"  Vyhledávací formulář nenalezen: {e}")

        except Exception as e:
            logger.debug(f"Selenium chyba: {e}")

        return decisions

    def _search_via_rss(self, court_info: Dict[str, str]) -> List[Decision]:
        """Zkusí najít a parsovat RSS feed"""

        decisions = []

        # Obvyklé URL pro RSS
        rss_urls = [
            f"{court_info['url']}/feed/",
            f"{court_info['url']}/rss/",
            f"{court_info['url']}/rozhodnuti/feed/",
        ]

        for rss_url in rss_urls:
            try:
                response = self.session.get(rss_url, timeout=10)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'xml')
                    items = soup.find_all('item')

                    for item in items:
                        try:
                            title = item.find('title').text
                            link = item.find('link').text

                            decision = Decision(
                                ecli=f"CZ:RSS:{link.split('/')[-2]}",
                                title=title,
                                url=link,
                                keywords=[]
                            )

                            decision.metadata = {
                                'court': court_info['name'],
                                'source': 'RSS feed'
                            }

                            decisions.append(decision)

                        except:
                            continue

                    if decisions:
                        logger.debug(f"  RSS úspěch: {rss_url}")
                        return decisions

            except:
                continue

        return decisions

    def __del__(self):
        """Cleanup"""
        if self.driver:
            self.driver.quit()


def search_all_courts(keywords: List[str], max_results_per_court: int = 20) -> List[Decision]:
    """
    Vyhledá ve všech krajských soudech

    Args:
        keywords: Seznam klíčových slov
        max_results_per_court: Max výsledků na soud

    Returns:
        Seznam objektů Decision
    """
    searcher = RegionalCourtSearcher(delay=2.0, use_selenium=True)
    return searcher.search_all_courts(keywords, max_results_per_court)


if __name__ == "__main__":
    # Test
    test_keywords = ["územní plán"]
    results = search_all_courts(test_keywords, max_results_per_court=3)

    print(f"\n📊 Celkem nalezeno: {len(results)} rozhodnutí")

    # Seskupit podle soudu
    by_court = {}
    for decision in results:
        court = decision.metadata.get('court', 'Neznámý')
        if court not in by_court:
            by_court[court] = []
        by_court[court].append(decision)

    for court, decisions in by_court.items():
        print(f"\n{court}: {len(decisions)} rozhodnutí")
        for i, decision in enumerate(decisions, 1):
            print(f"  {i}. {decision.title[:60]}...")
            print(f"     URL: {decision.url}")

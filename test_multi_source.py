#!/usr/bin/env python3
"""
test_multi_source.py
Test multi-source crawleru (NSS pouze, ostatní zatím testově vypnuté)
"""

import logging
from config import *

# Dočasně vypnout NS a krajské soudy (testujeme jen NSS xlsx)
ENABLE_NSS = True
ENABLE_SUPREME_COURT = False
ENABLE_REGIONAL_COURTS = False

from search_nss import search_decisions as search_nss

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_nss_only():
    """Test pouze NSS (xlsx data)"""
    logger.info("=" * 60)
    logger.info("🧪 TEST: NSS xlsx crawler")
    logger.info("=" * 60)

    keywords = ["územní plán"]
    max_results = 5

    logger.info(f"\n📌 Klíčová slova: {keywords}")
    logger.info(f"🔢 Max výsledků: {max_results}")

    try:
        decisions = search_nss(keywords, max_results)

        logger.info(f"\n✅ Nalezeno: {len(decisions)} rozhodnutí\n")

        for i, decision in enumerate(decisions, 1):
            print(f"{i}. {decision.title}")
            print(f"   ECLI: {decision.ecli}")
            print(f"   URL: {decision.url}")
            print(f"   Datum: {decision.date}")
            print(f"   Soud: {decision.metadata.get('court', 'N/A')}")
            print(f"   Spisová značka: {decision.metadata.get('spisova_znacka', 'N/A')}")
            print()

        return True

    except Exception as e:
        logger.error(f"❌ Chyba: {e}")
        return False


if __name__ == "__main__":
    success = test_nss_only()

    if success:
        print("\n" + "=" * 60)
        print("✅ TEST ÚSPĚŠNÝ")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("❌ TEST SELHAL")
        print("=" * 60)

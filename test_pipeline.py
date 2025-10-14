#!/usr/bin/env python3
"""
test_pipeline.py
Komplexní test NSS crawleru
"""

import unittest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

# Import modulů
from models import Decision, CrawlerStats
from search_nss import NSSSearcher
from download_nss import NSSDownloader
from storage import DecisionStorage
from indexer import DecisionIndexer
import config


class TestNSSCrawler(unittest.TestCase):
    """Testy pro NSS crawler"""

    @classmethod
    def setUpClass(cls):
        """Příprava před testy"""
        # Vytvoření dočasného adresáře pro testy
        cls.temp_dir = Path(tempfile.mkdtemp())

        # Nastavení testových cest
        cls.original_db = config.DB_PATH
        config.DB_PATH = cls.temp_dir / "test.sqlite"

        print(f"\n🧪 Testovací prostředí: {cls.temp_dir}")

    @classmethod
    def tearDownClass(cls):
        """Úklid po testech"""
        try:
            # Restore original config
            config.DB_PATH = cls.original_db
            shutil.rmtree(cls.temp_dir)
            print(f"🧹 Vyčištěno: {cls.temp_dir}")
        except Exception as e:
            print(f"⚠️  Chyba při úklidu: {e}")

    def test_01_decision_model(self):
        """Test datového modelu Decision"""
        print("\n▶️  Test 1: Decision model")

        decision = Decision(
            ecli="ECLI:CZ:NSS:2025:TEST.001",
            title="Testovací rozhodnutí",
            date=datetime(2025, 1, 1),
            url="http://test.cz"
        )

        self.assertEqual(decision.ecli, "ECLI:CZ:NSS:2025:TEST.001")
        self.assertIsNotNone(decision.title)

        print("   ✅ Decision model OK")

    def test_02_storage_init(self):
        """Test inicializace databáze"""
        print("\n▶️  Test 2: Inicializace databáze")

        storage = DecisionStorage(config.DB_PATH)

        # Kontrola, že DB existuje
        self.assertTrue(config.DB_PATH.exists())

        # Kontrola tabulek
        import sqlite3
        conn = sqlite3.connect(str(config.DB_PATH))
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        self.assertIn('decisions', tables)
        self.assertIn('decisions_fts', tables)

        conn.close()
        storage.close()

        print("   ✅ Databáze inicializována")

    def test_03_save_and_retrieve(self):
        """Test ukládání a načítání"""
        print("\n▶️  Test 3: Ukládání a načítání")

        storage = DecisionStorage(config.DB_PATH)

        # Vytvoření testovacího rozhodnutí
        decision = Decision(
            ecli="ECLI:CZ:NSS:2025:TEST.002",
            title="Test ukládání",
            date=datetime(2025, 1, 2),
            url="http://test2.cz",
            full_text="Testovací text rozhodnutí s klíčovými slovy: územní plán, výstavba"
        )

        # Uložení
        result = storage.save_decision(decision)
        self.assertTrue(result)

        # Načtení
        loaded = storage.get_decision("ECLI:CZ:NSS:2025:TEST.002")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.title, "Test ukládání")

        storage.close()

        print("   ✅ Ukládání a načítání OK")

    def test_04_fulltext_search(self):
        """Test fulltextového vyhledávání"""
        print("\n▶️  Test 4: Fulltextové vyhledávání")

        storage = DecisionStorage(config.DB_PATH)

        # Přidání testovacích rozhodnutí
        test_decisions = [
            Decision(
                ecli=f"ECLI:CZ:NSS:2025:FTS.00{i}",
                title=f"Rozhodnutí {i}",
                date=datetime(2025, 1, 1),
                url=f"http://test{i}.cz",
                full_text=text
            )
            for i, text in enumerate([
                "Výstavba v nezastavitelné ploše územního plánu",
                "Větrná elektrárna a krajinný ráz",
                "Rozhodnutí o vydání stavebního povolení"
            ], 1)
        ]

        for decision in test_decisions:
            storage.save_decision(decision)

        # Vyhledávání
        results = storage.search_fulltext("územní plán", limit=10)
        self.assertGreater(len(results), 0)

        results2 = storage.search_fulltext("větrná elektrárna", limit=10)
        self.assertGreater(len(results2), 0)

        storage.close()

        print(f"   ✅ Vyhledávání OK (nalezeno: {len(results)} a {len(results2)} výsledků)")

    def test_05_statistics(self):
        """Test statistik"""
        print("\n▶️  Test 5: Statistiky")

        storage = DecisionStorage(config.DB_PATH)
        stats = storage.get_stats()

        self.assertIn('total', stats)
        self.assertGreater(stats['total'], 0)

        storage.close()

        print(f"   ✅ Statistiky OK (celkem: {stats['total']} rozhodnutí)")

    def test_06_crawler_stats(self):
        """Test objektu CrawlerStats"""
        print("\n▶️  Test 6: CrawlerStats")

        stats = CrawlerStats()
        stats.decisions_found = 100
        stats.decisions_downloaded = 95
        stats.decisions_ocr_processed = 90
        stats.decisions_indexed = 90
        stats.errors = 5
        stats.end_time = datetime.now()

        duration = stats.duration()
        self.assertGreaterEqual(duration, 0)

        print("   ✅ CrawlerStats OK")

    def test_07_nss_searcher_init(self):
        """Test inicializace NSSSearcher"""
        print("\n▶️  Test 7: NSSSearcher inicializace")

        searcher = NSSSearcher(delay=0.5)
        self.assertIsNotNone(searcher.session)
        self.assertEqual(searcher.delay, 0.5)

        print("   ✅ NSSSearcher OK")

    def test_08_downloader_init(self):
        """Test inicializace NSSDownloader"""
        print("\n▶️  Test 8: NSSDownloader inicializace")

        downloader = NSSDownloader()
        self.assertIsNotNone(downloader.session)

        print("   ✅ NSSDownloader OK")

    def test_09_indexer(self):
        """Test indexeru"""
        print("\n▶️  Test 9: Indexer")

        indexer = DecisionIndexer()

        decision = Decision(
            ecli="ECLI:CZ:NSS:2025:IDX.001",
            title="Test indexace",
            date=datetime(2025, 1, 1),
            url="http://test.cz",
            full_text="Test indexace dokumentu"
        )

        result = indexer.index_decisions([decision])
        self.assertEqual(result, 1)

        indexer.close()

        print("   ✅ Indexer OK")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 NSS CRAWLER - TESTOVACÍ SUITE")
    print("="*60)

    # Spuštění unit testů
    print("\n📍 UNIT TESTY")
    print("-"*60)

    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestNSSCrawler)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Výsledek unit testů
    if result.wasSuccessful():
        print("\n" + "="*60)
        print("🎉 VŠECHNY TESTY ÚSPĚŠNÉ")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ Některé testy selhaly")
        print("="*60)

#!/usr/bin/env python3
"""
test_pipeline.py
Komplexní testy NSS crawleru
"""

import unittest
from datetime import datetime
from pathlib import Path
import tempfile
import shutil

from models import Decision, CrawlerStats
from search_nss import NSSSearcher
from storage import DecisionStorage
from indexer import DecisionIndexer


class TestDecisionModel(unittest.TestCase):
    """Testy pro Decision model"""

    def test_create_decision(self):
        """Test vytvoření Decision objektu"""
        decision = Decision(
            ecli="ECLI:CZ:NSS:2025:TEST.1",
            title="Test rozhodnutí",
            date=datetime.now(),
            url="https://example.com"
        )
        self.assertEqual(decision.ecli, "ECLI:CZ:NSS:2025:TEST.1")
        self.assertEqual(decision.title, "Test rozhodnutí")

    def test_decision_with_keywords(self):
        """Test Decision s klíčovými slovy"""
        decision = Decision(
            ecli="ECLI:CZ:NSS:2025:TEST.1",
            title="Test",
            keywords=["územní plán", "test"]
        )
        self.assertEqual(len(decision.keywords), 2)
        self.assertIn("územní plán", decision.keywords)


class TestCrawlerStats(unittest.TestCase):
    """Testy pro CrawlerStats"""

    def test_create_stats(self):
        """Test vytvoření statistik"""
        stats = CrawlerStats()
        self.assertEqual(stats.decisions_found, 0)
        self.assertEqual(stats.errors, 0)
        self.assertIsInstance(stats.start_time, datetime)

    def test_stats_duration(self):
        """Test výpočtu doby běhu"""
        stats = CrawlerStats()
        stats.end_time = datetime.now()
        duration = stats.duration()
        self.assertGreaterEqual(duration, 0)


class TestNSSSearcher(unittest.TestCase):
    """Testy pro NSSSearcher"""

    def setUp(self):
        self.searcher = NSSSearcher(delay=0.1)

    def test_extract_ecli(self):
        """Test extrakce ECLI"""
        text = "ECLI:CZ:NSS:2025:1A.123 nějaký text"
        ecli = self.searcher._extract_ecli(text)
        self.assertIn("ECLI:CZ:NSS", ecli)

    def test_extract_date(self):
        """Test extrakce data"""
        text = "Rozhodnutí ze dne 15.3.2025"
        date = self.searcher._extract_date(text)
        self.assertEqual(date, "15.3.2025")


class TestStorage(unittest.TestCase):
    """Testy pro DecisionStorage"""

    def setUp(self):
        """Vytvoří dočasnou databázi"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"
        self.storage = DecisionStorage(self.db_path)

    def tearDown(self):
        """Smaže dočasnou databázi"""
        self.storage.close()
        shutil.rmtree(self.temp_dir)

    def test_save_and_load_decision(self):
        """Test uložení a načtení rozhodnutí"""
        decision = Decision(
            ecli="ECLI:CZ:NSS:2025:TEST.1",
            title="Test rozhodnutí",
            date=datetime.now(),
            url="https://example.com",
            full_text="Toto je testovací text.",
            keywords=["test"]
        )

        # Uložení
        result = self.storage.save_decision(decision)
        self.assertTrue(result)

        # Načtení
        loaded = self.storage.get_decision(decision.ecli)
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.ecli, decision.ecli)
        self.assertEqual(loaded.title, decision.title)

    def test_save_multiple_decisions(self):
        """Test uložení více rozhodnutí"""
        decisions = [
            Decision(
                ecli=f"ECLI:CZ:NSS:2025:TEST.{i}",
                title=f"Test {i}",
                keywords=["test"]
            )
            for i in range(1, 4)
        ]

        count = self.storage.save_decisions(decisions)
        self.assertEqual(count, 3)

        # Ověření
        all_decisions = self.storage.get_all_decisions()
        self.assertEqual(len(all_decisions), 3)

    def test_fulltext_search(self):
        """Test fulltextového vyhledávání"""
        decisions = [
            Decision(
                ecli="ECLI:CZ:NSS:2025:TEST.1",
                title="Rozhodnutí o územním plánu",
                full_text="Toto rozhodnutí se týká územního plánu obce.",
                keywords=["územní plán"]
            ),
            Decision(
                ecli="ECLI:CZ:NSS:2025:TEST.2",
                title="Rozhodnutí o větrné elektrárně",
                full_text="Toto rozhodnutí se týká stavby větrné elektrárny.",
                keywords=["větrná elektrárna"]
            )
        ]

        self.storage.save_decisions(decisions)

        # Vyhledávání
        results = self.storage.search_fulltext("územní plán")
        self.assertGreater(len(results), 0)

        # Ověření, že výsledek obsahuje správné rozhodnutí
        eclis = [r.ecli for r in results]
        self.assertIn("ECLI:CZ:NSS:2025:TEST.1", eclis)

    def test_get_stats(self):
        """Test získání statistik databáze"""
        decisions = [
            Decision(
                ecli=f"ECLI:CZ:NSS:2025:TEST.{i}",
                title=f"Test {i}",
                full_text=f"Text {i}",
                ocr_pdf_path=f"/path/to/{i}.pdf" if i % 2 == 0 else None
            )
            for i in range(1, 6)
        ]

        self.storage.save_decisions(decisions)
        stats = self.storage.get_stats()

        self.assertEqual(stats['total'], 5)
        self.assertEqual(stats['with_ocr'], 2)
        self.assertEqual(stats['with_fulltext'], 5)


class TestIndexer(unittest.TestCase):
    """Testy pro DecisionIndexer"""

    def setUp(self):
        """Vytvoří dočasnou databázi"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test.db"

    def tearDown(self):
        """Smaže dočasnou databázi"""
        shutil.rmtree(self.temp_dir)

    def test_index_decisions(self):
        """Test indexace rozhodnutí"""
        # Použijeme SQLite pro testy
        import config
        original_db = config.DB_PATH
        config.DB_PATH = self.db_path

        indexer = DecisionIndexer()

        decisions = [
            Decision(
                ecli=f"ECLI:CZ:NSS:2025:TEST.{i}",
                title=f"Test {i}",
                keywords=["test"]
            )
            for i in range(1, 4)
        ]

        count = indexer.index_decisions(decisions)
        self.assertEqual(count, 3)

        # Ověření
        results = indexer.search("Test")
        self.assertGreater(len(results), 0)

        indexer.close()

        # Restore
        config.DB_PATH = original_db


def run_tests():
    """Spustí všechny testy"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Přidání testů
    suite.addTests(loader.loadTestsFromTestCase(TestDecisionModel))
    suite.addTests(loader.loadTestsFromTestCase(TestCrawlerStats))
    suite.addTests(loader.loadTestsFromTestCase(TestNSSSearcher))
    suite.addTests(loader.loadTestsFromTestCase(TestStorage))
    suite.addTests(loader.loadTestsFromTestCase(TestIndexer))

    # Spuštění
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("🧪 SPOUŠTÍM TESTY NSS CRAWLERU")
    print("=" * 60)

    success = run_tests()

    print("\n" + "=" * 60)
    if success:
        print("✅ VŠECHNY TESTY PROŠLY")
        sys.exit(0)
    else:
        print("❌ NĚKTERÉ TESTY SELHALY")
        sys.exit(1)

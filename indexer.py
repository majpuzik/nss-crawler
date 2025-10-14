"""
indexer.py
Wrapper pro indexaci rozhodnutí (SQLite nebo Elasticsearch)
"""

import logging
from typing import List
from models import Decision
from storage import DecisionStorage
from config import USE_ELASTICSEARCH, DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DecisionIndexer:
    """Třída pro indexaci rozhodnutí"""

    def __init__(self):
        """Inicializuje indexer"""
        self.use_elasticsearch = USE_ELASTICSEARCH

        if self.use_elasticsearch:
            logger.info("🔍 Používám Elasticsearch")
            # TODO: Implementace Elasticsearch
            raise NotImplementedError("Elasticsearch zatím není implementován")
        else:
            logger.info(f"🗄️  Používám SQLite: {DB_PATH}")
            self.storage = DecisionStorage(DB_PATH)

    def index_decisions(self, decisions: List[Decision]) -> int:
        """
        Indexuje rozhodnutí

        Args:
            decisions: Seznam rozhodnutí

        Returns:
            Počet úspěšně indexovaných
        """
        if not decisions:
            logger.warning("⚠️  Žádná rozhodnutí k indexaci")
            return 0

        logger.info(f"📇 Indexuji {len(decisions)} rozhodnutí...")

        if self.use_elasticsearch:
            return self._index_to_elasticsearch(decisions)
        else:
            return self._index_to_sqlite(decisions)

    def _index_to_sqlite(self, decisions: List[Decision]) -> int:
        """Indexuje do SQLite"""
        return self.storage.save_decisions(decisions)

    def _index_to_elasticsearch(self, decisions: List[Decision]) -> int:
        """Indexuje do Elasticsearch"""
        # TODO: Implementace Elasticsearch indexace
        raise NotImplementedError("Elasticsearch zatím není implementován")

    def search(self, query: str, limit: int = 100) -> List[Decision]:
        """
        Vyhledává v indexu

        Args:
            query: Vyhledávací dotaz
            limit: Maximální počet výsledků

        Returns:
            Seznam nalezených rozhodnutí
        """
        if self.use_elasticsearch:
            return self._search_elasticsearch(query, limit)
        else:
            return self._search_sqlite(query, limit)

    def _search_sqlite(self, query: str, limit: int) -> List[Decision]:
        """Vyhledává v SQLite"""
        return self.storage.search_fulltext(query, limit)

    def _search_elasticsearch(self, query: str, limit: int) -> List[Decision]:
        """Vyhledává v Elasticsearch"""
        # TODO: Implementace Elasticsearch vyhledávání
        raise NotImplementedError("Elasticsearch zatím není implementován")

    def get_stats(self) -> dict:
        """
        Získá statistiky indexu

        Returns:
            Dict se statistikami
        """
        if self.use_elasticsearch:
            return self._get_elasticsearch_stats()
        else:
            return self.storage.get_stats()

    def _get_elasticsearch_stats(self) -> dict:
        """Získá statistiky z Elasticsearch"""
        # TODO: Implementace Elasticsearch statistik
        raise NotImplementedError("Elasticsearch zatím není implementován")

    def close(self):
        """Zavře připojení"""
        if not self.use_elasticsearch and self.storage:
            self.storage.close()


def index_decisions(decisions: List[Decision]) -> int:
    """
    Hlavní funkce pro indexaci

    Args:
        decisions: Seznam rozhodnutí

    Returns:
        Počet úspěšně indexovaných
    """
    indexer = DecisionIndexer()
    count = indexer.index_decisions(decisions)
    indexer.close()
    return count


if __name__ == "__main__":
    # Test
    from datetime import datetime

    test_decisions = [
        Decision(
            ecli="ECLI:CZ:NSS:2025:TEST.1",
            title="Testovací rozhodnutí o územním plánu",
            date=datetime.now(),
            url="https://example.com/1",
            full_text="Toto je testovací text rozhodnutí o územním plánu.",
            keywords=["test", "územní plán"]
        ),
        Decision(
            ecli="ECLI:CZ:NSS:2025:TEST.2",
            title="Testovací rozhodnutí o větrné elektrárně",
            date=datetime.now(),
            url="https://example.com/2",
            full_text="Toto je testovací text rozhodnutí o větrné elektrárně.",
            keywords=["test", "větrná elektrárna"]
        )
    ]

    # Indexace
    count = index_decisions(test_decisions)
    print(f"✅ Indexováno: {count} rozhodnutí")

    # Vyhledávání
    indexer = DecisionIndexer()
    results = indexer.search("územní plán")
    print(f"🔍 Nalezeno: {len(results)} rozhodnutí")

    for r in results:
        print(f"  - {r.ecli}: {r.title}")

    # Statistiky
    stats = indexer.get_stats()
    print(f"📊 Statistiky: {stats}")

    indexer.close()

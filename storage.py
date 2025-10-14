"""
storage.py
SQLite databáze s FTS5 pro fulltextové vyhledávání
"""

import sqlite3
import logging
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from models import Decision
from config import DB_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DecisionStorage:
    """Třída pro práci s SQLite databází"""

    def __init__(self, db_path: Path = DB_PATH):
        """
        Args:
            db_path: Cesta k databázi
        """
        self.db_path = db_path
        self.conn = None
        self._init_database()

    def _init_database(self):
        """Inicializuje databázi a vytvoří tabulky"""
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row

        cursor = self.conn.cursor()

        # Vytvoření hlavní tabulky
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ecli TEXT UNIQUE NOT NULL,
                title TEXT,
                date TEXT,
                url TEXT,
                pdf_path TEXT,
                ocr_pdf_path TEXT,
                full_text TEXT,
                keywords TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Vytvoření FTS5 tabulky pro fulltextové vyhledávání
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS decisions_fts USING fts5(
                ecli UNINDEXED,
                title,
                full_text,
                content='decisions',
                content_rowid='id'
            )
        """)

        # Triggery pro synchronizaci s FTS5
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS decisions_ai AFTER INSERT ON decisions BEGIN
                INSERT INTO decisions_fts(rowid, ecli, title, full_text)
                VALUES (new.id, new.ecli, new.title, new.full_text);
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS decisions_ad AFTER DELETE ON decisions BEGIN
                DELETE FROM decisions_fts WHERE rowid = old.id;
            END;
        """)

        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS decisions_au AFTER UPDATE ON decisions BEGIN
                UPDATE decisions_fts
                SET title = new.title, full_text = new.full_text
                WHERE rowid = new.id;
            END;
        """)

        # Indexy pro rychlé vyhledávání
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ecli ON decisions(ecli)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON decisions(date)")

        self.conn.commit()
        logger.info(f"✅ Databáze inicializována: {self.db_path}")

    def save_decision(self, decision: Decision) -> bool:
        """
        Uloží rozhodnutí do databáze

        Args:
            decision: Rozhodnutí k uložení

        Returns:
            True pokud úspěšné
        """
        try:
            cursor = self.conn.cursor()

            # Konverze keywords na string
            keywords_str = ",".join(decision.keywords) if decision.keywords else ""

            # Konverze datetime na string
            date_str = decision.date.isoformat() if decision.date else None

            cursor.execute("""
                INSERT OR REPLACE INTO decisions
                (ecli, title, date, url, pdf_path, ocr_pdf_path, full_text, keywords, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                decision.ecli,
                decision.title,
                date_str,
                decision.url,
                decision.pdf_path,
                decision.ocr_pdf_path,
                decision.full_text,
                keywords_str,
                datetime.now().isoformat()
            ))

            self.conn.commit()
            return True

        except sqlite3.Error as e:
            logger.error(f"❌ Chyba při ukládání {decision.ecli}: {e}")
            return False

    def save_decisions(self, decisions: List[Decision]) -> int:
        """
        Uloží více rozhodnutí najednou

        Args:
            decisions: Seznam rozhodnutí

        Returns:
            Počet úspěšně uložených
        """
        saved_count = 0
        for decision in decisions:
            if self.save_decision(decision):
                saved_count += 1

        logger.info(f"💾 Uloženo: {saved_count}/{len(decisions)} rozhodnutí")
        return saved_count

    def get_decision(self, ecli: str) -> Optional[Decision]:
        """
        Načte rozhodnutí podle ECLI

        Args:
            ecli: ECLI identifikátor

        Returns:
            Decision nebo None
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM decisions WHERE ecli = ?", (ecli,))
        row = cursor.fetchone()

        if row:
            return self._row_to_decision(row)
        return None

    def search_fulltext(self, query: str, limit: int = 100) -> List[Decision]:
        """
        Fulltextové vyhledávání v rozhodnutích

        Args:
            query: Vyhledávací dotaz
            limit: Maximální počet výsledků

        Returns:
            Seznam nalezených rozhodnutí
        """
        cursor = self.conn.cursor()

        # FTS5 dotaz
        cursor.execute("""
            SELECT d.* FROM decisions d
            JOIN decisions_fts fts ON d.id = fts.rowid
            WHERE decisions_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))

        rows = cursor.fetchall()
        return [self._row_to_decision(row) for row in rows]

    def get_all_decisions(self, limit: Optional[int] = None) -> List[Decision]:
        """
        Načte všechna rozhodnutí

        Args:
            limit: Maximální počet výsledků

        Returns:
            Seznam rozhodnutí
        """
        cursor = self.conn.cursor()

        if limit:
            cursor.execute("SELECT * FROM decisions ORDER BY date DESC LIMIT ?", (limit,))
        else:
            cursor.execute("SELECT * FROM decisions ORDER BY date DESC")

        rows = cursor.fetchall()
        return [self._row_to_decision(row) for row in rows]

    def get_stats(self) -> dict:
        """
        Získá statistiky databáze

        Returns:
            Dict se statistikami
        """
        cursor = self.conn.cursor()

        # Celkový počet
        cursor.execute("SELECT COUNT(*) FROM decisions")
        total = cursor.fetchone()[0]

        # Počet s OCR
        cursor.execute("SELECT COUNT(*) FROM decisions WHERE ocr_pdf_path IS NOT NULL")
        with_ocr = cursor.fetchone()[0]

        # Počet s full textem
        cursor.execute("SELECT COUNT(*) FROM decisions WHERE full_text IS NOT NULL")
        with_text = cursor.fetchone()[0]

        return {
            "total": total,
            "with_ocr": with_ocr,
            "with_fulltext": with_text
        }

    def _row_to_decision(self, row: sqlite3.Row) -> Decision:
        """Konvertuje SQLite řádek na Decision objekt"""
        # Konverze date string na datetime
        date_obj = None
        if row['date']:
            try:
                date_obj = datetime.fromisoformat(row['date'])
            except ValueError:
                pass

        # Konverze keywords string na list
        keywords = row['keywords'].split(',') if row['keywords'] else []

        return Decision(
            ecli=row['ecli'],
            title=row['title'],
            date=date_obj,
            url=row['url'],
            pdf_path=row['pdf_path'],
            ocr_pdf_path=row['ocr_pdf_path'],
            full_text=row['full_text'],
            keywords=keywords
        )

    def close(self):
        """Zavře připojení k databázi"""
        if self.conn:
            self.conn.close()
            logger.info("✅ Databáze uzavřena")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


if __name__ == "__main__":
    # Test
    storage = DecisionStorage()

    # Test data
    test_decision = Decision(
        ecli="ECLI:CZ:NSS:2025:TEST.1",
        title="Testovací rozhodnutí",
        date=datetime.now(),
        url="https://example.com",
        full_text="Toto je testovací text rozhodnutí o územním plánu.",
        keywords=["test", "územní plán"]
    )

    # Uložení
    storage.save_decision(test_decision)

    # Načtení
    loaded = storage.get_decision(test_decision.ecli)
    print(f"Načteno: {loaded.title}")

    # Fulltextové vyhledávání
    results = storage.search_fulltext("územní plán")
    print(f"Nalezeno: {len(results)} rozhodnutí")

    # Statistiky
    stats = storage.get_stats()
    print(f"Statistiky: {stats}")

    storage.close()

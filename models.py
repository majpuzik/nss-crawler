"""
models.py
Datové struktury pro NSS crawler
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Decision:
    """Reprezentace jednoho soudního rozhodnutí"""

    ecli: str
    title: str
    date: Optional[datetime] = None
    url: Optional[str] = None
    pdf_path: Optional[str] = None
    ocr_pdf_path: Optional[str] = None
    full_text: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def __str__(self):
        return f"Decision({self.ecli}, {self.title})"


@dataclass
class CrawlerStats:
    """Statistiky běhu crawleru"""

    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    decisions_found: int = 0
    decisions_downloaded: int = 0
    decisions_ocr_processed: int = 0
    decisions_indexed: int = 0
    errors: int = 0

    def duration(self) -> float:
        """Vrací dobu běhu v sekundách"""
        if self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return (datetime.now() - self.start_time).total_seconds()

    def __str__(self):
        return f"""Crawler Stats:
  Duration: {self.duration():.1f}s
  Found: {self.decisions_found}
  Downloaded: {self.decisions_downloaded}
  OCR Processed: {self.decisions_ocr_processed}
  Indexed: {self.decisions_indexed}
  Errors: {self.errors}"""

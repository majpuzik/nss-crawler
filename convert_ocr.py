"""
convert_ocr.py
OCR konverze PDF rozhodnutí pomocí Tesseract
"""

import logging
import subprocess
from pathlib import Path
from typing import List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import pytesseract
from pdf2image import convert_from_path
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import io

from models import Decision
from config import (
    PDF_STORAGE_PATH,
    PDF_OCR_PATH,
    OCR_LANGUAGE,
    OCR_DPI,
    MAX_WORKERS_OCR
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PDFOCRConverter:
    """Třída pro OCR konverzi PDF"""

    def __init__(self, max_workers: int = MAX_WORKERS_OCR):
        """
        Args:
            max_workers: Počet paralelních procesů
        """
        self.max_workers = max_workers
        self.ocr_language = OCR_LANGUAGE
        self.dpi = OCR_DPI

    def convert_decisions(self, decisions: List[Decision]) -> List[Decision]:
        """
        Konvertuje všechna PDF s OCR paralelně

        Args:
            decisions: Seznam rozhodnutí s pdf_path

        Returns:
            Seznam rozhodnutí s vyplněnými ocr_pdf_path a full_text
        """
        logger.info(f"📝 Zpracovávám {len(decisions)} PDF ({self.max_workers} procesů)...")

        processed_decisions = []
        failed_count = 0

        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Spuštění paralelního OCR
            future_to_decision = {
                executor.submit(self._convert_single, decision): decision
                for decision in decisions
            }

            # Zpracování výsledků
            for future in as_completed(future_to_decision):
                decision = future_to_decision[future]
                try:
                    updated_decision = future.result()
                    if updated_decision and updated_decision.ocr_pdf_path:
                        processed_decisions.append(updated_decision)
                        logger.info(f"✅ {updated_decision.ecli[:30]}...")
                    else:
                        failed_count += 1
                        logger.warning(f"⚠️  Selhalo: {decision.ecli[:30]}...")
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Chyba při OCR {decision.ecli}: {e}")

        logger.info(f"📊 Zpracováno: {len(processed_decisions)}, Selhalo: {failed_count}")
        return processed_decisions

    def _convert_single(self, decision: Decision) -> Decision:
        """
        Konvertuje jedno PDF s OCR

        Args:
            decision: Rozhodnutí s pdf_path

        Returns:
            Decision s vyplněným ocr_pdf_path a full_text
        """
        if not decision.pdf_path:
            logger.warning(f"⚠️  Chybí PDF pro {decision.ecli}")
            return None

        pdf_path = Path(decision.pdf_path)
        if not pdf_path.exists():
            logger.warning(f"⚠️  PDF neexistuje: {pdf_path}")
            return None

        # Výstupní cesta
        safe_ecli = decision.ecli.replace(':', '_').replace('/', '_')
        ocr_pdf_filename = f"{safe_ecli}_ocr.pdf"
        ocr_pdf_path = PDF_OCR_PATH / ocr_pdf_filename

        # Pokud už existuje, přeskočit
        if ocr_pdf_path.exists():
            logger.debug(f"⏭️  Již existuje: {ocr_pdf_filename}")
            decision.ocr_pdf_path = str(ocr_pdf_path)
            decision.full_text = self._extract_text_from_pdf(ocr_pdf_path)
            return decision

        try:
            # Metoda 1: Zkusit extrahovat text přímo z PDF
            existing_text = self._extract_text_from_pdf(pdf_path)

            if existing_text and len(existing_text.strip()) > 100:
                # PDF už má text, pouze zkopírovat
                logger.debug(f"📄 PDF už má text, kopíruji: {decision.ecli[:30]}...")
                ocr_pdf_path.write_bytes(pdf_path.read_bytes())
                decision.ocr_pdf_path = str(ocr_pdf_path)
                decision.full_text = existing_text
                return decision

            # Metoda 2: PDF je sken, musíme udělat OCR
            logger.debug(f"🔍 Provádím OCR: {decision.ecli[:30]}...")

            # Konverze PDF na obrázky
            images = convert_from_path(
                str(pdf_path),
                dpi=self.dpi,
                fmt='png'
            )

            # OCR pro každou stránku
            full_text_parts = []
            for i, image in enumerate(images):
                text = pytesseract.image_to_string(
                    image,
                    lang=self.ocr_language
                )
                full_text_parts.append(text)
                logger.debug(f"  Stránka {i+1}/{len(images)}: {len(text)} znaků")

            full_text = "\n\n--- NOVÁ STRÁNKA ---\n\n".join(full_text_parts)

            # Vytvoření PDF s textem
            self._create_searchable_pdf(images, full_text_parts, ocr_pdf_path)

            decision.ocr_pdf_path = str(ocr_pdf_path)
            decision.full_text = full_text

            logger.debug(f"✅ OCR dokončeno: {decision.ecli[:30]}... ({len(full_text)} znaků)")
            return decision

        except Exception as e:
            logger.error(f"❌ Chyba při OCR {decision.ecli}: {e}")
            return None

    def _extract_text_from_pdf(self, pdf_path: Path) -> str:
        """Extrahuje text z PDF"""
        try:
            reader = PdfReader(str(pdf_path))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.debug(f"⚠️  Nelze extrahovat text z {pdf_path}: {e}")
            return ""

    def _create_searchable_pdf(self, images: List, texts: List[str], output_path: Path):
        """Vytvoří PDF s vloženým textem (searchable PDF)"""
        try:
            # Jednoduchá verze: vytvoříme nové PDF s textem
            writer = PdfWriter()

            for i, (image, text) in enumerate(zip(images, texts)):
                # Konverze obrázku na PDF stránku
                img_path = PDF_OCR_PATH / f"temp_page_{i}.pdf"

                # Uložíme obrázek jako PDF pomocí reportlab
                packet = io.BytesIO()
                can = canvas.Canvas(packet, pagesize=A4)

                # Vložíme obrázek
                width, height = A4
                can.drawInlineImage(image, 0, 0, width=width, height=height)

                # Vložíme neviditelný text (pro vyhledávání)
                can.setFillColorRGB(1, 1, 1)  # Bílá barva = neviditelné
                can.setFont("Helvetica", 8)
                can.drawString(10, 10, text[:1000])  # První část textu

                can.save()

                # Přidáme stránku
                packet.seek(0)
                page_reader = PdfReader(packet)
                writer.add_page(page_reader.pages[0])

            # Uložíme výsledné PDF
            with open(output_path, 'wb') as output_file:
                writer.write(output_file)

        except Exception as e:
            logger.warning(f"⚠️  Chyba při vytváření searchable PDF: {e}")
            # Fallback: pouze zkopírovat originál
            output_path.write_bytes(images[0].tobytes())


def convert_decisions(decisions: List[Decision], max_workers: int = MAX_WORKERS_OCR) -> List[Decision]:
    """
    Hlavní funkce pro OCR konverzi

    Args:
        decisions: Seznam rozhodnutí s pdf_path
        max_workers: Počet paralelních procesů

    Returns:
        Seznam rozhodnutí s vyplněnými ocr_pdf_path a full_text
    """
    converter = PDFOCRConverter(max_workers=max_workers)
    return converter.convert_decisions(decisions)


if __name__ == "__main__":
    # Test
    from search_nss import search_decisions
    from download_nss import download_decisions

    test_keywords = ["územní plán"]
    decisions = search_decisions(test_keywords, max_results=2)

    if decisions:
        downloaded = download_decisions(decisions, max_workers=2)
        if downloaded:
            processed = convert_decisions(downloaded, max_workers=1)
            print(f"\n📊 Zpracováno: {len(processed)} PDF")
            for d in processed:
                print(f"  - {d.ecli}")
                print(f"    OCR: {d.ocr_pdf_path}")
                print(f"    Text: {len(d.full_text) if d.full_text else 0} znaků")

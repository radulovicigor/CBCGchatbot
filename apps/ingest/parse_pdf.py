"""
PDF parsing pomoću PyMuPDF.
"""
import fitz  # PyMuPDF
from typing import Iterator, Dict


def extract_pdf(path: str) -> Iterator[Dict]:
    """
    Ekstrakcija teksta sa stranica PDF-a.
    
    Args:
        path: Putanja do PDF fajla
        
    Yields:
        {'page': int, 'text': str}
    """
    doc = fitz.open(path)
    for i, page in enumerate(doc):
        text = page.get_text("text")
        yield {"page": i + 1, "text": text}
    doc.close()


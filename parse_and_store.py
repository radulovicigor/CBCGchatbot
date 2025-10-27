"""Parsiraj PDF i sačuvaj lokalno."""
import sys
from pathlib import Path

# Dodaj apps u path
sys.path.insert(0, str(Path(__file__).parent))

from apps.ingest.parse_pdf import extract_pdf
from apps.ingest.chunking import chunk
from apps.ingest.local_storage import save_documents


def parse_pdf_and_store(pdf_path: str):
    """Parsiraj PDF i sačuvaj u lokalni storage."""
    print(f"Parsing PDF: {pdf_path}")
    
    docs = []
    
    # Parse PDF
    for page in extract_pdf(pdf_path):
        print(f"  Parsing page {page['page']}...")
        
        # Chunk tekst
        for seg in chunk(page["text"]):
            doc = {
                "id": f"pdf_page_{page['page']}_{hash(seg) % 10000}",
                "title": "SEPA Q&A",
                "content": seg,
                "source": "pdf:SEPA_QnA",
                "page": page["page"]
            }
            docs.append(doc)
    
    # Sačuvaj
    save_documents(docs)
    
    print(f"\nDone! Parsed {len(docs)} chunks from PDF")
    return docs


if __name__ == "__main__":
    pdf_path = "data/SEPA_QnA.pdf"
    
    if not Path(pdf_path).exists():
        print(f"Error: {pdf_path} not found!")
        sys.exit(1)
    
    parse_pdf_and_store(pdf_path)


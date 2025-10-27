"""
LOCAL retrieval - koristi VECTOR SEARCH sa FAISS + OpenAI embeddings.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict

# Dodaj root u path za import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.ingest.local_storage_vector import search_documents, load_documents
from apps.ingest.local_storage import search_documents as keyword_search


def retrieve(query: str, k: int = 8) -> List[Dict]:
    """
    LOCAL retrieval - vraća dokumente iz parsed PDF-a.
    
    Args:
        query: Pitanje korisnika
        k: Broj rezultata
        
    Returns:
        Lista konteksta (content, title, source, page)
    """
    # Provjeri da li postoje lokalni dokumenti
    docs = load_documents()
    
    if not docs:
        # Fallback na sample dokumente ako nema parsiranog PDF-a
        print("WARNING: No parsed PDF data found. Using sample documents.")
        print("Run: python parse_and_store.py")
        
        return _get_sample_docs()[:k]
    
    # HYBRID SEARCH: Koristi keyword search PRVENSTVENO (instant, ~10ms),
    # a vector search SAMO za kompleksne upite
    import time
    
    # Prvo probaj keyword search (instant, ~10ms)
    start = time.time()
    keyword_results = keyword_search(query, k=k)
    keyword_time = time.time() - start
    
    # Ako keyword search daje dobre rezultate (> 2 matches), koristi ga (99% slučajeva)
    if len(keyword_results) >= 2:
        max_chunks = int(os.getenv("MAX_CHUNKS", "12"))
        return keyword_results[:max_chunks]
    
    # Samo ako keyword search NE DADE rezultate - koristi vector search
    # (veoma rijetko, samo za kompleksne semantic queries)
    try:
        start = time.time()
        vector_results = search_documents(query, k=k)
        vector_time = time.time() - start
        results = vector_results
    except Exception as e:
        # Fallback na keyword ako vector search fail-uje
        results = keyword_results
    
    if not results:
        return _get_sample_docs()[:k]
    
    max_chunks = int(os.getenv("MAX_CHUNKS", "12"))
    return results[:max_chunks]


def _get_sample_docs() -> List[Dict]:
    """Fallback sample dokumenti."""
    return [
        {
            "content": "SEPA (Single Euro Payments Area) je jedinstvena platažna oblast u kojoj građani, kompanije i druge pravne osobe mogu da izvršavaju i primaju euro plaćanja.",
            "title": "SEPA Q&A - Šta je SEPA?",
            "source": "pdf:SEPA_QnA",
            "page": 1
        },
        {
            "content": "Postoje dva osnovna tipa SEPA plaćanja: SEPA Credit Transfer (SCT) i SEPA Direct Debit (SDD).",
            "title": "SEPA Q&A - Tipovi plaćanja",
            "source": "pdf:SEPA_QnA",
            "page": 2
        }
    ]


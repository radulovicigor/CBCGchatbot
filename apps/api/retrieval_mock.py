"""
LOCAL retrieval - koristi VECTOR SEARCH sa FAISS + OpenAI embeddings.
"""
import os
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime, timedelta

# Dodaj root u path za import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.ingest.local_storage_vector_multilingual import search_documents, load_documents
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
    try:
        # Provjeri da li postoje lokalni dokumenti
        docs = load_documents()
        
        if not docs:
            # Fallback na sample dokumente ako nema parsiranog PDF-a
            print("WARNING: No parsed PDF data found. Using sample documents.")
            print("Run: python parse_and_store.py")
            
            return _get_sample_docs()[:k]
    except Exception as e:
        print(f"Error loading documents: {e}")
        # Fallback na sample dokumente ako učitavanje ne uspe
        return _get_sample_docs()[:k]
    
    # Proveri da li je pitanje o "trenutno/sad" - ako jeste, filtriraj SAMO najnovije članke
    query_lower = query.lower()
    is_current_question = any(word in query_lower for word in ['sad', 'trenutno', 'sada', 'danas', 'novo', 'najnovije', 'šta se dešava', 'šta se desava'])
    
    # HYBRID SEARCH 2.0: Kombinuj keyword + vector za NAJBOLJE rezultate
    # Uzmi oba pristupa i merge-uj rezultate sa reciprocal rank fusion
    import time
    
    # 1. KEYWORD SEARCH (instant, odličan za specifične termine)
    start = time.time()
    keyword_results = keyword_search(query, k=k * 2)
    keyword_time = time.time() - start
    
    # 2. VECTOR SEARCH (semantic, odličan za razumevanje)
    start = time.time()
    vector_results = search_documents(query, k=k * 2)
    vector_time = time.time() - start
    
    print(f"[SEARCH] Keyword: {len(keyword_results)} u {keyword_time:.3f}s | Vector: {len(vector_results)} u {vector_time:.3f}s")
    
    # 3. RECIPROCAL RANK FUSION: Kombinuj rezultate (state-of-the-art metoda)
    # RRF = 1 / (rank + k) gde je k=60 standard
    from collections import defaultdict
    
    doc_scores = defaultdict(float)
    doc_map = {}
    
    # Dodaj keyword scores
    for rank, doc in enumerate(keyword_results, 1):
        doc_id = doc.get('source', '') + doc.get('title', '') + str(doc.get('page', ''))
        doc_scores[doc_id] += 1.0 / (rank + 60)
        doc_map[doc_id] = doc
    
    # Dodaj vector scores
    for rank, doc in enumerate(vector_results, 1):
        doc_id = doc.get('source', '') + doc.get('title', '') + str(doc.get('page', ''))
        doc_scores[doc_id] += 1.0 / (rank + 60)
        if doc_id not in doc_map:
            doc_map[doc_id] = doc
    
    # Sortiraj po kombinovanom skoru
    sorted_docs = sorted(doc_scores.items(), key=lambda x: x[1], reverse=True)
    results = [doc_map[doc_id] for doc_id, score in sorted_docs[:k * 2]]
    
    # 4. FILTRIRAJ ZA "TRENUTNO" PITANJA
    if is_current_question:
        now = datetime.now()
        filtered_results = []
        for doc in results:
            published_at = doc.get("published_at")
            if published_at:
                try:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    days_old = (now - pub_date.replace(tzinfo=None) if pub_date.tzinfo else now - pub_date).days
                    if days_old <= 90:  # SAMO članci iz poslednjih 90 dana
                        filtered_results.append(doc)
                except:
                    pass
        
        results = filtered_results[:k]
        print(f"[FILTER] Filtered {len(results)} recent articles (RRF fusion)")
    else:
        results = results[:k]
    
    # Uvek dodaj osnovne činjenice o CBCG kao prvi dokument za relevantna pitanja
    cbcg_basics_keywords = ['osnovan', 'osnovana', 'kada', 'kad', 'dje', 'gdje', 'adresa', 'lokacija', 
                            'sjedište', 'sedište', 'guverner', 'cbcg', 'centralna banka']
    
    currency_history_keywords = ['prije eura', 'pre eura', 'stare pare', 'valuta', 'novac', 'marka', 
                                 'dinar', 'prve pare', 'historija', 'istorija']
    
    query_lower = query.lower()
    
    # Dodaj CBCG osnovne činjenice
    if any(keyword in query_lower for keyword in cbcg_basics_keywords):
        cbcg_basics = {
            "content": "Centralna banka Crne Gore osnovana je 11. marta 2001. godine. Guvernerka je dr Irena Radović (od 2023. godine). Sjedište Centralne banke Crne Gore nalazi se u Podgorici na adresi Bulevar Svetog Petra Cetinjskog 6.",
            "title": "O Centralnoj banci Crne Gore",
            "source": "cbcg.me",
            "page": 1,
            "published_at": "2001-03-11T00:00:00"
        }
        results = [cbcg_basics] + results
    
    # Dodaj istorijske informacije o valuti
    if any(keyword in query_lower for keyword in currency_history_keywords):
        currency_history = {
            "content": "Prije uvođenja eura, u Crnoj Gori se koristila njemačka marka (DEM) od 1999. godine. Prije toga, 1990-ih godina, koristio se jugoslovenski dinar. Euro je uveden kao službena valuta 2002. godine, nakon što je Crna Gora jednostrano usvojila euro kao sredstvo plaćanja.",
            "title": "Istorija valute u Crnoj Gori",
            "source": "cbcg.me",
            "page": 1,
            "published_at": "2002-01-01T00:00:00"
        }
        results = [currency_history] + results
    
    if not results:
        return _get_sample_docs()[:k]
    
    max_chunks = int(os.getenv("MAX_CHUNKS", "12"))
    return results[:max_chunks]


def _get_sample_docs() -> List[Dict]:
    """Fallback sample dokumenti."""
    return [
        {
            "content": "Centralna banka Crne Gore osnovana je 11. marta 2001. godine. Guvernerka je dr Irena Radović (od 2023. godine). Sjedište Centralne banke Crne Gore nalazi se u Podgorici na adresi Bulevar Svetog Petra Cetinjskog 6.",
            "title": "O Centralnoj banci Crne Gore",
            "source": "cbcg.me",
            "page": 1,
            "published_at": "2001-03-11T00:00:00"
        },
        {
            "content": "SEPA (Single Euro Payments Area) je jedinstvena platažna oblast u kojoj građani, kompanije i druge pravne osobe mogu da izvršavaju i primaju euro plaćanja. Crna Gora je postala operativni dio SEPA zone 7. oktobra 2025. godine.",
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


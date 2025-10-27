"""
Local storage za parsed data (bez Azure).
"""
import json
import hashlib
from pathlib import Path
from typing import List, Dict


STORAGE_FILE = Path("data/parsed_data.json")


def save_documents(docs: List[Dict]):
    """Sačuvaj dokumente u JSON."""
    STORAGE_FILE.parent.mkdir(exist_ok=True)
    with open(STORAGE_FILE, 'w', encoding='utf-8') as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)
    print(f"Saved {len(docs)} documents to {STORAGE_FILE}")


def load_documents() -> List[Dict]:
    """Učitaj dokumente iz JSON."""
    if not STORAGE_FILE.exists():
        return []
    
    with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def search_documents(query: str, k: int = 8) -> List[Dict]:
    """
    Simple keyword search kroz lokalne dokumente.
    Prioritizuje news dokumente ako odgovaraju query.
    
    Args:
        query: Search query
        k: Max number of results
        
    Returns:
        List of matching documents
    """
    docs = load_documents()
    
    if not docs:
        return []
    
    # Simple keyword matching
    query_lower = query.lower()
    query_words = set(query_lower.split())
    
    # Score dokumenata
    scored_docs = []
    for doc in docs:
        content_lower = doc.get("content", "").lower()
        title_lower = doc.get("title", "").lower()
        
        score = 0
        content_words = set(content_lower.split())
        title_words = set(title_lower.split())
        
        # Match u naslovu = više bodova
        score += len(query_words & title_words) * 3
        
        # Match u content-u
        score += len(query_words & content_words)
        
        # Substring match
        if query_lower in content_lower or query_lower in title_lower:
            score += 5
        
        # Bonus za news dokumente - prioritizuj ih
        if doc.get("type") == "news":
            score += 2
        
        scored_docs.append((score, doc))
    
    # Sort po score i vrati top k
    scored_docs.sort(key=lambda x: x[0], reverse=True)
    
    # Vrati samo pozitivne rezultate
    results = [doc for score, doc in scored_docs if score > 0][:k]
    
    return results


def hash_content(content: str) -> str:
    """Hash content za deduplikaciju."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()


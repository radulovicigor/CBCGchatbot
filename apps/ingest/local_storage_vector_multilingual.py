"""
Vector storage sa MULTILINGUAL embedding modelom optimizovanim za srpski/crnogorski jezik.
Koristi intfloat/multilingual-e5-large umesto OpenAI embeddings.
"""
import os
import pickle
import numpy as np
import faiss
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Paths - koristi apsolutne putanje relativne na lokaciju projekta
PROJECT_ROOT = Path(__file__).parent.parent.parent.absolute()
DATA_DIR = PROJECT_ROOT / "data"
STORAGE_FILE = DATA_DIR / "parsed_data.json"
VECTOR_INDEX_FILE = DATA_DIR / "vector_index_multilingual.faiss"
DOCS_METADATA_FILE = DATA_DIR / "docs_metadata_multilingual.pkl"

# Multilingual model - NAJBOLJI za srpski/crnogorski jezik
MODEL_NAME = "intfloat/multilingual-e5-large"
# Model se ucitava lazy - samo kada je potreban
model = None

def get_model():
    """Lazy load model samo kada je potreban."""
    global model
    if model is None:
        model = SentenceTransformer(MODEL_NAME)
    return model


def get_embedding(text: str) -> np.ndarray:
    """
    Generiši embedding za tekst koristeći multilingual model.
    Optimizovano za srpski/crnogorski jezik.
    """
    # E5 modeli zahtevaju prefix "query: " za upite i "passage: " za dokumente
    # Za jednostavnost, koristim "passage: " za sve (dobro radi u praksi)
    m = get_model()
    embedding = m.encode(f"passage: {text}", normalize_embeddings=True)
    return embedding


def load_documents():
    """Load documents from JSON."""
    import json
    if not STORAGE_FILE.exists():
        return []
    with open(STORAGE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def build_vector_index():
    """
    Napravi FAISS index sa multilingual embeddings.
    MNOGO BOLJI za naš jezik od OpenAI!
    """
    docs = load_documents()
    
    if not docs:
        print("Nema dokumenata za indeksiranje!")
        return
    
    print(f"Building FAISS index for {len(docs)} documents...")
    print(f"Model: {MODEL_NAME} (optimized for Serbian/Montenegrin)")
    
    # Pripremi tekstove za embedding
    texts = []
    metadata = []
    
    for doc in docs:
        # Kombinuj naslov + content za bolji embedding
        title = doc.get('title', '')
        content = doc.get('content', '')
        combined_text = f"{title}. {content}"
        
        texts.append(combined_text)
        metadata.append(doc)
    
    # Generiši embeddings (batch processing za brzinu)
    print("Generating embeddings...")
    m = get_model()
    embeddings = m.encode(
        [f"passage: {text}" for text in texts],
        show_progress_bar=True,
        batch_size=32,
        normalize_embeddings=True
    )
    
    embeddings_array = np.array(embeddings, dtype='float32')
    
    # Napravi FAISS index (Inner Product za normalized embeddings = cosine similarity)
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner Product za normalized vectors
    index.add(embeddings_array)
    
    # Sačuvaj index i metadata
    DATA_DIR.mkdir(exist_ok=True)
    faiss.write_index(index, str(VECTOR_INDEX_FILE))
    
    with open(DOCS_METADATA_FILE, 'wb') as f:
        pickle.dump(metadata, f)
    
    print(f"[OK] FAISS index saved: {VECTOR_INDEX_FILE}")
    print(f"[OK] Metadata saved: {DOCS_METADATA_FILE}")
    print(f"[OK] Dimension: {dimension}, Documents: {len(docs)}")


def search_documents(query: str, k: int = 5) -> List[Dict]:
    """
    Pretraži dokumente koristeći multilingual semantic search.
    BOLJI za srpski/crnogorski od OpenAI!
    
    Args:
        query: Upit korisnika
        k: Broj rezultata
    
    Returns:
        Lista dokumenata rangiranih po relevantnosti
    """
    # Proveri da li postoji index
    if not VECTOR_INDEX_FILE.exists() or not DOCS_METADATA_FILE.exists():
        print("UPOZORENJE: Multilingual FAISS index ne postoji! Pokreni build_vector_index()")
        return []
    
    # Učitaj index i metadata
    index = faiss.read_index(str(VECTOR_INDEX_FILE))
    with open(DOCS_METADATA_FILE, 'rb') as f:
        metadata = pickle.load(f)
    
    # Generiši embedding za query (sa "query: " prefixom za E5 model)
    m = get_model()
    query_embedding = m.encode(
        f"query: {query}",
        normalize_embeddings=True
    )
    query_vector = np.array([query_embedding], dtype='float32')
    
    # Pretraži FAISS index
    distances, indices = index.search(query_vector, k)
    
    # Pripremi rezultate sa dodatnim skoringom
    results = []
    now = datetime.now()
    
    for idx, (distance, doc_idx) in enumerate(zip(distances[0], indices[0])):
        if doc_idx < len(metadata):
            doc = metadata[doc_idx].copy()
            
            # Bazni skor od FAISS (cosine similarity za normalized vectors)
            base_score = float(distance)
            
            # Bonus za novije članke (prioritet skorijim informacijama)
            date_bonus = 0
            published_at = doc.get('published_at')
            if published_at:
                try:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    days_old = (now - pub_date.replace(tzinfo=None) if pub_date.tzinfo else now - pub_date).days
                    
                    if days_old <= 30:
                        date_bonus = 0.15  # Vrlo nov
                    elif days_old <= 90:
                        date_bonus = 0.10  # Nov
                    elif days_old <= 365:
                        date_bonus = 0.05  # Relativno nov
                except:
                    pass
            
            # Kombinovani skor
            final_score = base_score + date_bonus
            doc['_score'] = final_score
            
            results.append(doc)
    
    # Sortiraj po finalnom skoru
    results.sort(key=lambda x: x.get('_score', 0), reverse=True)
    
    return results


if __name__ == "__main__":
    print("\n" + "="*80)
    print("MULTILINGUAL VECTOR INDEX BUILDER")
    print("Model: intfloat/multilingual-e5-large")
    print("Optimizovano za srpski/crnogorski jezik")
    print("="*80 + "\n")
    
    build_vector_index()
    
    print("\n" + "="*80)
    print("TEST: Pretraga sa multilingual modelom")
    print("="*80 + "\n")
    
    # Test upiti
    test_queries = [
        "kad je osnovana centralna banka",
        "kako da pošaljem pare u Njemačku",
        "šta je SEPA",
        "guvernerka Centralne banke"
    ]
    
    for query in test_queries:
        print(f"\nUpit: {query}")
        results = search_documents(query, k=3)
        for i, doc in enumerate(results[:3], 1):
            title = doc.get('title', 'N/A')[:60]
            score = doc.get('_score', 0)
            print(f"  {i}. [{score:.3f}] {title}")


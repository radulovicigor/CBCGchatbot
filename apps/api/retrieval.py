"""
Hibridni retrieval (BM25 + opciono vektorska pretraga).
"""
import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from typing import List, Dict

load_dotenv()

SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
FAQ_INDEX = os.getenv("AZURE_SEARCH_FAQ_INDEX", "faq_sepa")
NEWS_INDEX = os.getenv("AZURE_SEARCH_NEWS_INDEX", "news_cbcg")
SEARCH_KEY = os.getenv("AZURE_SEARCH_API_KEY")

# Only create clients if credentials are provided
if SEARCH_ENDPOINT and SEARCH_KEY:
    faq = SearchClient(SEARCH_ENDPOINT, FAQ_INDEX, AzureKeyCredential(SEARCH_KEY))
    news = SearchClient(SEARCH_ENDPOINT, NEWS_INDEX, AzureKeyCredential(SEARCH_KEY))
else:
    faq = None
    news = None


def retrieve(query: str, k: int = 8) -> List[Dict]:
    """
    Hibridni retrieval: FAQ + NEWS.
    
    Args:
        query: Pitanje korisnika
        k: Broj rezultata
        
    Returns:
        Lista konteksta (content, title, source, page)
    """
    ctx = []
    
    if not faq or not news:
        return ctx  # Return empty if Azure not configured
    
    # FAQ retrieval
    faq_hits = list(faq.search(query, top=k))
    for d in faq_hits:
        ctx.append({
            "content": d.get("content", ""),
            "title": d.get("title", "SEPA Q&A"),
            "source": d.get("source", "pdf:SEPA_QnA"),
            "page": d.get("page")
        })
    
    # NEWS retrieval (polovina kapaciteta)
    news_hits = list(news.search(query, top=max(0, k//2)))
    for d in news_hits:
        ctx.append({
            "content": d.get("body", ""),
            "title": d.get("title", ""),
            "source": d.get("url", "cbcg.me"),
            "page": None
        })
    
    # Limit
    max_chunks = int(os.getenv("MAX_CHUNKS", "12"))
    return ctx[:max_chunks]


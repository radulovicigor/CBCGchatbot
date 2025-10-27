"""
Etički scraper za cbcg.me sa throttling-om i delta-detekcijom.
"""
import httpx
import time
import hashlib
import os
import uuid
from datetime import datetime
from typing import Set
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_API_KEY"]
NEWS_INDEX = os.environ["AZURE_SEARCH_NEWS_INDEX"]

BASES = [
    "https://www.cbcg.me/me/javnost-rada/aktuelno/saopstenja",
    "https://www.cbcg.me/en/javnost-rada/aktuelno/saopstenja"  # Dvojezično
]

# User-Agent za etično ponašanje
HEADERS = {"User-Agent": "cbcgbot/1.0"}


def fetch(url: str, timeout: float = 30.0) -> tuple[str, str]:
    """
    HTTP fetch sa throttling.
    
    Returns:
        (html_text, final_url)
    """
    with httpx.Client(timeout=timeout, headers=HEADERS, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text, str(r.url)


def find_article_links(html: str, base_url: str) -> list[str]:
    """
    Pronalazak linkova članaka iz DOM-a.
    
    Prilagodi selektore nakon inspekcije cbcg.me strukture.
    """
    from selectolax.parser import HTMLParser
    
    dom = HTMLParser(html)
    links = []
    
    for a in dom.css("a"):
        href = a.attributes.get("href", "")
        if "/saopstenja/" in href or "/aktuelno/" in href:
            full_url = httpx.URL(href, base=base_url).human_repr()
            if full_url not in links:
                links.append(full_url)
    
    return links


def parse_article(html: str) -> tuple[str, str, str, str]:
    """
    Parsiranje članka (naslov, datum, body, hash).
    
    Returns:
        (title, published_at, body, digest)
    """
    from selectolax.parser import HTMLParser
    
    dom = HTMLParser(html)
    
    # Naslov
    title_el = dom.css_first("h1")
    title = title_el.text(strip=True) if title_el else ""
    
    # Datum
    time_el = dom.css_first("time")
    published_at = time_el.attributes.get("datetime", "") if time_el else ""
    
    # Body
    paragraphs = [p.text(strip=True) for p in dom.css("p") if p.text(strip=True)]
    body = "\n".join(paragraphs)
    
    # Hash za deduplikaciju
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    
    return title, published_at, body, digest


def load_seen_hashes(search_client: SearchClient, top: int = 100) -> Set[str]:
    """
    Učitaj postojeće hash-eve za delta-detekciju.
    """
    seen = set()
    
    try:
        results = search_client.search(search_text="*", top=top, order_by=["search.score() desc"])
        for doc in results:
            if "hash" in doc:
                seen.add(doc["hash"])
    except Exception as e:
        print(f"Error loading seen hashes: {e}")
    
    return seen


def run_scrape():
    """
    Glavna funkcija scrapera.
    """
    search = SearchClient(SEARCH_ENDPOINT, NEWS_INDEX, AzureKeyCredential(SEARCH_KEY))
    
    # Delta-detekcija
    seen_hashes = load_seen_hashes(search)
    
    to_upload = []
    
    for base in BASES:
        try:
            html, base_final = fetch(base)
            links = find_article_links(html, base_final)
            
            for u in links[:50]:  # Safety limit
                try:
                    art_html, final_url = fetch(u)
                    title, published_at, body, digest = parse_article(art_html)
                    
                    # Skip ako već postoji
                    if digest in seen_hashes:
                        continue
                    
                    doc = {
                        "id": str(uuid.uuid4()),
                        "title": title or final_url,
                        "url": final_url,
                        "published_at": published_at or datetime.utcnow().isoformat(),
                        "body": body,
                        "hash": digest
                    }
                    
                    to_upload.append(doc)
                    
                    # Throttle
                    time.sleep(0.7)
                
                except Exception as e:
                    print(f"Error processing {u}: {e}")
                    continue
        
        except Exception as e:
            print(f"Error processing base {base}: {e}")
            continue
    
    # Upload novih članaka
    if to_upload:
        search.upload_documents(to_upload)
        print(f"Uploaded {len(to_upload)} new articles")
    else:
        print("No new articles to upload")


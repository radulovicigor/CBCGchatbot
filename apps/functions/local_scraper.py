"""
Lokalni scraper za cbcg.me (bez Azure Functions).
Poboljšana verzija sa boljim parsing-om.
"""
import httpx
import time
import re
from datetime import datetime
from pathlib import Path
import json
from selectolax.parser import HTMLParser

# Dodaj u path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from apps.ingest.local_storage import save_documents, load_documents, hash_content

# Content koje se skrejpuje SVAKI DAN
DAILY_BASES = [
    "https://www.cbcg.me/me/javnost-rada/aktuelno/saopstenja",
    "https://www.cbcg.me/me/javnost-rada/aktuelno/dogadjaji",
    "https://www.cbcg.me/me/javnost-rada/izlaganja/intervjui-i-autorski-tekstovi",
    "https://www.cbcg.me/me/javnost-rada/blog",
]

# Content koje se skrejpuje SAMO JEDNOM (ne menja se)
ONCE_BASES = [
    "https://www.cbcg.me/me/javnost-rada/informacije/najcesce-postavljena-pitanja",
    "https://www.cbcg.me/me/javnost-rada/informacije/pristup-informacijama",
    "https://www.cbcg.me/me/o-nama",
]

# Kombiniuj sve za scraper
BASES = DAILY_BASES + ONCE_BASES


def get_all_page_urls(base_url, client):
    """Pronađi sve URL-ove sa svih stranica."""
    all_links = set()
    page = 1
    
    while True:
        try:
            # Dodaj page parametar
            if '?' in base_url:
                url = f"{base_url}&page={page}"
            else:
                url = f"{base_url}?page={page}"
            
            print(f"  Fetching page {page}...")
            r = client.get(url)
            r.raise_for_status()
            html = r.text
            
            # Parse HTML
            tree = HTMLParser(html)
            
            # Find all content links on the page
            page_links = set()
            for a_tag in tree.css('a'):
                href = a_tag.attributes.get('href', '')
                if not href:
                    continue
                
                # Build full URL
                if href.startswith('/'):
                    link = f"https://www.cbcg.me{href}"
                elif href.startswith('http'):
                    link = href
                else:
                    link = f"https://www.cbcg.me/{href}"
                
                # Filter relevant content
                if any(keyword in link for keyword in ['saopstenja', 'dogadjaji', 'izlaganja', 'blog', 'dogadjanja', 'intervjui', 'faq', 'najcesce', 'pristup', 'o-nama']):
                    if link not in page_links and len(link) > 30:
                        page_links.add(link)
            
            # Break if no new links found
            if not page_links or all(link in all_links for link in page_links):
                break
            
            all_links.update(page_links)
            page += 1
            
            time.sleep(0.5)  # Throttle
            
        except Exception as e:
            print(f"    Error on page {page}: {e}")
            break
    
    return list(all_links)


def scrape_cbcg():
    """Scrape cbcg.me i dodaj u lokalni storage."""
    print("Scraping cbcg.me...")
    
    # Check existing docs for "once" content
    existing_docs = load_documents()
    existing_urls = {doc.get("url") for doc in existing_docs if doc.get("url")}
    
    news_docs = []
    
    for base_url in BASES:
        try:
            print(f"\n=== Processing: {base_url} ===")
            
            # Check if this is "once" content and already scraped
            if base_url in ONCE_BASES:
                # Provjeri ima li već dokumenata sa ovog URL-a
                if any(base_url in url for url in existing_urls):
                    print(f"  SKIP - Already scraped (once content)")
                    continue
            
            with httpx.Client(
                timeout=30.0, 
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                verify=False,
                follow_redirects=True
            ) as client:
                # Get all links from all pages
                links = get_all_page_urls(base_url, client)
                print(f"  Found {len(links)} articles across all pages")
                
                # Parse artikle - SVE (bez limita)
                for idx, link in enumerate(links, 1):
                    try:
                        print(f"    [{idx}/{len(links)}] Parsing: {link}")
                        
                        r = client.get(link)
                        r.raise_for_status()
                        content = r.text
                        
                        # Extract naslov
                        title = "CBCG Saopštenje"
                        title_patterns = [
                            r'<h1[^>]*>(.*?)</h1>',
                            r'<title>(.*?)</title>',
                            r'<h2[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h2>',
                            r'class="entry-title"[^>]*>(.*?)</',
                        ]
                        
                        for pattern in title_patterns:
                            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
                            if match:
                                title = re.sub(r'<[^>]+>', '', match.group(1)).strip()
                                if len(title) > 10:
                                    break
                        
                        # Extract body
                        # Extract body using selectolax - traži page-text div
                        body = ""
                        tree_content = HTMLParser(content)
                        
                        # Prvo pokušaj da nađeš page-text div
                        for div in tree_content.css('div.page-text'):
                            body = div.text()
                            if len(body) > 100:
                                break
                        
                        # Fallback: ako nema page-text, probaj ostale
                        if not body or len(body) < 100:
                            body_patterns = [
                                r'<article[^>]*>(.*?)</article>',
                                r'<div[^>]*class="[^"]*content[^"]*"[^>]*>(.*?)</div>',
                            ]
                            
                            for pattern in body_patterns:
                                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                                if matches:
                                    body = max(matches, key=len)
                                    break
                        
                        # Clean body text (ukloni extra whitespace)
                        if body:
                            # Remove common junk
                            body = re.sub(r'(Kontakti|Mapa sajta|Najčešće postavljena pitanja|Home|O nama)', '', body, flags=re.IGNORECASE)
                            body = ' '.join(body.split())  # Normalize whitespace
                            body = body.strip()
                            
                            # Remove if still too long (probably includes header/footer)
                            if len(body) > 8000:
                                body = body[:8000]
                        
                        # Extract publication date from HTML
                        published_at = datetime.now().isoformat()  # Fallback to now
                        try:
                            # Try to find date in format DD/MM/YYYY
                            date_match = re.search(r"class=['\"]date['\"][^>]*>(\d{1,2}/\d{1,2}/\d{4})<", html_content)
                            if date_match:
                                date_str = date_match.group(1)  # e.g., "06/11/2025"
                                # Parse DD/MM/YYYY to ISO format
                                date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                                published_at = date_obj.isoformat()
                        except Exception as e:
                            # If date parsing fails, use current time
                            pass
                        
                        # Save if sufficient content
                        if len(body) > 150:
                            doc_id = f"cbcg_{hash_content(link)}"
                            doc = {
                                "id": doc_id,
                                "title": title,
                                "content": body[:3000],
                                "source": "cbcg.me",
                                "url": link,
                                "published_at": published_at,
                                "page": None,
                                "type": "news"
                            }
                            news_docs.append(doc)
                            print(f"      OK Saved: {title[:60]}...")
                        else:
                            print(f"      SKIP Too short, skipping")
                        
                        time.sleep(0.3)
                    
                    except Exception as e:
                        print(f"      ERROR: {e}")
                        continue
        
        except Exception as e:
            print(f"  Error fetching {base_url}: {e}")
            continue
    
    if news_docs:
        print(f"\n=== CHECKING FOR NEW ARTICLES ===")
        existing_docs = load_documents()
        
        # Mapiraj postojeće URL-ove za brzu provjeru
        existing_urls = {doc.get("url") for doc in existing_docs if doc.get("url")}
        existing_titles = {doc.get("title") for doc in existing_docs if doc.get("title")}
        
        print(f"  Existing in database: {len(existing_docs)} documents")
        print(f"  Scraped today: {len(news_docs)} articles")
        
        # Pronađi nove - razlika u URL-u ILI u naslovu
        new_docs = []
        skipped = []
        
        for doc in news_docs:
            doc_url = doc.get("url", "")
            doc_title = doc.get("title", "")
            
            # Provjeri da li postoji
            if doc_url in existing_urls:
                skipped.append(f"URL: {doc_url[:60]}...")
            elif doc_title in existing_titles:
                skipped.append(f"Title: {doc_title[:60]}...")
            else:
                new_docs.append(doc)
        
        print(f"\n  RESULTS:")
        print(f"  - New articles found: {len(new_docs)}")
        print(f"  - Already in database: {len(skipped)}")
        
        if new_docs:
            print(f"\n  Adding new articles to database...")
            all_docs = existing_docs + new_docs
            save_documents(all_docs)
            print(f"  SUCCESS: Total documents now: {len(all_docs)}")
            
            # Prikaži prve 3 nove (sanitize za Windows console)
            for i, doc in enumerate(new_docs[:3], 1):
                title = doc.get('title', 'No title')
                safe_title = title.encode('ascii', 'ignore').decode('ascii')
                print(f"    {i}. {safe_title[:70]}")
            
            # Rebuild vector index
            try:
                print(f"\n  Rebuilding vector index...")
                from apps.ingest.local_storage_vector import build_vector_index
                build_vector_index()
                print(f"  Vector index rebuilt successfully!")
            except Exception as e:
                print(f"  WARNING: Could not rebuild vector index: {e}")
        else:
            print(f"\n  INFO: No new articles - database is up to date!")
    else:
        print("\n  ERROR: No articles scraped (check website or network)")
    
    return len(news_docs)


if __name__ == "__main__":
    scrape_cbcg()

"""Quick script to check scraper status and show detailed progress."""
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from apps.ingest.local_storage import load_documents

docs = load_documents()

print("\n" + "="*70)
print("CBCG CHATBOT DATABASE STATUS")
print("="*70)
print(f"\n   Total documents: {len(docs)}")

# Group by category
categories = {
    "Saopštenja": 0,
    "Događaji": 0,
    "Intervjui": 0,
    "Blog": 0,
    "FAQ": 0,
    "Pristup informacijama": 0,
    "O nama": 0,
    "PDF/SEPA": 0,
    "Other": 0
}

# Track recent articles by date
news_docs = []
pdf_docs = []

for doc in docs:
    url = doc.get('url', '')
    source = doc.get('source', '')
    doc_type = doc.get('type', '')
    
    # Categorize
    if doc_type == "news" or "cbcg.me" in source:
        if "saopstenja" in url.lower():
            categories["Saopštenja"] += 1
        elif "dogadjaji" in url.lower() or "dogadjanja" in url.lower():
            categories["Događaji"] += 1
        elif "intervjui" in url.lower() or "autorski-tekstovi" in url.lower():
            categories["Intervjui"] += 1
        elif "blog" in url.lower():
            categories["Blog"] += 1
        elif "najcesce-postavljena-pitanja" in url.lower() or "faq" in url.lower():
            categories["FAQ"] += 1
        elif "pristup-informacijama" in url.lower():
            categories["Pristup informacijama"] += 1
        elif "o-nama" in url.lower():
            categories["O nama"] += 1
        else:
            categories["Other"] += 1
        
        # Track news for recent list
        if doc.get('published_at') or doc_type == "news":
            news_docs.append(doc)
    elif "pdf" in source.lower() or "sepa" in source.lower():
        categories["PDF/SEPA"] += 1
        pdf_docs.append(doc)
    else:
        categories["Other"] += 1

print("\n   Documents by Category:")
for category, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
    if count > 0:
        bar = "=" * min(count // 10, 30)
        safe_category = category.encode('ascii', 'ignore').decode('ascii') or category
        print(f"   {safe_category:25s} {count:4d} {bar}")

# Show recent news
print("\n   Recent News (last 5):")
for i, doc in enumerate(news_docs[-5:], 1):
    title = doc.get('title', 'No title')
    safe_title = title.encode('ascii', 'ignore').decode('ascii')
    url = doc.get('url', 'no url')
    date = doc.get('published_at', 'N/A')
    if date != 'N/A':
        try:
            dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
            date = dt.strftime('%Y-%m-%d')
        except:
            pass
    print(f"   {i}. [{date}] {safe_title[:50]}")

# Show summary
print("\n   Database Summary:")
if len(news_docs) > 0:
    print(f"      - News articles: {len(news_docs)}")
if len(pdf_docs) > 0:
    print(f"      - PDF/SEPA docs: {len(pdf_docs)}")

# Check coverage
expected_categories = ["Saopštenja", "Događaji", "Intervjui", "Blog", "FAQ", "Pristup informacijama", "O nama"]
covered = sum(1 for cat in expected_categories if categories[cat] > 0)
print(f"\n   Coverage: {covered}/7 categories")
if covered == 7:
    print("      >> All categories scraped!")

print("\n" + "="*70)
print("Status check complete!")
print("="*70 + "\n")


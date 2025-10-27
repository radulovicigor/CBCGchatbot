"""
Evaluacija RAG API koristeći golden set.
"""
import csv
import requests
import os
from typing import List, Dict


API_BASE = os.getenv("API_BASE", "http://localhost:8000")


def test_faq_golden(csv_path: str = "tests/faq_golden.csv"):
    """
    Eval golden set iz SEPA Q&A.
    
    Args:
        csv_path: Putanja do CSV fajla sa pitanjima
    """
    if not os.path.exists(csv_path):
        print(f"Warning: {csv_path} not found, skipping test")
        return
    
    results = []
    
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            q = row["question"]
            expected = row.get("expected", "").lower()
            page = row.get("page", "")
            
            # API call
            try:
                r = requests.post(
                    f"{API_BASE}/ask",
                    json={"question": q, "lang": "me"},
                    timeout=30.0
                )
                r.raise_for_status()
                j = r.json()
                
                answer = j["answer"].lower()
                sources = j.get("sources", [])
                
                # Check substring match
                match = expected in answer if expected else True
                
                # Check PDF source citation
                has_pdf_source = any(
                    s.get("source", "").startswith("pdf:SEPA_QnA")
                    for s in sources
                )
                
                results.append({
                    "question": q,
                    "match": match,
                    "has_source": has_pdf_source,
                    "answer": j["answer"],
                    "sources_count": len(sources)
                })
                
                print(f"✓ {q[:50]}... | match={match} | sources={len(sources)}")
            
            except Exception as e:
                print(f"✗ {q[:50]}... | ERROR: {e}")
                results.append({
                    "question": q,
                    "match": False,
                    "has_source": False,
                    "error": str(e)
                })
    
    # Summary
    total = len(results)
    matched = sum(1 for r in results if r.get("match", False))
    with_sources = sum(1 for r in results if r.get("has_source", False))
    
    print(f"\n{'='*60}")
    print(f"Results: {matched}/{total} matched ({matched/total*100:.1f}%)")
    print(f"With sources: {with_sources}/{total} ({with_sources/total*100:.1f}%)")
    print(f"{'='*60}")


if __name__ == "__main__":
    test_faq_golden()


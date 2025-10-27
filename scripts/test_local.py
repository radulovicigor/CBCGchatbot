"""
Local testing script - testira API bez Azure deploymenta.
"""
import sys
import time
from pathlib import Path

# Dodaj apps u path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_imports():
    """Test da li se svi moduli mogu importovati."""
    print("Testing imports...")
    
    try:
        from apps.api import main as api_main
        print("✓ apps.api imported")
        
        from apps.api.schemas import AskRequest, AskResponse
        print("✓ Schemas imported")
        
        from apps.api.retrieval import retrieve
        print("✓ Retrieval imported")
        
        from apps.ingest.parse_pdf import extract_pdf
        print("✓ PDF parser imported")
        
        from apps.ingest.chunking import chunk
        print("✓ Chunking imported")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False


def test_chunking():
    """Test chunking logike."""
    print("\nTesting chunking...")
    
    from apps.ingest.chunking import chunk
    
    test_text = "This is a test sentence. " * 100  # Long text
    chunks = list(chunk(test_text))
    
    if len(chunks) > 0:
        print(f"✓ Chunking works: {len(chunks)} chunks created")
        return True
    else:
        print("✗ Chunking failed")
        return False


def test_api_schemas():
    """Test Pydantic schemas."""
    print("\nTesting schemas...")
    
    from apps.api.schemas import AskRequest, AskResponse, Source
    
    # Test AskRequest
    req = AskRequest(question="Test", lang="me")
    assert req.question == "Test"
    print("✓ AskRequest works")
    
    # Test Source
    src = Source(title="Test", source="pdf:test", page=1)
    assert src.title == "Test"
    print("✓ Source works")
    
    # Test AskResponse
    resp = AskResponse(answer="Test", sources=[src], answer_id="test-123")
    assert resp.answer == "Test"
    print("✓ AskResponse works")
    
    return True


def test_prompts():
    """Test system prompts."""
    print("\nTesting prompts...")
    
    from apps.api.prompts import SYSTEM_PROMPT
    
    assert "SEPA" in SYSTEM_PROMPT
    assert "asistent" in SYSTEM_PROMPT.lower()
    print("✓ Prompts configured")
    
    return True


def main():
    """Glavna test funkcija."""
    print("="*50)
    print("  CBCG Chatbot - Local Tests")
    print("="*50)
    print()
    
    tests = [
        ("Imports", test_imports),
        ("Chunking", test_chunking),
        ("Schemas", test_api_schemas),
        ("Prompts", test_prompts),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"✗ {name} failed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "="*50)
    print("  RESULTS")
    print("="*50)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())


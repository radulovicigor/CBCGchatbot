"""
Development helpers - korisne funkcije za brzi dev workflow.
"""
import os
import sys
from pathlib import Path


def show_project_status():
    """Prikaz statusa projekta."""
    print("="*60)
    print("  CBCG Chatbot - Project Status")
    print("="*60)
    
    # .env status
    print("\n📝 Configuration:")
    if Path(".env").exists():
        print("  ✓ .env file exists")
        
        # Read key variables
        from dotenv import load_dotenv
        load_dotenv()
        
        keys = ["OPENAI_API_KEY", "AZURE_SEARCH_ENDPOINT", "AZURE_SEARCH_API_KEY"]
        for key in keys:
            val = os.getenv(key)
            if val and val != "..." and not val.startswith("<"):
                masked = val[:10] + "..." if len(val) > 10 else val
                print(f"  ✓ {key}: {masked}")
            else:
                print(f"  ✗ {key}: not configured")
    else:
        print("  ✗ .env file missing")
        print("  → Run: python scripts/create_env.py")
    
    # Dependencies
    print("\n📦 Dependencies:")
    deps = {
        "fastapi": "FastAPI",
        "openai": "OpenAI",
        "azure.search.documents": "Azure Search",
        "PyMuPDF": "PDF parser"
    }
    
    for module, name in deps.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except:
            print(f"  ✗ {name} not installed")
    
    # Data
    print("\n📄 Data:")
    if Path("data/SEPA_QnA.pdf").exists():
        print("  ✓ SEPA_QnA.pdf exists")
    else:
        print("  ✗ SEPA_QnA.pdf missing")
        print("  → Add PDF to data/ folder")
    
    # Virtual env
    print("\n🐍 Environment:")
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("  ✓ Virtual environment active")
        print(f"  → Python: {sys.version}")
    else:
        print("  ⚠ Virtual environment not active")
        print("  → Run: source .venv/bin/activate")
    
    print("\n" + "="*60)


def quick_test_api():
    """Quick test API endpoint-a."""
    print("🧪 Testing API...")
    
    try:
        import httpx
        
        # Test health endpoint
        r = httpx.get("http://localhost:8000/health", timeout=5.0)
        if r.status_code == 200:
            print("✓ API is running")
            return True
        else:
            print(f"✗ API returned {r.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ API not running: {e}")
        print("  → Start API: uvicorn apps.api.main:app --reload")
        return False


def check_azure_connection():
    """Proverava Azure Search connection."""
    print("🔍 Checking Azure Search...")
    
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from dotenv import load_dotenv
        
        load_dotenv()
        
        endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
        key = os.getenv("AZURE_SEARCH_API_KEY")
        index = os.getenv("AZURE_SEARCH_FAQ_INDEX")
        
        if not all([endpoint, key, index]):
            print("✗ Azure credentials not configured")
            return False
        
        # Try connection
        client = SearchClient(endpoint, index, AzureKeyCredential(key))
        results = list(client.search(search_text="*", top=1))
        
        print(f"✓ Connected to Azure Search")
        print(f"  → Index: {index}")
        print(f"  → Documents: at least {len(results)}")
        return True
        
    except Exception as e:
        print(f"✗ Azure Search connection failed: {e}")
        return False


def main():
    """Main menu."""
    import argparse
    
    parser = argparse.ArgumentParser(description="CBCG Chatbot dev helpers")
    parser.add_argument("command", choices=["status", "test-api", "check-azure"])
    
    args = parser.parse_args()
    
    if args.command == "status":
        show_project_status()
    elif args.command == "test-api":
        quick_test_api()
    elif args.command == "check-azure":
        check_azure_connection()


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("Usage: python scripts/dev_helpers.py [status|test-api|check-azure]")
        sys.exit(1)
    main()


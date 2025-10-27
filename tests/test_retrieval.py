"""
Test retrieval logike.
"""
import os
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv

load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_API_KEY"]
FAQ_INDEX = os.environ["AZURE_SEARCH_FAQ_INDEX"]


def test_search_connection():
    """Test konekcije sa Azure Search."""
    client = SearchClient(SEARCH_ENDPOINT, FAQ_INDEX, AzureKeyCredential(SEARCH_KEY))
    
    try:
        # Test query
        results = list(client.search(search_text="SEPA", top=5))
        print(f"✓ Connection OK, found {len(results)} results")
        return True
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def test_search_schema():
    """Test schema polja."""
    client = SearchClient(SEARCH_ENDPOINT, FAQ_INDEX, AzureKeyCredential(SEARCH_KEY))
    
    try:
        results = list(client.search(search_text="*", top=1))
        if results:
            doc = results[0]
            required_fields = ["id", "content", "title", "source", "page"]
            missing = [f for f in required_fields if f not in doc]
            
            if missing:
                print(f"✗ Missing fields: {missing}")
                return False
            else:
                print("✓ Schema OK")
                return True
        else:
            print("⚠ No documents found")
            return False
    except Exception as e:
        print(f"✗ Schema test failed: {e}")
        return False


if __name__ == "__main__":
    test_search_connection()
    test_search_schema()


"""
Azure AI Search index kreiranje i ingest pipeline.
"""
import os
import uuid
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex, SimpleField, SearchFieldDataType, VectorSearch,
    VectorSearchAlgorithmConfiguration, SearchField, SearchableField,
    SemanticConfiguration, SemanticSettings, PrioritizedFields
)
from azure.search.documents import SearchClient
from openai import OpenAI
from typing import List
from dotenv import load_dotenv

load_dotenv()

SEARCH_ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
SEARCH_KEY = os.environ["AZURE_SEARCH_API_KEY"]
FAQ_INDEX = os.environ["AZURE_SEARCH_FAQ_INDEX"]
NEWS_INDEX = os.environ["AZURE_SEARCH_NEWS_INDEX"]


def create_index_faq():
    """
    Kreira faq_sepa indeks (hibridni: BM25 + vektori, 3072-D).
    """
    client = SearchIndexClient(SEARCH_ENDPOINT, AzureKeyCredential(SEARCH_KEY))
    
    index = SearchIndex(
        name=FAQ_INDEX,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="simple"),
            SearchableField(name="content", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
            SimpleField(name="source", type=SearchFieldDataType.String, filterable=True, facetable=True),
            SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=True),
            # Vektor (3072 dim za text-embedding-3-large)
            SearchField(
                name="content_vector",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=3072,
                vector_search_configuration="vscos"
            )
        ],
        vector_search=VectorSearch(
            algorithms=[
                VectorSearchAlgorithmConfiguration(name="vscos", kind="hnsw")
            ]
        ),
        semantic_settings=SemanticSettings(
            configurations=[
                SemanticConfiguration(
                    name="default",
                    prioritized_fields=PrioritizedFields(
                        title_field=None,
                        content_fields=[{"fieldName": "content"}]
                    )
                )
            ]
        )
    )
    
    client.create_or_update_index(index)
    print(f"Created index: {FAQ_INDEX}")


def create_index_news():
    """
    Kreira news_cbcg indeks (BM25-only, opciono vektori kasnije).
    """
    client = SearchIndexClient(SEARCH_ENDPOINT, AzureKeyCredential(SEARCH_KEY))
    
    index = SearchIndex(
        name=NEWS_INDEX,
        fields=[
            SimpleField(name="id", type=SearchFieldDataType.String, key=True),
            SearchableField(name="title", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
            SearchableField(name="body", type=SearchFieldDataType.String, analyzer_name="standard.lucene"),
            SimpleField(name="url", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="published_at", type=SearchFieldDataType.String, filterable=True),
            SimpleField(name="hash", type=SearchFieldDataType.String, filterable=True)
        ]
    )
    
    client.create_or_update_index(index)
    print(f"Created index: {NEWS_INDEX}")


def embed(texts: List[str], model: str = "text-embedding-3-large") -> List[List[float]]:
    """
    OpenAI embedding generation.
    
    Args:
        texts: Lista teksta za embedding
        model: Embedding model (text-embedding-3-large)
        
    Returns:
        Lista embedding vektora
    """
    client = OpenAI(
        api_key=os.environ["OPENAI_API_KEY"],
        base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    )
    
    resp = client.embeddings.create(
        model=model,
        input=texts
    )
    
    return [d.embedding for d in resp.data]


def ingest_pdf(pdf_path: str):
    """
    Ingest PDF dokumenta u Azure AI Search.
    
    Args:
        pdf_path: Putanja do PDF fajla
    """
    from .parse_pdf import extract_pdf
    from .chunking import chunk
    
    docs = []
    
    # Parse PDF
    for page in extract_pdf(pdf_path):
        for seg in chunk(page["text"]):
            doc_id = str(uuid.uuid4())
            docs.append({
                "id": doc_id,
                "title": "SEPA Q&A",
                "content": seg,
                "source": "pdf:SEPA_QnA",
                "page": page["page"]
            })
    
    # Batch embedding & upload
    search_client = SearchClient(SEARCH_ENDPOINT, FAQ_INDEX, AzureKeyCredential(SEARCH_KEY))
    
    batch_size = 64
    for i in range(0, len(docs), batch_size):
        slice_docs = docs[i:i + batch_size]
        
        # Embed
        vectors = embed([d["content"] for d in slice_docs])
        
        # Add vectors to docs
        for doc, vec in zip(slice_docs, vectors):
            doc["content_vector"] = vec
        
        # Upload
        search_client.upload_documents(slice_docs)
        print(f"Uploaded batch {i//batch_size + 1}/{(len(docs)-1)//batch_size + 1}")
    
    print(f"Ingested {len(docs)} chunks from {pdf_path}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        ingest_pdf(pdf_path)
    else:
        print("Usage: python push_to_search.py <pdf_path>")


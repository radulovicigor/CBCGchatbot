# CBCG Chatbot - SEPA RAG Assistant

End-to-end RAG chatbot za Centralnu banku Crne Gore, sa fokusom na SEPA plaćanja i javna saopštenja CBCG.

## 🎯 Features

- **Hybrid Search**: Kombinacija keyword + semantic search za brze i pametne odgovore
- **Vector Database**: FAISS + OpenAI embeddings za semantic understanding
- **Auto-Scraping**: Automatski skrejpovanje cbcg.me za nove vesti i saopštenja
- **Smart Source Extraction**: Prikazuje relevantne izvore samo kada su potrebni
- **1740+ Documents**: Saopštenja, vesti, blog, intervjui, FAQ, SEPA dokumentacija

## 🚀 Quick Start

### 1. Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
copy env_template.txt .env
# Edit .env i dodaj svoj OPENAI_API_KEY
```

### 3. Parse PDF & Build Vector Index

```bash
python parse_and_store.py
python build_vector_index.py
```

### 4. Start API

```bash
python run_api.bat
```

### 5. Test

Otvorite `simple_chat.html` u browseru ili koristite API:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question":"Kako da posaljem novac u Njemacku?","lang":"cg"}'
```

## 📊 Current Status

- ✅ **1740 documents** indexed (news, PDF, blog, FAQ)
- ✅ **Hybrid search** (keyword + vector)
- ✅ **Auto-scraping** cbcg.me (daily)
- ✅ **Smart source** extraction
- ✅ **Vector DB** with caching
- ✅ **Local development** ready

## 🏗️ Architecture

```
CBCG_Chatbot/
├── apps/
│   ├── api/                 # FastAPI RAG servis
│   │   ├── main.py         # API endpoints
│   │   ├── rag_pipeline.py # RAG logic
│   │   ├── prompts.py      # System prompts
│   │   └── retrieval_mock.py # Hybrid search
│   ├── functions/           # Scraper functions
│   │   └── local_scraper.py # cbcg.me scraper
│   └── ingest/              # Data storage
│       ├── local_storage.py # Keyword search
│       └── local_storage_vector.py # Vector search
├── data/
│   ├── parsed_data.json     # 1740 documents
│   ├── vector_index.faiss  # FAISS index (10MB)
│   └── docs_metadata.pkl    # Metadata
├── simple_chat.html         # Chat UI
├── run_api.bat             # Start API
├── run_scraper.bat         # Run scraper
└── check_scraper_status.py # Database status
```

## 🔧 Usage

### Start API Server

```bash
# Windows
run_api.bat

# Manually
uvicorn apps.api.main:app --reload --port 8000
```

API dostupan na: `http://localhost:8000`

### Run Scraper

```bash
# Manually
python apps\functions\local_scraper.py

# With batch file
run_scraper.bat
```

### Check Database Status

```bash
python check_scraper_status.py
```

### Rebuild Vector Index

```bash
python build_vector_index.py
```

## 📁 Document Sources

- **SEPA Q&A** (PDF) - 34 dokumenta
- **Saopštenja** (cbcg.me) - 1249 vesti
- **Događaji** (cbcg.me) - 137 vesti
- **Intervjui** (cbcg.me) - 81 vest
- **Blog** (cbcg.me) - 16 članaka
- **FAQ** (cbcg.me) - 16 pitanja
- **O nama** (cbcg.me) - 185 stranica

**Total: 1740 dokumenta**

## 🔍 Search Strategy

### Hybrid Approach

1. **Keyword Search** (90% slučajeva - instant)
   - Brz keyword matching
   - Uzima prvi izvor sa validnim URL-om

2. **Vector Search** (10% slučajeva - 1s)
   - Semantic understanding
   - Za kompleksne upite

### Caching

- Embeddings se keširaju (`data/embedding_cache.pkl`)
- Isti query → instant odgovor (0.04s)

## 🚀 Next Steps: Azure Deployment

### 1. Azure Resources

- **App Service** - FastAPI hosting
- **Azure AI Search** - Managed vector database
- **Blob Storage** - Document storage
- **Functions** - Scheduled scraper

### 2. Migration

```bash
# Move from local_storage_vector.py to Azure AI Search
# Update retrieval_mock.py to use Azure Search
# Deploy to Azure App Service
```

## 📚 API Endpoints

- `GET /health` - Health check
- `POST /ask` - Ask question
  ```json
  {
    "question": "Kako da posaljem novac?",
    "lang": "cg"
  }
  ```
- `GET /docs` - API documentation

## 🔧 Configuration

### Environment Variables (.env)

```env
OPENAI_API_KEY=sk-...
OPENAI_MODEL_RESPONSES=gpt-4o
ANSWER_TEMPERATURE=0.1
MAX_CHUNKS=12
```

## 📝 Development

### Local Development

```bash
# Start API
uvicorn apps.api.main:app --reload --port 8000

# Run scraper
python apps\functions\local_scraper.py

# Check status
python check_scraper_status.py

# Rebuild indexes
python build_vector_index.py
```

## 📊 Performance

- **Keyword Search**: 10-20ms
- **Vector Search**: 1s (first call), 40ms (cached)
- **Hybrid**: 99% keyword (fast), 1% vector (smart)
- **Total Response Time**: 2-3s (includes LLM)

## 📖 More Info

- `VECTOR_DATABASE_INFO.md` - Vector DB details
- `simple_chat.html` - Chat UI
- `check_scraper_status.py` - Database status script

## 📄 License

MIT

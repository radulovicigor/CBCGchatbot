# 🏦 CBCG Chatbot - Službeni Asistent za SEPA Plaćanja

Inteligentni chatbot asistent Centralne banke Crne Gore za pitanja o SEPA plaćanjima i službenim saopštenjima.

## 🚀 Karakteristike

- **Multilingual AI model** - Optimizovan za srpski/crnogorski jezik
- **Automatsko ažuriranje** - Dnevno skrejpuje nove članke sa cbcg.me
- **Hibridna pretraga** - Kombinuje keyword i semantic search za najbolje rezultate
- **Kontekstualni razgovori** - Pamti prethodna pitanja u konverzaciji
- **Temporalna svjesnost** - Prioritizuje novije informacije

## 📋 Tehnologije

- **Backend**: FastAPI (Python 3.10+)
- **LLM**: OpenAI GPT-4o & GPT-4o-mini
- **Vector DB**: FAISS + multilingual-e5-large embeddings (1024-dim)
- **Scraper**: httpx + selectolax
- **Frontend**: HTML + Vanilla JavaScript

## 🔧 Brza Instalacija

### 1. Kloniraj repo
```bash
git clone https://github.com/radulovicigor/CBCGchatbot.git
cd CBCGchatbot
```

### 2. Instaliraj dependencies
```bash
pip install -r requirements.txt
```

### 3. Konfiguriši OpenAI API
```bash
# Kopiraj template i dodaj svoj API key
copy env_template.txt .env

# Edituj .env i dodaj:
# OPENAI_API_KEY=sk-your-key-here
```

### 4. Inicijalizuj bazu (prvi put)
```bash
# Scrape-uj članke sa cbcg.me
python apps/functions/local_scraper.py

# Build vektorsku bazu
python build_vector_index.py
```

### 5. Pokreni API server
```bash
# Windows
run_api.bat

# Linux/Mac
uvicorn apps.api.main:app --reload --port 8000
```

### 6. Otvori chat
Otvori `simple_chat.html` u browseru ili poseti:
```
http://localhost:8000/widget.html
```

## 📁 Struktura Projekta

```
CBCG_Chatbot/
├── apps/
│   ├── api/              # FastAPI backend
│   │   ├── main.py       # API endpoints
│   │   ├── rag_pipeline.py  # RAG logic
│   │   └── prompts.py    # System prompts
│   ├── functions/        # Scraper
│   │   └── local_scraper.py
│   └── ingest/           # Data processing
│       ├── local_storage_vector_multilingual.py  # Vector DB
│       └── local_storage.py  # JSON storage
├── data/                 # Database (gitignored)
│   ├── parsed_data.json  # Scraped articles
│   └── vector_index_multilingual.faiss  # Vector index
├── simple_chat.html      # Chat UI
├── schedule_scraper.py   # Daily scraper
└── requirements.txt
```

## 🔄 Automatsko Ažuriranje

### Jednom (ručno)
```bash
python apps/functions/local_scraper.py
python build_vector_index.py
```

### Svaki dan (automatski)
```bash
python schedule_scraper.py
```

Scraper se pokreće svaki dan u 2 AM i:
1. Skrejpuje nove članke sa cbcg.me
2. Dodaje ih u `parsed_data.json`
3. Automatski rebuild-uje vector index

## 🌐 API Endpoints

### POST `/ask`
Pošalji pitanje chatbot-u
```json
{
  "question": "Šta je SEPA?",
  "conversation_history": []  // Opciono
}
```

Odgovor:
```json
{
  "answer": "SEPA je platažna zona od 41 zemlje...",
  "sources": [
    {
      "title": "SEPA Q&A",
      "url": "https://cbcg.me/...",
      "published_at": "2025-10-27T15:55:49"
    }
  ],
  "answer_id": "chatcmpl-xxx"
}
```

### GET `/health`
Provera statusa servera

## 🎨 Frontend Integracija

### Samostalni Chat
```html
<iframe src="http://localhost:8000/widget.html" 
        width="400" height="600" frameborder="0">
</iframe>
```

### Custom implementacija
```javascript
fetch('http://localhost:8000/ask', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    question: 'Kako da pošaljem pare u Holandiju?'
  })
})
.then(res => res.json())
.then(data => console.log(data.answer));
```

## 🔑 Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-xxx              # Obavezno
OPENAI_MODEL_RESPONSES=gpt-4o      # Default: gpt-4o
ANSWER_TEMPERATURE=0.1             # Default: 0.1

# Server
MAX_CHUNKS=12                      # Max retrieved documents
PORT=8000                          # Server port
```

## 📊 Baza Podataka

### Trenutno stanje
```bash
# Provjeri status baze
python -c "
import json
with open('data/parsed_data.json', 'r', encoding='utf-8') as f:
    docs = json.load(f)
print(f'Total articles: {len(docs)}')
print(f'News: {len([d for d in docs if d.get(\"type\") == \"news\"])}')
print(f'PDF: {len([d for d in docs if d.get(\"type\") == \"pdf\"])}')
"
```

### Re-build vector index
```bash
# Nakon novih članaka
python build_vector_index.py
```

## 🐛 Troubleshooting

### Problem: "ModuleNotFoundError"
```bash
pip install -r requirements.txt
```

### Problem: "OPENAI_API_KEY not found"
```bash
# Provjeri .env fajl
echo %OPENAI_API_KEY%  # Windows
echo $OPENAI_API_KEY   # Linux/Mac
```

### Problem: "No articles scraped"
```bash
# Provjeri internet konekciju i SSL
python apps/functions/local_scraper.py
```

### Problem: "Slow response times"
- Prvo pitanje je sporije (učitavanje multilingual modela ~5-10s)
- Kasnije pitanje su brže (~1-2s)

## 🚀 Azure Deployment

Za deployment na Azure AI Foundry, pogledaj:
- `AZURE_DEPLOYMENT_CHECKLIST.md` - Detaljne instrukcije
- Estimirani troškovi: **$30-45/mjesec**
- Vrijeme: **6-8 sati**

## 📝 Licence

MIT License - slobodno koristiti za komercijalne svrhe.

## 🤝 Podrška

Za pitanja i podršku:
- Email: info@cbcg.me
- Web: https://www.cbcg.me

---

**Developed with ❤️ for Centralna Banka Crne Gore**

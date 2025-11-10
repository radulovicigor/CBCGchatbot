# Azure AI Foundry Deployment Checklist

## 1. Azure Resources Potrebni

### Obavezno:
- [ ] **Azure OpenAI Service**
  - Model: `gpt-4o` (za synthesis)
  - Model: `gpt-4o-mini` (za provere)
  - Region: **Sweden Central** ili **East US 2** (najbolja dostupnost)
  
- [ ] **Azure App Service**
  - Tier: **B1** (Basic, ~$13/month)
  - OS: Linux
  - Runtime: Python 3.10

- [ ] **Azure Blob Storage**
  - Account type: Standard (LRS)
  - Za: `parsed_data.json`, `vector_index_multilingual.faiss`, backups

### Opciono (ali preporučeno):
- [ ] **Azure Logic Apps** ili **Azure Functions**
  - Za: Daily scraper (Timer Trigger u 2 AM)
  
- [ ] **Azure Key Vault**
  - Za: API keys, connection strings

- [ ] **Azure Application Insights**
  - Za: Monitoring i logging

---

## 2. Izmene Koda

### A. Azure OpenAI umesto OpenAI API

**Trenutno (local):**
```python
from openai import OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
```

**Za Azure:**
```python
from openai import AzureOpenAI
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
)
```

**Fajlovi za izmenu:**
- `apps/api/rag_pipeline.py`
- `apps/api/main.py`

---

### B. Azure Blob Storage za vektorsku bazu

**Dodati:**
```python
from azure.storage.blob import BlobServiceClient

# Download FAISS index from Blob on startup
# Upload updated index after scraping
```

**Fajlovi:**
- `apps/ingest/local_storage_vector_multilingual.py`
- `apps/functions/local_scraper.py`

---

### C. Environment Variables

**Kreirati `.env` za Azure:**
```bash
# Azure OpenAI
AZURE_OPENAI_KEY=your-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_GPT4=gpt-4o
AZURE_OPENAI_DEPLOYMENT_GPT4_MINI=gpt-4o-mini

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=your-connection-string
AZURE_STORAGE_CONTAINER=cbcg-data

# App Settings
PORT=8000
WORKERS=2
```

---

## 3. Deployment Files Potrebni

### A. `requirements.txt` - već postoji ✅

### B. `startup.sh` - kreiraj
```bash
#!/bin/bash
# Download vector index from Azure Blob
python scripts/download_index.py

# Start FastAPI
gunicorn apps.api.main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 300
```

### C. `azure.yaml` (za Azure Developer CLI)
```yaml
name: cbcg-chatbot
services:
  api:
    project: .
    language: python
    host: appservice
```

---

## 4. Deployment Koraci

### Lokalna priprema:
```bash
# 1. Testiraj sve lokalno
python -m uvicorn apps.api.main:app --port 8000

# 2. Freeze dependencies
pip freeze > requirements.txt

# 3. Test scraper
python apps/functions/local_scraper.py
```

### Azure setup:
```bash
# 1. Login
az login

# 2. Kreiraj resource group
az group create --name cbcg-chatbot-rg --location swedencentral

# 3. Kreiraj Azure OpenAI
az cognitiveservices account create \
  --name cbcg-openai \
  --resource-group cbcg-chatbot-rg \
  --kind OpenAI \
  --sku S0 \
  --location swedencentral

# 4. Deploy modele
az cognitiveservices account deployment create \
  --name cbcg-openai \
  --resource-group cbcg-chatbot-rg \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version "2024-05-13" \
  --model-format OpenAI \
  --sku-capacity 10 \
  --sku-name "Standard"

# 5. Kreiraj App Service
az webapp up \
  --runtime PYTHON:3.10 \
  --sku B1 \
  --name cbcg-chatbot \
  --resource-group cbcg-chatbot-rg

# 6. Set environment variables
az webapp config appsettings set \
  --resource-group cbcg-chatbot-rg \
  --name cbcg-chatbot \
  --settings AZURE_OPENAI_KEY=xxx AZURE_OPENAI_ENDPOINT=xxx
```

---

## 5. Scraper Automation na Azure

### Opcija A: Azure Logic Apps (najjednostavnije)
1. Kreiraj Logic App
2. Timer Trigger: "Recurrence" - svaki dan u 2 AM
3. HTTP Action: POST na `https://cbcg-chatbot.azurewebsites.net/api/scrape`

### Opcija B: Azure Functions
```python
import azure.functions as func

app = func.FunctionApp()

@app.schedule(schedule="0 0 2 * * *", arg_name="timer")
def daily_scraper(timer: func.TimerRequest):
    # Run scraper
    from apps.functions.local_scraper import scrape_cbcg
    count = scrape_cbcg()
    return f"Scraped {count} articles"
```

---

## 6. Monitoring

### Application Insights
```python
# Dodaj u main.py
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging

logger = logging.getLogger(__name__)
logger.addHandler(AzureLogHandler(
    connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
))
```

### Health Check Endpoint
```python
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "database": check_database(),
        "vector_index": check_vector_index(),
        "openai": check_openai_connection()
    }
```

---

## 7. Optimizacije za Production

### A. Caching
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_embedding_cached(text: str):
    return get_embedding(text)
```

### B. Rate Limiting
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/ask")
@limiter.limit("10/minute")
def ask(request: Request, payload: AskRequest):
    ...
```

### C. CORS za production
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://cbcg.me", "https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)
```

---

## 8. Estimated Costs (mjesečno)

### Minimalna konfiguracija:
- Azure App Service (B1): **$13**
- Azure OpenAI (GPT-4o, ~100k tokens/day): **$15-30**
- Azure Storage (10 GB): **$1**
- Azure Logic Apps (1 run/day): **$0.50**
- **UKUPNO: ~$30-45/mjesec**

### Optimalna konfiguracija:
- Azure Container Apps: **$30**
- Azure OpenAI: **$30-50**
- Azure AI Search (Basic): **$75**
- Azure Functions: **$5**
- **UKUPNO: ~$140-165/mjesec**

---

## 9. Deployment Timeline

### Faza 1: Azure Setup (2-3 sata)
- Kreiranje Azure resursa
- Konfiguracija OpenAI modela
- Setup storage account-a

### Faza 2: Code Changes (1-2 sata)
- Prelazak na Azure OpenAI
- Dodavanje Blob storage integracije
- Environment variables setup

### Faza 3: Deployment (1 sat)
- Push kod na Azure
- Testiranje API-ja
- Upload vektorske baze

### Faza 4: Scraper Setup (30 min)
- Kreiranje Logic App ili Function
- Testiranje scrapers

### Faza 5: Testing & Monitoring (1 sat)
- End-to-end testing
- Setup Application Insights
- Performance tuning

**UKUPNO: ~6-8 sati**

---

## 10. Pre-deployment Checklist

- [ ] Backup `parsed_data.json`
- [ ] Backup `vector_index_multilingual.faiss`
- [ ] Test API lokalno
- [ ] Dokumentuj sve API keys
- [ ] Pripremi production `.env`
- [ ] Test scraper
- [ ] Prepare rollback plan

---

## NEXT STEPS:

1. **Da li želiš MINIMALNU ili OPTIMALNU konfiguraciju?**
2. **Imaš li već Azure subscription?**
3. **Da li odmah krećemo ili prvo pravimo detaljnije skripte?**


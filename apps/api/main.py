"""
FastAPI RAG API za CBCG SEPA chatbot.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import AskRequest, AskResponse, Source
from .rag_pipeline import synthesize_answer
import os
from dotenv import load_dotenv

load_dotenv()

# Choose retrieval based on environment
# If Azure credentials are not configured or are placeholders, use mock
AZURE_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_KEY = os.getenv("AZURE_SEARCH_API_KEY", "")

USE_AZURE = (
    AZURE_ENDPOINT and 
    AZURE_KEY and 
    AZURE_ENDPOINT != "https://<search-name>.search.windows.net" and
    AZURE_KEY != "<admin-or-query-key>"
)

if USE_AZURE:
    from .retrieval import retrieve
    print("Using Azure Search for retrieval")
else:
    from .retrieval_mock import retrieve
    print("Using MOCK retrieval (no Azure configured)")

app = FastAPI(
    title="CBCG SEPA Bot",
    version="0.1.0",
    description="RAG chatbot za Centralnu banku Crne Gore"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_sources(answer_text: str, ctx_docs: list, question: str) -> list[Source]:
    """
    Eksrakcija citata iz odgovora - PAMETNA logika za relevantne izvore.
    """
    # Ako je pitanje greeting ili casual - NE daj izvore
    greeting_words = ['ćao', 'zdravo', 'dobro jutro', 'dobro veče', 'dobro dan', 'zdravo', 'pozdrav', 'hello', 'hi']
    if any(word in question.lower() for word in greeting_words):
        return []
    
    # Ako pitanje ima "kako si", "kako ste" - NE daj izvore
    if 'kako si' in question.lower() or 'kako ste' in question.lower():
        return []
    
    # Ako je odgovor previše kratak - verovatno general knowledge, NE daj izvor
    if len(answer_text) < 50:
        return []
    
    # Ako je odgovor samo general info bez specifičnih detalja - NE daj izvor
    generic_answers = ['nemam informacija', 'trenutno nemam', 'ne znam', 'ne mogu da odgovorim']
    if any(phrase in answer_text.lower() for phrase in generic_answers):
        return []
    
    # Ako nema konteksta - NE daj izvore
    if not ctx_docs:
        return []
    
    # Uzmi NAJPOUZDANIJI izvor:
    # 1. Preferiraj news dokumente (sa URL-om)
    # 2. Izbegavaj generičke izvore
    # 3. Koristi samo postojeće izvore
    
    for doc in ctx_docs:
        # Preskoči dokumente bez sadržaja
        if not doc.get("content"):
            continue
            
        # Preferiraj news dokumente (sa HTTP URL-om)
        if doc.get("url") and doc["url"].startswith("http"):
            title = doc.get("title", "CBCG saopštenje")
            if len(title) > 5:  # Valid title
                return [Source(
                    title=title[:100],  # Limit length
                    url=doc["url"],
                    source=doc.get("source", "cbcg.me"),
                    page=doc.get("page")
                )]
        
        # Fallback na PDF/SEPA dokumente
        if doc.get("source") and "pdf" in doc["source"].lower():
            return [Source(
                title=doc.get("title", "SEPA Q&A"),
                url=None,
                source=doc.get("source", "pdf:SEPA_QnA"),
                page=doc.get("page")
            )]
    
    # Ako nema ništa relevantno - NE daj izvor
    return []


def check_inappropriate_content(question: str) -> str | None:
    """
    Proverava da li pitanje sadrži neprimjerene sadržaje.
    Vraća profesionalni odgovor ako je neprimjereno.
    """
    inappropriate_words = ['kurva', 'kurac', 'jebem', 'picka', 'sr*ane', 'gluposti']
    
    question_lower = question.lower()
    for word in inappropriate_words:
        if word in question_lower:
            return "Možete izvršiti plaćanje kroz SEPA sistem, ali molimo vas da zadržite profesionalni i pošten način komunikacije. Hvala na razumijevanju."
    
    return None


@app.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    """
    Glavni endpoint za postavljanje pitanja.
    
    Args:
        payload: AskRequest (question, lang)
        
    Returns:
        AskResponse (answer, sources, answer_id)
    """
    try:
        # Proveri neprimjeren sadržaj
        inappropriate_response = check_inappropriate_content(payload.question)
        if inappropriate_response:
            return AskResponse(
                answer=inappropriate_response,
                sources=[],
                answer_id="inappropriate"
            )
        
        # Retrieval
        ctx = retrieve(payload.question, k=8)
        
        if not ctx:
            return AskResponse(
                answer="Trenutno nemam pouzdan izvor za ovo.",
                sources=[],
                answer_id="no-source"
            )
        
        # Synthesis
        answer, answer_id = synthesize_answer(payload.question, ctx)
        
        # Extract sources (samo za relevantna pitanja)
        sources = extract_sources(answer, ctx, payload.question)
        
        return AskResponse(
            answer=answer,
            sources=sources,
            answer_id=answer_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


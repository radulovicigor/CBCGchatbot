"""
RAG pipeline: retrieval + synthesis (OpenAI Chat Completions).
"""
import os
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from openai import OpenAI
from .prompts import get_system_prompt
from dotenv import load_dotenv

# Load .env file
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)


def synthesize_answer(
    query: str, 
    ctx_docs: List[Dict],
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> tuple[str, str]:
    """
    Sinteza odgovora koristeći kontekst + OpenAI Chat Completions.
    
    Args:
        query: Korisničko pitanje
        ctx_docs: Lista relevantnih dokumenata
        conversation_history: Prethodne poruke u konverzaciji (opciono)
        
    Returns:
        (answer, answer_id)
    """
    # Kontekst svedi na ~10-15k tokena
    context_blocks = []
    for i, d in enumerate(ctx_docs, start=1):
        # Ne dodaj numerisane reference - samo content
        body = d["content"][:2000]  # Skrati na 2000 char
        # Dodaj datum ako postoji
        if d.get("published_at"):
            try:
                pub_date = datetime.fromisoformat(d.get("published_at", "").replace('Z', '+00:00'))
                date_str = pub_date.strftime("%Y-%m-%d")
                body = f"[Datum: {date_str}] {body}"
            except:
                pass
        context_blocks.append(body)
    
    # Proveri da li kontekst sadrži relevantne informacije
    if not context_blocks or len(context_blocks) == 0:
        return "Nemam informacije o tome.", "no-context"
    
    # Kreiraj system prompt sa trenutnim datumom
    current_date = datetime.now().strftime("%Y-%m-%d")
    system_prompt = get_system_prompt(current_date)
    
    # Kreiraj messages sa kontekstom konverzacije
    messages = [{"role": "system", "content": system_prompt}]
    
    # Dodaj prethodne poruke ako postoje
    if conversation_history:
        for msg in conversation_history[-6:]:  # Zadnje 6 poruka (3 pitanja + 3 odgovora)
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                messages.append({"role": role, "content": content})
    
    # Dodaj trenutno pitanje i kontekst
    context_text = "\n\n---\n\n".join(context_blocks)
    user_content = f"""Pitanje: {query}

Kontekst sa relevantnim informacijama:
{context_text}

TVOJ ZADATAK:
- Pažljivo pročitaj kontekst
- Izvuci sve informacije relevantne za pitanje
- Sintetiši ih u prirodan, koncizan odgovor
- Ako kontekst ima informacije - ODGOVORI, ne traži savršen match
- Ako kontekst je potpuno prazan ili nerelevanten - kaži "Nemam informacije o tome."
"""
    messages.append({"role": "user", "content": user_content})
    
    # Chat Completions API – standardni poziv
    # Koristi gpt-4o za najbolje odgovore (synthesis zahteva najbolji model)
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.3,  # Balans izmedu preciznosti i kreativnosti za bolje reasoning
        max_tokens=800
    )
    
    text = resp.choices[0].message.content
    answer_id = resp.id
    
    # Clean up response - ukloni nepotrebne klauze na kraju
    # Ukloni fraze poput "Nadam se da...", "Ako imaš još pitanja..." itd.
    import re
    
    # Remove "Zdravo!" u više odgovora
    # Ako odgovor počinje sa "Zdravo!" a pitanje NIJE greeting - ukloni
    if text.strip().startswith('Zdravo!') and len(text) > 50:
        text = text.replace('Zdravo!', '').strip()
        if text.startswith(' '):
            text = text[1:]
    
    # Remove markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove **bold**
    text = re.sub(r'\*(.*?)\*', r'\1', text)      # Remove *italic*
    text = re.sub(r'^#+ ', '', text, flags=re.MULTILINE)  # Remove headers
    text = re.sub(r'^\d+\.\s+', '', text, flags=re.MULTILINE)  # Remove 1. 2. 3. lists
    text = re.sub(r'^-\s+', '- ', text, flags=re.MULTILINE)  # Keep dashes natural
    
    # Remove common ending phrases - STROGO UKLONJENO
    unwanted_endings = [
        r'Ako imate još.*',
        r'Ako imate dodatna pitanja.*',
        r'Ako imate.*pitanja.*',
        r'slobodno.*pitajte.*',
        r'slobodno ih postavite.*',
        r'Nadam se da.*',
        r'Hvala na razumevanju.*',
        r'Obratite se.*',
        r'kontaktirate.*',
        r'preporučujem.*',
        r'posjetite.*',
        r'Preporučujem da posjetite.*',
        r'Preporučujem da kontaktirate.*',
        r'Ako vam treba.*',
        r'Za.*informacije.*kontaktirate.*',
        r'Za.*informacije.*posjetite.*',
        r'Srdačno.*',
        r'Uživajte.*',
        r'Veselim se.*',
        r'Imate još pitanja.*',
        r'Za dodatne informacije.*',
        r'Ako imaš.*',
        r'Slagam se.*',
        r'^U redu.*',
        r'SEPA Q\&A.*',
        r'pdf:SEPA_QnA.*',
        r'str\.\s*\d+.*',
        r'\(.*pdf.*\).*',
    ]
    
    for pattern in unwanted_endings:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    # Remove multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Remove lines that are just page references
    lines = text.split('\n')
    filtered_lines = []
    for line in lines:
        line_clean = line.strip()
        # Skip ako je linija sadrži samo reference info
        if any(keyword in line_clean for keyword in ['SEPA Q&A', 'pdf:', 'str.', '(pdf', '[1]', '[2]', '[3]']):
            continue
        # Skip prazne linije
        if not line_clean:
            continue
        filtered_lines.append(line)
    
    text = '\n'.join(filtered_lines)
    
    # If answer is too long (over 500 chars), try to summarize first paragraph
    if len(text) > 500 and '\n' in text:
        first_part = text.split('\n')[0]
        if len(first_part) < 100:
            # Take first two paragraphs
            text = '\n'.join(text.split('\n')[:2])
    
    # Trim whitespace
    text = text.strip()
    
    # STROGA PROVERA: Ako je odgovor generičan ili ne odgovara na pitanje
    query_lower = query.lower()
    answer_lower = text.lower()
    
    # Ako odgovor sadrži generičke fraze koje ne daju konkretan odgovor
    generic_phrases = [
        'kontaktirate', 'preporučujem', 'obratite se', 'posjetite', 
        'zvaničnu web stranicu', 'za precizne informacije',
        'nisu dostupne', 'nisu navedene', 'nije navedena', 'nije dostupna',
        'dostavljenim dokumentima', 'dostupnim informacijama',
        'ako imate dodatna pitanja', 'slobodno pitajte',
        'međutim.*nisu dostupne', 'ali.*nije navedena',
        'za.*informacije.*kontaktirate', 'za.*informacije.*posjetite'
    ]
    
    # Ako pitanje traži specifične informacije (ulica, adresa, tačan podatak, prve pare)
    specific_question_keywords = ['ulici', 'ulica', 'adresi', 'adresa', 'adresu', 'tačno', 'tačan', 'tačna', 'prve pare', 'prvi']
    
    # PROVERA 1: Specifična pitanja + generički odgovori = NEMAM INFORMACIJE
    if any(word in query_lower for word in specific_question_keywords):
        # Proveri da li odgovor sadrži generičke fraze (koristi regex za pattern-e)
        has_generic = False
        for phrase in generic_phrases:
            if re.search(phrase, answer_lower, re.IGNORECASE):
                has_generic = True
                break
        if has_generic:
            return "Nemam informacije o tome.", "no-info"
    
    # PROVERA 2: Ako odgovor govori o nečem što nije u pitanju
    # Npr. pitanje o "prvim parama" a odgovor o "Prvoj banci" - NE ODGOVARA
    if 'prve pare' in query_lower or 'prvi pare' in query_lower:
        # Ako odgovor ne spominje valutu/novac već samo banku
        if 'prva banka' in answer_lower and ('valuta' not in answer_lower and 'pare' not in answer_lower):
            return "Nemam informacije o tome.", "no-info"
    
    # PROVERA 3: Ako odgovor je previše kratak i generičan
    if len(text) < 50:
        # Ako je odgovor kratak i sadrži generičke fraze
        short_generic = ['za više informacija', 'dostupnim', 'nisu dostupne', 'nisu navedene', 'preporučujem']
        if any(phrase in answer_lower for phrase in short_generic):
            return "Nemam informacije o tome.", "no-info"
    
    # PROVERA 4: Ako odgovor je prekinut - samo ako je VEOMA kratak (verovatno greška)
    # Ne prekidaj ako je normalna rečenica koja se nastavlja
    if text.endswith(',') and len(text) < 30:
        # Odgovor je prekinut i kratak - verovatno greška
        return "Nemam informacije o tome.", "no-info"
    
    return text, answer_id


"""
RAG pipeline: retrieval + synthesis (OpenAI Chat Completions).
"""
import os
import uuid
from typing import List, Dict
from openai import OpenAI
from .prompts import SYSTEM_PROMPT
from dotenv import load_dotenv

# Load .env file
load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)


def synthesize_answer(query: str, ctx_docs: List[Dict]) -> tuple[str, str]:
    """
    Sinteza odgovora koristeći kontekst + OpenAI Chat Completions.
    
    Args:
        query: Korisničko pitanje
        ctx_docs: Lista relevantnih dokumenata
        
    Returns:
        (answer, answer_id)
    """
    # Kontekst svedi na ~10-15k tokena
    context_blocks = []
    for i, d in enumerate(ctx_docs, start=1):
        # Ne dodaj numerisane reference - samo content
        body = d["content"][:2000]  # Skrati na 2000 char
        context_blocks.append(body)
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Pitanje: {query}\n\nKoristi ove informacije da odgovoriš:\n" + "\n\n---\n\n".join(context_blocks)}
    ]
    
    # Chat Completions API – standardni poziv
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL_RESPONSES", "gpt-4o"),
        messages=messages,
        temperature=float(os.getenv("ANSWER_TEMPERATURE", "0.1")),
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
    
    # Remove common ending phrases
    unwanted_endings = [
        r'Ako imate još.*',
        r'Nadam se da.*',
        r'Hvala na razumevanju.*',
        r'Obratite se.*',
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
        text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.MULTILINE)
    
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
    
    return text, answer_id


"""
FastAPI RAG API za CBCG SEPA chatbot.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .schemas import AskRequest, AskResponse, Source
from .rag_pipeline import synthesize_answer
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# OpenAI client za LLM-based provere
openai_client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
)

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
    Uzima NAJRELEVANTNIJI dokument (prvi iz ctx_docs jer je sortiran po relevantnosti).
    """
    # Ako je pitanje greeting ili casual - NE daj izvore
    greeting_words = ['ćao', 'zdravo', 'dobro jutro', 'dobro veče', 'dobro dan', 'zdravo', 'pozdrav', 'hello', 'hi']
    if any(word in question.lower() for word in greeting_words):
        return []
    
    # Ako pitanje ima "kako si", "kako ste" - NE daj izvore
    if 'kako si' in question.lower() or 'kako ste' in question.lower():
        return []
    
    # Ako je pitanje nejasno (samo "kad?", "gde?", "kako?") - NE daj izvore
    # Ako je odgovor generički (npr. "Vaše pitanje nije dovoljno jasno")
    if len(question.strip()) <= 5 and question.strip().rstrip('?').strip().lower() in ['kad', 'gde', 'kako', 'sta', 'sto', 'ko', 'kad?', 'gde?', 'kako?', 'sta?', 'sto?', 'ko?']:
        return []
    
    # Ako odgovor kaže da pitanje nije jasno - NE daj izvor
    unclear_phrases = ['nije dovoljno jasno', 'precizirate šta', 'nije jasno']
    if any(phrase in answer_text.lower() for phrase in unclear_phrases):
        return []
    
    # LLM-BASED PROVERA: Da li je odgovor disclaimer/generički odgovor?
    # Koristi GPT-4o da inteligentno proveri da li odgovor je disclaimer ili generički odgovor
    answer_lower = answer_text.lower()
    
    # BRZA PROVERA: Ako odgovor počinje sa izvinjavanjem, disclaimerom ili generičkim frazama - ne daj izvor
    answer_start = answer_text.strip()
    if (answer_start.startswith('Izvinjavam se') or 
        answer_start.startswith('Izvinjavam') or
        answer_start.startswith('Kako vam mogu pomoći') or
        answer_start.startswith('Ako imate') or
        answer_start.startswith('Možete izvršiti plaćanje kroz SEPA sistem') or
        answer_start.startswith('Možete izvršiti plaćanje') or
        answer_start.startswith('Zdravo!') or
        answer_start.startswith('Izgleda da vaše pitanje') or
        answer_start.startswith('Molim vas da ga precizirate') or
        answer_start.startswith('Nemam informacije o tome') or
        answer_start == 'Zdravo! Kako vam mogu pomoći?' or
        'molimo vas da zadržite profesionalni' in answer_lower or
        'nije jasno' in answer_lower or
        'molim vas da ga precizirate' in answer_lower):
        return []  # Sigurno je generički odgovor/disclaimer - ne daj izvor
    
    try:
        disclaimer_check = openai_client.chat.completions.create(
            model="gpt-4o-mini",  # Brz i jeftin za jednostavne DA/NE provere
            messages=[
                {
                    "role": "system",
                    "content": "Ti si asistent koji proverava da li odgovor je disclaimer/generički odgovor koji NE daje konkretne informacije. Odgovori SAMO sa 'DA' ili 'NE'."
                },
                {
                    "role": "user",
                    "content": f"Pitanje: {question}\n\nOdgovor: {answer_text}\n\nDa li je ovaj odgovor disclaimer/generički odgovor koji NE daje konkretne informacije?\n\nVAŽNO: Ako odgovor počinje sa 'Izvinjavam se', 'Kako vam mogu pomoći', 'Ako imate konkretno pitanje', 'nisam siguran šta tačno želite' - to su generički odgovori koji NE treba da imaju izvore.\n\nOdgovori SAMO sa 'DA' ili 'NE'."
                }
            ],
            temperature=0.1,
            max_tokens=10
        )
        
        disclaimer_answer = disclaimer_check.choices[0].message.content.strip().upper()
        if disclaimer_answer.startswith('DA'):
            return []  # Odgovor je disclaimer/generički - ne daj izvor
    except Exception as e:
        print(f"Error checking disclaimer: {e}")
        # Fallback: ako LLM fail-uje, koristi osnovne provere
        generic_phrases_fallback = [
            'nisam siguran', 'izvinjavam se', 'molim vas da postavite', 
            'možete izvršiti plaćanje', 'hvala', 'kako vam mogu pomoći',
            'ako imate konkretno pitanje', 'slobodno ga postavite'
        ]
        if any(phrase in answer_lower for phrase in generic_phrases_fallback):
            return []  # Generički odgovor - ne daj izvor
    
    # DODATNA PROVERA: Ako odgovor ne odgovara na pitanje (generički odgovor) - NE daj izvor
    # Npr. "kolko je sati" -> "ne mogu vam reći koliko je sati" - to nije odgovor iz članka
    generic_non_answer_phrases = [
        'ne mogu vam reći',
        'nažalost, ne mogu',
        'molim vas da provjerite',
        'na svom uređaju',
        'ili satu',
        'ako imate pitanja o sepa',
        'slobodno pitajte',
        'izgleda da je vaš upit prekinut',
        'ako imate konkretno pitanje',
        'slobodno ga postavite',
        'rado ću vam pomoći',
        'za više informacija o sepa plaćanjima',
        'za više informacija',
        'ako ste iz',
        'zanima vas sepa'
    ]
    if any(phrase in answer_lower for phrase in generic_non_answer_phrases):
        return []  # Generički odgovor koji ne odgovara na pitanje - ne daj izvor
    
    # Ako je odgovor previše kratak - verovatno general knowledge, NE daj izvor
    if len(answer_text) < 50:
        return []
    
    # Ako je odgovor samo general info bez specifičnih detalja - NE daj izvor
    # Proveri različite varijante "nemam informacija"
    no_info_phrases = [
        'nemam informacija', 
        'nemam informacije',
        'nemam informacije o tome',
        'trenutno nemam', 
        'ne znam', 
        'ne mogu da odgovorim',
        'nemam podatke',
        'nemam dostupne informacije',
        'trenutno nemam dostupne informacije',
        'nemam pouzdan izvor',
        'nema informacija',
        'ne mogu pronaći',
        'ne mogu pronaći informacije',
        'nije dostupna',
        'nisu dostupne',
        'nije navedena',
        'nisu navedene',
        'nije dostupan',
        'nisu dostupni'
    ]
    # STROGA PROVERA: Ako odgovor SADRŽI bilo koju od ovih fraza - NE DAVATI IZVOR
    if any(phrase in answer_lower for phrase in no_info_phrases):
        return []
    
    # DODATNA PROVERA: Ako odgovor je previše kratak i generičan - ne daj izvor
    if len(answer_text.strip()) < 50:
        # Proveri da li sadrži generičke fraze
        generic_phrases = ['kontaktirate', 'preporučujem', 'obratite se', 'posjetite', 'za više informacija']
        if any(phrase in answer_lower for phrase in generic_phrases):
            return []  # Previše generičan odgovor - ne daj izvor
    
    # Ako nema konteksta - NE daj izvore
    if not ctx_docs:
        return []
    
    # Uzmi NAJRELEVANTNIJI izvor - ali proveri da li je ZAPRAVO relevantan
    # (retrieve vraća dokumente sortirane po relevantnosti)
    
    question_lower = question.lower()
    answer_lower = answer_text.lower()
    
    # Izvuci ključne reči iz pitanja i odgovora
    # Ukloni stop-words (kratke, nevažne reči)
    stop_words = {'kako', 'da', 'za', 'su', 'je', 'na', 'ne', 'se', 'ili', 'o', 'i', 'a', 'u', 'po', 'sa', 'od', 'kao'}
    
    keywords_from_question = set([w for w in question_lower.split() if len(w) > 3 and w not in stop_words])
    keywords_from_answer = set([w for w in answer_lower.split() if len(w) > 3 and w not in stop_words])
    all_keywords = keywords_from_question | keywords_from_answer
    
    # Dodaj specifične keyword-e za različite tipove pitanja
    if any(word in question_lower for word in ['sepa', 'plaćanj', 'transfer', 'slati', 'posalji', 'novac', 'pare']):
        all_keywords.add('sepa')
        all_keywords.add('plaćanj')
    
    if any(word in question_lower for word in ['irsk', 'irskoj', 'irsk']):
        all_keywords.add('irsk')
    
    if any(word in question_lower for word in ['provizij', 'trošk', 'cijen']):
        all_keywords.add('provizij')
        all_keywords.add('trošk')
    
    best_doc = None
    best_score = 0
    
    # Izvuci specifične informacije iz odgovora PRED petljom (koriste se i van petlje)
    import re
    answer_numbers = set(re.findall(r'\b\d{4}\b', answer_text))  # Godine kao 2001
    important_terms = [w for w in answer_lower.split() if len(w) > 5 and w not in stop_words]
    
    # UNIVERZALNI FILTER: Ukloni dokumente koji očigledno nisu relevantni
    # (bez hardcodovanja specifičnih pitanja)
    filtered_docs = []
    for doc in ctx_docs:
        if not doc.get("content"):
            continue
        content_lower = doc.get("content", "").lower()
        title_lower = doc.get("title", "").lower()
        
        # Proveri da li dokument ima minimalan match sa pitanjem
        # (barem jedan keyword iz pitanja mora biti u naslovu ili content-u)
        has_question_match = any(kw in title_lower or kw in content_lower[:500] for kw in keywords_from_question if len(kw) > 3)
        
        if not has_question_match and len(keywords_from_question) > 0:
            continue
        
        filtered_docs.append(doc)
    
    ctx_docs = filtered_docs if filtered_docs else ctx_docs
    
    # Prođi kroz dokumente i nađi onaj koji je NAJRELEVANTNIJI za pitanje
    for doc in ctx_docs:
        if not doc.get("content"):
            continue
        
        content_lower = doc.get("content", "").lower()
        title_lower = doc.get("title", "").lower()
        
        # Score relevantnosti - koliko keyword-a se poklapa
        score = 0
        matched_keywords_set = set()  # Unique matched keywords
        
        # Match u naslovu = više bodova
        for keyword in all_keywords:
            if keyword in title_lower:
                score += 5
                matched_keywords_set.add(keyword)
            if keyword in content_lower[:500]:  # Prvih 500 karaktera je važnije
                score += 2
                matched_keywords_set.add(keyword)
        
        # KRITIČNA PROVERA: Da li dokument ZAPRAVO sadrži informacije iz odgovora?
        # Izvuci ključne informacije iz odgovora
        answer_keywords = set([w for w in answer_lower.split() if len(w) > 4 and w not in stop_words])
        
        # Dodaj specifične informacije iz odgovora (brojevi, specifične reči)
        import re
        # Izvuci brojeve (npr. 2001, 41, brexit, ujedinjeno kraljevstvo)
        numbers = re.findall(r'\b\d{4}\b', answer_text)  # Godine kao 2001
        specific_terms = []
        if 'brexit' in answer_lower or 'uk' in answer_lower or 'ujedinjeno' in answer_lower:
            specific_terms.extend(['brexit', 'uk', 'ujedinjeno', 'kraljevstvo'])
        if 'osnovan' in answer_lower or 'osnovana' in answer_lower:
            specific_terms.extend(['osnovan', 'osnovana', 'godine'])
        
        # Proveri da li dokument sadrži specifične informacije
        answer_matches = sum(1 for kw in answer_keywords if kw in content_lower[:1500])
        specific_matches = sum(1 for term in specific_terms if term in content_lower)
        number_matches = sum(1 for num in numbers if num in content_lower)
        
        # STRICT: Dokument MORA imati barem 2 match-a iz odgovora ILI specifičnu informaciju
        total_answer_matches = answer_matches + specific_matches + number_matches
        
        # JAKA PROVERA: Dokument MORA imati minimum 3 match-a iz odgovora
        # (osim ako nema puno keyword-a u odgovoru - onda minimum 2)
        min_answer_matches_required = 3 if len(answer_keywords) > 4 else 2
        
        if len(answer_keywords) > 2:
            if total_answer_matches < min_answer_matches_required:
                # Dokument ne sadrži dovoljno informacija iz odgovora - preskoči
                continue
        
        # UNIVERZALNA PROVERA: Dokument mora sadržati SPECIFIČNE informacije iz ODGOVORA
        # Proveri da li dokument sadrži barem NEKE specifične informacije iz odgovora
        doc_has_answer_numbers = any(num in content_lower for num in answer_numbers)
        doc_has_important_terms = sum(1 for term in important_terms if term in content_lower[:2000])
        
        # Ako odgovor ima specifične brojeve (npr. "2001"), dokument MORA da ih sadrži
        if len(answer_numbers) > 0:
            # Ako odgovor ima broj ali dokument ga nema - preskoči
            if not doc_has_answer_numbers:
                continue
        
        # Ako odgovor ima više važnih termina, dokument mora imati barem neke
        if len(important_terms) > 3:
            if doc_has_important_terms < 2:
                # Dokument ne sadrži dovoljno važnih termina iz odgovora
                continue
        
        # Bonus za SEPA dokumente ako je pitanje o SEPA-u
        if 'sepa' in question_lower and 'sepa' in content_lower:
            score += 3
            matched_keywords_set.add('sepa')
        if 'sepa' in question_lower and 'sepa' in title_lower:
            score += 5
            matched_keywords_set.add('sepa')
        
        matched_keywords_count = len(matched_keywords_set)
        
        # JAKA PROVERA: Dokument MORA imati minimum 3 keyword match-a za biti relevantan
        # (osim ako nema puno keyword-a - onda minimum 2)
        min_required = 3 if len(all_keywords) > 4 else 2
        if matched_keywords_count < min_required:
            # Preskoči ovaj dokument - nije dovoljno relevantan
            continue
        
        # DODATNA PROVERA: Dokument mora imati match i u naslovu ILI na početku content-a
        has_title_match = any(kw in title_lower for kw in all_keywords)
        has_early_content_match = any(kw in content_lower[:300] for kw in all_keywords)
        
        if not (has_title_match or has_early_content_match):
            # Ako nema match ni u naslovu ni na početku - preskoči
            continue
        
        # Bonus za news dokumente sa URL-om
        if doc.get("url") and doc["url"].startswith("http"):
            score += 1
        
        # UNIVERZALNA PROVERA: Naslov i content moraju biti relevantni za pitanje
        # Proveri da li naslov ili content sadrže keyword-e iz pitanja
        title_matches_question = any(kw in title_lower for kw in keywords_from_question if len(kw) > 3)
        content_matches_question = any(kw in content_lower[:500] for kw in keywords_from_question if len(kw) > 3)
        
        # Ako ni naslov ni content ne odgovaraju na pitanje - preskoči
        if not (title_matches_question or content_matches_question):
            continue
        
        # DODATNA PROVERA: Ako odgovor sadrži specifične brojeve, proveri da dokument NE sadrži samo pogrešne
        # Npr. ako odgovor kaže "2001", dokument ne sme imati samo "1901" bez "2001"
        if len(answer_numbers) > 0:
            # Proveri da li dokument ima tačan broj - već provereno gore, ali dodatna sigurnosna provera
            # Ovo je samo dodatna provera - glavna provera je gore
            pass
        
        # FINALNA PROVERA: Dokument mora imati JAK match
        # Minimum score: barem 7 bodova (barem 1 keyword u naslovu + 2-3 u content-u)
        if score < 7:
            continue
        
        # Ako dokument ima dobar score i validan je - sačuvaj ga
        # TAKOĐE: mora imati barem 2 keyword match-a i barem 2 match-a iz odgovora
        if score > best_score and matched_keywords_count >= 2 and total_answer_matches >= 2:
            # Validacija: dokument mora imati smislen sadržaj
            if doc.get("title") and len(doc.get("title", "")) > 5:
                best_doc = doc
                best_score = score
    
    # UNIVERZALNA FINALNA PROVERA: Dokument mora proći SVE provere i imati visok score
    # Minimum score: mora imati barem 10 bodova (barem 2 keyword-a u naslovu + nekoliko u content-u)
    # Povećaj minimum ako odgovor sadrži specifične informacije (brojevi, imena)
    min_score_required = 10
    
    # Ako odgovor sadrži specifične brojeve (godine, brojevi) - povećaj minimum
    if len(answer_numbers) > 0:
        min_score_required = 15  # Više bodova za specifične brojeve
    
    # Ako odgovor sadrži više važnih termina - povećaj minimum
    if len(important_terms) > 5:
        min_score_required = 15
    
    # DODATNA PROVERA: Ako nema dovoljno jak match, jednostavno ne dati izvor
    # NEMA FALLBACK-a - ako dokument ne prođe sve provere, ne daj izvor
    if best_score < min_score_required:
        return []
    
    # FINALNA PROVERA: Da li odgovor ZAPRAVO sadrži specifične informacije iz dokumenta?
    # Ako odgovor ne sadrži specifične informacije (npr. samo generički odgovor), ne daj izvor
    if best_doc:
        # Proveri da li odgovor sadrži specifične informacije koje se mogu naći u dokumentu
        doc_content_lower = best_doc.get("content", "").lower()
        doc_title_lower = best_doc.get("title", "").lower()
        
        # Izvuci specifične reči iz odgovora (duže od 5 karaktera, nisu stop-words)
        specific_words_in_answer = [w for w in answer_lower.split() if len(w) > 5 and w not in stop_words]
        
        # Proveri da li barem 3 specifične reči iz odgovora se mogu naći u dokumentu
        matches_in_doc = sum(1 for word in specific_words_in_answer if word in doc_content_lower[:2000] or word in doc_title_lower)
        
        # STROGA PROVERA: Ako odgovor ne sadrži dovoljno specifičnih informacija iz dokumenta - ne daj izvor
        if matches_in_doc < 3:
            return []  # Odgovor ne sadrži dovoljno specifičnih informacija iz dokumenta (minimum 3 match-a)
        
        # DODATNA PROVERA: Da li odgovor odgovara na pitanje?
        # Ako pitanje traži specifičnu informaciju (npr. "kolko je sati", "gde je"), a odgovor kaže "ne mogu" - ne daj izvor
        question_keywords = set([w for w in question_lower.split() if len(w) > 3 and w not in stop_words])
        answer_keywords = set([w for w in answer_lower.split() if len(w) > 3 and w not in stop_words])
        
        # Ako pitanje i odgovor nemaju dovoljno zajedničkih keyword-a - možda odgovor ne odgovara na pitanje
        common_keywords = question_keywords & answer_keywords
        
        # STROGA PROVERA: Ako pitanje ima keyword-e, a odgovor nema NIJEDAN zajednički keyword - ne daj izvor
        if len(question_keywords) > 0 and len(common_keywords) == 0:
            return []  # Odgovor ne odgovara na pitanje - ne daj izvor
        
        # DODATNA PROVERA: Ako pitanje nije o SEPA/CBCG, a odgovor je o SEPA-u - možda ne odgovara na pitanje
        # Npr. "oce li partizan dobiti" -> odgovor o "dobit" (profit) - ne odgovara na pitanje
        question_has_sepa_cbcg = any(word in question_lower for word in ['sepa', 'cbcg', 'centraln', 'banka', 'plaćanj', 'transfer', 'novac', 'pare', 'finansij', 'monetarn'])
        answer_has_sepa_cbcg = any(word in answer_lower for word in ['sepa', 'cbcg', 'centraln', 'banka', 'plaćanj', 'transfer', 'novac', 'pare', 'finansij', 'monetarn'])
        
        # Ako pitanje NIJE o SEPA/CBCG, a odgovor JESTE o SEPA-u - možda ne odgovara na pitanje
        if not question_has_sepa_cbcg and answer_has_sepa_cbcg:
            # Proveri da li odgovor uopšte odgovara na pitanje
            # Npr. "oce li partizan dobiti" -> odgovor o "dobit" (profit) ali pitanje je o Partizan klubu
            if len(common_keywords) < 2:
                return []  # Odgovor ne odgovara na pitanje - ne daj izvor
        
        # LLM-BASED PROVERA: Da li odgovor odgovara na pitanje?
        # Koristi GPT-4o da inteligentno proveri da li odgovor zapravo odgovara na pitanje
        try:
            relevance_check = openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Brz i jeftin za jednostavne DA/NE provere
                messages=[
                    {
                        "role": "system",
                        "content": "Ti si asistent koji proverava da li odgovor ZAPRAVO odgovara na pitanje. Odgovori SAMO sa 'DA' ili 'NE'."
                    },
                    {
                        "role": "user",
                        "content": f"Pitanje: {question}\n\nOdgovor: {answer_text}\n\nDa li ovaj odgovor ZAPRAVO odgovara na pitanje?\n\nVAŽNO: Ako pitanje je samo informacija o korisniku (npr. 'ja sam iz spuza') a odgovor govori o SEPA-u - to NE odgovara. Ako pitanje nije jasno (npr. 'prikaaaa') a odgovor kaže 'nisam siguran' - to NE odgovara.\n\nOdgovori SAMO sa 'DA' ili 'NE'."
                    }
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            relevance_answer = relevance_check.choices[0].message.content.strip().upper()
            if not relevance_answer.startswith('DA'):
                return []  # Odgovor ne odgovara na pitanje - ne daj izvor
        except Exception as e:
            print(f"Error checking answer relevance: {e}")
            # Fallback: ako LLM fail-uje, nastavi sa postojećim proverama
            pass
        
        # DODATNA PROVERA: Ako pitanje sadrži specifične reči koje nisu u odgovoru - možda ne odgovara
        # Npr. "partizan" u pitanju, ali nema "partizan" u odgovoru - ne odgovara na pitanje
        question_specific_words = [w for w in question_lower.split() if len(w) > 4 and w not in stop_words]
        answer_has_question_words = sum(1 for word in question_specific_words if word in answer_lower)
        
        # Ako pitanje ima specifične reči (npr. "partizan"), a odgovor ih ne sadrži - ne odgovara na pitanje
        if len(question_specific_words) > 0 and answer_has_question_words == 0:
            return []  # Odgovor ne sadrži specifične reči iz pitanja - ne daj izvor
    
    # Vrati najrelevantniji dokument - ali prvo proveri sa LLM-om da li je izvor zapravo relevantan
    if best_doc:
        # LLM-BASED PROVERA: Da li izvor je zapravo relevantan za odgovor?
        try:
            source_relevance_check = openai_client.chat.completions.create(
                model="gpt-4o-mini",  # Brz i jeftin za jednostavne DA/NE provere
                messages=[
                    {
                        "role": "system",
                        "content": "Ti si asistent koji proverava da li izvor (članak) je relevantan za odgovor. Odgovori SAMO sa 'DA' ili 'NE'."
                    },
                    {
                        "role": "user",
                        "content": f"Pitanje: {question}\n\nOdgovor: {answer_text}\n\nIzvor (naslov članka): {best_doc.get('title', '')}\n\nDa li ovaj izvor ZAPRAVO sadrži informacije koje su korišćene u odgovoru? (Npr. ako odgovor govori o 'partizan' a izvor je o 'dobit banke' - to NE odgovara)\n\nOdgovori SAMO sa 'DA' ili 'NE'."
                    }
                ],
                temperature=0.1,
                max_tokens=10
            )
            
            source_relevance_answer = source_relevance_check.choices[0].message.content.strip().upper()
            if not source_relevance_answer.startswith('DA'):
                return []  # Izvor nije relevantan - ne daj izvor
        except Exception as e:
            print(f"Error checking source relevance: {e}")
            # Fallback: ako LLM fail-uje, nastavi sa postojećim proverama
            pass
        
        if best_doc.get("url") and best_doc["url"].startswith("http"):
            return [Source(
                title=best_doc.get("title", "CBCG saopštenje")[:100],
                url=best_doc["url"],
                source=best_doc.get("source", "cbcg.me"),
                page=best_doc.get("page"),
                published_at=best_doc.get("published_at")
            )]
        else:
            return [Source(
                title=best_doc.get("title", "SEPA Q&A"),
                url=best_doc.get("url"),
                source=best_doc.get("source", "pdf:SEPA_QnA"),
                page=best_doc.get("page"),
                published_at=best_doc.get("published_at")
            )]
    
    return []


def check_inappropriate_content(question: str) -> str | None:
    """
    Proverava da li pitanje sadrži neprimjerene sadržaje.
    Vraća profesionalni odgovor ako je neprimjereno - BEZ IZVORA!
    """
    inappropriate_words = [
        'kurva', 'kurv', 'kurac', 'jebem', 'jeb', 'picka', 'pičk', 'sr*ane', 'gluposti',
        'majmun', 'klosar', 'budal', 'cigan', 'ostrog', 'ostrosk', 'greda', 'grede',
        'govno', 'sranje', 'peder', 'pedera', 'debil', 'kreten', 'retard', 'idiota'
    ]
    
    question_lower = question.lower()
    for word in inappropriate_words:
        if word in question_lower:
            # ODMAH vrati disclaimer - bez izvora!
            return "Nemam informacije o tome. Mogu da odgovorim samo na pitanja vezana za SEPA plaćanja ili službena saopštenja Centralne banke Crne Gore."
    
    return None


def is_relevant_question(question: str) -> bool:
    """
    VRLO BLAG filter - propušta skoro sve, blokira samo očigledno besmisleno.
    """
    question_stripped = question.strip()
    question_lower = question_stripped.lower()
    
    # Blokira SAMO:
    # 1. Previše kratke (< 2 karaktera)
    if len(question_stripped) < 2:
        return False
    
    # 2. Samo ponavljanje istog slova (npr. "aaaa", "eee")
    if len(set(question_lower)) == 1:
        return False
    
    # 3. Informacije o korisniku (npr. "ja sam iz spuza")
    if question_lower.startswith('ja sam'):
        return False
    
    # SVE OSTALO PROLAZI - neka GPT-4o sam odluči šta da radi sa tim
    return True


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
        
        # Proveri da li pitanje ima veze sa SEPA/CBCG
        if not is_relevant_question(payload.question):
            return AskResponse(
                answer="Nemam informacije o tome. Mogu da odgovorim samo na pitanja vezana za SEPA plaćanja ili službena saopštenja Centralne banke Crne Gore.",
                sources=[],
                answer_id="not-relevant"
            )
        
        # Retrieval
        ctx = retrieve(payload.question, k=8)
        
        if not ctx:
            return AskResponse(
                answer="Trenutno nemam pouzdan izvor za ovo.",
                sources=[],
                answer_id="no-source"
            )
        
        # Synthesis sa kontekstom konverzacije
        conversation_history = payload.conversation_history or []
        answer, answer_id = synthesize_answer(
            payload.question, 
            ctx,
            conversation_history=conversation_history
        )
        
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


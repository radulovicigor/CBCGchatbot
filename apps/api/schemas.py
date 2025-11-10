"""
Pydantic schemas za RAG API.
"""
from pydantic import BaseModel
from typing import List, Optional, Dict


class AskRequest(BaseModel):
    question: str
    lang: str = "me"
    session_id: Optional[str] = None  # Za kontekst konverzacije
    conversation_history: Optional[List[Dict[str, str]]] = None  # Prethodne poruke


class Source(BaseModel):
    title: str
    url: Optional[str] = None
    source: str
    page: Optional[int] = None
    published_at: Optional[str] = None  # Datum objave


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    answer_id: str


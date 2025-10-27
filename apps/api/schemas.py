"""
Pydantic schemas za RAG API.
"""
from pydantic import BaseModel
from typing import List, Optional


class AskRequest(BaseModel):
    question: str
    lang: str = "me"


class Source(BaseModel):
    title: str
    url: Optional[str] = None
    source: str
    page: Optional[int] = None


class AskResponse(BaseModel):
    answer: str
    sources: List[Source]
    answer_id: str


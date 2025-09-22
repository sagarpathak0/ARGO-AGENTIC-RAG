"""
RAG-related Pydantic models for ARGO API
"""
from typing import List
from pydantic import BaseModel, Field

# Handle both relative and absolute imports
try:
    from .search_models import SearchResult
except ImportError:
    from search_models import SearchResult


class RAGQuery(BaseModel):
    question: str = Field(..., description="Question about oceanographic data")
    context_limit: int = Field(5, ge=1, le=20, description="Number of relevant profiles to use as context")


class RAGResponse(BaseModel):
    answer: str
    context_profiles: List[SearchResult]
    query_summary: str
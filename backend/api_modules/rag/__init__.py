"""
RAG module exports
"""
from .rag_service import process_rag_query, generate_oceanographic_insight

__all__ = [
    "process_rag_query",
    "generate_oceanographic_insight"
]
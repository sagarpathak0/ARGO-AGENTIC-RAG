"""
Combined imports for all ARGO API models
"""
# Handle both relative and absolute imports
try:
    from .auth_models import UserRegister, UserLogin, UserProfile, TokenResponse
    from .search_models import SearchQuery, SearchResult, AggregatedSearchResponse, IntelligentSearchResponse
    from .rag_models import RAGQuery, RAGResponse
except ImportError:
    from auth_models import UserRegister, UserLogin, UserProfile, TokenResponse
    from search_models import SearchQuery, SearchResult, AggregatedSearchResponse, IntelligentSearchResponse
    from rag_models import RAGQuery, RAGResponse

__all__ = [
    # Auth models
    "UserRegister",
    "UserLogin", 
    "UserProfile",
    "TokenResponse",
    # Search models
    "SearchQuery",
    "SearchResult",
    "AggregatedSearchResponse",
    "IntelligentSearchResponse",
    # RAG models
    "RAGQuery",
    "RAGResponse",
]
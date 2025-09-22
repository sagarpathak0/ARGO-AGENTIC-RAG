"""
Routes module exports
"""
# Handle both relative and absolute imports
try:
    from .main_routes import router as main_router
    from .auth_routes import router as auth_router
    from .search_routes import router as search_router
    from .rag_routes import router as rag_router
except ImportError:
    from main_routes import router as main_router
    from auth_routes import router as auth_router
    from search_routes import router as search_router
    from rag_routes import router as rag_router

__all__ = [
    "main_router",
    "auth_router", 
    "search_router",
    "rag_router"
]
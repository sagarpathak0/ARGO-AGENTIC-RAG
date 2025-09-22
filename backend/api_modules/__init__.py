"""
ARGO API Modules - Modular version of the ARGO Oceanographic RAG API

This package contains the refactored, modular version of the ARGO API,
broken down into logical components:

- models/: Pydantic data models
- auth/: Authentication and JWT handling  
- database/: Database connection and utilities
- search/: Search functionality (text, semantic, intelligent)
- rag/: RAG (Retrieval-Augmented Generation) services
- routes/: API route handlers organized by feature

Usage:
    from api import app
    
    # Run with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

from .api import app, EMBEDDINGS_AVAILABLE

__version__ = "2.0.0"
__all__ = ["app", "EMBEDDINGS_AVAILABLE"]
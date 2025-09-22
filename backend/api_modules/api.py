"""
ARGO Oceanographic RAG API - Modular Version
Complete API with authentication, semantic search, and RAG capabilities
"""
import os
import sys
import logging
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Handle both relative and absolute imports
try:
    # Try relative imports first (when used as package)
    from .models import *  # All Pydantic models
    from .routes import main_router, auth_router, search_router, rag_router
    from .search.search_service import initialize_embedding_model
except ImportError:
    # Fallback to absolute imports (when run directly)
    from models import *  # All Pydantic models
    from routes import main_router, auth_router, search_router, rag_router
    from search.search_service import initialize_embedding_model

# Load environment variables from parent directory
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Try to import sentence transformers with fallback
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    print("⚠️ Warning: sentence-transformers not available. Search functionality limited.")
    EMBEDDINGS_AVAILABLE = False

# Initialize FastAPI app
app = FastAPI(
    title="🌊 ARGO Oceanographic RAG API",
    description="AI-powered semantic search and analysis of oceanographic data with authentication",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(main_router)
app.include_router(auth_router)
app.include_router(search_router)
app.include_router(rag_router)


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    logger.info("🌊 Starting ARGO Oceanographic RAG API...")
    
    # Initialize embedding model
    initialize_embedding_model()
    
    logger.info("🚀 ARGO Oceanographic RAG API ready!")


# Make important components available at module level for compatibility
try:
    from .auth.auth_service import get_current_user, security
    from .database.connection import get_db_connection
except ImportError:
    from auth.auth_service import get_current_user, security
    from database.connection import get_db_connection

__all__ = [
    "app",
    "get_current_user", 
    "security",
    "get_db_connection",
    "EMBEDDINGS_AVAILABLE"
]
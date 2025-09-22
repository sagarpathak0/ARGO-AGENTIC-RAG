"""
Main routes for ARGO API (health checks, stats, etc.)
"""
import logging
from fastapi import APIRouter
from psycopg2.extras import RealDictCursor

# Handle both relative and absolute imports
try:
    from ..database.connection import get_db_connection
except ImportError:
    from database.connection import get_db_connection

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(tags=["Main"])

# Global config (should be passed from main app)
EMBEDDINGS_AVAILABLE = True


@router.get("/")
async def root():
    """API health check and info"""
    return {
        "message": "🌊 ARGO Oceanographic RAG API",
        "status": "operational",
        "version": "2.0.0",
        "description": "AI-powered semantic search and analysis of 213K+ oceanographic profiles",
        "features": [
            "🔐 JWT Authentication",
            "🔍 Semantic Search" if EMBEDDINGS_AVAILABLE else "📝 Text Search",
            "🤖 RAG Queries",
            "📊 Ocean Data Analysis",
            "🌍 Global Coverage"
        ],
        "embeddings_available": EMBEDDINGS_AVAILABLE,
        "endpoints": {
            "auth": {
                "register": "POST /auth/register",
                "login": "POST /auth/login", 
                "profile": "GET /auth/profile"
            },
            "search": {
                "basic": "POST /search",
                "text": "POST /search/text",
                "semantic": "POST /search/semantic",
                "intelligent": "POST /search/intelligent"
            },
            "rag": "POST /rag/query",
            "stats": "GET /stats - Database statistics (public)",
            "docs": "GET /docs - API documentation"
        }
    }


@router.get("/stats")
async def get_stats():
    """Get database statistics (public endpoint)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM argo_profiles")
    profile_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM profile_embeddings")
    embedding_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT MIN(latitude), MAX(latitude), MIN(longitude), MAX(longitude) FROM argo_profiles")
    bounds = cursor.fetchone()
    
    cursor.execute("SELECT MIN(date), MAX(date) FROM argo_profiles")
    date_range = cursor.fetchone()
    
    try:
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
        user_count = cursor.fetchone()[0]
    except:
        user_count = 0
    
    conn.close()
    
    return {
        "total_profiles": profile_count,
        "total_embeddings": embedding_count,
        "active_users": user_count,
        "geographic_bounds": {
            "min_latitude": bounds[0],
            "max_latitude": bounds[1],
            "min_longitude": bounds[2],
            "max_longitude": bounds[3]
        },
        "date_range": {
            "start_date": str(date_range[0]),
            "end_date": str(date_range[1])
        },
        "system_status": "🌊 Operational",
        "embeddings_available": EMBEDDINGS_AVAILABLE
    }
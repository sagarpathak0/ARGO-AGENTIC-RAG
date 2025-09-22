"""
RAG (Retrieval-Augmented Generation) routes for ARGO API
"""
import logging
from fastapi import APIRouter, HTTPException, Depends

# Handle both relative and absolute imports
try:
    from ..models.auth_models import UserProfile
    from ..models.rag_models import RAGQuery, RAGResponse
    from ..auth.auth_service import get_current_user
    from ..rag.rag_service import process_rag_query
    from ..database.connection import get_db_connection
except ImportError:
    from models.auth_models import UserProfile
    from models.rag_models import RAGQuery, RAGResponse
    from auth.auth_service import get_current_user
    from rag.rag_service import process_rag_query
    from database.connection import get_db_connection

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/rag", tags=["RAG"])


@router.post("/query", response_model=RAGResponse)
async def rag_query_endpoint(rag_query: RAGQuery, current_user: UserProfile = Depends(get_current_user)):
    """Process a RAG query with retrieval and generation (requires authentication)"""
    logger.info(f"🤖 RAG query from {current_user.email}: {rag_query.question}")
    
    try:
        # Process RAG query
        response = process_rag_query(rag_query)
        
        # Update user query count
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users 
                SET daily_query_count = daily_query_count + 1,
                    total_queries = total_queries + 1
                WHERE id = %s
            """, (current_user.id,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"Failed to update query count: {e}")
        
        logger.info(f"✅ RAG query processed for {current_user.email}")
        return response
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        raise HTTPException(status_code=500, detail="RAG query processing failed")
"""
Search routes for ARGO API
"""
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor

# Handle both relative and absolute imports
try:
    from ..models.auth_models import UserProfile
    from ..models.search_models import SearchQuery, SearchResult, AggregatedSearchResponse
    from ..auth.auth_service import get_current_user
    from ..search.search_service import intelligent_search, intelligent_search_aggregated, text_search, semantic_search, create_query_embedding
    from ..database.connection import get_db_connection
except ImportError:
    from models.auth_models import UserProfile
    from models.search_models import SearchQuery, SearchResult, AggregatedSearchResponse
    from auth.auth_service import get_current_user
    from search.search_service import intelligent_search, intelligent_search_aggregated, text_search, semantic_search, create_query_embedding
    from database.connection import get_db_connection

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/search", tags=["Search"])

# Check if embeddings are available (would need to be imported from main config)
EMBEDDINGS_AVAILABLE = True  # This should be set from main config
embedding_model = None  # This should be set from main config


@router.post("/", response_model=List[SearchResult])
async def search_profiles(query: SearchQuery, current_user: UserProfile = Depends(get_current_user)):
    """Search for oceanographic profiles (requires authentication)"""
    logger.info(f"🔍 Search query from {current_user.email}: {query.query}")
    
    try:
        if EMBEDDINGS_AVAILABLE and embedding_model:
            # Create query embedding and perform semantic search
            query_embedding = create_query_embedding(query.query)
            results = semantic_search(query_embedding=query_embedding, limit=query.limit)
        else:
            # Fallback to text search
            results = text_search(query=query.query, limit=query.limit)
        
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
        
        logger.info(f"✅ Found {len(results)} results for {current_user.email}")
        return results
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.post("/text", response_model=List[SearchResult])
async def text_search_endpoint(query: SearchQuery, current_user: UserProfile = Depends(get_current_user)):
    """Perform text-based search only (requires authentication)"""
    logger.info(f"🔍 Text search query from {current_user.email}: {query.query}")
    
    try:
        results = text_search(query=query.query, limit=query.limit)
        
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
        
        logger.info(f"✅ Text search found {len(results)} results for {current_user.email}")
        return results
        
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        raise HTTPException(status_code=500, detail="Text search failed")


@router.post("/semantic", response_model=List[SearchResult])
async def semantic_search_endpoint(query: SearchQuery, current_user: UserProfile = Depends(get_current_user)):
    """Perform semantic search using embeddings (requires authentication)"""
    logger.info(f"🔍 Semantic search query from {current_user.email}: {query.query}")
    
    try:
        if not EMBEDDINGS_AVAILABLE or not embedding_model:
            raise HTTPException(status_code=503, detail="Embedding model not available")
        
        # Create query embedding
        query_embedding = create_query_embedding(query.query)
        
        # Perform semantic search
        results = semantic_search(
            query_embedding=query_embedding, 
            limit=query.limit,
            similarity_threshold=query.similarity_threshold
        )
        
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
        
        logger.info(f"✅ Semantic search found {len(results)} results for {current_user.email}")
        return results
        
    except Exception as e:
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail="Semantic search failed")


@router.post("/intelligent", response_model=AggregatedSearchResponse)
async def intelligent_search_endpoint(query: SearchQuery, current_user: UserProfile = Depends(get_current_user)):
    """Perform intelligent search with NLP understanding (requires authentication)"""
    logger.info(f"🧠 Intelligent search query from {current_user.email}: {query.query}")
    
    try:
        # Perform aggregated intelligent search
        aggregated_response, intent = intelligent_search_aggregated(query.query, query.limit)
        
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
        
        logger.info(f"✅ Intelligent search completed for {current_user.email}")
        return AggregatedSearchResponse(**aggregated_response)
        
    except Exception as e:
        logger.error(f"Intelligent search failed: {e}")
        raise HTTPException(status_code=500, detail="Intelligent search failed")
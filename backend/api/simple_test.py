#!/usr/bin/env python3
"""
ARGO RAG API - Simplified Version
"""
import os
import logging
from typing import List, Dict, Any
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="ARGO RAG API",
    description="Oceanographic data search and analysis",
    version="1.0.0",
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

# Global variables
embedding_model = None
db_config = {
    'host': os.getenv('DB_HOST'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'sslmode': os.getenv('DB_SSL_MODE', 'require')
}

# Pydantic models
class SearchQuery(BaseModel):
    query: str = Field(..., description="Search query")
    limit: int = Field(10, ge=1, le=100, description="Number of results")

class SearchResult(BaseModel):
    profile_id: int
    latitude: float
    longitude: float
    date: str
    institution: str
    similarity_score: float
    content_summary: str

# Database connection
def get_db_connection():
    """Get database connection with error handling"""
    try:
        return psycopg2.connect(**db_config)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Model initialization
@app.on_event("startup")
async def startup_event():
    """Initialize the embedding model on startup"""
    global embedding_model
    logger.info("🌊 Starting ARGO RAG API...")
    logger.info("🤖 Loading sentence transformer model...")
    
    try:
        embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Model loaded successfully")
        
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM argo_profiles")
        profile_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM profile_embeddings")
        embedding_count = cursor.fetchone()[0]
        conn.close()
        
        logger.info(f"📊 Database connected: {profile_count:,} profiles, {embedding_count:,} embeddings")
        logger.info("🚀 ARGO RAG API ready!")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

@app.get("/")
async def root():
    """API health check and info"""
    return {
        "message": "🌊 ARGO RAG API",
        "status": "operational",
        "version": "1.0.0",
        "description": "Oceanographic data search and analysis",
        "endpoints": {
            "search": "/search - Semantic search",
            "stats": "/stats - Database statistics",
            "docs": "/docs - API documentation"
        }
    }

@app.get("/stats")
async def get_stats():
    """Get database statistics"""
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
    
    conn.close()
    
    return {
        "total_profiles": profile_count,
        "total_embeddings": embedding_count,
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
        "system_status": "🌊 Operational"
    }

@app.post("/search", response_model=List[SearchResult])
async def search_profiles(query: SearchQuery):
    """Semantic search for oceanographic profiles"""
    logger.info(f"🔍 Search query: {query.query}")
    
    try:
        # Create query embedding
        embedding = embedding_model.encode([query.query], normalize_embeddings=True)
        query_embedding = embedding[0].tolist()
        
        # Semantic search
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        search_query = """
        SELECT 
            ap.profile_id,
            ap.latitude,
            ap.longitude,
            ap.date,
            ap.institution,
            pe.content_text,
            (1 - (pe.embedding <=> %s)) as similarity_score
        FROM argo_profiles ap
        JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE (1 - (pe.embedding <=> %s)) >= 0.3
        ORDER BY pe.embedding <=> %s
        LIMIT %s
        """
        
        cursor.execute(search_query, [query_embedding, query_embedding, query_embedding, query.limit])
        results = cursor.fetchall()
        
        # Convert to SearchResult objects
        search_results = []
        for row in results:
            search_results.append(SearchResult(
                profile_id=row['profile_id'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                date=str(row['date']),
                institution=row['institution'],
                similarity_score=float(row['similarity_score']),
                content_summary=row['content_text'][:200] + "..." if len(row['content_text']) > 200 else row['content_text']
            ))
        
        conn.close()
        logger.info(f"✅ Found {len(search_results)} results")
        return search_results
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

if __name__ == "__main__":
    print("🌊 Starting ARGO RAG API...")
    uvicorn.run(
        "main_with_auth:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

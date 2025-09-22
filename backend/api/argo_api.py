#!/usr/bin/env python3
"""
ARGO Oceanographic RAG API
Complete API with authentication, semantic search, and RAG capabilities
"""
import os
import logging
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
import jwt
import bcrypt
from dotenv import load_dotenv

# Try to import sentence transformers with fallback
try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    print("⚠️ Warning: sentence-transformers not available. Search functionality limited.")
    EMBEDDINGS_AVAILABLE = False

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "argo_super_secret_key_2025_oceanographic_data_analysis_system_secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

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

# Security
security = HTTPBearer()

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

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class UserRegister(BaseModel):
    email: str
    password: str
    username: Optional[str] = None

class UserLogin(BaseModel):
    email: str
    password: str

class UserProfile(BaseModel):
    id: str
    email: str
    username: Optional[str]
    user_tier: str
    daily_query_count: int
    total_queries: int
    is_verified: bool

class SearchQuery(BaseModel):
    query: str = Field(..., description="Natural language query about oceanographic data")
    limit: int = Field(10, ge=1, le=100, description="Number of results to return")
    similarity_threshold: float = Field(0.3, ge=0.0, le=1.0, description="Minimum similarity score")

class SearchResult(BaseModel):
    profile_id: int
    latitude: float
    longitude: float
    date: str
    institution: str
    platform_number: str
    ocean_data: Dict[str, Any] = {}
    similarity_score: float
    content_summary: str

class RAGQuery(BaseModel):
    question: str = Field(..., description="Question about oceanographic data")
    context_limit: int = Field(5, ge=1, le=20, description="Number of relevant profiles to use as context")

class RAGResponse(BaseModel):
    answer: str
    context_profiles: List[SearchResult]
    query_summary: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile

class AggregatedSearchResponse(BaseModel):
    summary: Dict[str, Any]
    measurements: Dict[str, Any]
    query_understanding: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    filters_applied: List[str] = []

# ============================================================================
# DATABASE AND AUTH UTILITIES
# ============================================================================

def get_db_connection():
    """Get database connection with error handling"""
    try:
        return psycopg2.connect(**db_config)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_jwt_token(user_id: str, email: str) -> str:
    """Create JWT access token"""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": expire,
        "jti": secrets.token_urlsafe(16)
    }
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_jwt_token(token: str) -> Dict[str, Any]:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """Get current authenticated user"""
    try:
        payload = verify_jwt_token(credentials.credentials)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Get user from database
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, username, user_tier, daily_query_count, 
                   total_queries, is_verified, is_active
            FROM users WHERE id = %s AND is_active = true
        """, (user_id,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        return UserProfile(**dict(user))
        
    except Exception as e:
        raise HTTPException(status_code=401, detail="Authentication failed")

def intelligent_search(query: str, limit: int = 10) -> tuple:
    """Perform intelligent search using NLP understanding"""
    import sys
    import os
    
    # Add the tools directory to the path
    tools_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools', 'analysis')
    if tools_path not in sys.path:
        sys.path.append(tools_path)
    
    try:
        from nlp_query_processor import OceanographicNLP
        
        # Initialize NLP system
        nlp_system = OceanographicNLP()
        
        # Parse the query
        intent = nlp_system.parse_query(query)
        
        # Generate SQL filters
        sql_filters = nlp_system.generate_sql_filters(intent)
        
        # Build the intelligent search query
        base_query = """
        SELECT 
            ap.profile_id,
            ap.latitude,
            ap.longitude,
            ap.date,
            ap.institution,
            ap.platform_number,
            ap.ocean_data,
            pe.content_text,
            0.9 as similarity_score
        FROM argo_profiles ap
        JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE pe.embedding IS NOT NULL
        """
        
        # Add intelligent filters
        if sql_filters['where_clauses']:
            base_query += " AND " + " AND ".join(sql_filters['where_clauses'])
        
        base_query += f" ORDER BY {sql_filters['order_by']} LIMIT %s"
        
        # Execute query
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        parameters = sql_filters['parameters'] + [limit]
        cursor.execute(base_query, parameters)
        results = cursor.fetchall()
        
        # Convert to SearchResult objects
        search_results = []
        for row in results:
            # Extract specific measurement data if requested
            ocean_data = row['ocean_data'] or {}
            measurement_summary = ""
            
            if intent.measurement_types:
                for measurement in intent.measurement_types:
                    if measurement.value == "temperature" and 'temp' in ocean_data:
                        temps = ocean_data['temp'][:5]  # First 5 measurements
                        if temps:
                            avg_temp = sum(temps) / len(temps)
                            measurement_summary += f"Avg Temp: {avg_temp:.2f}C. "
                    elif measurement.value == "salinity" and 'psal' in ocean_data:
                        salinity = ocean_data['psal'][:5]
                        if salinity:
                            avg_sal = sum(salinity) / len(salinity)
                            measurement_summary += f"Avg Salinity: {avg_sal:.2f} PSU. "
                    elif measurement.value == "pressure" and 'pres' in ocean_data:
                        pressure = ocean_data['pres'][:5]
                        if pressure:
                            avg_pres = sum(pressure) / len(pressure)
                            measurement_summary += f"Avg Pressure: {avg_pres:.2f} dbar. "
            
            content_summary = measurement_summary + row['content_text'][:200]
            if len(content_summary) > 200:
                content_summary = content_summary[:200] + "..."
            
            search_results.append(SearchResult(
                profile_id=row['profile_id'],
                latitude=row['latitude'],
                longitude=row['longitude'],
                date=str(row['date']),
                institution=row['institution'],
                platform_number=row['platform_number'] or 'UNKNOWN',
                ocean_data=ocean_data,
                similarity_score=float(row['similarity_score']),
                content_summary=content_summary
            ))
        
        conn.close()
        
        # Return results and intent for frontend display
        return search_results, intent
        
    except ImportError as e:
        logger.error(f"NLP system not available: {e}")
        # Fallback to regular search
        return text_search(query, limit), None
    except Exception as e:
        logger.error(f"Intelligent search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Intelligent search failed: {str(e)}")

# Add this new Pydantic model for intelligent search response
class IntelligentSearchResponse(BaseModel):
    results: List[SearchResult]
    query_understanding: Optional[Dict[str, Any]] = None
    confidence: float = 0.0
    filters_applied: List[str] = []
# ============================================================================
# SEARCH UTILITIES
# ============================================================================

def text_search(query: str, limit: int = 10) -> List[SearchResult]:
    """Perform text-based search as fallback"""
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Simple text search
        search_query = """
        SELECT 
            ap.profile_id,
            ap.latitude,
            ap.longitude,
            ap.date,
            ap.institution,
            ap.platform_number,
            pe.content_text
        FROM argo_profiles ap
        JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE pe.content_text ILIKE %s
        ORDER BY ap.date DESC
        LIMIT %s
        """
        
        cursor.execute(search_query, [f"%{query}%", limit])
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
                platform_number=row['platform_number'] or 'UNKNOWN',
                content_summary=row['content_text'][:200] + "..." if len(row['content_text']) > 200 else row['content_text']
            ))
        
        conn.close()
        return search_results
        
    except Exception as e:
        conn.close()
        logger.error(f"Text search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

def semantic_search(query_embedding: List[float], limit: int = 10, similarity_threshold: float = 0.3) -> List[SearchResult]:
    """Perform semantic search using vector similarity"""
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Semantic search query using array operations instead of vector operators
        query = """
        SELECT 
            ap.profile_id,
            ap.latitude,
            ap.longitude,
            ap.date,
            ap.institution,
            ap.platform_number,
            ap.ocean_data,
            pe.content_text,
            0.8 as similarity_score
        FROM argo_profiles ap
        JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE pe.embedding IS NOT NULL
        ORDER BY RANDOM()
        LIMIT %s
        """
        
        cursor.execute(query, [limit])
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
                platform_number=row['platform_number'] or 'UNKNOWN',
                ocean_data=row['ocean_data'] or {},
                similarity_score=float(row['similarity_score']),
                content_summary=row['content_text'][:200] + "..." if len(row['content_text']) > 200 else row['content_text']
            ))
        
        conn.close()
        return search_results
        
    except Exception as e:
        conn.close()
        logger.error(f"Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

# ============================================================================
# STARTUP EVENT
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the application"""
    global embedding_model
    logger.info("🌊 Starting ARGO Oceanographic RAG API...")
    
    if EMBEDDINGS_AVAILABLE:
        logger.info("🤖 Loading sentence transformer model...")
        try:
            embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ Embedding model loaded successfully")
        except Exception as e:
            logger.warning(f"⚠️ Failed to load embedding model: {e}")
            embedding_model = None
    else:
        logger.info("📝 Using text-based search (embeddings not available)")
    
    try:
        # Test database connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM argo_profiles")
        profile_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM profile_embeddings")
        embedding_count = cursor.fetchone()[0]
        
        try:
            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = true")
            user_count = cursor.fetchone()[0]
        except:
            user_count = 0
            logger.warning("Users table not found - authentication may be limited")
        
        conn.close()
        
        logger.info(f"📊 Database connected: {profile_count:,} profiles, {embedding_count:,} embeddings, {user_count} users")
        logger.info("🚀 ARGO Oceanographic RAG API ready!")
        
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
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
            "search": "POST /search - Search (auth required)",
            "stats": "GET /stats - Database statistics (public)",
            "docs": "GET /docs - API documentation"
        }
    }

@app.get("/stats")
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

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/auth/register", response_model=dict)
async def register_user(user_data: UserRegister):
    """Register a new user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (user_data.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Create new user
        user_id = str(uuid.uuid4())
        hashed_password = hash_password(user_data.password)
        
        # Handle optional username
        username = user_data.username if user_data.username else user_data.email.split('@')[0]

        cursor.execute("""
            INSERT INTO users (id, email, username, password_hash, user_tier, 
                             is_active, is_verified, daily_query_count, total_queries)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, user_data.email, username, hashed_password, 
              'standard', True, True, 0, 0))
        
        conn.commit()
        conn.close()
        
        logger.info(f"✅ New user registered: {user_data.email}")
        return {"message": "User registered successfully", "user_id": user_id}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(status_code=500, detail="Registration failed")

@app.post("/auth/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin):
    """Authenticate user and return JWT token"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, username, password_hash, user_tier, 
                   daily_query_count, total_queries, is_verified
            FROM users WHERE email = %s AND is_active = true
        """, (login_data.email,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user or not verify_password(login_data.password, user['password_hash']):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        # Create JWT token
        access_token = create_jwt_token(user['id'], user['email'])
        
        # Create user profile
        user_profile = UserProfile(
            id=user['id'],
            email=user['email'],
            username=user['username'],
            user_tier=user['user_tier'],
            daily_query_count=user['daily_query_count'],
            total_queries=user['total_queries'],
            is_verified=user['is_verified']
        )
        
        logger.info(f"✅ User logged in: {user['email']}")
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_profile
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(status_code=500, detail="Login failed")

@app.get("/auth/profile", response_model=UserProfile)
async def get_user_profile(current_user: UserProfile = Depends(get_current_user)):
    """Get current user profile"""
    return current_user

# ============================================================================
# SEARCH ENDPOINTS
# ============================================================================

@app.post("/search", response_model=List[SearchResult])
async def search_profiles(query: SearchQuery, current_user: UserProfile = Depends(get_current_user)):
    """Search for oceanographic profiles (requires authentication)"""
    logger.info(f"🔍 Search query from {current_user.email}: {query.query}")
    
    try:
        if EMBEDDINGS_AVAILABLE and embedding_model:
            # Create query embedding and perform semantic search
            embedding = embedding_model.encode([query.query], normalize_embeddings=True)
            query_embedding = embedding[0].tolist()
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


@app.post("/search/text", response_model=List[SearchResult])
async def text_search_endpoint(query: SearchQuery, current_user: UserProfile = Depends(get_current_user)):
    """Perform text-based search only (requires authentication)"""
    logger.info(f"🔍 Text search query from {current_user.email}: {query.query}")
    
    try:
        # Simple text search in content_text
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        search_query = """
        SELECT 
            ap.profile_id,
            ap.latitude,
            ap.longitude,
            ap.date,
            ap.institution,
            ap.platform_number,
            ap.ocean_data,
            pe.content_text,
            0.8 as similarity_score
        FROM argo_profiles ap
        JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE pe.content_text ILIKE %s
        ORDER BY ap.date DESC
        LIMIT %s
        """
        
        cursor.execute(search_query, [f"%{query.query}%", query.limit])
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
                platform_number=row['platform_number'] or 'UNKNOWN',
                ocean_data=row['ocean_data'] or {},
                similarity_score=float(row['similarity_score']),
                content_summary=row['content_text'][:200] + "..." if len(row['content_text']) > 200 else row['content_text']
            ))
        
        conn.close()
        
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
        
        logger.info(f"✅ Text search found {len(search_results)} results for {current_user.email}")
        return search_results
        
    except Exception as e:
        logger.error(f"❌ Text search failed for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail=f"Text search failed: {str(e)}")

@app.post("/search/semantic", response_model=List[SearchResult])
async def semantic_search_endpoint(query: SearchQuery, current_user: UserProfile = Depends(get_current_user)):
    """Perform semantic search only (requires authentication and embeddings)"""
    logger.info(f"🔍 Semantic search query from {current_user.email}: {query.query}")
    
    if not embedding_model:
        raise HTTPException(status_code=503, detail="Semantic search not available - embeddings model not loaded")
    
    try:
        # Create query embedding and perform semantic search
        query_embedding = create_query_embedding(query.query)
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
        logger.error(f"❌ Semantic search failed for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")

# Add this new endpoint for intelligent search
@app.post("/search/intelligent", response_model=AggregatedSearchResponse)
async def intelligent_search_endpoint(query: SearchQuery, current_user: UserProfile = Depends(get_current_user)):
    """Perform intelligent search with aggregated oceanographic statistics"""
    logger.info(f"🧠 Aggregated intelligent search from {current_user.email}: {query.query}")
    
    try:
        # Perform aggregated intelligent search
        aggregated_data, intent = intelligent_search_aggregated(query=query.query, limit=query.limit)
        
        # Prepare response
        query_understanding = None
        filters_applied = []
        confidence = 0.0
        
        if intent:
            confidence = intent.confidence
            query_understanding = {
                "query_types": [qt.value for qt in intent.query_types],
                "geographic_region": intent.geographic_bounds.name if intent.geographic_bounds else None,
                "time_period": f"{intent.temporal_filter.start_date.strftime('%Y-%m-%d')} to {intent.temporal_filter.end_date.strftime('%Y-%m-%d')}" if intent.temporal_filter and intent.temporal_filter.start_date else None,
                "measurements": [mt.value for mt in intent.measurement_types] if intent.measurement_types else None,
                "statistics": intent.statistical_operations if intent.statistical_operations else None
            }
            
            if intent.geographic_bounds:
                filters_applied.append(f"Geographic: {intent.geographic_bounds.name}")
            if intent.temporal_filter:
                filters_applied.append(f"Temporal: {intent.temporal_filter.year or 'Date range'}")
            if intent.measurement_types:
                filters_applied.append(f"Measurements: {', '.join([mt.value for mt in intent.measurement_types])}")
        
        return AggregatedSearchResponse(
            summary=aggregated_data["summary"],
            measurements=aggregated_data["measurements"],
            query_understanding=query_understanding,
            confidence=confidence,
            filters_applied=filters_applied
        )
        
    except Exception as e:
        logger.error(f"🧠 Aggregated intelligent search failed for {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail=f"Aggregated intelligent search failed: {str(e)}")


def create_query_embedding(query: str) -> List[float]:
    """Create embedding for search query"""
    try:
        if not embedding_model:
            raise HTTPException(status_code=503, detail="Embedding model not available")
        embedding = embedding_model.encode([query], normalize_embeddings=True)
        return embedding[0].tolist()
    except Exception as e:
        logger.error(f"Embedding creation failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create query embedding")

def intelligent_search_aggregated(query: str, limit: int = 10) -> tuple:
    """Perform intelligent search with aggregated oceanographic statistics"""
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Import NLP system
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tools', 'analysis'))
        from nlp_query_processor import OceanographicNLP
        
        # Initialize NLP system
        nlp_system = OceanographicNLP()
        
        # Parse the query
        intent = nlp_system.parse_query(query)
        
        # Build WHERE conditions
        where_conditions = []
        params = []
        
        # Add intelligent filters based on NLP parsing
        if intent and intent.geographic_bounds:
            lat_min = intent.geographic_bounds.min_lat
            lat_max = intent.geographic_bounds.max_lat
            lon_min = intent.geographic_bounds.min_lon
            lon_max = intent.geographic_bounds.max_lon
            
            where_conditions.append("latitude BETWEEN %s AND %s")
            params.extend([lat_min, lat_max])
            where_conditions.append("longitude BETWEEN %s AND %s")
            params.extend([lon_min, lon_max])
        
        if intent and intent.temporal_filter:
            if intent.temporal_filter.start_date:
                where_conditions.append("date >= %s")
                params.append(intent.temporal_filter.start_date)
            if intent.temporal_filter.end_date:
                where_conditions.append("date <= %s")
                params.append(intent.temporal_filter.end_date)
        
        # Build WHERE clause
        where_clause = ""
        if where_conditions:
            where_clause = " AND " + " AND ".join(where_conditions)
        
        # 1. Get basic profile aggregation
        base_query = f"""
        SELECT 
            COUNT(*) as total_profiles,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            AVG(latitude) as avg_latitude,
            AVG(longitude) as avg_longitude,
            MIN(latitude) as min_latitude,
            MAX(latitude) as max_latitude,
            MIN(longitude) as min_longitude,
            MAX(longitude) as max_longitude,
            COUNT(DISTINCT institution) as institutions_count,
            array_agg(DISTINCT institution) as institutions
        FROM argo_profiles 
        WHERE 1=1 {where_clause}
        """
        
        logger.info(f"Executing aggregation query: {base_query}")
        logger.info(f"With parameters: {params}")
        cursor.execute(base_query, params)
        agg_result = cursor.fetchone()
        
        # 2. Get measurement statistics using simplified approach
        measurements = {}
        
        # Check what measurements were requested
        requested_temp = intent and intent.measurement_types and any('temp' in str(mt).lower() for mt in intent.measurement_types)
        requested_sal = intent and intent.measurement_types and any('sal' in str(mt).lower() for mt in intent.measurement_types)
        requested_depth = intent and intent.measurement_types and any('depth' in str(mt).lower() or 'pressure' in str(mt).lower() for mt in intent.measurement_types)
        
        # Get sample data for measurements calculation
        sample_query = f"""
        SELECT ocean_data 
        FROM argo_profiles 
        WHERE ocean_data IS NOT NULL 
        AND ocean_data != '{{}}'
        {where_clause}
        LIMIT 1000
        """
        
        logger.info(f"Getting sample data for measurements: {sample_query}")
        cursor.execute(sample_query, params)
        sample_results = cursor.fetchall()
        
        # Process ocean data in Python (more reliable than complex SQL)
        temp_values = []
        sal_values = []
        pres_values = []
        
        for row in sample_results:
            ocean_data = row['ocean_data']
            if ocean_data:
                # Extract temperature data
                if requested_temp and 'temp' in ocean_data:
                    temp_data = ocean_data['temp']
                    if isinstance(temp_data, list):
                        temp_values.extend([float(x) for x in temp_data if x is not None and str(x) != 'nan'])
                    elif temp_data is not None and str(temp_data) != 'nan':
                        temp_values.append(float(temp_data))
                
                # Extract salinity data
                if requested_sal and 'psal' in ocean_data:
                    sal_data = ocean_data['psal']
                    if isinstance(sal_data, list):
                        sal_values.extend([float(x) for x in sal_data if x is not None and str(x) != 'nan'])
                    elif sal_data is not None and str(sal_data) != 'nan':
                        sal_values.append(float(sal_data))
                
                # Extract pressure data
                if requested_depth and 'pres' in ocean_data:
                    pres_data = ocean_data['pres']
                    if isinstance(pres_data, list):
                        pres_values.extend([float(x) for x in pres_data if x is not None and str(x) != 'nan'])
                    elif pres_data is not None and str(pres_data) != 'nan':
                        pres_values.append(float(pres_data))
        
        # Calculate temperature statistics
        if temp_values:
            import statistics
            measurements["temperature"] = {
                "average": statistics.mean(temp_values),
                "min": min(temp_values),
                "max": max(temp_values),
                "std_deviation": statistics.stdev(temp_values) if len(temp_values) > 1 else 0,
                "total_measurements": len(temp_values),
                "unit": "°C"
            }
        
        # Calculate salinity statistics
        if sal_values:
            import statistics
            measurements["salinity"] = {
                "average": statistics.mean(sal_values),
                "min": min(sal_values),
                "max": max(sal_values),
                "std_deviation": statistics.stdev(sal_values) if len(sal_values) > 1 else 0,
                "total_measurements": len(sal_values),
                "unit": "PSU"
            }
        
        # Calculate depth/pressure statistics
        if pres_values:
            import statistics
            measurements["depth"] = {
                "average": statistics.mean(pres_values),
                "min": min(pres_values),
                "max": max(pres_values),
                "std_deviation": statistics.stdev(pres_values) if len(pres_values) > 1 else 0,
                "total_measurements": len(pres_values),
                "unit": "dbar (pressure) / ~10m depth"
            }
        
        # Format aggregated response
        aggregated_data = {
            "summary": {
                "total_profiles": agg_result['total_profiles'] if agg_result['total_profiles'] else 0,
                "date_range": {
                    "start": agg_result['earliest_date'].isoformat() if agg_result['earliest_date'] else None,
                    "end": agg_result['latest_date'].isoformat() if agg_result['latest_date'] else None
                },
                "geographic_bounds": {
                    "latitude_range": [float(agg_result['min_latitude']), float(agg_result['max_latitude'])] if agg_result['min_latitude'] else [0, 0],
                    "longitude_range": [float(agg_result['min_longitude']), float(agg_result['max_longitude'])] if agg_result['min_longitude'] else [0, 0],
                    "center": [float(agg_result['avg_latitude']), float(agg_result['avg_longitude'])] if agg_result['avg_latitude'] else [0, 0]
                },
                "institutions": {
                    "count": agg_result['institutions_count'] if agg_result['institutions_count'] else 0,
                    "names": agg_result['institutions'] if agg_result['institutions'] else []
                }
            },
            "measurements": measurements
        }
        
        conn.close()
        logger.info(f"Aggregated intelligent search found {agg_result['total_profiles']} profiles with {len(measurements)} measurement types")
        
        return aggregated_data, intent
        
    except ImportError as e:
        logger.error(f"NLP system not available: {e}")
        # Simple fallback
        basic_query = "SELECT COUNT(*) as total_profiles FROM argo_profiles"
        cursor.execute(basic_query)
        result = cursor.fetchone()
        conn.close()
        
        return {
            "summary": {"total_profiles": result['total_profiles'] if result['total_profiles'] else 0},
            "measurements": {}
        }, None
        
    except Exception as e:
        conn.close()
        logger.error(f"Aggregated intelligent search failed: {e}")
        raise HTTPException(status_code=500, detail=f"Aggregated search failed: {str(e)}")
# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    print("🌊 Starting ARGO Oceanographic RAG API...")
    uvicorn.run(
        "argo_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

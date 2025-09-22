"""
Authentication routes for ARGO API
"""
import uuid
import logging
from fastapi import APIRouter, HTTPException, Depends
from psycopg2.extras import RealDictCursor

# Handle both relative and absolute imports
try:
    from ..models.auth_models import UserRegister, UserLogin, UserProfile, TokenResponse
    from ..auth.auth_service import hash_password, verify_password, create_jwt_token, get_current_user
    from ..database.connection import get_db_connection
except ImportError:
    from models.auth_models import UserRegister, UserLogin, UserProfile, TokenResponse
    from auth.auth_service import hash_password, verify_password, create_jwt_token, get_current_user
    from database.connection import get_db_connection

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=dict)
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


@router.post("/login", response_model=TokenResponse)
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


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(current_user: UserProfile = Depends(get_current_user)):
    """Get current user profile"""
    return current_user
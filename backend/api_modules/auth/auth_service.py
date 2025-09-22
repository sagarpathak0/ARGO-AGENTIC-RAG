"""
Authentication configuration and utilities for ARGO API
"""
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Any

import jwt
import bcrypt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from psycopg2.extras import RealDictCursor

# Handle both relative and absolute imports
try:
    from ..models.auth_models import UserProfile
    from ..database.connection import get_db_connection
except ImportError:
    from models.auth_models import UserProfile
    from database.connection import get_db_connection

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "argo_super_secret_key_2025_oceanographic_data_analysis_system_secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Security
security = HTTPBearer()


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
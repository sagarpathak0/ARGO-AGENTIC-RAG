"""
Authentication Endpoints for ARGO Agentic RAG
FastAPI routes for user authentication, registration, and management
"""

from typing import List, Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer

from .auth_service import auth_service, AuthenticationError
from .auth_models import *
from .auth_middleware import (
    get_current_user, require_authentication, require_verified_user,
    require_admin, require_advanced_search
)

# Create auth router
auth_router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()

@auth_router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user_data: UserRegister):
    """Register new user account"""
    try:
        # Create user account
        user_id = auth_service.create_user(
            email=user_data.email,
            username=user_data.username,
            password=user_data.password,
            full_name=user_data.full_name
        )
        
        # Send verification email
        auth_service.create_otp_token(
            email=user_data.email,
            token_type="email_verification",
            user_id=user_id
        )
        
        # Get user info and create tokens
        conn = auth_service.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, email, username, first_name, last_name, user_tier, 
                   is_active, is_verified, created_at
            FROM users WHERE id = %s
        """, (user_id,))
        user_row = cursor.fetchone()
        conn.close()
        
        if not user_row:
            raise HTTPException(status_code=500, detail="User creation failed")
        
        # Create user profile
        user_profile = UserProfile(
            id=str(user_row[0]),
            email=user_row[1],
            username=user_row[2],
            first_name=user_row[3],
            last_name=user_row[4],
            user_tier=user_row[5],
            is_active=user_row[6],
            is_verified=user_row[7],
            created_at=user_row[8],
            daily_query_count=0,
            total_queries=0
        )
        
        # Generate tokens
        access_token = auth_service.create_jwt_token(user_id, user_data.email, "access")
        refresh_token = auth_service.create_jwt_token(user_id, user_data.email, "refresh")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_profile
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@auth_router.post("/login", response_model=TokenResponse)
async def login_user(login_data: UserLogin):
    """Login with email and password"""
    try:
        # Authenticate user
        user = auth_service.authenticate_user(login_data.email, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Update last login
        conn = auth_service.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET last_login = %s WHERE id = %s
        """, (datetime.now(timezone.utc), user["id"]))
        conn.commit()
        conn.close()
        
        # Create user profile
        user_profile = UserProfile(
            id=str(user["id"]),
            email=user["email"],
            username=user["username"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            user_tier=user["user_tier"],
            is_active=user["is_active"],
            is_verified=user["is_verified"],
            google_id=user["google_id"],
            created_at=datetime.now(timezone.utc),  # Will be overridden with real data
            daily_query_count=0,
            total_queries=0
        )
        
        # Generate tokens
        access_token = auth_service.create_jwt_token(str(user["id"]), user["email"], "access")
        refresh_token = auth_service.create_jwt_token(str(user["id"]), user["email"], "refresh")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_profile
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@auth_router.post("/google", response_model=TokenResponse)
async def google_login(google_data: GoogleLogin):
    """Login with Google OAuth2"""
    try:
        user = auth_service.authenticate_google_user(google_data.google_token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google authentication failed"
            )
        
        # Update last login
        conn = auth_service.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET last_login = %s WHERE id = %s
        """, (datetime.now(timezone.utc), user["id"]))
        conn.commit()
        conn.close()
        
        # Create user profile
        user_profile = UserProfile(
            id=str(user["id"]),
            email=user["email"],
            username=user["username"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            user_tier=user["user_tier"],
            is_active=user["is_active"],
            is_verified=user["is_verified"],
            google_id=user["google_id"],
            created_at=datetime.now(timezone.utc),
            daily_query_count=0,
            total_queries=0
        )
        
        # Generate tokens
        access_token = auth_service.create_jwt_token(str(user["id"]), user["email"], "access")
        refresh_token = auth_service.create_jwt_token(str(user["id"]), user["email"], "refresh")
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=user_profile
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )

@auth_router.post("/otp/send")
async def send_otp(otp_request: OTPRequest):
    """Send OTP code via email"""
    try:
        auth_service.create_otp_token(
            email=otp_request.email,
            token_type=otp_request.token_type
        )
        
        return {"message": f"OTP sent to {otp_request.email}"}
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@auth_router.post("/otp/verify")
async def verify_otp(otp_data: OTPVerify):
    """Verify OTP code"""
    try:
        is_valid = auth_service.verify_otp_token(
            email=otp_data.email,
            otp_code=otp_data.otp_code,
            token_type=otp_data.token_type
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code"
            )
        
        # If email verification, mark user as verified
        if otp_data.token_type == "email_verification":
            conn = auth_service.get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE users SET is_verified = true WHERE email = %s
            """, (otp_data.email,))
            conn.commit()
            conn.close()
        
        return {"message": "OTP verified successfully"}
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@auth_router.post("/password/reset")
async def reset_password(reset_data: PasswordReset):
    """Reset password with OTP"""
    try:
        # Verify OTP first
        is_valid = auth_service.verify_otp_token(
            email=reset_data.email,
            otp_code=reset_data.otp_code,
            token_type="password_reset"
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code"
            )
        
        # Update password
        hashed_password = auth_service.hash_password(reset_data.new_password)
        conn = auth_service.get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET password_hash = %s WHERE email = %s
        """, (hashed_password, reset_data.email))
        conn.commit()
        conn.close()
        
        return {"message": "Password reset successfully"}
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@auth_router.get("/profile", response_model=UserProfile)
async def get_user_profile(user: UserProfile = Depends(require_authentication)):
    """Get current user profile"""
    return user

@auth_router.get("/api-keys", response_model=List[APIKeyInfo])
async def list_api_keys(user: UserProfile = Depends(require_verified_user)):
    """List user API keys"""
    conn = auth_service.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT key_id, key_name, key_prefix, is_active, permissions,
               created_at, last_used, usage_count
        FROM api_keys WHERE user_id = %s ORDER BY created_at DESC
    """, (user.id,))
    
    keys = []
    for row in cursor.fetchall():
        keys.append(APIKeyInfo(
            key_id=row[0],
            key_name=row[1],
            key_prefix=row[2],
            is_active=row[3],
            permissions=row[4] or [],
            created_at=row[5],
            last_used=row[6],
            usage_count=row[7] or 0
        ))
    
    conn.close()
    return keys

@auth_router.post("/api-keys", response_model=APIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(key_data: APIKeyCreate, user: UserProfile = Depends(require_verified_user)):
    """Create new API key"""
    try:
        key_info = auth_service.create_api_key(user.id, key_data.key_name)
        
        return APIKeyResponse(
            key_id=key_info["key_id"],
            key_name=key_info["key_name"],
            api_key=key_info["api_key"],
            key_prefix=key_info["key_prefix"],
            created_at=datetime.now(timezone.utc)
        )
        
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@auth_router.delete("/api-keys/{key_id}")
async def delete_api_key(key_id: int, user: UserProfile = Depends(require_verified_user)):
    """Delete API key"""
    conn = auth_service.get_db_connection()
    cursor = conn.cursor()
    
    # Check if key belongs to user
    cursor.execute("""
        SELECT key_id FROM api_keys WHERE key_id = %s AND user_id = %s
    """, (key_id, user.id))
    
    if not cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Delete the key
    cursor.execute("DELETE FROM api_keys WHERE key_id = %s", (key_id,))
    conn.commit()
    conn.close()
    
    return {"message": "API key deleted successfully"}

@auth_router.get("/stats", response_model=UserStats)
async def get_user_stats(user: UserProfile = Depends(require_authenticated_user)):
    """Get user statistics"""
    conn = auth_service.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT daily_query_count, total_queries, created_at, last_login
        FROM users WHERE id = %s
    """, (user.id,))
    
    row = cursor.fetchone()
    
    cursor.execute("""
        SELECT COUNT(*) FROM api_keys WHERE user_id = %s AND is_active = true
    """, (user.id,))
    
    api_keys_count = cursor.fetchone()[0]
    
    conn.close()
    
    if row:
        account_age = (datetime.now(timezone.utc) - row[2]).days
        return UserStats(
            daily_queries=row[0] or 0,
            total_queries=row[1] or 0,
            api_keys_count=api_keys_count,
            account_age_days=account_age,
            last_login=row[3]
        )
    
    return UserStats(
        daily_queries=0,
        total_queries=0,
        api_keys_count=0,
        account_age_days=0
    )

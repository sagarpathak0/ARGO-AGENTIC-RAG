"""
Authentication Middleware for ARGO Agentic RAG
JWT and API key authentication middleware
"""

import time
from typing import Optional, Tuple, Dict, Any
from datetime import datetime, timezone

from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware

from .auth_service import auth_service, AuthenticationError
from .auth_models import UserProfile, AuthStatus

# Security scheme for JWT tokens
security = HTTPBearer(auto_error=False)

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware for authentication and rate limiting"""
    
    def __init__(self, app):
        super().__init__(app)
        self.rate_limits = {}  # In-memory rate limiting (use Redis in production)
    
    async def dispatch(self, request: Request, call_next):
        """Process authentication for each request"""
        
        # Skip auth for public endpoints
        if self._is_public_endpoint(request.url.path):
            response = await call_next(request)
            return response
        
        # Try to authenticate user
        auth_result = await self._authenticate_request(request)
        
        # Add auth info to request state
        request.state.auth = auth_result
        
        # Check rate limits
        if not self._check_rate_limits(request, auth_result):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "rate_limit_exceeded",
                    "message": "Too many requests. Please try again later.",
                    "retry_after": 60
                }
            )
        
        response = await call_next(request)
        return response
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no auth required)"""
        public_paths = [
            "/",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/auth/register",
            "/auth/login",
            "/auth/google",
            "/auth/otp/send",
            "/auth/otp/verify",
            "/auth/password/reset",
            "/health",
            "/stats"  # Public stats endpoint
        ]
        
        return any(path.startswith(p) for p in public_paths)
    
    async def _authenticate_request(self, request: Request) -> AuthStatus:
        """Authenticate request via JWT or API key"""
        
        # Try API key first (header: X-API-Key)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            try:
                api_result = auth_service.verify_api_key(api_key)
                if api_result:
                    user_profile = UserProfile(
                        id=api_result["user_id"],
                        email=api_result["email"],
                        user_tier=api_result["user_tier"],
                        is_active=api_result["is_active"],
                        is_verified=True,
                        created_at=datetime.now(timezone.utc),
                        daily_query_count=0,
                        total_queries=0
                    )
                    
                    return AuthStatus(
                        authenticated=True,
                        user=user_profile,
                        method="api_key",
                        permissions=api_result.get("permissions", ["basic_search"])
                    )
            except Exception:
                pass
        
        # Try JWT token (Authorization: Bearer <token>)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = auth_service.verify_jwt_token(token)
                if payload and payload.get("type") == "access":
                    # Get user info from database
                    user_info = self._get_user_by_id(payload["sub"])
                    if user_info:
                        user_profile = UserProfile(**user_info)
                        return AuthStatus(
                            authenticated=True,
                            user=user_profile,
                            method="jwt",
                            permissions=self._get_user_permissions(user_profile.user_tier)
                        )
            except AuthenticationError:
                pass
        
        # No valid authentication found
        return AuthStatus(
            authenticated=False,
            user=None,
            method="none",
            permissions=[]
        )
    
    def _get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user info from database by ID"""
        try:
            conn = auth_service.get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, email, username, first_name, last_name, 
                       user_tier, is_active, is_verified, google_id, avatar_url,
                       created_at, last_login, daily_query_count, total_queries
                FROM users WHERE id = %s AND is_active = true
            """, (user_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": str(row[0]),
                    "email": row[1],
                    "username": row[2],
                    "first_name": row[3],
                    "last_name": row[4],
                    "user_tier": row[5],
                    "is_active": row[6],
                    "is_verified": row[7],
                    "google_id": row[8],
                    "avatar_url": row[9],
                    "created_at": row[10],
                    "last_login": row[11],
                    "daily_query_count": row[12] or 0,
                    "total_queries": row[13] or 0
                }
        except Exception:
            pass
        
        return None
    
    def _get_user_permissions(self, user_tier: str) -> List[str]:
        """Get permissions based on user tier"""
        permissions_map = {
            "standard": ["basic_search", "basic_rag"],
            "premium": ["basic_search", "basic_rag", "advanced_search", "export_data"],
            "researcher": ["basic_search", "basic_rag", "advanced_search", "export_data", "bulk_access", "analytics"],
            "admin": ["all_features"]
        }
        return permissions_map.get(user_tier, ["basic_search"])
    
    def _check_rate_limits(self, request: Request, auth: AuthStatus) -> bool:
        """Check rate limits based on user tier or IP"""
        
        # Get identifier for rate limiting
        if auth.authenticated and auth.user:
            identifier = f"user:{auth.user.id}"
            limits = self._get_user_rate_limits(auth.user.user_tier)
        else:
            # Use IP for unauthenticated requests
            client_ip = request.client.host
            identifier = f"ip:{client_ip}"
            limits = {"per_minute": 10, "per_hour": 100, "per_day": 500}  # Default limits
        
        # Simple in-memory rate limiting (use Redis in production)
        current_time = time.time()
        
        # Clean old entries
        if identifier in self.rate_limits:
            self.rate_limits[identifier] = [
                timestamp for timestamp in self.rate_limits[identifier]
                if current_time - timestamp < 86400  # Keep last 24 hours
            ]
        else:
            self.rate_limits[identifier] = []
        
        # Add current request
        self.rate_limits[identifier].append(current_time)
        
        # Check limits
        minute_count = len([t for t in self.rate_limits[identifier] if current_time - t < 60])
        hour_count = len([t for t in self.rate_limits[identifier] if current_time - t < 3600])
        day_count = len([t for t in self.rate_limits[identifier] if current_time - t < 86400])
        
        return (minute_count <= limits["per_minute"] and 
                hour_count <= limits["per_hour"] and 
                day_count <= limits["per_day"])
    
    def _get_user_rate_limits(self, user_tier: str) -> Dict[str, int]:
        """Get rate limits based on user tier"""
        limits_map = {
            "standard": {"per_minute": 5, "per_hour": 20, "per_day": 100},
            "premium": {"per_minute": 15, "per_hour": 100, "per_day": 1000},
            "researcher": {"per_minute": 30, "per_hour": 500, "per_day": 5000},
            "admin": {"per_minute": 100, "per_hour": 1000, "per_day": 10000}
        }
        return limits_map.get(user_tier, limits_map["standard"])

# Dependency functions for FastAPI
async def get_current_user(request: Request) -> Optional[UserProfile]:
    """Get currently authenticated user"""
    auth: AuthStatus = getattr(request.state, "auth", None)
    if auth and auth.authenticated:
        return auth.user
    return None

async def require_authentication(request: Request) -> UserProfile:
    """Require authentication - raise 401 if not authenticated"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return user

async def require_verified_user(request: Request) -> UserProfile:
    """Require verified user account"""
    user = await require_authentication(request)
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required"
        )
    return user

async def require_permission(permission: str):
    """Create dependency that requires specific permission"""
    async def _check_permission(request: Request) -> UserProfile:
        user = await require_verified_user(request)
        auth: AuthStatus = getattr(request.state, "auth", None)
        
        if auth and (permission in auth.permissions or "all_features" in auth.permissions):
            return user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission}' required"
        )
    
    return _check_permission

# Specific permission dependencies
require_admin = require_permission("all_features")
require_advanced_search = require_permission("advanced_search")
require_export_data = require_permission("export_data")
require_analytics = require_permission("analytics")

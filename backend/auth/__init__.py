"""
Authentication Module for ARGO Agentic RAG
Provides JWT, OAuth2, OTP authentication and user management
"""

from .auth_service import auth_service, AuthenticationError
from .auth_models import *
from .auth_middleware import (
    AuthenticationMiddleware,
    get_current_user,
    require_authentication,
    require_verified_user,
    require_admin,
    require_advanced_search,
    require_export_data,
    require_analytics
)
from .auth_routes import auth_router

__all__ = [
    # Service
    "auth_service",
    "AuthenticationError",
    
    # Models
    "UserTier",
    "TokenType", 
    "UserRegister",
    "UserLogin",
    "GoogleLogin",
    "OTPRequest",
    "OTPVerify",
    "PasswordReset",
    "APIKeyCreate",
    "UserProfile",
    "TokenResponse",
    "APIKeyResponse",
    "AuthStatus",
    "UserStats",
    
    # Middleware and Dependencies
    "AuthenticationMiddleware",
    "get_current_user",
    "require_authentication", 
    "require_verified_user",
    "require_admin",
    "require_advanced_search",
    "require_export_data",
    "require_analytics",
    
    # Router
    "auth_router"
]

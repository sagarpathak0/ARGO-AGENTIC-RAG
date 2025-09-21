"""
Authentication Models for ARGO Agentic RAG
Pydantic models for authentication endpoints
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from enum import Enum

class UserTier(str, Enum):
    STANDARD = "standard"
    PREMIUM = "premium"
    RESEARCHER = "researcher"
    ADMIN = "admin"

class TokenType(str, Enum):
    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"
    LOGIN_2FA = "login_2fa"

# Request Models
class UserRegister(BaseModel):
    email: EmailStr
    username: Optional[str] = None
    password: str = Field(min_length=8, description="Password must be at least 8 characters")
    full_name: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class GoogleLogin(BaseModel):
    google_token: str = Field(description="Google OAuth2 ID token")

class OTPRequest(BaseModel):
    email: EmailStr
    token_type: TokenType = TokenType.EMAIL_VERIFICATION

class OTPVerify(BaseModel):
    email: EmailStr
    otp_code: str = Field(min_length=6, max_length=10)
    token_type: TokenType = TokenType.EMAIL_VERIFICATION

class PasswordReset(BaseModel):
    email: EmailStr
    otp_code: str
    new_password: str = Field(min_length=8)

class APIKeyCreate(BaseModel):
    key_name: str = Field(max_length=255, description="Descriptive name for the API key")

class APIKeyUpdate(BaseModel):
    key_name: Optional[str] = None
    is_active: Optional[bool] = None

# Response Models
class UserProfile(BaseModel):
    id: str
    email: str
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    user_tier: UserTier
    is_active: bool
    is_verified: bool
    google_id: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: datetime
    last_login: Optional[datetime] = None
    daily_query_count: int = 0
    total_queries: int = 0

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 1800  # 30 minutes
    user: UserProfile

class APIKeyResponse(BaseModel):
    key_id: int
    key_name: str
    api_key: str = Field(description="Full API key - store securely, won not be shown again")
    key_prefix: str = Field(description="First 12 characters for identification")
    created_at: datetime

class APIKeyInfo(BaseModel):
    key_id: int
    key_name: str
    key_prefix: str
    is_active: bool
    permissions: List[str]
    created_at: datetime
    last_used: Optional[datetime] = None
    usage_count: int = 0

class AuthStatus(BaseModel):
    authenticated: bool
    user: Optional[UserProfile] = None
    method: str = Field(description="jwt, api_key, or none")
    permissions: List[str] = []

class UserStats(BaseModel):
    daily_queries: int
    total_queries: int
    api_keys_count: int
    account_age_days: int
    last_login: Optional[datetime] = None

# Error Response Models
class AuthError(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None

class RateLimitError(BaseModel):
    error: str = "rate_limit_exceeded"
    message: str
    retry_after: int = Field(description="Seconds to wait before retry")
    limit_type: str = Field(description="daily, hourly, or minute")

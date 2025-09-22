"""
Authentication-related Pydantic models for ARGO API
"""
from typing import Optional
from pydantic import BaseModel


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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserProfile
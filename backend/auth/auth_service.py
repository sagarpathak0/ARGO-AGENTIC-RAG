#!/usr/bin/env python3
"""
Authentication Service for ARGO Agentic RAG
Core authentication logic with JWT, OAuth2, OTP, and user management
"""

import os
import secrets
import string
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
import uuid
import smtplib
from email.mime.text import MimeText
from email.mime.multipart import MimeMultipart

import jwt
import bcrypt
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import HTTPException, status

# Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "argo_super_secret_key_2025_oceanographic_data_analysis_system_secure")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30
OTP_EXPIRE_MINUTES = 10

# Google OAuth2 configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = os.getenv("GOOGLE_REFRESH_TOKEN")
EMAIL_ADDRESS = os.getenv("EMAIL")

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL")

class AuthenticationError(Exception):
    """Custom authentication error"""
    pass

class AuthService:
    """Authentication service with OAuth2, JWT, and OTP support"""
    
    def __init__(self):
        self.db_url = DATABASE_URL
        
    def get_db_connection(self):
        """Get database connection"""
        try:
            return psycopg2.connect(self.db_url)
        except Exception as e:
            raise AuthenticationError(f"Database connection failed: {e}")

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def generate_otp(self, length: int = 6) -> str:
        """Generate OTP code"""
        digits = string.digits
        return ''.join(secrets.choice(digits) for _ in range(length))
    
    def generate_api_key(self) -> tuple:
        """Generate API key and prefix"""
        key = 'argo_' + secrets.token_urlsafe(32)
        prefix = key[:12]  # First 12 chars for display
        return key, prefix
    
    def create_jwt_token(self, user_id: str, email: str, token_type: str = "access") -> str:
        """Create JWT token"""
        now = datetime.now(timezone.utc)
        
        if token_type == "access":
            expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        else:  # refresh token
            expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": token_type,
            "iat": now,
            "exp": expire,
            "jti": secrets.token_urlsafe(16)
        }
        
        return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    def verify_jwt_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.JWTError:
            raise AuthenticationError("Invalid token")
    
    def send_otp_email(self, email: str, otp_code: str, purpose: str = "verification"):
        """Send OTP via email (simplified version)"""
        try:
            print(f" Sending OTP {otp_code} to {email} for {purpose}")
            # In production, use actual email service
            return True
        except Exception as e:
            print(f" Failed to send OTP email: {e}")
            return False
    
    def create_user(self, email: str, username: str = None, password: str = None, 
                   full_name: str = None, google_id: str = None, avatar_url: str = None) -> str:
        """Create new user account"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            user_id = str(uuid.uuid4())
            
            # Hash password if provided
            hashed_password = self.hash_password(password) if password else None
            
            cursor.execute("""
                INSERT INTO users (id, email, username, password_hash, first_name, last_name, 
                                 google_id, avatar_url, user_tier, is_active, is_verified)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (user_id, email, username, hashed_password, 
                  full_name.split()[0] if full_name else None,
                  ' '.join(full_name.split()[1:]) if full_name and len(full_name.split()) > 1 else None,
                  google_id, avatar_url, 'standard', True, google_id is not None))
            
            created_id = cursor.fetchone()[0]
            conn.commit()
            
            return str(created_id)
            
        except psycopg2.IntegrityError as e:
            conn.rollback()
            if "email" in str(e):
                raise AuthenticationError("Email already registered")
            elif "username" in str(e):
                raise AuthenticationError("Username already taken")
            else:
                raise AuthenticationError("User creation failed")
        finally:
            conn.close()
    
    def authenticate_user(self, email: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate user with email and password"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT id, email, username, password_hash, first_name, last_name, 
                   is_active, is_verified, user_tier, google_id
            FROM users WHERE email = %s AND is_active = true
        """, (email,))
        
        user = cursor.fetchone()
        conn.close()
        
        if not user or not user['password_hash']:
            return None
            
        if not self.verify_password(password, user['password_hash']):
            return None
            
        return dict(user)
    
    def create_otp_token(self, email: str, token_type: str, user_id: str = None) -> str:
        """Create and send OTP token"""
        otp_code = self.generate_otp()
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRE_MINUTES)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO otp_tokens (user_id, email, otp_code, token_type, expires_at)
            VALUES (%s, %s, %s, %s, %s)
        """, (user_id, email, otp_code, token_type, expires_at))
        
        conn.commit()
        conn.close()
        
        # Send OTP via email
        if self.send_otp_email(email, otp_code, token_type):
            return otp_code
        else:
            raise AuthenticationError("Failed to send OTP email")
    
    def verify_otp_token(self, email: str, otp_code: str, token_type: str) -> bool:
        """Verify OTP token"""
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT token_id FROM otp_tokens 
            WHERE email = %s AND otp_code = %s AND token_type = %s 
            AND expires_at > %s AND is_used = false
        """, (email, otp_code, token_type, datetime.now(timezone.utc)))
        
        token = cursor.fetchone()
        
        if token:
            # Mark token as used
            cursor.execute("""
                UPDATE otp_tokens SET is_used = true, used_at = %s 
                WHERE token_id = %s
            """, (datetime.now(timezone.utc), token[0]))
            conn.commit()
            conn.close()
            return True
        else:
            conn.close()
            return False
    
    def create_api_key(self, user_id: str, key_name: str) -> Dict[str, str]:
        """Create API key for user"""
        api_key, prefix = self.generate_api_key()
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO api_keys (user_id, key_name, api_key, key_prefix)
            VALUES (%s, %s, %s, %s)
            RETURNING key_id
        """, (user_id, key_name, api_key, prefix))
        
        key_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()
        
        return {
            "key_id": key_id,
            "api_key": api_key,
            "key_prefix": prefix,
            "key_name": key_name
        }
    
    def verify_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Verify API key and return user info"""
        conn = self.get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT ak.user_id, ak.key_name, ak.permissions, ak.usage_count,
                   u.email, u.user_tier, u.is_active
            FROM api_keys ak
            JOIN users u ON ak.user_id = u.id
            WHERE ak.api_key = %s AND ak.is_active = true AND u.is_active = true
        """, (api_key,))
        
        result = cursor.fetchone()
        
        if result:
            # Update usage count and last used
            cursor.execute("""
                UPDATE api_keys 
                SET usage_count = usage_count + 1, last_used = %s
                WHERE api_key = %s
            """, (datetime.now(timezone.utc), api_key))
            conn.commit()
        
        conn.close()
        return dict(result) if result else None

# Global auth service instance
auth_service = AuthService()

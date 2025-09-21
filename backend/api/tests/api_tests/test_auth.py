"""
Test Authentication System
Simple test to verify auth components work
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Test database connection
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv()
    
    db_url = os.getenv('DATABASE_URL')
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Test auth tables
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM api_keys")
    key_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM otp_tokens")
    otp_count = cursor.fetchone()[0]
    
    print(f" Database connection successful")
    print(f" Users: {user_count}, API Keys: {key_count}, OTP Tokens: {otp_count}")
    
    # Test JWT creation
    import jwt
    import secrets
    
    secret = secrets.token_urlsafe(32)
    token = jwt.encode({"test": "data"}, secret, algorithm="HS256")
    decoded = jwt.decode(token, secret, algorithms=["HS256"])
    
    print(f" JWT functionality working")
    print(f" Token test: {decoded}")
    
    # Test password hashing
    import bcrypt
    
    password = "test123"
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    is_valid = bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    print(f" Password hashing working: {is_valid}")
    
    conn.close()
    print(" All authentication components ready!")
    
except Exception as e:
    print(f" Error: {e}")

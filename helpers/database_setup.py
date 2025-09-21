#!/usr/bin/env python3
"""
Database Setup Script for Agentic RAG System
Safely tests connection and sets up extensions
"""
import os
import psycopg2
from sqlalchemy import create_engine, text

# Your existing connection string
PG_URL = "postgresql://avnadmin:AVNS_T7GmZnlliHeBAIDQB0r@pg-rabbitanimated-postgres-animate28.i.aivencloud.com:13249/AlgoForge?sslmode=require"

def test_connection():
    """Test database connection"""
    try:
        engine = create_engine(PG_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            print(" Database connection successful!")
            print(f"PostgreSQL version: {result.fetchone()[0]}")
            return True
    except Exception as e:
        print(f" Connection failed: {e}")
        return False

def check_extensions():
    """Check which extensions are already installed"""
    try:
        engine = create_engine(PG_URL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT extname, extversion 
                FROM pg_extension 
                WHERE extname IN ('postgis', 'vector', 'pg_trgm')
                ORDER BY extname
            """))
            extensions = result.fetchall()
            print("\n Current Extensions:")
            for ext in extensions:
                print(f"   {ext[0]} v{ext[1]}")
            return extensions
    except Exception as e:
        print(f" Failed to check extensions: {e}")
        return []

def check_profiles_table():
    """Check profiles table schema and count"""
    try:
        engine = create_engine(PG_URL)
        with engine.connect() as conn:
            # Check if table exists
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'profiles'
            """))
            if result.fetchone()[0] == 0:
                print(" Profiles table does not exist!")
                return False
            
            # Get row count
            result = conn.execute(text("SELECT COUNT(*) FROM profiles"))
            count = result.fetchone()[0]
            print(f"\n Profiles table: {count:,} records")
            
            # Check for geom column
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'profiles' AND column_name = 'geom'
            """))
            geom_col = result.fetchone()
            if geom_col:
                print(f"   Geom column exists: {geom_col[1]}")
            else:
                print("   No geom column found")
            
            return True
    except Exception as e:
        print(f" Failed to check profiles table: {e}")
        return False

if __name__ == "__main__":
    print(" Agentic RAG Database Setup")
    print("=" * 40)
    
    if test_connection():
        check_extensions()
        check_profiles_table()
    else:
        print("Please check your database connection!")

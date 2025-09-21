#!/usr/bin/env python3
"""
Enable missing extensions for Agentic RAG System
"""
from sqlalchemy import create_engine, text

# Your existing connection string
PG_URL = "postgresql://avnadmin:AVNS_T7GmZnlliHeBAIDQB0r@pg-rabbitanimated-postgres-animate28.i.aivencloud.com:13249/AlgoForge?sslmode=require"

def enable_extensions():
    """Enable pgvector and pg_trgm extensions"""
    try:
        engine = create_engine(PG_URL)
        with engine.connect() as conn:
            print(" Enabling extensions...")
            
            # Enable pgvector
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                print("   pgvector extension enabled")
            except Exception as e:
                print(f"   pgvector failed: {e}")
            
            # Enable pg_trgm
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
                print("   pg_trgm extension enabled")
            except Exception as e:
                print(f"   pg_trgm failed: {e}")
            
            conn.commit()
            
            # Verify all extensions
            result = conn.execute(text("""
                SELECT extname, extversion 
                FROM pg_extension 
                WHERE extname IN ('postgis', 'vector', 'pg_trgm')
                ORDER BY extname
            """))
            extensions = result.fetchall()
            print("\n All Extensions Status:")
            for ext in extensions:
                print(f"   {ext[0]} v{ext[1]}")
            
            return True
    except Exception as e:
        print(f" Failed to enable extensions: {e}")
        return False

if __name__ == "__main__":
    print(" Enabling Extensions for Agentic RAG")
    print("=" * 40)
    enable_extensions()

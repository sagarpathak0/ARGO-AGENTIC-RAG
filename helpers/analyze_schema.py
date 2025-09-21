#!/usr/bin/env python3
"""
Analyze current profiles table schema
"""
from sqlalchemy import create_engine, text

PG_URL = "postgresql://avnadmin:AVNS_T7GmZnlliHeBAIDQB0r@pg-rabbitanimated-postgres-animate28.i.aivencloud.com:13249/AlgoForge?sslmode=require"

def analyze_schema():
    """Analyze current profiles table schema"""
    try:
        engine = create_engine(PG_URL)
        with engine.connect() as conn:
            # Get detailed column information
            result = conn.execute(text("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns 
                WHERE table_name = 'profiles'
                ORDER BY ordinal_position;
            """))
            
            print(" Current Profiles Table Schema:")
            print("=" * 60)
            columns = result.fetchall()
            for col in columns:
                name, dtype, max_len, nullable, default = col
                len_info = f"({max_len})" if max_len else ""
                null_info = "NULL" if nullable == "YES" else "NOT NULL"
                default_info = f" DEFAULT {default}" if default else ""
                print(f"  {name:<20} {dtype}{len_info:<15} {null_info}{default_info}")
            
            # Get indexes
            result = conn.execute(text("""
                SELECT 
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE tablename = 'profiles'
                ORDER BY indexname;
            """))
            
            print("\n Current Indexes:")
            print("=" * 60)
            indexes = result.fetchall()
            for idx in indexes:
                print(f"  {idx[0]}")
                print(f"    {idx[1]}")
                print()
            
            # Sample a few rows to see data
            result = conn.execute(text("""
                SELECT 
                    profile_id,
                    latitude,
                    longitude,
                    time_coverage_start,
                    keywords,
                    institution,
                    parquet_path
                FROM profiles 
                LIMIT 3;
            """))
            
            print(" Sample Data:")
            print("=" * 60)
            samples = result.fetchall()
            for sample in samples:
                print(f"Profile ID: {sample[0]}")
                print(f"Location: ({sample[1]}, {sample[2]})")
                print(f"Time: {sample[3]}")
                print(f"Keywords: {sample[4]}")
                print(f"Institution: {sample[5]}")
                print(f"Parquet: {sample[6]}")
                print("-" * 40)

    except Exception as e:
        print(f" Error analyzing schema: {e}")

if __name__ == "__main__":
    analyze_schema()

# Schema analysis tool for ARGO database
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.database import get_database_url, db_config
from sqlalchemy import create_engine, text
import pandas as pd
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_profiles_schema():
    """Analyze the current profiles table schema"""
    try:
        pg_url = get_database_url()
        logger.info(f"Analyzing schema on: {db_config.host}:{db_config.port}/{db_config.name}")
        
        engine = create_engine(pg_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # Get table info
            result = conn.execute(text("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM information_schema.columns 
                WHERE table_name = 'profiles'
                ORDER BY ordinal_position;
            """))
            
            schema_info = result.fetchall()
            
            if not schema_info:
                logger.warning(" Profiles table not found")
                return False
            
            logger.info(f"\n PROFILES TABLE SCHEMA ANALYSIS")
            logger.info("=" * 60)
            
            for i, (col_name, data_type, max_length, nullable, default, position) in enumerate(schema_info, 1):
                length_info = f"({max_length})" if max_length else ""
                null_info = "NULL" if nullable == "YES" else "NOT NULL"
                default_info = f" DEFAULT {default}" if default else ""
                
                logger.info(f"{i:2}. {col_name:25} {data_type}{length_info:10} {null_info:8}{default_info}")
            
            # Get row count and basic stats
            result = conn.execute(text("SELECT COUNT(*) FROM profiles;"))
            total_rows = result.fetchone()[0]
            
            logger.info(f"\n TABLE STATISTICS")
            logger.info("-" * 30)
            logger.info(f"Total rows: {total_rows:,}")
            
            # Sample some data characteristics
            if total_rows > 0:
                sample_query = text("""
                    SELECT 
                        COUNT(DISTINCT float_id) as unique_floats,
                        COUNT(DISTINCT platform_number) as unique_platforms,
                        MIN(latitude) as min_lat,
                        MAX(latitude) as max_lat,
                        MIN(longitude) as min_lon,
                        MAX(longitude) as max_lon,
                        MIN(created_at) as earliest_record,
                        MAX(created_at) as latest_record
                    FROM profiles 
                    WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
                """)
                
                result = conn.execute(sample_query)
                stats = result.fetchone()
                
                if stats:
                    unique_floats, unique_platforms, min_lat, max_lat, min_lon, max_lon, earliest, latest = stats
                    
                    logger.info(f"Unique floats: {unique_floats:,}")
                    logger.info(f"Unique platforms: {unique_platforms:,}")
                    logger.info(f"Latitude range: {min_lat:.2f} to {max_lat:.2f}")
                    logger.info(f"Longitude range: {min_lon:.2f} to {max_lon:.2f}")
                    logger.info(f"Date range: {earliest} to {latest}")
            
            # Check indexes
            result = conn.execute(text("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes 
                WHERE tablename = 'profiles'
                ORDER BY indexname;
            """))
            
            indexes = result.fetchall()
            
            logger.info(f"\n INDEXES ({len(indexes)} total)")
            logger.info("-" * 40)
            
            for schema, table, idx_name, idx_def in indexes:
                # Extract key parts of index definition
                if "USING btree" in idx_def:
                    idx_type = "BTREE"
                elif "USING gist" in idx_def:
                    idx_type = "GIST"
                elif "USING gin" in idx_def:
                    idx_type = "GIN"
                else:
                    idx_type = "OTHER"
                
                logger.info(f" {idx_name:30} ({idx_type})")
            
            logger.info(f"\n Schema analysis complete!")
            return True
            
    except Exception as e:
        logger.error(f" Schema analysis failed: {e}")
        return False

def analyze_data_quality():
    """Analyze data quality in the profiles table"""
    try:
        pg_url = get_database_url()
        engine = create_engine(pg_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            logger.info(f"\n DATA QUALITY ANALYSIS")
            logger.info("=" * 40)
            
            # Check for NULL values in key columns
            quality_query = text("""
                SELECT 
                    COUNT(*) as total_rows,
                    COUNT(latitude) as has_latitude,
                    COUNT(longitude) as has_longitude,
                    COUNT(profile_time) as has_profile_time,
                    COUNT(float_id) as has_float_id,
                    COUNT(platform_number) as has_platform_number,
                    COUNT(file_path) as has_file_path,
                    COUNT(parquet_path) as has_parquet_path
                FROM profiles;
            """)
            
            result = conn.execute(quality_query)
            quality_stats = result.fetchone()
            
            if quality_stats:
                total, lat, lon, time, float_id, platform, file_path, parquet = quality_stats
                
                logger.info(f"Total records: {total:,}")
                logger.info(f"Has latitude: {lat:,} ({lat/total*100:.1f}%)")
                logger.info(f"Has longitude: {lon:,} ({lon/total*100:.1f}%)")
                logger.info(f"Has profile_time: {time:,} ({time/total*100:.1f}%)")
                logger.info(f"Has float_id: {float_id:,} ({float_id/total*100:.1f}%)")
                logger.info(f"Has platform_number: {platform:,} ({platform/total*100:.1f}%)")
                logger.info(f"Has file_path: {file_path:,} ({file_path/total*100:.1f}%)")
                logger.info(f"Has parquet_path: {parquet:,} ({parquet/total*100:.1f}%)")
            
            return True
            
    except Exception as e:
        logger.error(f" Data quality analysis failed: {e}")
        return False

if __name__ == "__main__":
    logger.info(" Database Schema Analysis Tool")
    logger.info("=" * 50)
    
    # Test configuration loading
    if not db_config.database_url:
        logger.error(" Database configuration not loaded. Check your .env file.")
        sys.exit(1)
    
    logger.info(f" Target database: {db_config.host}:{db_config.port}/{db_config.name}")
    
    success = True
    success &= analyze_profiles_schema()
    success &= analyze_data_quality()
    
    if success:
        logger.info("\n Analysis complete!")
    else:
        logger.error("\n Analysis failed.")
        sys.exit(1)

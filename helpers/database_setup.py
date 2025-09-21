# Database setup and connection testing for Aiven PostgreSQL
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.database import get_database_url, db_config
from sqlalchemy import create_engine, text
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    """Test the database connection"""
    try:
        # Use environment-based configuration
        pg_url = get_database_url()
        logger.info(f"Testing connection to database: {db_config.host}:{db_config.port}/{db_config.name}")
        
        engine = create_engine(pg_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            logger.info(f" Connection successful!")
            logger.info(f"PostgreSQL version: {version}")
            
            # Test database name
            result = conn.execute(text("SELECT current_database();"))
            db_name = result.fetchone()[0]
            logger.info(f"Connected to database: {db_name}")
            
            return True
            
    except Exception as e:
        logger.error(f" Connection failed: {e}")
        return False

def check_extensions():
    """Check if required extensions are installed"""
    try:
        pg_url = get_database_url()
        engine = create_engine(pg_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # Check for PostGIS
            result = conn.execute(text("""
                SELECT name, default_version, installed_version 
                FROM pg_available_extensions 
                WHERE name IN ('postgis', 'pgvector', 'pg_trgm')
                ORDER BY name;
            """))
            
            extensions = result.fetchall()
            logger.info("\n Extension Status:")
            logger.info("-" * 50)
            
            for ext in extensions:
                name, default_ver, installed_ver = ext
                status = " INSTALLED" if installed_ver else " NOT INSTALLED"
                version_info = f"(v{installed_ver})" if installed_ver else f"(available: v{default_ver})"
                logger.info(f"{name:10} {status} {version_info}")
            
            return True
            
    except Exception as e:
        logger.error(f" Failed to check extensions: {e}")
        return False

def check_profiles_table():
    """Check the current profiles table structure"""
    try:
        pg_url = get_database_url()
        engine = create_engine(pg_url, pool_pre_ping=True)
        
        with engine.connect() as conn:
            # Check if profiles table exists
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'profiles'
                );
            """))
            
            table_exists = result.fetchone()[0]
            
            if table_exists:
                # Get row count
                result = conn.execute(text("SELECT COUNT(*) FROM profiles;"))
                row_count = result.fetchone()[0]
                logger.info(f"\n Profiles Table Status:")
                logger.info(f" Table exists with {row_count:,} records")
                
                # Get column info
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'profiles'
                    ORDER BY ordinal_position;
                """))
                
                columns = result.fetchall()
                logger.info(f" Current schema ({len(columns)} columns):")
                for col_name, data_type, nullable in columns:
                    null_info = "NULL" if nullable == "YES" else "NOT NULL"
                    logger.info(f"  - {col_name:20} {data_type:15} {null_info}")
                
            else:
                logger.info("\n Profiles Table Status:")
                logger.info(" Table does not exist")
            
            return table_exists
            
    except Exception as e:
        logger.error(f" Failed to check profiles table: {e}")
        return False

if __name__ == "__main__":
    logger.info(" Database Setup and Connection Test")
    logger.info("=" * 50)
    
    # Test configuration loading
    if not db_config.database_url:
        logger.error(" Database configuration not loaded. Check your .env file.")
        sys.exit(1)
    
    logger.info(f" Configuration loaded from environment")
    logger.info(f"   Host: {db_config.host}")
    logger.info(f"   Port: {db_config.port}")
    logger.info(f"   Database: {db_config.name}")
    logger.info(f"   User: {db_config.user}")
    
    # Run tests
    success = True
    success &= test_connection()
    success &= check_extensions()
    success &= check_profiles_table()
    
    logger.info("\n" + "=" * 50)
    if success:
        logger.info(" All checks passed! Database is ready.")
    else:
        logger.error(" Some checks failed. Please review the errors above.")
        sys.exit(1)

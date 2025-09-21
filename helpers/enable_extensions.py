# Enable PostgreSQL extensions for Agentic RAG system
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

def enable_extensions():
    """Enable required PostgreSQL extensions"""
    try:
        pg_url = get_database_url()
        logger.info(f"Enabling extensions on database: {db_config.host}:{db_config.port}/{db_config.name}")
        
        engine = create_engine(pg_url, pool_pre_ping=True)
        
        extensions = [
            'postgis',    # For geospatial data
            'pgvector',   # For vector embeddings
            'pg_trgm',    # For text similarity search
            '"uuid-ossp"' # For UUID generation (quoted because of hyphen)
        ]
        
        with engine.begin() as conn:
            logger.info(" Enabling extensions...")
            
            for ext in extensions:
                try:
                    conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {ext};"))
                    logger.info(f" {ext.strip('\"')} enabled")
                except Exception as e:
                    logger.error(f" Failed to enable {ext}: {e}")
                    
            # Verify extensions are installed
            result = conn.execute(text("""
                SELECT extname, extversion 
                FROM pg_extension 
                WHERE extname IN ('postgis', 'pgvector', 'pg_trgm', 'uuid-ossp')
                ORDER BY extname;
            """))
            
            installed = result.fetchall()
            logger.info("\n Verification - Installed Extensions:")
            logger.info("-" * 40)
            
            for ext_name, ext_version in installed:
                logger.info(f" {ext_name:12} v{ext_version}")
            
            logger.info("\n Extension setup complete!")
            return True
            
    except Exception as e:
        logger.error(f" Failed to enable extensions: {e}")
        return False

if __name__ == "__main__":
    logger.info(" PostgreSQL Extension Setup")
    logger.info("=" * 40)
    
    # Test configuration loading
    if not db_config.database_url:
        logger.error(" Database configuration not loaded. Check your .env file.")
        sys.exit(1)
    
    logger.info(f" Target database: {db_config.host}:{db_config.port}/{db_config.name}")
    
    success = enable_extensions()
    
    if success:
        logger.info(" All extensions enabled successfully!")
    else:
        logger.error(" Extension setup failed.")
        sys.exit(1)

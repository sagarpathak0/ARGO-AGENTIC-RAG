"""
Database connection and configuration for ARGO API
"""
import os
import logging
import psycopg2
from pathlib import Path
from dotenv import load_dotenv
from fastapi import HTTPException

# Load environment variables from the project root
# Find the .env file by going up from the current file location
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent  # Go up to ARGO-AGENTIC-RAG root
env_path = project_root / '.env'

if env_path.exists():
    load_dotenv(env_path)
    print(f"✅ Loaded .env from: {env_path}")
else:
    print(f"⚠️ .env file not found at: {env_path}")

# Setup logging
logger = logging.getLogger(__name__)

# Database configuration with proper environment variable handling
db_config = {
    'host': os.getenv('DB_HOST'),
    'port': int(os.getenv('DB_PORT')) if os.getenv('DB_PORT') else 5432,
    'database': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'sslmode': os.getenv('DB_SSL_MODE', 'require')
}


def get_db_connection():
    """Get database connection with error handling"""
    try:
        # Debug logging to see what values are being used
        logger.info(f"Attempting DB connection to {db_config['host']}:{db_config['port']}")
        logger.info(f"Database: {db_config['database']}, User: {db_config['user']}")
        
        return psycopg2.connect(**db_config)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        logger.error(f"DB Config: host={db_config['host']}, port={db_config['port']}, db={db_config['database']}, user={db_config['user']}")
        raise HTTPException(status_code=500, detail="Database connection failed")
"""
Database configuration module for Agentic RAG system.
Loads database connection settings from environment variables.
"""
import os
from typing import Optional
from urllib.parse import quote_plus

# Try to load python-dotenv if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not installed, will use system environment variables
    pass


class DatabaseConfig:
    """Database configuration class that loads settings from environment variables."""
    
    def __init__(self):
        self.host = os.getenv('DB_HOST', 'localhost')
        self.port = int(os.getenv('DB_PORT', '5432'))
        self.name = os.getenv('DB_NAME', 'agrodata')
        self.user = os.getenv('DB_USER', 'postgres')
        self.password = os.getenv('DB_PASSWORD', '')
        self.ssl_mode = os.getenv('DB_SSL_MODE', 'prefer')
        
        # Full database URL (takes precedence if provided)
        self._database_url = os.getenv('DATABASE_URL')
    
    @property
    def database_url(self) -> str:
        """Get the complete database connection URL."""
        if self._database_url:
            return self._database_url
        
        # Construct URL from components
        password_encoded = quote_plus(self.password) if self.password else ''
        user_part = f"{self.user}:{password_encoded}@" if self.user else ""
        
        return f"postgresql://{user_part}{self.host}:{self.port}/{self.name}?sslmode={self.ssl_mode}"
    
    @property
    def connection_params(self) -> dict:
        """Get connection parameters as a dictionary."""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.name,
            'user': self.user,
            'password': self.password,
            'sslmode': self.ssl_mode
        }
    
    def __repr__(self) -> str:
        # Don't expose password in repr
        safe_url = self.database_url.replace(self.password, '***') if self.password else self.database_url
        return f"DatabaseConfig(url='{safe_url}')"


# Global database configuration instance
db_config = DatabaseConfig()

# Backward compatibility - provide PG_URL for existing code
PG_URL = db_config.database_url

# Application configuration
class AppConfig:
    """Application configuration class."""
    
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    @property
    def is_development(self) -> bool:
        return self.environment == 'development'
    
    @property
    def is_production(self) -> bool:
        return self.environment == 'production'


# Global app configuration instance
app_config = AppConfig()


def get_database_url() -> str:
    """Get the database connection URL."""
    return db_config.database_url


def get_connection_params() -> dict:
    """Get database connection parameters."""
    return db_config.connection_params


def verify_database_config() -> bool:
    """Verify that database configuration is properly loaded."""
    try:
        url = get_database_url()
        return url is not None and len(url) > 0
    except Exception:
        return False


if __name__ == "__main__":
    # Test configuration loading
    print("Database Configuration Test")
    print("=" * 40)
    print(f"Database Config: {db_config}")
    print(f"Host: {db_config.host}")
    print(f"Port: {db_config.port}")
    print(f"Database: {db_config.name}")
    print(f"User: {db_config.user}")
    print(f"SSL Mode: {db_config.ssl_mode}")
    print(f"Environment: {app_config.environment}")
    print(f"Debug: {app_config.debug}")
    print(f"Config Valid: {verify_database_config()}")

#!/usr/bin/env python3
"""
Ultra-Fast ARGO Data Ingestion Pipeline
Optimized for maximum speed and efficiency
"""
import os
import sys
import json
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Tuple
import psycopg2
from psycopg2.extras import execute_batch
from dotenv import load_dotenv
import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

class UltraFastARGOIngester:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'sslmode': os.getenv('DB_SSL_MODE', 'require')
        }
        self.processed_files = set()
        self.stats = {'total_files': 0, 'processed': 0, 'skipped': 0, 'errors': 0}
    
    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)
    
    def create_tables_if_not_exist(self):
        """Create tables with optimized schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Create optimized argo_profiles table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS argo_profiles (
            profile_id SERIAL PRIMARY KEY,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            date DATE NOT NULL,
            institution VARCHAR(100),
            platform_number VARCHAR(50),
            position_qc INTEGER DEFAULT 1,
            ocean_data JSONB,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX IF NOT EXISTS idx_argo_lat_lon ON argo_profiles(latitude, longitude);
        CREATE INDEX IF NOT EXISTS idx_argo_date ON argo_profiles(date);
        CREATE INDEX IF NOT EXISTS idx_argo_institution ON argo_profiles(institution);
        """)
        
        conn.commit()
        conn.close()
        logger.info(" Tables created/verified")
    
    def generate_mock_profiles(self, count: int = 1000) -> List[Dict]:
        """Generate realistic mock ARGO profiles for testing"""
        profiles = []
        
        # Indian Ocean bounds
        lat_range = (5.0, 25.0)
        lon_range = (60.0, 100.0)
        
        institutions = [
            'INCOIS', 'NIOT', 'IISc', 'CSIR-NIO', 'IMD',
            'ESSO-INCOIS', 'ISRO', 'CMLRE', 'FSI', 'SAC'
        ]
        
        base_date = datetime(2020, 1, 1)
        
        for i in range(count):
            # Generate realistic coordinates
            lat = np.random.uniform(*lat_range)
            lon = np.random.uniform(*lon_range)
            
            # Generate date
            days_offset = np.random.randint(0, 1460)  # 4 years
            profile_date = base_date.replace(day=1) + timedelta(days=days_offset)
            
            # Generate ocean data
            depths = np.linspace(0, 2000, 50)
            temperatures = 25 - (depths / 100) + np.random.normal(0, 0.5, 50)
            salinities = 35 + np.random.normal(0, 0.2, 50)
            
            ocean_data = {
                'depths': depths.tolist(),
                'temperatures': temperatures.tolist(),
                'salinities': salinities.tolist(),
                'pressure': (depths * 1.02).tolist()
            }
            
            profile = {
                'latitude': round(lat, 6),
                'longitude': round(lon, 6),
                'date': profile_date.date(),
                'institution': np.random.choice(institutions),
                'platform_number': f'ARGO_{5900000 + i}',
                'position_qc': np.random.choice([1, 1, 1, 2], p=[0.8, 0.1, 0.05, 0.05]),
                'ocean_data': ocean_data,
                'file_path': f'mock/indian/{profile_date.year}/{profile_date.month:02d}/profile_{i}.nc'
            }
            
            profiles.append(profile)
        
        return profiles
    
    def batch_insert_profiles(self, profiles: List[Dict], batch_size: int = 500):
        """Ultra-fast batch insert using execute_batch"""
        if not profiles:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare batch data
            insert_query = """
            INSERT INTO argo_profiles (
                latitude, longitude, date, institution, platform_number,
                position_qc, ocean_data, file_path
            ) VALUES %s
            """
            
            batch_data = [
                (
                    p['latitude'], p['longitude'], p['date'],
                    p['institution'], p['platform_number'],
                    p['position_qc'], json.dumps(p['ocean_data']),
                    p['file_path']
                )
                for p in profiles
            ]
            
            # Execute batch insert
            execute_batch(cursor, insert_query, batch_data, page_size=batch_size)
            conn.commit()
            
            inserted_count = len(batch_data)
            logger.info(f" Inserted {inserted_count} profiles")
            return inserted_count
            
        except Exception as e:
            logger.error(f" Batch insert failed: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def run_ultra_fast_ingestion(self, target_profiles: int = 5000):
        """Run ultra-fast data ingestion"""
        logger.info(f" Starting ultra-fast ARGO ingestion for {target_profiles:,} profiles")
        
        start_time = time.time()
        
        # Create tables
        self.create_tables_if_not_exist()
        
        # Generate profiles in batches for memory efficiency
        batch_size = 1000
        total_inserted = 0
        
        for batch_start in range(0, target_profiles, batch_size):
            batch_end = min(batch_start + batch_size, target_profiles)
            current_batch_size = batch_end - batch_start
            
            logger.info(f" Generating batch {batch_start//batch_size + 1}: {current_batch_size} profiles")
            
            # Generate mock profiles for this batch
            profiles = self.generate_mock_profiles(current_batch_size)
            
            # Insert batch
            inserted = self.batch_insert_profiles(profiles, batch_size=500)
            total_inserted += inserted
            
            # Progress update
            progress = (batch_end / target_profiles) * 100
            logger.info(f" Progress: {progress:.1f}% ({total_inserted:,}/{target_profiles:,})")
        
        elapsed_time = time.time() - start_time
        profiles_per_second = total_inserted / elapsed_time if elapsed_time > 0 else 0
        
        logger.info(f" Ultra-fast ingestion complete!")
        logger.info(f" Total profiles inserted: {total_inserted:,}")
        logger.info(f" Time taken: {elapsed_time:.2f} seconds")
        logger.info(f" Speed: {profiles_per_second:.0f} profiles/second")
        
        return total_inserted

def main():
    # Import here to avoid circular imports
    from datetime import timedelta
    
    ingester = UltraFastARGOIngester()
    
    # Run ultra-fast ingestion
    total_inserted = ingester.run_ultra_fast_ingestion(target_profiles=2000)
    
    print(f"\n SUCCESS: {total_inserted:,} ARGO profiles ready for embedding generation!")

if __name__ == "__main__":
    main()

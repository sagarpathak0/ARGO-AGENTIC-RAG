#!/usr/bin/env python3
"""
Ultra-Fast ARGO Data Ingestion Pipeline - OPTIMIZED
"""
import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class SpeedARGOIngester:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'sslmode': os.getenv('DB_SSL_MODE', 'require')
        }
    
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def create_table(self):
        conn = self.get_connection()
        cursor = conn.cursor()
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
        """)
        conn.commit()
        conn.close()
        logger.info(" Table ready")
    
    def generate_profiles(self, count: int) -> List[tuple]:
        """Generate tuples for fast insert"""
        logger.info(f" Generating {count:,} profiles...")
        
        profiles = []
        institutions = ['INCOIS', 'NIOT', 'CSIR-NIO', 'IMD', 'ISRO']
        base_date = datetime(2020, 1, 1)
        
        for i in range(count):
            lat = np.random.uniform(5.0, 25.0)
            lon = np.random.uniform(60.0, 100.0)
            days = np.random.randint(0, 1460)
            date = base_date + timedelta(days=days)
            
            # Simple ocean data
            ocean_data = {
                'depths': list(range(0, 2000, 50)),
                'temperatures': [25 - (d/100) for d in range(0, 2000, 50)],
                'salinities': [35.0] * 40
            }
            
            profile = (
                round(lat, 6),
                round(lon, 6), 
                date.date(),
                np.random.choice(institutions),
                f'ARGO_{5900000 + i}',
                1,
                json.dumps(ocean_data),
                f'mock/profile_{i}.nc'
            )
            profiles.append(profile)
        
        return profiles
    
    def fast_insert(self, profiles: List[tuple]):
        """Super fast bulk insert"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
            INSERT INTO argo_profiles 
            (latitude, longitude, date, institution, platform_number, position_qc, ocean_data, file_path)
            VALUES %s
            """
            
            execute_values(cursor, query, profiles, page_size=1000)
            conn.commit()
            
            logger.info(f" Inserted {len(profiles):,} profiles")
            return len(profiles)
            
        except Exception as e:
            logger.error(f" Insert failed: {e}")
            conn.rollback()
            return 0
        finally:
            conn.close()
    
    def run(self, target: int = 2000):
        logger.info(f" ULTRA-FAST INGESTION: {target:,} profiles")
        start = time.time()
        
        self.create_table()
        profiles = self.generate_profiles(target)
        inserted = self.fast_insert(profiles)
        
        elapsed = time.time() - start
        speed = inserted / elapsed if elapsed > 0 else 0
        
        logger.info(f" COMPLETE: {inserted:,} profiles in {elapsed:.1f}s ({speed:.0f}/sec)")
        return inserted

def main():
    ingester = SpeedARGOIngester()
    result = ingester.run(2000)
    print(f"\n {result:,} ARGO profiles ready!")

if __name__ == "__main__":
    main()

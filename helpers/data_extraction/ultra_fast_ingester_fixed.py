#!/usr/bin/env python3
"""
ULTRA-FAST ARGO FULL DATASET EXTRACTOR
Processes all 214,400+ NetCDF files efficiently with multiprocessing
"""
import os
import glob
import logging
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
from netCDF4 import Dataset
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

def extract_single_profile(nc_file_path: str) -> Optional[Dict[str, Any]]:
    """Extract single profile - optimized for multiprocessing"""
    try:
        with Dataset(nc_file_path, 'r') as nc:
            # Quick coordinate extraction
            lat = lon = None
            
            if 'LATITUDE' in nc.variables:
                lat_data = nc.variables['LATITUDE'][:]
                lat = float(lat_data.flat[0]) if len(lat_data) > 0 else None
            elif 'latitude' in nc.variables:
                lat_data = nc.variables['latitude'][:]
                lat = float(lat_data.flat[0]) if len(lat_data) > 0 else None
                
            if 'LONGITUDE' in nc.variables:
                lon_data = nc.variables['LONGITUDE'][:]
                lon = float(lon_data.flat[0]) if len(lon_data) > 0 else None
            elif 'longitude' in nc.variables:
                lon_data = nc.variables['longitude'][:]
                lon = float(lon_data.flat[0]) if len(lon_data) > 0 else None
            
            # Validate coordinates
            if (lat is None or lon is None or 
                abs(lat) > 90 or abs(lon) > 180 or 
                np.isnan(lat) or np.isnan(lon)):
                return None
            
            # Extract date from file path (faster than parsing JULD)
            try:
                path_parts = nc_file_path.replace('\\', '/').split('/')
                year = int(path_parts[-3])
                month = int(path_parts[-2])
                profile_date = datetime(year, month, 15).date()
            except:
                profile_date = datetime(2000, 1, 1).date()
            
            # Get platform info (safely)
            platform = 'UNKNOWN'
            try:
                if 'PLATFORM_NUMBER' in nc.variables:
                    plat_data = nc.variables['PLATFORM_NUMBER'][:]
                    if hasattr(plat_data, 'tobytes'):
                        platform = plat_data.tobytes().decode('utf-8', errors='ignore').strip().replace('\x00', '')
                    else:
                        platform = str(plat_data[0])
                platform = platform[:50] if platform else 'UNKNOWN'
            except:
                platform = 'UNKNOWN'
            
            # Extract ocean data (temperature, salinity, pressure)
            ocean_data = {}
            try:
                for var_name in ['PRES', 'TEMP', 'PSAL']:
                    if var_name in nc.variables:
                        data = nc.variables[var_name][:]
                        if hasattr(data, 'compressed'):
                            clean_data = data.compressed()
                        else:
                            clean_data = data.flatten()
                        
                        # Keep only valid data
                        valid_data = clean_data[~np.isnan(clean_data)]
                        if len(valid_data) > 0:
                            ocean_data[var_name.lower()] = valid_data.tolist()[:100]  # Limit size
            except:
                pass
            
            return {
                'latitude': lat,
                'longitude': lon,
                'date': profile_date,
                'platform_number': platform,
                'institution': 'ARGO',
                'ocean_data': ocean_data,
                'file_path': nc_file_path
            }
            
    except Exception as e:
        return None

class UltraFastARGOExtractor:
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
    
    def setup_database(self):
        """Setup optimized database for bulk insert"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Drop and recreate for clean start
        cursor.execute("DROP TABLE IF EXISTS argo_profiles CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS profile_embeddings CASCADE;")
        
        # Create optimized table
        cursor.execute("""
        CREATE TABLE argo_profiles (
            profile_id SERIAL PRIMARY KEY,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            date DATE NOT NULL,
            institution VARCHAR(20) DEFAULT 'ARGO',
            platform_number VARCHAR(50),
            position_qc INTEGER DEFAULT 1,
            ocean_data JSONB,
            file_path TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
        """)
        
        # Create embedding table with correct schema
        cursor.execute("""
        CREATE TABLE profile_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            profile_id VARCHAR NOT NULL,
            content_type VARCHAR NOT NULL,
            content_text TEXT,
            embedding VECTOR(384),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        """)
        
        conn.commit()
        conn.close()
        logger.info(" Database setup complete")
    
    def bulk_insert_profiles(self, profiles: List[Dict[str, Any]]) -> int:
        """Ultra-fast bulk insert"""
        if not profiles:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare data
            insert_data = []
            for profile in profiles:
                insert_data.append((
                    profile['latitude'],
                    profile['longitude'],
                    profile['date'],
                    profile['institution'],
                    profile['platform_number'],
                    1,
                    json.dumps(profile['ocean_data']),
                    profile['file_path']
                ))
            
            # Ultra-fast bulk insert
            query = """
            INSERT INTO argo_profiles (
                latitude, longitude, date, institution, platform_number,
                position_qc, ocean_data, file_path
            ) VALUES %s
            """
            
            execute_values(
                cursor, query, insert_data, 
                template=None, page_size=10000
            )
            
            conn.commit()
            inserted = len(insert_data)
            conn.close()
            return inserted
            
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            conn.rollback()
            conn.close()
            return 0
    
    def extract_all_profiles_parallel(self, max_workers: int = None):
        """Extract ALL profiles using parallel processing"""
        logger.info(" ULTRA-FAST FULL ARGO EXTRACTION STARTING")
        
        # Setup database
        self.setup_database()
        
        # Find all NetCDF files
        logger.info(" Finding all NetCDF files...")
        nc_pattern = os.path.join("gadr", "data", "indian", "**", "*.nc")
        all_nc_files = glob.glob(nc_pattern, recursive=True)
        
        total_files = len(all_nc_files)
        logger.info(f" Found {total_files:,} NetCDF files")
        
        if total_files == 0:
            logger.error(" No NetCDF files found!")
            return 0
        
        # Setup multiprocessing
        if max_workers is None:
            max_workers = min(mp.cpu_count(), 8)  # Limit to prevent overwhelm
        
        logger.info(f" Using {max_workers} parallel workers")
        
        # Process files in parallel
        processed = 0
        inserted = 0
        batch_size = 5000  # Large batches for efficiency
        profiles_batch = []
        
        start_time = time.time()
        
        with ProcessPoolExecutor(max_workers=max_workers) as executor:
            # Submit all files for processing
            future_to_file = {
                executor.submit(extract_single_profile, nc_file): nc_file 
                for nc_file in all_nc_files
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_file):
                processed += 1
                
                try:
                    profile = future.result()
                    if profile:
                        profiles_batch.append(profile)
                        
                        # Insert when batch is full
                        if len(profiles_batch) >= batch_size:
                            batch_inserted = self.bulk_insert_profiles(profiles_batch)
                            inserted += batch_inserted
                            profiles_batch = []
                            
                            # Progress update
                            elapsed = time.time() - start_time
                            rate = processed / elapsed if elapsed > 0 else 0
                            progress = (processed / total_files) * 100
                            
                            logger.info(f" Progress: {processed:,}/{total_files:,} ({progress:.1f}%) | "
                                      f"Inserted: {inserted:,} | Rate: {rate:.1f} files/sec")
                except Exception as e:
                    logger.debug(f"Failed to process file: {e}")
        
        # Insert remaining profiles
        if profiles_batch:
            batch_inserted = self.bulk_insert_profiles(profiles_batch)
            inserted += batch_inserted
        
        # Final statistics
        elapsed_time = time.time() - start_time
        
        logger.info(f" ULTRA-FAST EXTRACTION COMPLETE!")
        logger.info(f" Files processed: {processed:,}")
        logger.info(f" Profiles inserted: {inserted:,}")
        logger.info(f" Total time: {elapsed_time:.1f} seconds")
        logger.info(f" Average speed: {processed/elapsed_time:.1f} files/sec")
        logger.info(f" Data rate: {inserted/elapsed_time:.1f} profiles/sec")
        
        return inserted

def main():
    extractor = UltraFastARGOExtractor()
    
    # Extract ALL profiles with parallel processing
    total_extracted = extractor.extract_all_profiles_parallel(max_workers=6)
    
    print(f"\n MISSION COMPLETE: {total_extracted:,} ARGO profiles extracted!")
    print(f" Full oceanographic dataset ready for vectorization!")

if __name__ == "__main__":
    main()

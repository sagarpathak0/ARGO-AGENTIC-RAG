#!/usr/bin/env python3
"""
ARGO NetCDF to Database Extractor
Efficiently extracts real ARGO oceanographic data from NetCDF files
"""
import os
import glob
import logging
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from netCDF4 import Dataset
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class ARGONetCDFExtractor:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'sslmode': os.getenv('DB_SSL_MODE', 'require')
        }
        self.stats = {'processed': 0, 'errors': 0, 'skipped': 0, 'inserted': 0}
        
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def create_table(self):
        """Create the argo_profiles table with proper schema"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Drop existing table to start fresh
        cursor.execute("DROP TABLE IF EXISTS argo_profiles CASCADE;")
        
        # Create new table
        cursor.execute("""
        CREATE TABLE argo_profiles (
            profile_id SERIAL PRIMARY KEY,
            latitude FLOAT NOT NULL,
            longitude FLOAT NOT NULL,
            date DATE NOT NULL,
            institution VARCHAR(100),
            platform_number VARCHAR(50),
            position_qc INTEGER DEFAULT 1,
            ocean_data JSONB,
            file_path TEXT,
            wmo_inst_type VARCHAR(50),
            project_name VARCHAR(100),
            data_centre VARCHAR(50),
            created_at TIMESTAMP DEFAULT NOW()
        );
        
        CREATE INDEX idx_argo_lat_lon ON argo_profiles(latitude, longitude);
        CREATE INDEX idx_argo_date ON argo_profiles(date);
        CREATE INDEX idx_argo_platform ON argo_profiles(platform_number);
        """)
        
        conn.commit()
        conn.close()
        logger.info(" Created fresh argo_profiles table")
    
    def extract_profile_from_nc(self, nc_file_path: str) -> Optional[Dict[str, Any]]:
        """Extract ARGO profile data from NetCDF file"""
        try:
            with Dataset(nc_file_path, 'r') as nc:
                # Extract basic profile information
                profile = {}
                
                # Geographic coordinates
                if 'LATITUDE' in nc.variables:
                    lat = nc.variables['LATITUDE'][:]
                    profile['latitude'] = float(lat[0]) if len(lat) > 0 else None
                elif 'latitude' in nc.variables:
                    profile['latitude'] = float(nc.variables['latitude'][:][0])
                
                if 'LONGITUDE' in nc.variables:
                    lon = nc.variables['LONGITUDE'][:]
                    profile['longitude'] = float(lon[0]) if len(lon) > 0 else None
                elif 'longitude' in nc.variables:
                    profile['longitude'] = float(nc.variables['longitude'][:][0])
                
                # Date/Time
                if 'JULD' in nc.variables:
                    juld = nc.variables['JULD'][:]
                    if len(juld) > 0 and not np.ma.is_masked(juld[0]):
                        # JULD is days since 1950-01-01
                        ref_date = datetime(1950, 1, 1)
                        try:
                            profile_date = ref_date + timedelta(days=float(juld[0]))
                            profile['date'] = profile_date.date()
                        except:
                            profile['date'] = datetime.now().date()
                    else:
                        profile['date'] = datetime.now().date()
                else:
                    profile['date'] = datetime.now().date()
                
                # Platform and institution info
                if 'PLATFORM_NUMBER' in nc.variables:
                    platform = nc.variables['PLATFORM_NUMBER'][:]
                    if hasattr(platform, 'tobytes'):
                        profile['platform_number'] = platform.tobytes().decode('utf-8').strip()
                    else:
                        profile['platform_number'] = str(platform[0]).strip()
                
                if 'DATA_CENTRE' in nc.variables:
                    dc = nc.variables['DATA_CENTRE'][:]
                    if hasattr(dc, 'tobytes'):
                        profile['data_centre'] = dc.tobytes().decode('utf-8').strip()
                    else:
                        profile['data_centre'] = str(dc[0]).strip()
                
                if 'WMO_INST_TYPE' in nc.variables:
                    wmo = nc.variables['WMO_INST_TYPE'][:]
                    if hasattr(wmo, 'tobytes'):
                        profile['wmo_inst_type'] = wmo.tobytes().decode('utf-8').strip()
                    else:
                        profile['wmo_inst_type'] = str(wmo[0]).strip()
                
                if 'PROJECT_NAME' in nc.variables:
                    proj = nc.variables['PROJECT_NAME'][:]
                    if hasattr(proj, 'tobytes'):
                        profile['project_name'] = proj.tobytes().decode('utf-8').strip()
                    else:
                        profile['project_name'] = str(proj[0]).strip()
                
                # Ocean data (temperature, salinity, pressure)
                ocean_data = {}
                
                # Pressure/Depth
                if 'PRES' in nc.variables:
                    pres = nc.variables['PRES'][:]
                    if not np.ma.is_masked(pres):
                        ocean_data['pressure'] = pres.compressed().tolist()
                
                # Temperature
                if 'TEMP' in nc.variables:
                    temp = nc.variables['TEMP'][:]
                    if not np.ma.is_masked(temp):
                        ocean_data['temperature'] = temp.compressed().tolist()
                
                # Salinity
                if 'PSAL' in nc.variables:
                    psal = nc.variables['PSAL'][:]
                    if not np.ma.is_masked(psal):
                        ocean_data['salinity'] = psal.compressed().tolist()
                
                profile['ocean_data'] = ocean_data
                profile['file_path'] = nc_file_path
                
                # Basic validation
                if (profile.get('latitude') is None or 
                    profile.get('longitude') is None or
                    abs(profile.get('latitude', 999)) > 90 or
                    abs(profile.get('longitude', 999)) > 180):
                    return None
                
                return profile
                
        except Exception as e:
            logger.debug(f"Failed to extract from {nc_file_path}: {e}")
            return None
    
    def batch_insert_profiles(self, profiles: List[Dict[str, Any]]):
        """Insert batch of profiles into database"""
        if not profiles:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Prepare data for insertion
            insert_data = []
            for profile in profiles:
                insert_data.append((
                    profile.get('latitude'),
                    profile.get('longitude'),
                    profile.get('date'),
                    profile.get('data_centre', 'Unknown')[:100],  # institution
                    profile.get('platform_number', 'Unknown')[:50],
                    1,  # position_qc
                    json.dumps(profile.get('ocean_data', {})),
                    profile.get('file_path'),
                    profile.get('wmo_inst_type', '')[:50],
                    profile.get('project_name', '')[:100],
                    profile.get('data_centre', '')[:50]
                ))
            
            # Batch insert
            insert_query = """
            INSERT INTO argo_profiles (
                latitude, longitude, date, institution, platform_number,
                position_qc, ocean_data, file_path, wmo_inst_type, project_name, data_centre
            ) VALUES %s
            """
            
            execute_values(cursor, insert_query, insert_data, page_size=1000)
            conn.commit()
            
            inserted_count = len(insert_data)
            conn.close()
            return inserted_count
            
        except Exception as e:
            logger.error(f"Batch insert failed: {e}")
            conn.rollback()
            conn.close()
            return 0
    
    def extract_all_profiles(self, max_files: Optional[int] = None, sample_rate: int = 1):
        """
        Extract all ARGO profiles from NetCDF files
        
        Args:
            max_files: Maximum number of files to process (None for all)
            sample_rate: Process every Nth file (1 for all files, 10 for every 10th file)
        """
        logger.info(f" Starting ARGO NetCDF extraction")
        logger.info(f"Sample rate: 1/{sample_rate} files")
        
        # Create fresh table
        self.create_table()
        
        # Find all NetCDF files
        nc_pattern = os.path.join("gadr", "data", "indian", "**", "*.nc")
        all_nc_files = glob.glob(nc_pattern, recursive=True)
        
        # Apply sampling
        nc_files = all_nc_files[::sample_rate]
        
        if max_files:
            nc_files = nc_files[:max_files]
        
        total_files = len(nc_files)
        logger.info(f" Found {len(all_nc_files):,} total NetCDF files")
        logger.info(f" Processing {total_files:,} files (sample rate: 1/{sample_rate})")
        
        # Process in batches
        batch_size = 100
        profiles_batch = []
        
        start_time = time.time()
        
        with tqdm(total=total_files, desc="Extracting profiles") as pbar:
            for i, nc_file in enumerate(nc_files):
                # Extract profile
                profile = self.extract_profile_from_nc(nc_file)
                
                if profile:
                    profiles_batch.append(profile)
                    self.stats['processed'] += 1
                else:
                    self.stats['skipped'] += 1
                
                # Insert batch when full
                if len(profiles_batch) >= batch_size:
                    inserted = self.batch_insert_profiles(profiles_batch)
                    self.stats['inserted'] += inserted
                    profiles_batch = []
                    
                    # Progress update
                    if (i + 1) % 1000 == 0:
                        elapsed = time.time() - start_time
                        rate = (i + 1) / elapsed if elapsed > 0 else 0
                        logger.info(f"Progress: {i+1:,}/{total_files:,} files, {self.stats['inserted']:,} profiles inserted ({rate:.1f} files/sec)")
                
                pbar.update(1)
        
        # Insert remaining profiles
        if profiles_batch:
            inserted = self.batch_insert_profiles(profiles_batch)
            self.stats['inserted'] += inserted
        
        elapsed_time = time.time() - start_time
        
        # Final statistics
        logger.info(f" ARGO extraction complete!")
        logger.info(f" Files processed: {self.stats['processed']:,}")
        logger.info(f" Files skipped: {self.stats['skipped']:,}")
        logger.info(f" Profiles inserted: {self.stats['inserted']:,}")
        logger.info(f" Time taken: {elapsed_time:.1f} seconds")
        logger.info(f" Speed: {self.stats['processed']/elapsed_time:.1f} files/sec")
        
        return self.stats['inserted']

def main():
    from datetime import timedelta
    
    extractor = ARGONetCDFExtractor()
    
    # Extract with sampling for reasonable processing time
    # Process every 100th file to get a good representative sample
    result = extractor.extract_all_profiles(max_files=5000, sample_rate=50)
    
    print(f"\n SUCCESS: {result:,} ARGO profiles extracted from real NetCDF data!")

if __name__ == "__main__":
    main()

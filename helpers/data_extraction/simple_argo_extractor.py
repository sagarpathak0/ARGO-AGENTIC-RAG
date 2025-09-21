#!/usr/bin/env python3
"""
Simple and Efficient ARGO Data Extractor
Extracts essential data from NetCDF files for the RAG system
"""
import os
import sys
import glob
import netCDF4 as nc
import psycopg2
import json
from datetime import datetime
from tqdm import tqdm

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
from config.database import get_database_url

class SimpleArgoExtractor:
    def __init__(self):
        self.db_url = get_database_url()
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def extract_netcdf_data(self, file_path):
        """Extract essential data from a NetCDF file"""
        try:
            with nc.Dataset(file_path, 'r') as dataset:
                # Extract basic profile information
                data = {}
                
                # Geographic coordinates
                if 'LATITUDE' in dataset.variables:
                    data['latitude'] = float(dataset.variables['LATITUDE'][0]) if len(dataset.variables['LATITUDE']) > 0 else None
                if 'LONGITUDE' in dataset.variables:
                    data['longitude'] = float(dataset.variables['LONGITUDE'][0]) if len(dataset.variables['LONGITUDE']) > 0 else None
                
                # Date information
                if 'JULD' in dataset.variables:
                    juld = dataset.variables['JULD'][0] if len(dataset.variables['JULD']) > 0 else None
                    if juld and juld != nc.default_fillvals['f8']:
                        # Convert Julian day to datetime (ARGO reference: 1950-01-01)
                        try:
                            ref_date = datetime(1950, 1, 1)
                            profile_date = ref_date + timedelta(days=float(juld))
                            data['date'] = profile_date.date()
                        except:
                            data['date'] = None
                    else:
                        data['date'] = None
                
                # Institution
                if 'INSTITUTION' in dataset.variables:
                    try:
                        inst = dataset.variables['INSTITUTION'][:].tobytes().decode('utf-8').strip()
                        data['institution'] = inst if inst else None
                    except:
                        data['institution'] = None
                
                # Platform number
                if 'PLATFORM_NUMBER' in dataset.variables:
                    try:
                        platform = dataset.variables['PLATFORM_NUMBER'][:].tobytes().decode('utf-8').strip()
                        data['platform_number'] = platform if platform else None
                    except:
                        data['platform_number'] = None
                
                # Position QC
                if 'POSITION_QC' in dataset.variables:
                    try:
                        qc = dataset.variables['POSITION_QC'][:].tobytes().decode('utf-8').strip()
                        data['position_qc'] = qc if qc else None
                    except:
                        data['position_qc'] = None
                
                # Ocean data (simplified)
                ocean_data = {}
                
                # Temperature
                if 'TEMP' in dataset.variables:
                    temp = dataset.variables['TEMP'][:]
                    if hasattr(temp, 'mask'):
                        temp_values = temp.compressed().tolist()[:50]  # Limit to first 50 points
                    else:
                        temp_values = temp.flatten().tolist()[:50]
                    ocean_data['temperature'] = temp_values
                
                # Salinity
                if 'PSAL' in dataset.variables:
                    psal = dataset.variables['PSAL'][:]
                    if hasattr(psal, 'mask'):
                        psal_values = psal.compressed().tolist()[:50]
                    else:
                        psal_values = psal.flatten().tolist()[:50]
                    ocean_data['salinity'] = psal_values
                
                # Pressure
                if 'PRES' in dataset.variables:
                    pres = dataset.variables['PRES'][:]
                    if hasattr(pres, 'mask'):
                        pres_values = pres.compressed().tolist()[:50]
                    else:
                        pres_values = pres.flatten().tolist()[:50]
                    ocean_data['pressure'] = pres_values
                
                data['ocean_data'] = ocean_data
                data['file_path'] = file_path
                
                return data
                
        except Exception as e:
            print(f"Error extracting {file_path}: {e}")
            return None
    
    def insert_profile(self, profile_data):
        """Insert a single profile into the database"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            insert_query = """
            INSERT INTO argo_profiles 
            (latitude, longitude, date, institution, platform_number, position_qc, ocean_data, file_path)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING profile_id
            """
            
            cursor.execute(insert_query, (
                profile_data.get('latitude'),
                profile_data.get('longitude'), 
                profile_data.get('date'),
                profile_data.get('institution'),
                profile_data.get('platform_number'),
                profile_data.get('position_qc'),
                json.dumps(profile_data.get('ocean_data', {})),
                profile_data.get('file_path')
            ))
            
            profile_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            return profile_id
            
        except Exception as e:
            print(f"Database insert error: {e}")
            if conn:
                conn.close()
            return None
    
    def process_directory(self, data_dir, max_files=1000):
        """Process NetCDF files in a directory"""
        # Find all NetCDF files
        pattern = os.path.join(data_dir, "**", "*.nc")
        nc_files = glob.glob(pattern, recursive=True)
        
        if max_files:
            nc_files = nc_files[:max_files]
        
        print(f"Found {len(nc_files)} NetCDF files to process")
        
        successful = 0
        failed = 0
        
        for file_path in tqdm(nc_files, desc="Processing files"):
            profile_data = self.extract_netcdf_data(file_path)
            
            if profile_data:
                profile_id = self.insert_profile(profile_data)
                if profile_id:
                    successful += 1
                else:
                    failed += 1
            else:
                failed += 1
        
        print(f"Processing complete: {successful} successful, {failed} failed")
        return successful

def main():
    """Run the simple extractor"""
    from datetime import timedelta
    
    extractor = SimpleArgoExtractor()
    
    # Process a subset of data for testing
    data_dir = "gadr/data/indian"
    success_count = extractor.process_directory(data_dir, max_files=100)
    
    print(f"Successfully processed {success_count} files")

if __name__ == "__main__":
    main()

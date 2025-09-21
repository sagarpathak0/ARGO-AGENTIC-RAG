#!/usr/bin/env python3
"""
Simple Mock Data Generator for ARGO Profiles
Creates sample oceanographic data for testing the RAG system
"""
import psycopg2
import json
import random
from datetime import datetime, date, timedelta
from tqdm import tqdm
import sys
import os

# Add config to path
sys.path.append(os.path.join(os.path.dirname(__file__)))
from config.database import get_database_url

class MockArgoGenerator:
    def __init__(self):
        self.db_url = get_database_url()
        
        # Sample institutions and platforms
        self.institutions = [
            'SCRIPPS_INSTITUTION_OCEANOGRAPHY',
            'WHOI', 'CSIRO', 'IFREMER', 'JMA',
            'INDIAN_OCEAN_RESEARCH', 'NEMO_FLOATS',
            'OCEANOGRAPHIC_SURVEY_INDIA'
        ]
        
        self.platforms = [
            'APEX_001', 'NOVA_002', 'SOLO_003', 'ARVOR_004',
            'PROVOR_005', 'NAVIS_006', 'DEEP_007'
        ]
        
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    def generate_ocean_data(self):
        """Generate realistic ocean measurement data"""
        depth_levels = random.randint(20, 100)
        ocean_data = {
            'temperature': [],
            'salinity': [],
            'pressure': []
        }
        
        for i in range(depth_levels):
            depth = i * random.uniform(5, 15)  # Depth in meters
            
            # Temperature decreases with depth
            temp = 25 - (depth * 0.01) + random.uniform(-2, 2)
            temp = max(temp, 2)  # Minimum temperature
            
            # Salinity varies
            salinity = 34.5 + random.uniform(-1, 1)
            
            # Pressure increases with depth
            pressure = depth * 0.1 + random.uniform(-0.1, 0.1)
            
            ocean_data['temperature'].append(round(temp, 2))
            ocean_data['salinity'].append(round(salinity, 2))
            ocean_data['pressure'].append(round(pressure, 2))
        
        return ocean_data
    
    def generate_profile(self):
        """Generate a single ARGO profile"""
        # Indian Ocean region coordinates
        latitude = random.uniform(-30, 30)  # Indian Ocean latitude range
        longitude = random.uniform(30, 120)  # Indian Ocean longitude range
        
        # Random date in the last 5 years
        start_date = date(2019, 1, 1)
        end_date = date(2024, 12, 31)
        random_days = random.randint(0, (end_date - start_date).days)
        profile_date = start_date + timedelta(days=random_days)
        
        profile = {
            'latitude': round(latitude, 4),
            'longitude': round(longitude, 4),
            'date': profile_date,
            'institution': random.choice(self.institutions),
            'platform_number': random.choice(self.platforms),
            'position_qc': random.choice(['1', '2', '8']),  # QC flags
            'ocean_data': self.generate_ocean_data(),
            'file_path': f'mock_data/profile_{random.randint(1000, 9999)}.nc'
        }
        
        return profile
    
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
                profile_data['latitude'],
                profile_data['longitude'], 
                profile_data['date'],
                profile_data['institution'],
                profile_data['platform_number'],
                profile_data['position_qc'],
                json.dumps(profile_data['ocean_data']),
                profile_data['file_path']
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
    
    def generate_mock_data(self, num_profiles=500):
        """Generate mock ARGO profiles"""
        print(f"Generating {num_profiles} mock ARGO profiles...")
        
        successful = 0
        failed = 0
        
        for i in tqdm(range(num_profiles), desc="Generating profiles"):
            profile_data = self.generate_profile()
            
            profile_id = self.insert_profile(profile_data)
            if profile_id:
                successful += 1
            else:
                failed += 1
        
        print(f"Generation complete: {successful} successful, {failed} failed")
        return successful

def main():
    """Generate mock ARGO data"""
    generator = MockArgoGenerator()
    
    # Generate sample data
    success_count = generator.generate_mock_data(num_profiles=250)
    
    print(f"Successfully generated {success_count} profiles")
    print("Ready for embedding generation!")

if __name__ == "__main__":
    main()

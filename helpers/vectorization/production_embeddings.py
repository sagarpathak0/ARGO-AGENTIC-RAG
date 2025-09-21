#!/usr/bin/env python3
"""
Fixed Embedding Generator - Full Production Version
"""
import os
import logging
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from tqdm import tqdm
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class ProductionEmbeddingGenerator:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.embedding_dim = 384
        self.model = None
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'sslmode': os.getenv('DB_SSL_MODE', 'require')
        }
        logger.info(f" Production Embedding Generator initialized: {model_name}")
        
    def _load_model(self):
        if self.model is None:
            logger.info(" Loading sentence transformer model...")
            self.model = SentenceTransformer(self.model_name)
            logger.info(" Model loaded successfully")
        return self.model
    
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def get_stats(self):
        """Get current statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM argo_profiles")
        total_profiles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT profile_id) FROM profile_embeddings")
        embedded_profiles = cursor.fetchone()[0]
        
        conn.close()
        return total_profiles, embedded_profiles
    
    def create_profile_text(self, profile):
        """Create comprehensive text from profile data"""
        parts = []
        
        if profile.get('latitude') and profile.get('longitude'):
            parts.append(f"Location: {profile['latitude']:.3f}N, {profile['longitude']:.3f}E")
        
        if profile.get('date'):
            parts.append(f"Date: {profile['date']}")
        
        if profile.get('institution'):
            parts.append(f"Institution: {profile['institution']}")
            
        if profile.get('platform_number'):
            parts.append(f"Platform: {profile['platform_number']}")
        
        # Add ocean data summary
        if profile.get('ocean_data'):
            try:
                ocean_data = profile['ocean_data']
                if isinstance(ocean_data, str):
                    ocean_data = json.loads(ocean_data)
                depths = ocean_data.get('depths', [])
                temps = ocean_data.get('temperatures', [])
                if depths and temps:
                    parts.append(f"Ocean data: {len(depths)} depth measurements from {min(depths)}m to {max(depths)}m")
                    parts.append(f"Temperature range: {min(temps):.1f}C to {max(temps):.1f}C")
            except:
                parts.append("Ocean measurement data available")
        
        return " | ".join(parts)
    
    def fetch_unprocessed_profiles(self, batch_size=100):
        """Fetch profiles that don't have embeddings yet"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT ap.profile_id, ap.latitude, ap.longitude, ap.date, 
               ap.institution, ap.platform_number, ap.ocean_data
        FROM argo_profiles ap
        LEFT JOIN profile_embeddings pe ON CAST(ap.profile_id AS VARCHAR) = pe.profile_id
        WHERE pe.profile_id IS NULL
        ORDER BY ap.profile_id
        LIMIT %s
        """
        
        cursor.execute(query, (batch_size,))
        columns = [desc[0] for desc in cursor.description]
        
        profiles = []
        for row in cursor.fetchall():
            profile = dict(zip(columns, row))
            profiles.append(profile)
        
        conn.close()
        return profiles
    
    def store_embedding(self, profile_id, text, embedding):
        """Store single embedding (reliable method)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO profile_embeddings (profile_id, content_type, content_text, embedding)
                VALUES (%s, %s, %s, %s)
            """, (
                str(profile_id),
                'full_metadata',
                text[:1000],  # Truncate if needed
                embedding.tolist()
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Storage failed for profile {profile_id}: {e}")
            conn.rollback()
            conn.close()
            return False
    
    def generate_embeddings_production(self, max_profiles=None):
        """Full production embedding generation"""
        logger.info(" Starting FULL PRODUCTION embedding generation")
        
        # Load model
        model = self._load_model()
        
        # Get initial stats
        total_profiles, embedded_profiles = self.get_stats()
        remaining = total_profiles - embedded_profiles
        
        logger.info(f" Total profiles: {total_profiles:,}")
        logger.info(f" Already embedded: {embedded_profiles:,}")
        logger.info(f" Remaining to process: {remaining:,}")
        
        if max_profiles:
            remaining = min(remaining, max_profiles)
            logger.info(f" Limited to: {remaining:,} profiles")
        
        if remaining == 0:
            logger.info(" All profiles already have embeddings!")
            return embedded_profiles
        
        # Process in batches
        processed = 0
        errors = 0
        batch_size = 50  # Smaller batches for reliability
        
        start_time = time.time()
        
        while processed < remaining:
            # Fetch batch
            profiles = self.fetch_unprocessed_profiles(batch_size)
            
            if not profiles:
                logger.info(" No more profiles to process")
                break
            
            logger.info(f" Processing batch of {len(profiles)} profiles...")
            
            # Process each profile
            batch_success = 0
            for profile in profiles:
                try:
                    # Create text
                    text = self.create_profile_text(profile)
                    
                    # Generate embedding
                    embedding = model.encode(text, convert_to_numpy=True).astype(np.float32)
                    
                    # Store embedding
                    if self.store_embedding(profile['profile_id'], text, embedding):
                        batch_success += 1
                    else:
                        errors += 1
                    
                    processed += 1
                    
                    # Progress update
                    if processed % 100 == 0:
                        elapsed = time.time() - start_time
                        rate = processed / elapsed if elapsed > 0 else 0
                        logger.info(f" Progress: {processed:,}/{remaining:,} ({processed/remaining*100:.1f}%) - {rate:.1f} profiles/sec")
                    
                    if max_profiles and processed >= max_profiles:
                        break
                        
                except Exception as e:
                    logger.error(f" Failed to process profile {profile.get('profile_id')}: {e}")
                    errors += 1
                    processed += 1
            
            logger.info(f" Batch complete: {batch_success}/{len(profiles)} successful")
            
            # Small delay to avoid overwhelming the system
            time.sleep(0.1)
        
        elapsed_time = time.time() - start_time
        rate = processed / elapsed_time if elapsed_time > 0 else 0
        
        # Final stats
        final_total, final_embedded = self.get_stats()
        
        logger.info(f" Production embedding generation COMPLETE!")
        logger.info(f" Processed: {processed:,} profiles")
        logger.info(f" Errors: {errors:,}")
        logger.info(f" Final embedded count: {final_embedded:,}")
        logger.info(f" Time taken: {elapsed_time:.1f} seconds")
        logger.info(f" Average speed: {rate:.1f} profiles/sec")
        
        return final_embedded

def main():
    generator = ProductionEmbeddingGenerator()
    
    # Run full production embedding generation
    result = generator.generate_embeddings_production()
    
    print(f"\n PRODUCTION COMPLETE: {result:,} profiles now have embeddings!")

if __name__ == "__main__":
    main()

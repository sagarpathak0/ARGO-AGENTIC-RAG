#!/usr/bin/env python3
"""
ULTRA-FAST VECTORIZATION SYSTEM
Processes 213,853 ARGO profiles with massive batch processing and parallel operations
"""
import os
import json
import time
import logging
import numpy as np
from typing import List, Dict, Any, Tuple
import psycopg2
from psycopg2.extras import execute_values
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import threading
from queue import Queue
import uuid

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class UltraFastVectorizer:
    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'sslmode': os.getenv('DB_SSL_MODE', 'require')
        }
        self.model = None
        
    def get_connection(self):
        return psycopg2.connect(**self.db_config)
    
    def load_model(self):
        """Load sentence transformer model once"""
        logger.info(" Loading sentence transformer model...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info(" Model loaded successfully")
    
    def create_content_text(self, profile: Dict[str, Any]) -> str:
        """Create optimized content text for embedding"""
        ocean_data = profile.get('ocean_data', {})
        
        # Build content efficiently
        parts = [
            f"Oceanographic profile at latitude {profile['latitude']:.3f}, longitude {profile['longitude']:.3f}",
            f"recorded on {profile['date']} by {profile['institution']}"
        ]
        
        # Add ocean measurements summary
        if ocean_data:
            measurements = []
            for param, values in ocean_data.items():
                if values and len(values) > 0:
                    avg_val = np.mean(values[:10])  # Use first 10 values for speed
                    measurements.append(f"{param}: {avg_val:.2f}")
            
            if measurements:
                parts.append(f"Measurements: {', '.join(measurements)}")
        
        return ". ".join(parts)
    
    def bulk_insert_embeddings(self, embeddings_data: List[Tuple]) -> int:
        """Ultra-fast bulk insert for embeddings"""
        if not embeddings_data:
            return 0
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
            INSERT INTO profile_embeddings (
                id, profile_id, content_type, content_text, embedding
            ) VALUES %s
            """
            
            execute_values(
                cursor, query, embeddings_data,
                template=None, page_size=5000  # Large page size for speed
            )
            
            conn.commit()
            inserted = len(embeddings_data)
            conn.close()
            return inserted
            
        except Exception as e:
            logger.error(f"Bulk insert failed: {e}")
            conn.rollback()
            conn.close()
            return 0
    
    def process_mega_batch(self, profiles: List[Dict[str, Any]]) -> int:
        """Process large batch of profiles at once"""
        if not profiles:
            return 0
        
        # Create content texts
        content_texts = []
        for profile in profiles:
            content_text = self.create_content_text(profile)
            content_texts.append(content_text)
        
        # Generate embeddings in one big batch
        logger.info(f" Generating {len(content_texts)} embeddings...")
        embeddings = self.model.encode(
            content_texts,
            batch_size=512,  # Large batch size
            show_progress_bar=True,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
        
        # Prepare data for bulk insert
        embeddings_data = []
        for i, profile in enumerate(profiles):
            embedding_vector = embeddings[i].tolist()
            
            embeddings_data.append((
                str(uuid.uuid4()),
                str(profile['profile_id']),
                'oceanographic_profile',
                content_texts[i],
                embedding_vector
            ))
        
        # Bulk insert
        logger.info(f" Bulk inserting {len(embeddings_data)} embeddings...")
        inserted = self.bulk_insert_embeddings(embeddings_data)
        
        return inserted
    
    def get_pending_profiles(self, limit: int = None) -> List[Dict[str, Any]]:
        """Get profiles that need embeddings"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT ap.profile_id, ap.latitude, ap.longitude, ap.date, 
               ap.institution, ap.platform_number, ap.ocean_data
        FROM argo_profiles ap
        LEFT JOIN profile_embeddings pe ON ap.profile_id::text = pe.profile_id
        WHERE pe.profile_id IS NULL
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query)
        
        profiles = []
        for row in cursor.fetchall():
            profiles.append({
                'profile_id': row[0],
                'latitude': row[1],
                'longitude': row[2],
                'date': row[3],
                'institution': row[4],
                'platform_number': row[5],
                'ocean_data': row[6] if row[6] else {}
            })
        
        conn.close()
        return profiles
    
    def vectorize_all_ultra_fast(self):
        """Ultra-fast vectorization of entire dataset"""
        logger.info(" ULTRA-FAST VECTORIZATION STARTING")
        
        # Load model once
        self.load_model()
        
        # Get total count
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM argo_profiles")
        total_profiles = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM profile_embeddings")
        existing_embeddings = cursor.fetchone()[0]
        conn.close()
        
        remaining = total_profiles - existing_embeddings
        
        logger.info(f" Total profiles: {total_profiles:,}")
        logger.info(f" Existing embeddings: {existing_embeddings:,}")
        logger.info(f" Remaining to process: {remaining:,}")
        
        if remaining == 0:
            logger.info(" All profiles already have embeddings!")
            return
        
        # Process in mega batches
        mega_batch_size = 10000  # Process 10K at a time
        processed = 0
        start_time = time.time()
        
        while True:
            # Get next mega batch
            logger.info(f" Loading next batch of {mega_batch_size:,} profiles...")
            profiles = self.get_pending_profiles(limit=mega_batch_size)
            
            if not profiles:
                logger.info(" All profiles processed!")
                break
            
            batch_start = time.time()
            
            # Process mega batch
            inserted = self.process_mega_batch(profiles)
            processed += inserted
            
            batch_time = time.time() - batch_start
            elapsed_total = time.time() - start_time
            
            # Statistics
            rate = processed / elapsed_total if elapsed_total > 0 else 0
            progress = (processed / remaining) * 100
            
            logger.info(f" Batch complete: {inserted:,} embeddings in {batch_time:.1f}s")
            logger.info(f" Progress: {processed:,}/{remaining:,} ({progress:.1f}%)")
            logger.info(f" Overall rate: {rate:.1f} embeddings/sec")
            
            # Estimate time remaining
            if rate > 0:
                remaining_count = remaining - processed
                eta_seconds = remaining_count / rate
                eta_minutes = eta_seconds / 60
                logger.info(f" ETA: {eta_minutes:.1f} minutes")
        
        # Final statistics
        total_time = time.time() - start_time
        final_rate = processed / total_time if total_time > 0 else 0
        
        logger.info(f" ULTRA-FAST VECTORIZATION COMPLETE!")
        logger.info(f" Total processed: {processed:,} embeddings")
        logger.info(f" Total time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
        logger.info(f" Average rate: {final_rate:.1f} embeddings/sec")
        
        return processed

def main():
    vectorizer = UltraFastVectorizer()
    
    # Start ultra-fast vectorization
    total_vectorized = vectorizer.vectorize_all_ultra_fast()
    
    print(f"\n VECTORIZATION COMPLETE: {total_vectorized:,} embeddings generated!")
    print(f" Full ARGO dataset is now vectorized and ready for semantic search!")

if __name__ == "__main__":
    main()

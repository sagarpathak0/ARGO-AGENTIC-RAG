#!/usr/bin/env python3
"""
Open-Source Vector Embedding Generation Pipeline for ARGO Oceanographic Data - FIXED VERSION
"""
import os
import sys
import logging
import json
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np
from tqdm import tqdm
import psycopg2
from psycopg2.extras import execute_batch
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
load_dotenv()

class EmbeddingGenerator:
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        self.model_name = model_name
        self.embedding_dim = 384
        self.model = None
        self.db_config = self._get_db_config()
        logger.info(f"Initializing EmbeddingGenerator with model: {model_name}")
        
    def _get_db_config(self) -> Dict[str, str]:
        return {
            'host': os.getenv('DB_HOST'),
            'port': os.getenv('DB_PORT'),
            'database': os.getenv('DB_NAME'),
            'user': os.getenv('DB_USER'),
            'password': os.getenv('DB_PASSWORD'),
            'sslmode': os.getenv('DB_SSL_MODE', 'require')
        }
    
    def _load_model(self) -> SentenceTransformer:
        if self.model is None:
            logger.info(f"Loading sentence transformer model: {self.model_name}")
            try:
                self.model = SentenceTransformer(self.model_name)
                logger.info("Model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load model: {e}")
                raise
        return self.model
    
    def get_db_connection(self) -> Optional[psycopg2.extensions.connection]:
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return None
    
    def get_profile_count(self) -> int:
        conn = self.get_db_connection()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM argo_profiles")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get profile count: {e}")
            if conn:
                conn.close()
            return 0
    
    def get_existing_embeddings_count(self) -> int:
        conn = self.get_db_connection()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(DISTINCT profile_id) FROM profile_embeddings")
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except Exception as e:
            logger.error(f"Failed to get existing embeddings count: {e}")
            if conn:
                conn.close()
            return 0
    
    def create_profile_text(self, profile: Dict[str, Any], embedding_type: str = 'full_metadata') -> str:
        if embedding_type == 'full_metadata':
            parts = []
            if profile.get('latitude') and profile.get('longitude'):
                parts.append(f"Location: {profile['latitude']:.3f}N, {profile['longitude']:.3f}E")
            if profile.get('date'):
                parts.append(f"Date: {profile['date']}")
            if profile.get('institution'):
                parts.append(f"Institution: {profile['institution']}")
            if profile.get('platform_number'):
                parts.append(f"Platform: {profile['platform_number']}")
            if profile.get('ocean_data'):
                ocean_summary = f"Ocean measurements with {len(profile['ocean_data'].get('depths', []))} data points"
                parts.append(ocean_summary)
            return " | ".join(parts)
        elif embedding_type == 'location':
            parts = []
            if profile.get('latitude') and profile.get('longitude'):
                parts.append(f"{profile['latitude']:.3f}N {profile['longitude']:.3f}E")
            if profile.get('date'):
                parts.append(f"{profile['date']}")
            return " ".join(parts)
        elif embedding_type == 'institution':
            parts = []
            if profile.get('institution'):
                parts.append(profile['institution'])
            if profile.get('platform_number'):
                parts.append(f"Platform {profile['platform_number']}")
            return " ".join(parts)
        else:
            return f"ARGO Profile {profile.get('profile_id', 'Unknown')}"
    
    def generate_embedding(self, text: str) -> np.ndarray:
        model = self._load_model()
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.astype(np.float32)
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def fetch_profiles_batch(self, offset: int, batch_size: int) -> List[Dict[str, Any]]:
        conn = self.get_db_connection()
        if not conn:
            return []
        try:
            cursor = conn.cursor()
            # FIXED: Cast profile_id to VARCHAR for proper JOIN
            query = """
            SELECT 
                ap.profile_id,
                ap.latitude,
                ap.longitude,
                ap.date,
                ap.institution,
                ap.platform_number,
                ap.position_qc,
                ap.ocean_data
            FROM argo_profiles ap
            LEFT JOIN profile_embeddings pe ON CAST(ap.profile_id AS VARCHAR) = pe.profile_id
            WHERE pe.profile_id IS NULL
            ORDER BY ap.profile_id
            LIMIT %s OFFSET %s
            """
            
            cursor.execute(query, (batch_size, offset))
            columns = [desc[0] for desc in cursor.description]
            
            profiles = []
            for row in cursor.fetchall():
                profile = dict(zip(columns, row))
                profiles.append(profile)
            
            conn.close()
            return profiles
        except Exception as e:
            logger.error(f"Failed to fetch profiles batch: {e}")
            if conn:
                conn.close()
            return []
    
    def store_embeddings_batch(self, embeddings_data: List[Dict[str, Any]]) -> int:
        conn = self.get_db_connection()
        if not conn:
            return 0
        try:
            cursor = conn.cursor()
            
            # Use the actual schema of profile_embeddings table
            insert_query = """
            INSERT INTO profile_embeddings (
                profile_id, content_type, content_text, embedding
            ) VALUES %s
            """
            
            values = []
            for data in embeddings_data:
                # Create simple content text
                content_text = f"ARGO Profile {data['profile_id']} - {data['embedding_type']}"
                if 'source_text' in data:
                    content_text = data['source_text'][:1000]  # Truncate if needed
                
                values.append((
                    str(data['profile_id']),  # Convert to string
                    data['embedding_type'],
                    content_text,
                    data['embedding_vector'].tolist()  # Convert to list
                ))
            
            execute_batch(cursor, insert_query, values, page_size=100)
            conn.commit()
            
            stored_count = len(values)
            conn.close()
            logger.info(f"Stored {stored_count} embeddings successfully")
            return stored_count
            
        except Exception as e:
            logger.error(f"Failed to store embeddings batch: {e}")
            if conn:
                conn.rollback()
                conn.close()
            return 0
    
    def generate_embeddings(self, batch_size: int = 100, max_profiles: Optional[int] = None, embedding_types: List[str] = ['full_metadata']) -> int:
        logger.info("Starting embedding generation process...")
        logger.info(f"Model: {self.model_name} (Dimensions: {self.embedding_dim})")
        logger.info(f"Embedding types: {embedding_types}")
        
        self._load_model()
        
        total_profiles = self.get_profile_count()
        existing_embeddings = self.get_existing_embeddings_count()
        
        logger.info(f"Total profiles available: {total_profiles:,}")
        logger.info(f"Existing embeddings: {existing_embeddings:,}")
        
        if max_profiles:
            total_profiles = min(total_profiles, max_profiles)
            logger.info(f"Limited to: {total_profiles:,} profiles")
        
        total_embeddings_generated = 0
        total_profiles_processed = 0
        offset = 0
        
        pbar = tqdm(total=total_profiles, desc="Generating embeddings")
        
        try:
            while total_profiles_processed < total_profiles:
                profiles_batch = self.fetch_profiles_batch(offset, batch_size)
                
                if not profiles_batch:
                    logger.info("No more profiles to process")
                    break
                
                embeddings_data = []
                
                for profile in profiles_batch:
                    if max_profiles and total_profiles_processed >= max_profiles:
                        break
                    
                    for embedding_type in embedding_types:
                        try:
                            text = self.create_profile_text(profile, embedding_type)
                            
                            if not text.strip():
                                logger.warning(f"Empty text for profile {profile.get('profile_id')}")
                                continue
                            
                            embedding = self.generate_embedding(text)
                            
                            embedding_data = {
                                'profile_id': profile['profile_id'],
                                'embedding_type': embedding_type,
                                'embedding_vector': embedding,
                                'source_text': text
                            }
                            
                            embeddings_data.append(embedding_data)
                            
                        except Exception as e:
                            logger.error(f"Failed to generate embedding for profile {profile.get('profile_id')}: {e}")
                            continue
                    
                    total_profiles_processed += 1
                    pbar.update(1)
                
                if embeddings_data:
                    stored_count = self.store_embeddings_batch(embeddings_data)
                    total_embeddings_generated += stored_count
                    
                    logger.info(f"Batch complete: {len(profiles_batch)} profiles, {stored_count} embeddings stored")
                
                offset += batch_size
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            logger.info("Embedding generation interrupted by user")
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
        finally:
            pbar.close()
        
        logger.info(f"Embedding generation complete!")
        logger.info(f"Total profiles processed: {total_profiles_processed:,}")
        logger.info(f"Total embeddings generated: {total_embeddings_generated:,}")
        
        return total_embeddings_generated

def main():
    generator = EmbeddingGenerator()
    success_count = generator.generate_embeddings(batch_size=50, embedding_types=['full_metadata'])
    print(f"Successfully generated {success_count} embeddings")

if __name__ == "__main__":
    main()

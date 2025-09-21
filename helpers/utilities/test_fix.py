def store_embeddings_batch(self, embeddings_data: List[Dict[str, Any]]) -> int:
    conn = self.get_db_connection()
    if not conn:
        return 0
    try:
        cursor = conn.cursor()
        
        # Simple individual inserts to avoid formatting issues
        for data in embeddings_data:
            content_text = f"ARGO Profile {data['profile_id']} - {data['embedding_type']}"
            if 'source_text' in data:
                content_text = data['source_text'][:1000]
            
            cursor.execute("""
                INSERT INTO profile_embeddings (profile_id, content_type, content_text, embedding)
                VALUES (%s, %s, %s, %s)
            """, (
                str(data['profile_id']),
                data['embedding_type'],
                content_text,
                data['embedding_vector'].tolist()
            ))
        
        conn.commit()
        stored_count = len(embeddings_data)
        conn.close()
        logger.info(f"Stored {stored_count} embeddings successfully")
        return stored_count
        
    except Exception as e:
        logger.error(f"Failed to store embeddings batch: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return 0

# Test directly
import sys
sys.path.append('backend')
from tools.embedding_generator import EmbeddingGenerator

generator = EmbeddingGenerator()
profiles = generator.fetch_profiles_batch(0, 1)
if profiles:
    profile = profiles[0]
    text = generator.create_profile_text(profile)
    embedding = generator.generate_embedding(text)
    
    test_data = [{
        'profile_id': profile['profile_id'],
        'embedding_type': 'test',
        'embedding_vector': embedding,
        'source_text': text
    }]
    
    result = generator.store_embeddings_batch(test_data)
    print(f'Test result: {result}')
else:
    print('No profiles found')

#!/usr/bin/env python3
"""
Test script for open-source embedding generation pipeline
No API keys required - uses sentence-transformers locally
"""
import sys
import os
from dotenv import load_dotenv

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from tools.embedding_generator import EmbeddingGenerator

def main():
    """Test the open-source embedding generation pipeline"""
    
    # Load environment variables
    load_dotenv()
    
    print(" Testing Open-Source Embedding Generation Pipeline...")
    print(" Using sentence-transformers (no API key required)")
    
    try:
        # Initialize embedding generator with open-source model
        print(" Initializing embedding generator...")
        generator = EmbeddingGenerator(model_name='all-MiniLM-L6-v2')
        print(f" Model: {generator.model_name} (Dimensions: {generator.embedding_dim})")
        
        # Test connection
        print(" Testing database connection...")
        test_conn = generator.get_db_connection()
        if test_conn:
            test_conn.close()
            print(" Database connection successful")
        else:
            print(" Database connection failed")
            return
        
        # Get profile count
        print(" Checking available profiles...")
        profile_count = generator.get_profile_count()
        print(f" Found {profile_count:,} profiles available for embedding")
        
        if profile_count == 0:
            print(" No profiles found. Please run data ingestion first.")
            return
        
        # Check existing embeddings
        existing_count = generator.get_existing_embeddings_count()
        print(f" Existing embeddings: {existing_count:,}")
        
        # Generate embeddings for a small test batch
        print("\n Starting test embedding generation (first 3 profiles)...")
        print(" This will download the model on first run (~80MB)")
        
        success_count = generator.generate_embeddings(
            batch_size=3, 
            max_profiles=3,
            embedding_types=['full_metadata']
        )
        
        print(f"\n Successfully generated embeddings for {success_count} profiles")
        
        # Verify embeddings were stored
        final_count = generator.get_existing_embeddings_count()
        print(f" Total embeddings after test: {final_count:,}")
        
        if final_count > existing_count:
            print(" Open-source embedding generation test successful!")
            print(" No API keys required - everything runs locally!")
            
            # Ask if user wants to continue with full generation
            print(f"\n Remaining profiles to process: {profile_count - (final_count // len(['full_metadata'])):,}")
            response = input("Continue with full embedding generation? (y/n): ").lower().strip()
            
            if response == 'y':
                print("\n Starting full embedding generation...")
                total_success = generator.generate_embeddings(
                    embedding_types=['full_metadata', 'location']
                )
                print(f" Total embeddings generated: {total_success:,}")
        else:
            print(" No new embeddings were created. Check the logs for issues.")
            
    except Exception as e:
        print(f" Error during embedding generation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

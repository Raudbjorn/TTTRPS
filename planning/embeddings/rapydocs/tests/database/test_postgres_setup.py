#!/usr/bin/env python3
"""
Test PostgreSQL setup with permission checks and auto-creation
"""

import logging
import sys
from src.database.postgres_embeddings import PostgreSQLEmbeddingsBackend

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_postgres_setup():
    """Test PostgreSQL setup with various scenarios"""
    
    print("=" * 60)
    print("PostgreSQL Embeddings Setup Test")
    print("=" * 60)
    
    # Test connection URLs from environment or defaults
    import os
    
    # Get test database URL from environment or use a safe default
    default_test_url = os.environ.get(
        'TEST_POSTGRES_URL',
        'postgresql://testuser:testpass@localhost/test_embeddings'
    )
    
    test_urls = [
        # Primary test URL from environment
        default_test_url,
        
        # Additional test URL if provided
        os.environ.get('TEST_POSTGRES_URL_2', default_test_url),
    ]
    
    for url in test_urls[:1]:  # Test first URL only for demo
        print(f"\nTesting: {url}")
        print("-" * 40)
        
        try:
            # Initialize backend (will auto-create database if missing)
            backend = PostgreSQLEmbeddingsBackend(
                connection_url=url,
                embedding_dim=768,
                auto_setup=True
            )
            
            # Verify setup
            print("\n📋 Verification Report:")
            report = backend.verify_setup()
            
            print(f"  Database: {report['database']}")
            print(f"  Connection: {'✓' if report['connection'] else '✗'}")
            
            print("\n  Permissions:")
            for perm, has_it in report['permissions'].items():
                status = '✓' if has_it else '✗'
                print(f"    {perm}: {status}")
            
            print("\n  Schema:")
            for item, exists in report['schema'].items():
                status = '✓' if exists else '✗'
                print(f"    {item}: {status}")
            
            if report['issues']:
                print("\n  ⚠️  Issues:")
                for issue in report['issues']:
                    print(f"    - {issue}")
            else:
                print("\n  ✅ No issues detected")
            
            # Test adding documents
            print("\n📝 Testing document operations...")
            
            test_docs = [
                "PostgreSQL is a powerful database",
                "pgvector enables vector similarity search",
                "Embeddings allow semantic search"
            ]
            test_meta = [
                {"type": "database"},
                {"type": "extension"},
                {"type": "feature"}
            ]
            test_ids = ["pg_1", "pg_2", "pg_3"]
            
            backend.add_documents(test_docs, test_meta, test_ids)
            
            # Get stats
            stats = backend.get_stats()
            print(f"\n📊 Database Stats:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
            
            # Test search (will use text search since no embedding function)
            print("\n🔍 Testing search...")
            results = backend.search("database", top_k=2)
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result['score']:.3f}")
                print(f"     Content: {result['content'][:50]}...")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("Test Complete")
    print("=" * 60)

if __name__ == "__main__":
    test_postgres_setup()
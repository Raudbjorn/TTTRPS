#!/usr/bin/env python3
"""Complete test of embeddings creation, persistence, and querying"""

import json
import logging
import os
import sys
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_embeddings_system():
    """Test the complete embeddings workflow"""
    
    try:
        # Import the embeddings factory
        from embeddings_factory import create_embeddings, initialize_database
        
        logger.info("=" * 60)
        logger.info("EMBEDDINGS SYSTEM TEST")
        logger.info("=" * 60)
        
        # Initialize the embeddings system
        logger.info("\n1. Initializing embeddings system...")
        embeddings = initialize_database()
        
        # Get system info
        if hasattr(embeddings, 'get_collection_stats'):
            stats = embeddings.get_collection_stats()
            logger.info(f"   Backend: {stats.get('device', 'unknown')}")
            logger.info(f"   Model: {stats.get('model', 'unknown')}")
            logger.info(f"   Documents: {stats.get('total_documents', 0)}")
            if stats.get('ollama_enabled'):
                logger.info("   ✓ Ollama GPU acceleration enabled")
        
        # Check if we need to populate the database
        doc_count = embeddings.get_collection_stats().get('total_documents', 0) if hasattr(embeddings, 'get_collection_stats') else 0
        
        if doc_count == 0:
            logger.info("\n2. Database is empty. Loading sample data...")
            
            # Create some sample documents if scraped_content.json doesn't exist
            sample_docs = [
                {
                    "content": "Rapyd is a global fintech platform that provides payment infrastructure for businesses worldwide. It offers APIs for accepting payments, sending payouts, and managing foreign exchange.",
                    "metadata": {
                        "title": "What is Rapyd",
                        "url": "https://docs.rapyd.net/intro",
                        "source": "rapyd_docs"
                    }
                },
                {
                    "content": "To make your first API call to Rapyd, you need to obtain API keys from the Client Portal. Use the access key and secret key to sign your requests with HMAC-SHA256 signature.",
                    "metadata": {
                        "title": "Getting Started with Rapyd API",
                        "url": "https://docs.rapyd.net/getting-started",
                        "source": "rapyd_docs"
                    }
                },
                {
                    "content": "Rapyd supports multiple payment methods including credit cards, debit cards, bank transfers, e-wallets, and cash payments. Each country has specific payment methods available.",
                    "metadata": {
                        "title": "Payment Methods",
                        "url": "https://docs.rapyd.net/payment-methods",
                        "source": "rapyd_docs"
                    }
                },
                {
                    "content": "Webhooks are HTTP callbacks that Rapyd sends to your server when certain events occur. You must verify webhook signatures to ensure the authenticity of the webhook.",
                    "metadata": {
                        "title": "Webhooks and Events",
                        "url": "https://docs.rapyd.net/webhooks",
                        "source": "rapyd_docs"
                    }
                },
                {
                    "content": "The Rapyd Collect API allows you to accept payments from customers globally. You can create checkout pages, process payments, and handle refunds through the API.",
                    "metadata": {
                        "title": "Rapyd Collect API",
                        "url": "https://docs.rapyd.net/collect",
                        "source": "rapyd_docs"
                    }
                }
            ]
            
            # Check if scraped_content.json exists
            scraped_file = Path("scraped_content.json")
            if scraped_file.exists():
                logger.info("   Found scraped_content.json, loading real data...")
                with open(scraped_file, 'r') as f:
                    data = json.load(f)
                    
                # Add documents from scraped content
                documents = []
                metadatas = []
                ids = []
                
                for idx, item in enumerate(data[:20]):  # Load first 20 for testing
                    if item.get('content'):
                        documents.append(item['content'])
                        metadatas.append({
                            'url': item.get('url', ''),
                            'title': item.get('title', ''),
                            'source': 'rapyd_docs'
                        })
                        ids.append(f"doc_{idx}")
                
                if documents:
                    logger.info(f"   Adding {len(documents)} documents from scraped_content.json...")
                    embeddings.add_documents(documents, metadatas, ids)
                    logger.info(f"   ✓ Successfully added {len(documents)} documents")
            else:
                logger.info("   Using sample documents for testing...")
                documents = []
                metadatas = []
                ids = []
                
                for idx, doc in enumerate(sample_docs):
                    documents.append(doc['content'])
                    metadatas.append(doc['metadata'])
                    ids.append(f"sample_{idx}")
                
                logger.info(f"   Adding {len(documents)} sample documents...")
                embeddings.add_documents(documents, metadatas, ids)
                logger.info(f"   ✓ Successfully added {len(documents)} documents")
        else:
            logger.info(f"\n2. Database already contains {doc_count} documents")
        
        # Test queries
        logger.info("\n3. Testing search queries...")
        logger.info("-" * 40)
        
        test_queries = [
            "How do I make my first API call?",
            "What payment methods are supported?",
            "How do webhooks work?",
            "Tell me about Rapyd Collect",
            "API authentication and signatures"
        ]
        
        for query in test_queries:
            logger.info(f"\nQuery: '{query}'")
            results = embeddings.search(query, top_k=3)
            
            if results:
                for i, result in enumerate(results, 1):
                    logger.info(f"  Result {i}:")
                    logger.info(f"    Score: {result.get('score', 0):.4f}")
                    metadata = result.get('metadata', {})
                    logger.info(f"    Title: {metadata.get('title', 'N/A')}")
                    content_preview = result.get('content', '')[:150]
                    if len(result.get('content', '')) > 150:
                        content_preview += "..."
                    logger.info(f"    Content: {content_preview}")
            else:
                logger.info("  No results found")
        
        # Final statistics
        logger.info("\n" + "=" * 60)
        logger.info("TEST COMPLETE")
        if hasattr(embeddings, 'get_collection_stats'):
            final_stats = embeddings.get_collection_stats()
            logger.info(f"Final document count: {final_stats.get('total_documents', 0)}")
            logger.info(f"Backend used: {final_stats.get('device', 'unknown')}")
        logger.info("=" * 60)
        
        return True
        
    except ImportError as e:
        logger.error(f"Import error: {e}")
        logger.error("Please ensure all dependencies are installed:")
        logger.error("  pip install chromadb ollama-python requests numpy")
        return False
    except Exception as e:
        logger.error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Change to the rapydocs directory
    os.chdir(Path(__file__).parent)
    
    success = test_embeddings_system()
    sys.exit(0 if success else 1)
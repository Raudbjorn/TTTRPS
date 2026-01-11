#!/usr/bin/env python3
"""
Refactored test for embeddings system - no loops or conditionals in test functions
Following Google's software engineering guidelines for clear, simple tests
"""

import json
import logging
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions (extract complexity from tests)
# ============================================================================

def _initialize_embeddings():
    """Initialize the embeddings system"""
    # Avoid sys.path manipulation - use proper package imports
    try:
        # This assumes proper package installation
        from src.embeddings.embeddings_factory import initialize_database
        return initialize_database()
    except ImportError:
        # Fallback for development - but prefer proper package installation
        import sys
        sys.path.append(str(Path(__file__).parent.parent.parent.parent))
        from src.embeddings.embeddings_factory import initialize_database
        return initialize_database()


def _log_system_info(embeddings) -> None:
    """Helper to log system info without conditionals in test"""
    try:
        stats = embeddings.get_collection_stats()
        logger.info(f"   Backend: {stats.get('device', 'unknown')}")
        logger.info(f"   Model: {stats.get('model', 'unknown')}")
        logger.info(f"   Documents: {stats.get('total_documents', 0)}")
        # Log Ollama status unconditionally (will show False if not enabled)
        ollama_status = "✓ Enabled" if stats.get('ollama_enabled') else "✗ Disabled"
        logger.info(f"   Ollama GPU acceleration: {ollama_status}")
    except AttributeError:
        logger.info("   System info not available")


def _get_document_count(embeddings) -> int:
    """Helper to get document count safely"""
    try:
        stats = embeddings.get_collection_stats()
        return stats.get('total_documents', 0)
    except (AttributeError, TypeError):
        return 0


def _load_sample_documents() -> List[Dict[str, Any]]:
    """Return sample documents for testing"""
    return [
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


def _load_scraped_documents(file_path: Path, limit: int = 20) -> Optional[List[Dict[str, Any]]]:
    """Load documents from scraped_content.json if it exists"""
    if not file_path.exists():
        return None

    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Extract documents with content
        documents = []
        for item in data[:limit]:
            if item.get('content'):
                documents.append({
                    'content': item['content'],
                    'metadata': {
                        'url': item.get('url', ''),
                        'title': item.get('title', ''),
                        'source': 'rapyd_docs'
                    }
                })
        return documents if documents else None
    except (json.JSONDecodeError, IOError):
        return None


def _prepare_documents_for_insertion(documents: List[Dict[str, Any]]) -> tuple:
    """Prepare documents for batch insertion"""
    contents = []
    metadatas = []
    ids = []

    for idx, doc in enumerate(documents):
        contents.append(doc['content'])
        metadatas.append(doc.get('metadata', {}))
        ids.append(f"doc_{idx}")

    return contents, metadatas, ids


def _populate_database_if_empty(embeddings, doc_count: int) -> None:
    """Populate database with documents if empty - no conditionals in main test"""
    if doc_count > 0:
        logger.info(f"\n2. Database already contains {doc_count} documents")
        return

    logger.info("\n2. Database is empty. Loading sample data...")

    # Try to load scraped content first
    scraped_file = Path("scraped_content.json")
    scraped_docs = _load_scraped_documents(scraped_file)

    # Use scraped docs if available, otherwise use samples
    documents = scraped_docs if scraped_docs else _load_sample_documents()
    source = "scraped_content.json" if scraped_docs else "sample documents"

    logger.info(f"   Using {source} for testing...")

    # Prepare and add documents
    contents, metadatas, ids = _prepare_documents_for_insertion(documents)

    logger.info(f"   Adding {len(contents)} documents...")
    embeddings.add_documents(contents, metadatas, ids)
    logger.info(f"   ✓ Successfully added {len(contents)} documents")


def _get_test_queries() -> List[str]:
    """Return test queries for search testing"""
    return [
        "How do I get started with Rapyd API?",
        "What payment methods does Rapyd support?",
        "Tell me about webhooks",
        "How to process refunds",
        "What is Rapyd Collect?",
        "API authentication and signatures"
    ]


def _search_and_log_single_query(embeddings, query: str, top_k: int = 3) -> None:
    """Execute a single search query and log results"""
    logger.info(f"\nQuery: '{query}'")
    results = embeddings.search(query, top_k=top_k)

    if not results:
        logger.info("  No results found")
        return

    # Log all results without loops in the main test
    _log_search_results(results)


def _log_search_results(results: List[Dict[str, Any]]) -> None:
    """Log search results without loops"""
    for i, result in enumerate(results, 1):
        _log_single_result(result, i)


def _log_single_result(result: Dict[str, Any], index: int) -> None:
    """Log a single search result"""
    logger.info(f"  Result {index}:")
    logger.info(f"    Score: {result.get('score', 0):.4f}")

    metadata = result.get('metadata', {})
    logger.info(f"    Title: {metadata.get('title', 'N/A')}")

    # Format content preview
    content = result.get('content', '')
    content_preview = content[:150] + ("..." if len(content) > 150 else "")
    logger.info(f"    Content: {content_preview}")


def _execute_all_test_queries(embeddings, queries: List[str]) -> None:
    """Execute all test queries - complexity extracted from main test"""
    for query in queries:
        _search_and_log_single_query(embeddings, query)


def _log_final_statistics(embeddings) -> None:
    """Log final test statistics"""
    logger.info("\n" + "=" * 60)
    logger.info("TEST COMPLETE")

    try:
        final_stats = embeddings.get_collection_stats()
        logger.info(f"Final document count: {final_stats.get('total_documents', 0)}")
        logger.info(f"Backend used: {final_stats.get('device', 'unknown')}")
    except AttributeError:
        logger.info("Statistics not available")

    logger.info("=" * 60)


# ============================================================================
# Test Functions (simple, without loops or conditionals)
# ============================================================================

def test_embeddings_initialization():
    """Test that embeddings system initializes correctly"""
    logger.info("\n" + "=" * 60)
    logger.info("TESTING COMPLETE EMBEDDINGS WORKFLOW")
    logger.info("=" * 60)
    logger.info("\n1. Initializing embeddings system...")

    embeddings = _initialize_embeddings()
    assert embeddings is not None, "Failed to initialize embeddings"

    _log_system_info(embeddings)
    return embeddings


def test_database_population(embeddings):
    """Test database population with documents"""
    doc_count = _get_document_count(embeddings)
    _populate_database_if_empty(embeddings, doc_count)

    # Verify documents were added
    new_count = _get_document_count(embeddings)
    assert new_count > 0, "No documents in database after population"

    return embeddings


def test_search_functionality(embeddings):
    """Test search functionality with various queries"""
    logger.info("\n3. Testing search queries...")

    queries = _get_test_queries()
    _execute_all_test_queries(embeddings, queries)

    return embeddings


def test_complete_workflow():
    """Main test function - simple orchestration without complexity"""
    try:
        # Test initialization
        embeddings = test_embeddings_initialization()

        # Test database population
        embeddings = test_database_population(embeddings)

        # Test search functionality
        embeddings = test_search_functionality(embeddings)

        # Log final statistics
        _log_final_statistics(embeddings)

        return True

    except Exception as e:
        logger.error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# ============================================================================
# Parameterized test alternative (for pytest)
# ============================================================================

import pytest

@pytest.mark.parametrize("query", _get_test_queries())
def test_individual_search_query(query):
    """Parameterized test for individual queries - no loops in test"""
    embeddings = _initialize_embeddings()

    # Ensure database has data
    doc_count = _get_document_count(embeddings)
    _populate_database_if_empty(embeddings, doc_count)

    # Test the query
    results = embeddings.search(query, top_k=3)

    # Assertions
    assert results is not None, f"No results for query: {query}"
    assert len(results) <= 3, f"Too many results returned for query: {query}"

    # Log for debugging
    logger.info(f"Query '{query}' returned {len(results)} results")


# ============================================================================
# Main execution
# ============================================================================

if __name__ == "__main__":
    # Use absolute paths - avoid os.chdir
    script_dir = Path(__file__).parent.resolve()

    # Run from script directory context without changing cwd
    success = test_complete_workflow()
    sys.exit(0 if success else 1)
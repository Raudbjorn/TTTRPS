"""
Common utilities and patterns used across the rapydocs project.
This consolidates frequently duplicated code patterns.
"""

from typing import Dict, List, Any, Optional, Callable, TypeVar
import time
import json
from contextlib import contextmanager
from .logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class ErrorHandler:
    """Centralized error handling with logging."""
    
    @staticmethod
    def handle_with_fallback(
        operation: Callable[[], T],
        fallback: T,
        error_msg: str,
        log_level: str = "error"
    ) -> T:
        """Execute operation with fallback on error."""
        try:
            return operation()
        except Exception as e:
            getattr(logger, log_level)(f"{error_msg}: {e}")
            return fallback
    
    @staticmethod
    @contextmanager
    def log_duration(operation_name: str):
        """Context manager to log operation duration."""
        start = time.time()
        try:
            logger.info(f"Starting {operation_name}")
            yield
        finally:
            duration = time.time() - start
            logger.info(f"{operation_name} completed in {duration:.3f}s")


class CollectionUtils:
    """Common utilities for working with embedding collections."""
    
    @staticmethod
    def format_search_results(results: Dict[str, Any], distances_key: str = 'distances') -> List[Dict[str, Any]]:
        """Format ChromaDB search results consistently."""
        formatted_results = []
        if results and results.get('documents') and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                score = 0
                if results.get(distances_key) and results[distances_key][0]:
                    score = 1 - results[distances_key][0][i]
                
                formatted_results.append({
                    'content': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i] if results.get('metadatas') and results['metadatas'][0] else {},
                    'score': score
                })
        return formatted_results
    
    @staticmethod
    def batch_process(items: List[T], batch_size: int, process_fn: Callable[[List[T]], None]) -> None:
        """Process items in batches."""
        total_batches = (len(items) - 1) // batch_size + 1
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            current_batch = i // batch_size + 1
            
            logger.info(f"Processing batch {current_batch}/{total_batches}")
            process_fn(batch)


class DatabaseLoader:
    """Common database loading utilities."""
    
    @staticmethod
    def load_scraped_content(file_path: str = 'scraped_content.json') -> Optional[List[Dict]]:
        """Load scraped content with error handling."""
        def load_operation():
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return ErrorHandler.handle_with_fallback(
            load_operation,
            None,
            f"Failed to load {file_path}",
            "warning"
        )
    
    @staticmethod
    def prepare_documents_for_embedding(data: List[Dict]) -> tuple[List[str], List[Dict], List[str]]:
        """Prepare documents, metadata, and IDs from scraped data."""
        documents, metadatas, ids = [], [], []
        
        for idx, item in enumerate(data):
            if 'content' in item and item['content'].strip():
                documents.append(item['content'])
                metadatas.append({
                    'url': item.get('url', ''),
                    'title': item.get('title', ''),
                    'source': item.get('source', 'rapyd_docs')
                })
                ids.append(f"doc_{idx}")
        
        return documents, metadatas, ids


def check_optional_dependency(module_name: str, install_command: str = None) -> bool:
    """Check if an optional dependency is available."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        if install_command:
            logger.info(f"{module_name} not available - install with: {install_command}")
        else:
            logger.info(f"{module_name} not available")
        return False
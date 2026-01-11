"""
Async/await processing infrastructure for MBED (T139)

This module provides comprehensive async processing capabilities:
- Async pipeline for document processing
- Concurrent backend operations
- Rate limiting and throttling
- Stream processing for large datasets
- Async context managers for resource management
"""

import asyncio
import hashlib
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncIterator, Callable, Union, TypeVar, Generic
from dataclasses import dataclass, field
from collections import deque
from contextlib import asynccontextmanager
import numpy as np
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import aiofiles

logger = logging.getLogger(__name__)

T = TypeVar('T')
R = TypeVar('R')

# Constants
DEFAULT_RATE_LIMIT_WAIT = 0.1  # Default wait time when rate limiting is disabled


@dataclass
class AsyncBatchConfig:
    """Configuration for async batch processing"""
    batch_size: int = 32
    max_concurrent_batches: int = 4
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    rate_limit_per_second: Optional[float] = None
    enable_progress_tracking: bool = True


class RateLimiter:
    """
    Token bucket rate limiter for async operations
    
    Features:
    - Smooth rate limiting without bursts
    - Async-friendly with non-blocking waits
    - Configurable refill rate
    """
    
    def __init__(self, rate_per_second: float, burst_size: Optional[int] = None):
        """
        Initialize rate limiter
        
        Args:
            rate_per_second: Maximum operations per second
            burst_size: Maximum burst size (defaults to rate_per_second)
        """
        if rate_per_second <= 0:
            raise ValueError("rate_per_second must be positive")
            
        self.rate = rate_per_second
        self.burst_size = burst_size or max(1, int(rate_per_second))
        self.tokens = float(self.burst_size)
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> None:
        """
        Acquire tokens, waiting if necessary
        
        Args:
            tokens: Number of tokens to acquire
        """
        async with self.lock:
            while tokens > self.tokens:
                # Refill tokens based on elapsed time
                now = time.monotonic()
                elapsed = now - self.last_refill
                self.tokens = min(
                    self.burst_size,
                    self.tokens + elapsed * self.rate
                )
                self.last_refill = now
                
                if tokens > self.tokens:
                    # Calculate wait time (with zero check)
                    if self.rate > 0:
                        wait_time = (tokens - self.tokens) / self.rate
                        await asyncio.sleep(wait_time)
                    else:
                        # If rate is 0 or negative, wait a default time
                        await asyncio.sleep(DEFAULT_RATE_LIMIT_WAIT)
            
            self.tokens -= tokens


class AsyncBatchProcessor(Generic[T, R]):
    """
    Generic async batch processor for parallel operations
    
    Features:
    - Dynamic batching with size optimization
    - Concurrent batch processing
    - Error handling with retries
    - Progress tracking
    - Rate limiting support
    """
    
    def __init__(self,
                 process_func: Callable[[List[T]], R],
                 config: AsyncBatchConfig = AsyncBatchConfig()):
        """
        Initialize async batch processor
        
        Args:
            process_func: Function to process a batch of items
            config: Batch processing configuration
        """
        self.process_func = process_func
        self.config = config
        
        # Rate limiter
        self.rate_limiter = None
        if config.rate_limit_per_second:
            self.rate_limiter = RateLimiter(config.rate_limit_per_second)
        
        # Progress tracking
        self.total_processed = 0
        self.total_errors = 0
        
        # Thread pool for CPU-bound operations
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_batches)
    
    async def process_all(self, 
                         items: List[T],
                         progress_callback: Optional[Callable[[int, int], None]] = None) -> List[R]:
        """
        Process all items in batches
        
        Args:
            items: Items to process
            progress_callback: Optional callback for progress updates
            
        Returns:
            List of results
        """
        if not items:
            return []
        
        # Create batches
        batches = self._create_batches(items)
        total_batches = len(batches)
        
        logger.info(f"Processing {len(items)} items in {total_batches} batches")
        
        # Process batches concurrently
        semaphore = asyncio.Semaphore(self.config.max_concurrent_batches)
        
        async def process_batch_with_semaphore(batch_idx: int, batch: List[T]) -> Optional[R]:
            async with semaphore:
                return await self._process_single_batch(batch, batch_idx)
        
        # Create tasks for all batches
        tasks = [
            process_batch_with_semaphore(i, batch)
            for i, batch in enumerate(batches)
        ]
        
        # Process with progress tracking
        results = []
        completed = 0
        
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result is not None:
                results.append(result)
            
            completed += 1
            
            if progress_callback and self.config.enable_progress_tracking:
                progress_callback(completed, total_batches)
        
        # Update total processed count based on input items
        self.total_processed += len(items)
        
        logger.info(f"Completed processing {len(items)} items with {self.total_errors} errors")
        
        return results
    
    async def process_stream(self, 
                           item_stream: AsyncIterator[T],
                           buffer_size: int = 1000) -> AsyncIterator[R]:
        """
        Process items from an async stream
        
        Args:
            item_stream: Async iterator of items
            buffer_size: Size of internal buffer
            
        Yields:
            Processed results
        """
        buffer = []
        
        async for item in item_stream:
            buffer.append(item)
            
            # Process when buffer is full
            if len(buffer) >= self.config.batch_size:
                batch = buffer[:self.config.batch_size]
                buffer = buffer[self.config.batch_size:]
                
                result = await self._process_single_batch(batch, self.total_processed)
                if result is not None:
                    yield result
        
        # Process remaining items
        while buffer:
            batch = buffer[:self.config.batch_size]
            buffer = buffer[self.config.batch_size:]
            
            result = await self._process_single_batch(batch, self.total_processed)
            if result is not None:
                yield result
    
    def _create_batches(self, items: List[T]) -> List[List[T]]:
        """Create batches from items"""
        batches = []
        for i in range(0, len(items), self.config.batch_size):
            batch = items[i:i + self.config.batch_size]
            batches.append(batch)
        return batches
    
    async def _process_single_batch(self, batch: List[T], batch_idx: int) -> Optional[R]:
        """Process a single batch with error handling and retries"""
        # Apply rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire(len(batch))
        
        for attempt in range(self.config.retry_attempts):
            try:
                # Set timeout for batch processing
                result = await asyncio.wait_for(
                    self._execute_process_func(batch),
                    timeout=self.config.timeout_seconds
                )
                
                return result
                
            except asyncio.TimeoutError:
                logger.warning(f"Batch {batch_idx} timed out on attempt {attempt + 1}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)
                else:
                    self.total_errors += len(batch)
                    logger.error(f"Batch {batch_idx} failed after {self.config.retry_attempts} attempts")
                    
            except Exception as e:
                logger.error(f"Error processing batch {batch_idx}: {e}")
                if attempt < self.config.retry_attempts - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)
                else:
                    self.total_errors += len(batch)
        
        return None
    
    async def _execute_process_func(self, batch: List[T]) -> R:
        """Execute the process function, handling both sync and async functions"""
        if asyncio.iscoroutinefunction(self.process_func):
            # Async function
            return await self.process_func(batch)
        else:
            # Sync function - run in thread pool
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor,
                partial(self.process_func, batch)
            )
    
    def close(self):
        """Close the processor and clean up resources"""
        self.executor.shutdown(wait=True)


class AsyncEmbeddingPipeline:
    """
    Async pipeline for embedding generation
    
    Features:
    - Async document loading
    - Parallel text preprocessing
    - Concurrent embedding generation
    - Async database storage
    - Stream processing support
    """
    
    def __init__(self, 
                 backend,
                 database=None,
                 cache_hierarchy=None,
                 config: AsyncBatchConfig = AsyncBatchConfig()):
        """
        Initialize async embedding pipeline
        
        Args:
            backend: Embedding backend
            database: Vector database (optional)
            cache_hierarchy: Cache hierarchy (optional)
            config: Processing configuration
        """
        self.backend = backend
        self.database = database
        self.cache_hierarchy = cache_hierarchy
        self.config = config
        
        # Create batch processor for embeddings
        self.embedding_processor = AsyncBatchProcessor(
            self._generate_embeddings_batch,
            config
        )
        
        logger.info("Async embedding pipeline initialized")
    
    async def process_documents(self, 
                               documents: Union[List[str], List[Path]],
                               metadata: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Process documents through the full pipeline
        
        Args:
            documents: List of document texts or file paths
            metadata: Optional metadata for each document
            
        Returns:
            Processing results
        """
        start_time = time.perf_counter()
        
        # Load documents if paths provided
        if documents and isinstance(documents[0], Path):
            logger.info("Loading documents from files...")
            documents = await self._load_documents_async(documents)
        
        # Preprocess texts
        logger.info("Preprocessing texts...")
        processed_texts = await self._preprocess_texts_async(documents)
        
        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = await self.embedding_processor.process_all(
            processed_texts,
            progress_callback=self._log_progress
        )
        
        # Combine results
        if embeddings:
            embeddings_array = np.vstack(embeddings)
        else:
            embeddings_array = np.empty((0, self.backend.get_embedding_dimension()))
        
        # Store in database if available
        if self.database:
            logger.info("Storing embeddings in database...")
            await self._store_embeddings_async(
                embeddings_array, 
                processed_texts, 
                metadata
            )
        
        # Calculate statistics
        duration = time.perf_counter() - start_time
        throughput = len(documents) / duration if duration > 0 else 0
        
        results = {
            "num_documents": len(documents),
            "num_embeddings": len(embeddings_array),
            "embedding_dim": embeddings_array.shape[1] if len(embeddings_array) > 0 else 0,
            "duration_seconds": duration,
            "throughput_docs_per_sec": throughput,
            "errors": self.embedding_processor.total_errors
        }
        
        logger.info(f"Pipeline completed: {results['num_documents']} docs in {duration:.2f}s "
                   f"({throughput:.1f} docs/sec)")
        
        return results
    
    async def process_document_stream(self, 
                                     document_stream: AsyncIterator[str]) -> AsyncIterator[np.ndarray]:
        """
        Process documents from an async stream
        
        Args:
            document_stream: Async iterator of documents
            
        Yields:
            Embedding arrays
        """
        # Create preprocessing stream
        preprocessed_stream = self._preprocess_stream(document_stream)
        
        # Process through embedding pipeline
        async for embeddings in self.embedding_processor.process_stream(preprocessed_stream):
            yield embeddings
    
    async def _load_documents_async(self, file_paths: List[Path]) -> List[str]:
        """Load documents asynchronously from files"""
        documents = []
        
        async def load_single_file(path: Path) -> str:
            try:
                async with aiofiles.open(path, 'r', encoding='utf-8') as f:
                    return await f.read()
            except Exception as e:
                logger.error(f"Error loading {path}: {e}")
                return ""
        
        # Load files concurrently
        tasks = [load_single_file(path) for path in file_paths]
        documents = await asyncio.gather(*tasks)
        
        return documents
    
    async def _preprocess_texts_async(self, texts: List[str]) -> List[str]:
        """Preprocess texts asynchronously"""
        # Run preprocessing in thread pool for CPU-bound operations
        loop = asyncio.get_event_loop()
        
        def preprocess_batch(batch: List[str]) -> List[str]:
            return [self._preprocess_single_text(text) for text in batch]
        
        # Process in batches
        batch_size = 100
        tasks = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            task = loop.run_in_executor(None, preprocess_batch, batch)
            tasks.append(task)
        
        # Gather results
        batch_results = await asyncio.gather(*tasks)
        
        # Flatten results
        processed = []
        for batch_result in batch_results:
            processed.extend(batch_result)
        
        return processed
    
    def _preprocess_single_text(self, text: str) -> str:
        """Preprocess a single text"""
        # Basic preprocessing - can be extended
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = " ".join(text.split())
        
        # Truncate if too long
        max_length = 8192
        if len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    async def _preprocess_stream(self, text_stream: AsyncIterator[str]) -> AsyncIterator[str]:
        """Preprocess texts from a stream"""
        async for text in text_stream:
            yield self._preprocess_single_text(text)
    
    async def _generate_embeddings_batch(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a batch of texts"""
        # Check cache first if available
        if self.cache_hierarchy:
            cached_embeddings = []
            uncached_texts = []
            uncached_indices = []
            
            for i, text in enumerate(texts):
                cache_key = self._create_cache_key(text)
                cached = await self.cache_hierarchy.get(cache_key)
                
                if cached is not None:
                    cached_embeddings.append((i, cached))
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(i)
            
            # Generate embeddings for uncached texts
            if uncached_texts:
                # Run synchronous embedding generation in thread pool
                loop = asyncio.get_event_loop()
                new_embeddings = await loop.run_in_executor(
                    None,
                    self.backend.generate_embeddings,
                    uncached_texts
                )
                
                # Cache new embeddings
                for text, embedding, idx in zip(uncached_texts, new_embeddings, uncached_indices):
                    cache_key = self._create_cache_key(text)
                    await self.cache_hierarchy.set(cache_key, embedding)
                    cached_embeddings.append((idx, embedding))
            
            # Sort by original index and extract embeddings
            cached_embeddings.sort(key=lambda x: x[0])
            embeddings = np.array([emb for _, emb in cached_embeddings])
            
        else:
            # No cache - generate directly in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                self.backend.generate_embeddings,
                texts
            )
        
        return embeddings
    
    def _create_cache_key(self, text: str) -> str:
        """Create cache key for text"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        return f"embedding:{self.backend.__class__.__name__}:{text_hash}"
    
    async def _store_embeddings_async(self, 
                                     embeddings: np.ndarray,
                                     texts: List[str],
                                     metadata: Optional[List[Dict[str, Any]]]):
        """Store embeddings in database asynchronously"""
        if not self.database:
            return
        
        # Prepare data for storage
        if metadata is None:
            metadata = [{}] * len(texts)
        
        # Store in batches
        batch_size = 100
        
        for i in range(0, len(texts), batch_size):
            batch_embeddings = embeddings[i:i + batch_size]
            batch_texts = texts[i:i + batch_size]
            batch_metadata = metadata[i:i + batch_size]
            
            # Add to database (assuming async interface)
            if hasattr(self.database, 'add_async'):
                await self.database.add_async(
                    embeddings=batch_embeddings,
                    documents=batch_texts,
                    metadatas=batch_metadata
                )
            else:
                # Fallback to sync in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    self.database.add,
                    batch_embeddings,
                    batch_texts,
                    batch_metadata
                )
    
    def _log_progress(self, completed: int, total: int):
        """Log processing progress"""
        percentage = (completed / total) * 100
        logger.info(f"Progress: {completed}/{total} batches ({percentage:.1f}%)")
    
    async def close(self):
        """Close the pipeline and clean up resources"""
        self.embedding_processor.close()


class AsyncResourceManager:
    """
    Async context manager for resource management
    
    Features:
    - Connection pooling
    - Resource lifecycle management
    - Automatic cleanup
    - Error handling
    """
    
    def __init__(self, max_connections: int = 10):
        """
        Initialize resource manager
        
        Args:
            max_connections: Maximum concurrent connections
        """
        self.max_connections = max_connections
        self.connection_pool = asyncio.Queue(maxsize=max_connections)
        self.active_connections = 0
        self.lock = asyncio.Lock()
    
    @asynccontextmanager
    async def acquire_connection(self):
        """Acquire a connection from the pool"""
        connection = None
        
        try:
            # Get or create connection
            try:
                connection = self.connection_pool.get_nowait()
            except asyncio.QueueEmpty:
                async with self.lock:
                    if self.active_connections < self.max_connections:
                        connection = await self._create_connection()
                        self.active_connections += 1
                    else:
                        # Wait for available connection
                        connection = await self.connection_pool.get()
            
            yield connection
            
        finally:
            # Return connection to pool
            if connection:
                await self.connection_pool.put(connection)
    
    async def _create_connection(self):
        """Create a new connection (override in subclasses)"""
        # Placeholder - implement actual connection logic
        return {"connection_id": self.active_connections}
    
    async def close_all(self):
        """Close all connections in the pool"""
        while not self.connection_pool.empty():
            try:
                connection = self.connection_pool.get_nowait()
                await self._close_connection(connection)
            except asyncio.QueueEmpty:
                break
        
        self.active_connections = 0
    
    async def _close_connection(self, connection):
        """Close a single connection (override in subclasses)"""
        # Placeholder - implement actual close logic
        pass


# Utility functions for async operations

async def gather_with_concurrency(n: int, *tasks) -> List[Any]:
    """
    Gather tasks with limited concurrency
    
    Args:
        n: Maximum concurrent tasks
        *tasks: Tasks to execute
        
    Returns:
        List of results
    """
    semaphore = asyncio.Semaphore(n)
    
    async def sem_task(task):
        async with semaphore:
            return await task
    
    return await asyncio.gather(*(sem_task(task) for task in tasks))


async def process_in_chunks(items: List[T], 
                          chunk_size: int,
                          process_func: Callable[[List[T]], R],
                          max_concurrent: int = 4) -> List[R]:
    """
    Process items in chunks with concurrency control
    
    Args:
        items: Items to process
        chunk_size: Size of each chunk
        process_func: Function to process each chunk
        max_concurrent: Maximum concurrent chunks
        
    Returns:
        List of results
    """
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    
    async def process_chunk(chunk):
        if asyncio.iscoroutinefunction(process_func):
            return await process_func(chunk)
        else:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, process_func, chunk)
    
    tasks = [process_chunk(chunk) for chunk in chunks]
    return await gather_with_concurrency(max_concurrent, *tasks)


# Note: The run_async function with nest_asyncio has been removed as it's an anti-pattern.
# The codebase now properly uses async/await throughout without needing to mix sync and async contexts.
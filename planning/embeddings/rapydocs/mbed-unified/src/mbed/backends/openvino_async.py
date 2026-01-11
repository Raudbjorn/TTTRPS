"""
Async inference pipeline for OpenVINO backend

This module provides asynchronous inference capabilities for the OpenVINO backend,
allowing for concurrent processing of multiple batches to maximize throughput.
"""

import asyncio
import numpy as np
from typing import List, Callable, Optional, Any, Dict
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class AsyncOpenVINOProcessor:
    """
    Asynchronous batch processor for OpenVINO embeddings
    """
    
    def __init__(self, backend, num_workers: int = 4):
        """
        Initialize async processor
        
        Args:
            backend: OpenVINO backend instance
            num_workers: Number of concurrent workers
        """
        self.backend = backend
        self.num_workers = num_workers
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
    
    async def process_batches_async(self, 
                                   text_batches: List[List[str]], 
                                   progress_callback: Optional[Callable] = None) -> np.ndarray:
        """
        Process multiple batches asynchronously
        
        Args:
            text_batches: List of text batches
            progress_callback: Optional progress callback
            
        Returns:
            Concatenated embeddings array
        """
        loop = asyncio.get_running_loop()
        
        # Create tasks for each batch
        tasks = []
        for i, batch in enumerate(text_batches):
            task = loop.run_in_executor(
                self.executor,
                self._process_batch_with_progress,
                batch,
                i,
                len(text_batches),
                progress_callback
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks)
        
        # Concatenate results
        return np.vstack(results)
    
    def _process_batch_with_progress(self, 
                                    batch: List[str], 
                                    batch_idx: int,
                                    total_batches: int,
                                    progress_callback: Optional[Callable]) -> np.ndarray:
        """
        Process a single batch with progress reporting
        
        Args:
            batch: Text batch to process
            batch_idx: Index of current batch
            total_batches: Total number of batches
            progress_callback: Optional progress callback
            
        Returns:
            Embeddings for the batch
        """
        # Generate embeddings
        embeddings = self.backend.generate_embeddings(batch)
        
        # Report progress
        if progress_callback:
            progress = (batch_idx + 1) / total_batches
            progress_callback(progress, f"Processed batch {batch_idx + 1}/{total_batches}")
        
        return embeddings
    
    def process_stream(self, 
                       text_stream: Any,
                       batch_size: int = 32) -> Any:
        """
        Process streaming text data
        
        Args:
            text_stream: Iterator or generator of texts
            batch_size: Size of batches to process
            
        Yields:
            Embeddings for each batch
        """
        batch = []
        
        for text in text_stream:
            batch.append(text)
            
            if len(batch) >= batch_size:
                # Process batch
                yield self.backend.generate_embeddings(batch)
                batch = []
        
        # Process remaining texts
        if batch:
            yield self.backend.generate_embeddings(batch)
    
    def shutdown(self):
        """Shutdown the executor"""
        self.executor.shutdown(wait=True)


def create_async_pipeline(backend, config: Optional[dict] = None) -> AsyncOpenVINOProcessor:
    """
    Create an async processing pipeline
    
    Args:
        backend: OpenVINO backend instance
        config: Optional pipeline configuration overrides
        
    Returns:
        Configured async processor
    """
    # Use backend's config as base, with optional overrides
    if config is None:
        config = {}
    
    # Get configuration from MBEDSettings or use provided overrides
    backend_config = backend.config if hasattr(backend, 'config') else None
    
    # Extract configuration values with proper fallbacks
    if backend_config:
        num_workers = config.get('num_workers', backend_config.workers)
        default_batch_size = backend_config.batch_size
    else:
        num_workers = config.get('num_workers', 4)
        default_batch_size = 128
    
    # Ensure backend is initialized
    if backend.model is None:
        backend.initialize()
    
    # Enable dynamic batching for better async performance
    if config.get('enable_dynamic_batching', True):
        min_batch = config.get('min_batch_size', 1)
        max_batch = config.get('max_batch_size', default_batch_size)
        backend.enable_dynamic_batching(min_batch, max_batch)
    
    # Create async processor
    processor = AsyncOpenVINOProcessor(backend, num_workers)
    
    logger.info(f"Created async pipeline with {num_workers} workers")
    
    return processor

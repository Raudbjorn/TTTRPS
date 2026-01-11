"""
Batch orchestration system for large-scale file processing
"""

import os
import time
import asyncio
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable, AsyncIterator, Union
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from ..core.result import Result
from ..core.orchestrator import ProcessedFile
from .file_processor import FileProcessor, ProcessingOptions, FileInfo

logger = logging.getLogger(__name__)


@dataclass
class BatchConfig:
    """Configuration for batch processing."""
    batch_size: int = 100
    max_workers: int = 4
    max_concurrent_files: int = 10
    use_process_pool: bool = False
    checkpoint_interval: int = 50
    retry_attempts: int = 3
    retry_delay: float = 1.0
    memory_threshold_mb: int = 1024
    disk_space_threshold_mb: int = 512
    timeout_seconds: Optional[int] = None


@dataclass
class BatchProgress:
    """Progress tracking for batch operations."""
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    start_time: float = field(default_factory=time.time)
    last_checkpoint: float = field(default_factory=time.time)
    current_batch: int = 0
    total_batches: int = 0
    estimated_completion: Optional[float] = None
    processing_rate: float = 0.0  # files per second

    def update_rate(self):
        """Update processing rate."""
        elapsed = time.time() - self.start_time
        if elapsed > 0:
            self.processing_rate = self.processed_files / elapsed

    def estimate_completion(self):
        """Estimate completion time."""
        if self.processing_rate > 0:
            remaining_files = self.total_files - self.processed_files
            estimated_seconds = remaining_files / self.processing_rate
            self.estimated_completion = time.time() + estimated_seconds


@dataclass
class BatchResult:
    """Result of batch processing operation."""
    progress: BatchProgress
    processed_files: List[ProcessedFile]
    failed_files: List[Dict[str, str]]  # file_path -> error_message
    checkpoint_path: Optional[Path] = None
    statistics: Dict[str, Any] = field(default_factory=dict)


class BatchOrchestrator:
    """Orchestrates large-scale batch processing operations."""

    def __init__(self, file_processor: FileProcessor, config: BatchConfig):
        self.file_processor = file_processor
        self.config = config
        self.checkpoint_manager = CheckpointManager()
        self.resource_monitor = ResourceMonitor()
        self.progress_callbacks: List[Callable[[BatchProgress], None]] = []
        # Shared executor for async file processing
        self._async_executor = ThreadPoolExecutor(max_workers=config.max_concurrent_files or 4)

    def add_progress_callback(self, callback: Callable[[BatchProgress], None]):
        """Add progress callback function."""
        self.progress_callbacks.append(callback)

    def _notify_progress(self, progress: BatchProgress):
        """Notify all progress callbacks."""
        progress.update_rate()
        progress.estimate_completion()

        for callback in self.progress_callbacks:
            try:
                callback(progress)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")

    async def process_files_async(
        self,
        file_paths: List[Union[str, Path]],
        resume_from: Optional[Path] = None
    ) -> Result[BatchResult, str]:
        """Process files asynchronously with batch orchestration."""
        try:
            # Initialize progress tracking
            progress = BatchProgress(total_files=len(file_paths))
            processed_files = []
            failed_files = []

            # Resume from checkpoint if specified
            if resume_from:
                checkpoint_result = self.checkpoint_manager.load_checkpoint(resume_from)
                if checkpoint_result.is_ok():
                    checkpoint_data = checkpoint_result.unwrap()
                    progress = checkpoint_data['progress']
                    processed_files = checkpoint_data.get('processed_files', [])
                    failed_files = checkpoint_data.get('failed_files', [])

                    # Filter out already processed files
                    # ProcessedFile objects have been reconstructed, use pf.path directly
                    processed_paths = {str(pf.path) for pf in processed_files}
                    failed_paths = {ff['file_path'] for ff in failed_files}
                    file_paths = [p for p in file_paths
                                 if str(p) not in processed_paths and str(p) not in failed_paths]

                    logger.info(f"Resuming from checkpoint: {len(file_paths)} files remaining")

            # Calculate batches
            total_batches = (len(file_paths) + self.config.batch_size - 1) // self.config.batch_size
            progress.total_batches = total_batches

            # Process files in batches
            for batch_idx in range(0, len(file_paths), self.config.batch_size):
                batch_files = file_paths[batch_idx:batch_idx + self.config.batch_size]
                progress.current_batch = batch_idx // self.config.batch_size + 1

                logger.info(f"Processing batch {progress.current_batch}/{total_batches} ({len(batch_files)} files)")

                # Check resources before processing batch
                if not self.resource_monitor.check_resources(self.config):
                    logger.warning("Resource constraints detected, pausing...")
                    await asyncio.sleep(5)  # Brief pause
                    continue

                # Process batch
                batch_result = await self._process_batch_async(batch_files, progress)
                if batch_result.is_err():
                    logger.error(f"Batch processing failed: {batch_result.unwrap_err()}")
                    continue

                batch_processed, batch_failed = batch_result.unwrap()
                processed_files.extend(batch_processed)
                failed_files.extend(batch_failed)

                # Update progress
                progress.processed_files += len(batch_processed) + len(batch_failed)
                progress.successful_files += len(batch_processed)
                progress.failed_files += len(batch_failed)

                self._notify_progress(progress)

                # Create checkpoint if needed
                if progress.current_batch % (self.config.checkpoint_interval // self.config.batch_size + 1) == 0:
                    checkpoint_path = self._create_checkpoint(progress, processed_files, failed_files)
                    logger.info(f"Checkpoint created: {checkpoint_path}")

            # Final statistics
            statistics = self._calculate_statistics(processed_files, failed_files, progress)

            result = BatchResult(
                progress=progress,
                processed_files=processed_files,
                failed_files=failed_files,
                statistics=statistics
            )

            return Result.Ok(result)

        except Exception as e:
            return Result.Err(f"Batch processing failed: {str(e)}")

    async def _process_batch_async(
        self, file_paths: List[Union[str, Path]], progress: BatchProgress
    ) -> Result[tuple[List[ProcessedFile], List[Dict[str, str]]], str]:
        """Process a single batch of files asynchronously."""
        try:
            processed_files = []
            failed_files = []

            # Create semaphore to limit concurrent processing
            semaphore = asyncio.Semaphore(self.config.max_concurrent_files)

            async def process_file_with_semaphore(file_path):
                async with semaphore:
                    return await self._process_file_async(file_path)

            # Create tasks for all files in batch
            tasks = [process_file_with_semaphore(file_path) for file_path in file_paths]

            # Process with timeout if configured
            if self.config.timeout_seconds:
                timeout = self.config.timeout_seconds
            else:
                timeout = None

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            for i, result in enumerate(results):
                file_path = file_paths[i]

                if isinstance(result, Exception):
                    error_msg = str(result)
                    failed_files.append({
                        'file_path': str(file_path),
                        'error': error_msg,
                        'attempt': 1
                    })
                    logger.error(f"File processing failed: {file_path} - {error_msg}")
                elif hasattr(result, 'is_ok') and result.is_ok():
                    processed_files.append(result.unwrap())
                elif hasattr(result, 'is_err'):
                    error_msg = result.unwrap_err()
                    failed_files.append({
                        'file_path': str(file_path),
                        'error': error_msg,
                        'attempt': 1
                    })

            return Result.Ok((processed_files, failed_files))

        except Exception as e:
            return Result.Err(f"Batch async processing failed: {str(e)}")

    async def _process_file_async(self, file_path: Union[str, Path]) -> Result[ProcessedFile, str]:
        """Process a single file asynchronously using shared executor."""
        loop = asyncio.get_event_loop()

        # Run file processing in shared thread pool to avoid blocking
        try:
            result = await loop.run_in_executor(
                self._async_executor,
                self.file_processor.process_file,
                file_path
            )
            return result
        except Exception as e:
            return Result.Err(f"Async file processing failed: {str(e)}")

    def process_files_sync(
        self,
        file_paths: List[Union[str, Path]],
        resume_from: Optional[Path] = None
    ) -> Result[BatchResult, str]:
        """Process files synchronously with batch orchestration."""
        try:
            # Initialize progress tracking
            progress = BatchProgress(total_files=len(file_paths))
            processed_files = []
            failed_files = []

            # Resume from checkpoint if specified
            if resume_from:
                checkpoint_result = self.checkpoint_manager.load_checkpoint(resume_from)
                if checkpoint_result.is_ok():
                    checkpoint_data = checkpoint_result.unwrap()
                    progress = checkpoint_data['progress']
                    processed_files = checkpoint_data.get('processed_files', [])
                    failed_files = checkpoint_data.get('failed_files', [])

            # Use thread pool or process pool for parallel processing
            executor_class = ProcessPoolExecutor if self.config.use_process_pool else ThreadPoolExecutor

            with executor_class(max_workers=self.config.max_workers) as executor:
                # Submit all files for processing
                future_to_file = {
                    executor.submit(self._process_file_with_retry, file_path): file_path
                    for file_path in file_paths
                }

                # Process completed futures
                for future in as_completed(future_to_file):
                    file_path = future_to_file[future]

                    try:
                        result = future.result(timeout=self.config.timeout_seconds)

                        if result.is_ok():
                            processed_files.append(result.unwrap())
                            progress.successful_files += 1
                        else:
                            failed_files.append({
                                'file_path': str(file_path),
                                'error': result.unwrap_err(),
                                'attempts': self.config.retry_attempts
                            })
                            progress.failed_files += 1

                        progress.processed_files += 1
                        self._notify_progress(progress)

                        # Create checkpoint if needed
                        if progress.processed_files % self.config.checkpoint_interval == 0:
                            checkpoint_path = self._create_checkpoint(progress, processed_files, failed_files)
                            logger.info(f"Checkpoint created: {checkpoint_path}")

                    except Exception as e:
                        failed_files.append({
                            'file_path': str(file_path),
                            'error': f"Executor error: {str(e)}",
                            'attempts': 0
                        })
                        progress.failed_files += 1
                        progress.processed_files += 1

            # Final statistics
            statistics = self._calculate_statistics(processed_files, failed_files, progress)

            result = BatchResult(
                progress=progress,
                processed_files=processed_files,
                failed_files=failed_files,
                statistics=statistics
            )

            return Result.Ok(result)

        except Exception as e:
            return Result.Err(f"Sync batch processing failed: {str(e)}")

    def _process_file_with_retry(self, file_path: Union[str, Path]) -> Result[ProcessedFile, str]:
        """Process file with retry logic."""
        last_error = None

        for attempt in range(1, self.config.retry_attempts + 1):
            try:
                result = self.file_processor.process_file(file_path)
                if result.is_ok():
                    return result

                last_error = result.unwrap_err()
                logger.warning(f"Attempt {attempt} failed for {file_path}: {last_error}")

                if attempt < self.config.retry_attempts:
                    time.sleep(self.config.retry_delay * attempt)  # Exponential backoff

            except Exception as e:
                last_error = str(e)
                logger.warning(f"Attempt {attempt} exception for {file_path}: {last_error}")

        return Result.Err(f"All {self.config.retry_attempts} attempts failed. Last error: {last_error}")

    def _create_checkpoint(
        self, progress: BatchProgress, processed_files: List[ProcessedFile], failed_files: List[Dict[str, str]]
    ) -> Path:
        """Create checkpoint file."""
        checkpoint_data = {
            'progress': progress,
            'processed_files': processed_files,
            'failed_files': failed_files,
            'timestamp': time.time()
        }

        checkpoint_path = Path(f"batch_checkpoint_{int(time.time())}.json")
        return self.checkpoint_manager.save_checkpoint(checkpoint_data, checkpoint_path)

    def _calculate_statistics(
        self, processed_files: List[ProcessedFile], failed_files: List[Dict[str, str]], progress: BatchProgress
    ) -> Dict[str, Any]:
        """Calculate comprehensive processing statistics."""
        total_time = time.time() - progress.start_time

        # File type statistics
        file_types = {}
        languages = {}
        chunk_strategies = {}
        total_chunks = 0
        total_embeddings = 0

        for pf in processed_files:
            file_type = pf.file_info.get('file_type', 'unknown')
            file_types[file_type] = file_types.get(file_type, 0) + 1

            language = pf.file_info.get('language')
            if language:
                languages[language] = languages.get(language, 0) + 1

            strategy = pf.processing_metadata.get('chunk_strategy', 'unknown')
            chunk_strategies[strategy] = chunk_strategies.get(strategy, 0) + 1

            total_chunks += len(pf.chunks)
            total_embeddings += len(pf.embeddings)

        return {
            'total_processing_time': total_time,
            'processing_rate': progress.processing_rate,
            'file_type_distribution': file_types,
            'language_distribution': languages,
            'chunk_strategy_usage': chunk_strategies,
            'total_chunks_generated': total_chunks,
            'total_embeddings_generated': total_embeddings,
            'average_chunks_per_file': total_chunks / max(len(processed_files), 1),
            'success_rate': progress.successful_files / max(progress.total_files, 1),
            'failure_rate': progress.failed_files / max(progress.total_files, 1)
        }

    def cleanup(self):
        """Clean up resources including the shared executor."""
        if hasattr(self, '_async_executor'):
            self._async_executor.shutdown(wait=True)

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()


class CheckpointManager:
    """Manages checkpoint creation and restoration."""

    def save_checkpoint(self, data: Dict[str, Any], path: Path) -> Path:
        """Save checkpoint data to file."""
        try:
            # Convert complex objects to serializable format
            serializable_data = self._make_serializable(data)

            with open(path, 'w') as f:
                json.dump(serializable_data, f, indent=2, default=str)

            logger.info(f"Checkpoint saved: {path}")
            return path

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")
            return path

    def load_checkpoint(self, path: Path) -> Result[Dict[str, Any], str]:
        """Load checkpoint data from file."""
        try:
            with open(path, 'r') as f:
                data = json.load(f)

            # Deserialize complex objects
            restored_data = self._restore_from_serializable(data)

            logger.info(f"Checkpoint loaded: {path}")
            return Result.Ok(restored_data)

        except Exception as e:
            return Result.Err(f"Failed to load checkpoint: {str(e)}")

    def _make_serializable(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format."""
        if hasattr(obj, '__dict__'):
            return {key: self._make_serializable(value) for key, value in obj.__dict__.items()}
        elif isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, Path):
            return str(obj)
        else:
            return obj

    def _restore_from_serializable(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Restore objects from serialized format."""
        restored = {}

        for key, value in data.items():
            if isinstance(value, dict):
                # Check if this looks like a BatchProgress object
                if self._is_batch_progress_dict(value):
                    restored[key] = self._reconstruct_batch_progress(value)
                # Check if this looks like a ProcessedFile object
                elif self._is_processed_file_dict(value):
                    restored[key] = self._reconstruct_processed_file(value)
                else:
                    # Recursively restore nested dictionaries
                    restored[key] = self._restore_from_serializable(value)
            elif isinstance(value, list):
                # Restore list of objects
                restored[key] = [
                    self._reconstruct_processed_file(item) if self._is_processed_file_dict(item)
                    else self._restore_from_serializable(item) if isinstance(item, dict)
                    else item
                    for item in value
                ]
            else:
                restored[key] = value

        return restored

    def _is_batch_progress_dict(self, obj: Dict[str, Any]) -> bool:
        """Check if dictionary represents a BatchProgress object."""
        required_fields = ['total_files', 'processed_files', 'successful_files', 'failed_files']
        return all(field in obj for field in required_fields)

    def _reconstruct_batch_progress(self, data: Dict[str, Any]) -> 'BatchProgress':
        """Reconstruct BatchProgress from dictionary."""
        return BatchProgress(
            total_files=data.get('total_files', 0),
            processed_files=data.get('processed_files', 0),
            successful_files=data.get('successful_files', 0),
            failed_files=data.get('failed_files', 0),
            skipped_files=data.get('skipped_files', 0),
            start_time=data.get('start_time', time.time()),
            last_checkpoint=data.get('last_checkpoint', time.time()),
            current_batch=data.get('current_batch', 0),
            total_batches=data.get('total_batches', 0),
            estimated_completion=data.get('estimated_completion'),
            processing_rate=data.get('processing_rate', 0.0)
        )

    def _is_processed_file_dict(self, obj: Any) -> bool:
        """Check if object represents a ProcessedFile."""
        if not isinstance(obj, dict):
            return False
        required_fields = ['path', 'file_type', 'chunks', 'metadata']
        return all(field in obj for field in required_fields)

    def _reconstruct_processed_file(self, data: Dict[str, Any]) -> Any:
        """Reconstruct ProcessedFile from dictionary."""
        try:
            from ..core.orchestrator import ProcessedFile
            from pathlib import Path

            return ProcessedFile(
                path=Path(data['path']),
                file_type=data.get('file_type', 'unknown'),
                chunks=data.get('chunks', []),
                metadata=data.get('metadata', {}),
                embeddings=data.get('embeddings'),
                processing_time=data.get('processing_time', 0.0),
                error=data.get('error')
            )
        except ImportError:
            # Fallback to dict if ProcessedFile not available
            return data


class ResourceMonitor:
    """Monitors system resources during batch processing."""

    def check_resources(self, config: BatchConfig) -> bool:
        """Check if system has sufficient resources to continue."""
        try:
            import psutil

            # Check memory usage
            memory = psutil.virtual_memory()
            memory_usage_mb = (memory.total - memory.available) / (1024 * 1024)

            if memory_usage_mb > config.memory_threshold_mb:
                logger.warning(f"Memory usage high: {memory_usage_mb:.1f}MB")
                return False

            # Check disk space
            disk = psutil.disk_usage('.')
            free_space_mb = disk.free / (1024 * 1024)

            if free_space_mb < config.disk_space_threshold_mb:
                logger.warning(f"Low disk space: {free_space_mb:.1f}MB")
                return False

            return True

        except ImportError:
            logger.warning("psutil not available for resource monitoring")
            return True
        except Exception as e:
            logger.warning(f"Resource check failed: {e}")
            return True
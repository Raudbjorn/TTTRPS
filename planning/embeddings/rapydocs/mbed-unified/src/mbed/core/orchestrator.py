"""
Embedding orchestrator for coordinating all operations
"""

import time
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .result import Result
from .config import MBEDSettings
from ..backends.base import BackendFactory, EmbeddingBackend
from ..pipeline.chunker import ChunkerFactory, ChunkingStrategy, ChunkConfig

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing operation."""
    files_processed: int
    chunks_created: int
    embeddings_generated: int
    errors: List[str]
    duration_seconds: float
    strategy_usage: Dict[str, int]


@dataclass
class ProcessedFile:
    """Result of processing a single file."""
    path: Path
    file_type: str
    chunks: List[Any]
    metadata: Dict[str, Any]
    embeddings: Optional[List[float]] = None
    processing_time: float = 0.0
    error: Optional[str] = None


class EmbeddingOrchestrator:
    """Central coordinator for all embedding operations."""

    def __init__(self, config: MBEDSettings):
        """
        Initialize orchestrator with configuration.

        Args:
            config: MBED configuration settings
        """
        self.config = config
        self.backend: Optional[EmbeddingBackend] = None
        self.chunker: Optional[ChunkingStrategy] = None
        self.storage = None
        self._is_initialized = False
        self._executor = None

    def initialize(self) -> Result[None, str]:
        """Initialize all components with proper error handling."""
        try:
            logger.info("Initializing EmbeddingOrchestrator...")

            # Initialize backend based on hardware detection
            self.backend = BackendFactory.create(self.config)
            logger.info(f"Initialized backend: {self.backend.__class__.__name__}")

            # Initialize chunking strategy
            chunk_config = ChunkConfig(
                size=self.config.chunk_size,
                overlap=self.config.chunk_overlap,
                strategy_specific={}
            )
            self.chunker = ChunkerFactory.create(
                self.config.chunk_strategy,
                chunk_config
            )
            logger.info(f"Initialized chunker: {self.config.chunk_strategy}")

            # TODO: Initialize storage backend when database components are available
            # self.storage = StorageFactory.create(
            #     self.config.database,
            #     self.config.db_config
            # )

            # Initialize thread pool for parallel processing
            self._executor = ThreadPoolExecutor(max_workers=self.config.workers)

            self._is_initialized = True
            logger.info("EmbeddingOrchestrator initialization complete")
            return Result.Ok(None)

        except Exception as e:
            error_msg = f"Initialization failed: {str(e)}"
            logger.error(error_msg)
            return Result.Err(error_msg)

    async def process_files(
        self,
        files: List[Path]
    ) -> Result[ProcessingResult, str]:
        """
        Main processing pipeline with error recovery.
        Coordinates: Chunking → Encoding → Storage → Indexing
        """
        if not self._is_initialized:
            init_result = self.initialize()
            if init_result.is_err():
                return Result.Err(init_result.unwrap_err())

        start_time = time.time()
        processed_files = []
        errors = []
        strategy_usage = {}

        logger.info(f"Processing {len(files)} files...")

        try:
            # Process files in parallel batches
            batch_size = min(self.config.workers, len(files))

            for i in range(0, len(files), batch_size):
                batch = files[i:i + batch_size]

                # Process batch in parallel
                batch_results = await self._process_batch(batch)

                for result in batch_results:
                    if result.error:
                        errors.append(f"{result.path}: {result.error}")
                    else:
                        processed_files.append(result)

                        # Track strategy usage
                        file_type = result.file_type
                        strategy_usage[file_type] = strategy_usage.get(file_type, 0) + 1

        except Exception as e:
            error_msg = f"Processing pipeline failed: {str(e)}"
            logger.error(error_msg)
            return Result.Err(error_msg)

        # Calculate statistics
        duration = time.time() - start_time
        total_chunks = sum(len(f.chunks) for f in processed_files)
        total_embeddings = sum(len(f.embeddings or []) for f in processed_files)

        result = ProcessingResult(
            files_processed=len(processed_files),
            chunks_created=total_chunks,
            embeddings_generated=total_embeddings,
            errors=errors,
            duration_seconds=duration,
            strategy_usage=strategy_usage
        )

        logger.info(f"Processing complete: {result.files_processed} files, "
                   f"{result.chunks_created} chunks, {result.duration_seconds:.2f}s")

        return Result.Ok(result)

    async def _process_batch(self, files: List[Path]) -> List[ProcessedFile]:
        """Process a batch of files in parallel."""
        loop = asyncio.get_event_loop()

        # Create tasks for parallel processing
        tasks = []
        for file_path in files:
            task = loop.run_in_executor(
                self._executor,
                self._process_single_file,
                file_path
            )
            tasks.append(task)

        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ProcessedFile(
                    path=files[i],
                    file_type="unknown",
                    chunks=[],
                    metadata={},
                    error=str(result)
                ))
            else:
                processed_results.append(result)

        return processed_results

    def _process_single_file(self, file_path: Path) -> ProcessedFile:
        """Process a single file through the complete pipeline."""
        start_time = time.time()

        try:
            # Validate file exists
            if not file_path.exists():
                return ProcessedFile(
                    path=file_path,
                    file_type="unknown",
                    chunks=[],
                    metadata={},
                    error="File not found"
                )

            # Detect file type
            file_type = self._detect_file_type(file_path)

            # Read content
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                # Try with other encodings
                for encoding in ['latin-1', 'cp1252']:
                    try:
                        content = file_path.read_text(encoding=encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    return ProcessedFile(
                        path=file_path,
                        file_type=file_type,
                        chunks=[],
                        metadata={},
                        error="Unable to decode file"
                    )

            # Configure chunking based on file type
            chunk_config = self._get_chunk_config_for_file_type(file_type)

            # Chunk the content
            chunks_result = self.chunker.chunk(content, chunk_config)
            if chunks_result.is_err():
                return ProcessedFile(
                    path=file_path,
                    file_type=file_type,
                    chunks=[],
                    metadata={},
                    error=f"Chunking failed: {chunks_result.unwrap_err()}"
                )

            chunks = chunks_result.unwrap()

            # Generate embeddings for chunks
            embeddings = None
            if chunks and self.backend:
                try:
                    chunk_texts = [chunk.text for chunk in chunks]
                    embeddings = self.backend.generate_embeddings(chunk_texts)
                except Exception as e:
                    logger.warning(f"Failed to generate embeddings for {file_path}: {e}")

            processing_time = time.time() - start_time

            return ProcessedFile(
                path=file_path,
                file_type=file_type,
                chunks=chunks,
                metadata={
                    'size': len(content),
                    'lines': content.count('\n') + 1,
                    'words': len(content.split())
                },
                embeddings=embeddings,
                processing_time=processing_time
            )

        except Exception as e:
            return ProcessedFile(
                path=file_path,
                file_type="unknown",
                chunks=[],
                metadata={},
                error=str(e),
                processing_time=time.time() - start_time
            )

    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type based on extension and content."""
        suffix = file_path.suffix.lower()

        if suffix in ['.py']:
            return 'python'
        elif suffix in ['.js', '.ts', '.jsx', '.tsx']:
            return 'javascript'
        elif suffix in ['.rs']:
            return 'rust'
        elif suffix in ['.md']:
            return 'markdown'
        elif suffix in ['.txt']:
            return 'text'
        elif suffix in ['.json']:
            return 'json'
        elif suffix in ['.xml']:
            return 'xml'
        elif suffix in ['.html', '.htm']:
            return 'html'
        else:
            return 'text'

    def _get_chunk_config_for_file_type(self, file_type: str):
        """Get appropriate chunk configuration for file type."""
        from ..pipeline.chunker import ChunkConfig

        # Base configuration
        base_config = ChunkConfig(
            size=self.config.chunk_size,
            overlap=self.config.chunk_overlap,
            strategy_specific={}
        )

        # File type specific adjustments
        if file_type in ['python', 'javascript', 'rust']:
            base_config.strategy_specific = {'language': file_type}
        elif file_type == 'markdown':
            base_config.strategy_specific = {'preserve_headers': True}
        elif file_type == 'json':
            base_config.strategy_specific = {'preserve_structure': True}

        return base_config

    def get_backend_info(self) -> Dict[str, Any]:
        """Get information about current backend configuration."""
        if not self.backend:
            return {"status": "not_initialized"}

        info = self.backend.get_info()
        info.update({
            "chunking_strategy": self.config.chunk_strategy,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "workers": self.config.workers,
            "initialized": self._is_initialized
        })

        return info

    def cleanup(self):
        """Clean up resources."""
        if self.backend:
            if hasattr(self.backend, 'cleanup'):
                self.backend.cleanup()

        if self._executor:
            self._executor.shutdown(wait=True)
            self._executor = None

        logger.info("EmbeddingOrchestrator cleanup complete")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
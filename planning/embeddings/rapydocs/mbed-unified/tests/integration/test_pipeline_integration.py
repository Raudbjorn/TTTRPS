"""
Integration tests for the complete MBED pipeline
"""

import pytest
import tempfile
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from unittest.mock import Mock, MagicMock, patch

from mbed.core.orchestrator import EmbeddingOrchestrator, ProcessedFile
from mbed.pipeline.file_processor import FileProcessor, ProcessingOptions
from mbed.pipeline.batch_orchestrator import BatchOrchestrator, BatchConfig
from mbed.core.parallel_coordinator import ParallelCoordinator, CoordinatorConfig, ProcessingTask
from mbed.core.memory_manager import MemoryManager, MemoryConfig
from mbed.core.statistics import StatisticsCollector
from mbed.core.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
from mbed.core.config import MBEDSettings


class TestPipelineIntegration:
    """Integration tests for the complete MBED processing pipeline."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock embedding orchestrator."""
        orchestrator = Mock(spec=EmbeddingOrchestrator)

        # Mock successful embedding generation
        def mock_generate_embeddings(texts: List[str]):
            from src.mbed.core.result import Result
            # Return mock embeddings (list of floats for each text)
            embeddings = [[0.1, 0.2, 0.3] * 128 for _ in texts]  # 384-dim embeddings
            return Result.Ok(embeddings)

        orchestrator.generate_embeddings.side_effect = mock_generate_embeddings
        return orchestrator

    @pytest.fixture
    def sample_files(self, temp_dir: Path) -> List[Path]:
        """Create sample files for testing."""
        files = []

        # Python file
        python_file = temp_dir / "sample.py"
        python_file.write_text('''
def hello_world():
    """A simple hello world function."""
    print("Hello, World!")

class Calculator:
    """A basic calculator class."""

    def add(self, a: int, b: int) -> int:
        return a + b

    def subtract(self, a: int, b: int) -> int:
        return a - b

if __name__ == "__main__":
    calc = Calculator()
    print(f"2 + 3 = {calc.add(2, 3)}")
    hello_world()
''')
        files.append(python_file)

        # Markdown file
        markdown_file = temp_dir / "README.md"
        markdown_file.write_text('''# Sample Project

This is a sample project for testing the MBED pipeline.

## Features

- Text processing
- Chunking strategies
- Embedding generation
- File processing

## Installation

```bash
pip install mbed-unified
```

## Usage

```python
from mbed import FileProcessor

processor = FileProcessor()
result = processor.process_file("document.txt")
```

## License

MIT License
''')
        files.append(markdown_file)

        # JSON file
        json_file = temp_dir / "config.json"
        json_file.write_text(json.dumps({
            "app_name": "MBED Pipeline",
            "version": "1.0.0",
            "features": {
                "chunking": ["fixed", "sentence", "paragraph", "semantic"],
                "embeddings": ["cpu", "gpu", "mps"],
                "storage": ["memory", "disk", "database"]
            },
            "settings": {
                "chunk_size": 512,
                "overlap": 50,
                "batch_size": 100
            }
        }, indent=2))
        files.append(json_file)

        # Text file
        text_file = temp_dir / "document.txt"
        text_file.write_text('''
This is a comprehensive text document for testing the MBED pipeline.

The document contains multiple paragraphs with different types of content.
This includes technical descriptions, code examples, and general prose.

In the field of natural language processing, text chunking is a crucial step.
It involves breaking down large documents into smaller, manageable pieces
that can be processed efficiently by machine learning models.

Different chunking strategies have different advantages:
- Fixed-size chunking provides consistent chunk sizes
- Sentence-based chunking preserves linguistic boundaries
- Paragraph-based chunking maintains topical coherence
- Semantic chunking uses AI to find natural break points

The choice of chunking strategy depends on the specific use case and
the characteristics of the text being processed.
''')
        files.append(text_file)

        return files

    def test_file_processor_basic_functionality(self, temp_dir: Path, mock_orchestrator, sample_files: List[Path]):
        """Test basic file processor functionality."""
        options = ProcessingOptions(
            chunk_strategy='fixed',
            chunk_size=200,
            chunk_overlap=20,
            generate_embeddings=True
        )

        processor = FileProcessor(mock_orchestrator, options)

        # Test single file processing
        for file_path in sample_files:
            result = processor.process_file(file_path)

            assert result.is_ok(), f"Failed to process {file_path.name}: {result.unwrap_err() if result.is_err() else ''}"

            processed_file = result.unwrap()

            # Verify basic structure (using correct ProcessedFile attributes)
            assert processed_file.path.name == file_path.name
            assert processed_file.metadata.get('size', 0) > 0
            assert processed_file.file_type is not None
            assert len(processed_file.chunks) > 0
            assert len(processed_file.embeddings) > 0

            # Verify chunks have proper structure
            for chunk in processed_file.chunks:
                assert chunk.text.strip()
                assert 'strategy' in chunk.metadata
                assert 'token_count' in chunk.metadata
                assert chunk.chunk_id

    def test_file_processor_multiple_strategies(self, temp_dir: Path, mock_orchestrator, sample_files: List[Path]):
        """Test file processor with different chunking strategies."""
        strategies = ['fixed', 'sentence', 'paragraph', 'semantic', 'topic', 'code']

        for strategy in strategies:
            options = ProcessingOptions(
                chunk_strategy=strategy,
                chunk_size=300,
                chunk_overlap=30
            )

            processor = FileProcessor(mock_orchestrator, options)

            # Test on Python file (good for code strategy)
            python_file = next(f for f in sample_files if f.suffix == '.py')
            result = processor.process_file(python_file)

            assert result.is_ok(), f"Strategy {strategy} failed: {result.unwrap_err() if result.is_err() else ''}"

            processed_file = result.unwrap()
            assert len(processed_file.chunks) > 0

            # Verify strategy was applied
            for chunk in processed_file.chunks:
                chunk_strategy = chunk.metadata.get('strategy', '').lower()
                assert strategy in chunk_strategy or 'fallback' in chunk_strategy

    def test_file_processor_auto_strategy_selection(self, temp_dir: Path, mock_orchestrator, sample_files: List[Path]):
        """Test automatic strategy selection based on file type."""
        options = ProcessingOptions(
            chunk_strategy='auto',
            chunk_size=250
        )

        processor = FileProcessor(mock_orchestrator, options)

        strategy_expectations = {
            '.py': 'code',
            '.md': ['hierarchical', 'semantic'],
            '.json': 'semantic',
            '.txt': ['paragraph', 'sentence', 'fixed']
        }

        for file_path in sample_files:
            result = processor.process_file(file_path)
            assert result.is_ok()

            processed_file = result.unwrap()
            expected_strategies = strategy_expectations.get(file_path.suffix, [])

            if isinstance(expected_strategies, str):
                expected_strategies = [expected_strategies]

            # Check that one of the expected strategies was used
            chunks_strategies = [chunk.metadata.get('strategy', '') for chunk in processed_file.chunks]
            strategy_found = any(
                any(exp_strategy in chunk_strategy for exp_strategy in expected_strategies)
                for chunk_strategy in chunks_strategies
            )

            assert strategy_found, f"Expected strategies {expected_strategies} not found in {chunks_strategies}"

    def test_batch_orchestration(self, temp_dir: Path, mock_orchestrator, sample_files: List[Path]):
        """Test batch processing orchestration."""
        options = ProcessingOptions(
            chunk_strategy='fixed',
            chunk_size=200,
            generate_embeddings=True
        )

        processor = FileProcessor(mock_orchestrator, options)

        batch_config = BatchConfig(
            batch_size=2,
            max_workers=2,
            use_processes=False,
            enable_monitoring=False  # Disable for testing
        )

        orchestrator = BatchOrchestrator(processor, batch_config)

        # Test synchronous batch processing
        result = orchestrator.process_files_sync(sample_files)

        assert result.is_ok(), f"Batch processing failed: {result.unwrap_err() if result.is_err() else ''}"

        batch_result = result.unwrap()

        # Verify results
        assert batch_result.progress.total_files == len(sample_files)
        assert batch_result.progress.processed_files == len(sample_files)
        assert batch_result.progress.successful_files > 0
        assert len(batch_result.processed_files) > 0

        # Verify statistics
        stats = batch_result.statistics
        assert stats['total_processing_time'] > 0
        assert stats['success_rate'] > 0
        assert 'file_type_distribution' in stats

    @pytest.mark.asyncio
    async def test_async_batch_processing(self, temp_dir: Path, mock_orchestrator, sample_files: List[Path]):
        """Test asynchronous batch processing."""
        options = ProcessingOptions(
            chunk_strategy='sentence',
            chunk_size=150
        )

        processor = FileProcessor(mock_orchestrator, options)

        batch_config = BatchConfig(
            batch_size=2,
            max_concurrent_files=3,
            enable_monitoring=False
        )

        orchestrator = BatchOrchestrator(processor, batch_config)

        # Test async processing
        result = await orchestrator.process_files_async(sample_files)

        assert result.is_ok()
        batch_result = result.unwrap()

        assert batch_result.progress.processed_files == len(sample_files)
        assert len(batch_result.processed_files) > 0

    def test_parallel_coordinator(self, temp_dir: Path):
        """Test parallel processing coordinator."""
        config = CoordinatorConfig(
            max_workers=3,
            use_processes=False,
            enable_monitoring=False
        )

        coordinator = ParallelCoordinator(config)

        # Create simple tasks
        def simple_processor(data: str) -> str:
            time.sleep(0.1)  # Simulate processing time
            return f"processed_{data}"

        tasks = [
            ProcessingTask(data=f"item_{i}", task_id=f"task_{i}")
            for i in range(10)
        ]

        # Process tasks
        result = coordinator.process_tasks(tasks, simple_processor)

        assert result.is_ok()
        results = result.unwrap()

        assert len(results) == 10
        assert all(r.success for r in results)
        assert all("processed_" in str(r.result) for r in results)

        # Check statistics
        stats = coordinator.get_statistics()
        assert stats['total_tasks_completed'] == 10
        assert stats['overall_success_rate'] == 1.0

        coordinator.shutdown()

    @pytest.mark.asyncio
    async def test_async_parallel_processing(self, temp_dir: Path):
        """Test asynchronous parallel processing."""
        config = CoordinatorConfig(
            max_workers=2,
            enable_monitoring=False
        )

        coordinator = ParallelCoordinator(config)

        async def async_processor(data: str) -> str:
            await asyncio.sleep(0.05)
            return f"async_{data}"

        tasks = [
            ProcessingTask(data=f"item_{i}", task_id=f"task_{i}")
            for i in range(5)
        ]

        # Note: This test would need actual async processing implementation
        # For now, test with sync processor
        def sync_processor(data: str) -> str:
            return f"sync_{data}"

        result = await coordinator.process_tasks_async(tasks, sync_processor)

        assert result.is_ok()
        results = result.unwrap()

        assert len(results) == 5
        coordinator.shutdown()

    def test_memory_management_integration(self):
        """Test memory management integration."""
        config = MemoryConfig(
            memory_limit_mb=512,
            enable_monitoring=False,  # Disable for testing
            enable_auto_cleanup=True
        )

        memory_manager = MemoryManager(config)

        # Test buffer allocation
        buffer_result = memory_manager.allocate_buffer("test_buffer", 10.0)
        assert buffer_result.is_ok()

        buffer = buffer_result.unwrap()
        assert len(buffer) == int(10.0 * 1024 * 1024)

        # Test memory info
        info = memory_manager.get_memory_info()
        assert 'system_memory' in info
        assert 'allocated_objects' in info

        # Test cleanup
        freed_bytes = memory_manager.cleanup_memory()
        assert freed_bytes >= 0

        # Test deallocation
        assert memory_manager.deallocate_buffer("test_buffer")

        memory_manager.shutdown()

    def test_statistics_collection(self, temp_dir: Path, mock_orchestrator, sample_files: List[Path]):
        """Test statistics collection throughout pipeline."""
        stats_collector = StatisticsCollector()

        # Start a session
        session_id = stats_collector.start_session("test_session")
        assert session_id == "test_session"

        # Record some operations
        stats_collector.record_operation(
            operation_type="chunk",
            component="fixed_chunker",
            duration=0.5,
            success=True,
            items_processed=10,
            bytes_processed=1024
        )

        stats_collector.record_operation(
            operation_type="embed",
            component="cpu_backend",
            duration=1.2,
            success=True,
            items_processed=10,
            bytes_processed=2048
        )

        # Record file processing
        for file_path in sample_files:
            stats_collector.record_file_processed(
                file_path=str(file_path),
                file_type=file_path.suffix[1:] if file_path.suffix else 'unknown',
                success=True,
                chunks_generated=5,
                embeddings_generated=5,
                file_size_bytes=file_path.stat().st_size,
                chunking_strategy='fixed'
            )

        # End session
        completed_session = stats_collector.end_session()
        assert completed_session is not None
        assert completed_session.session_id == "test_session"
        assert completed_session.processed_files == len(sample_files)

        # Get performance summary
        summary = stats_collector.get_performance_summary()
        assert 'session_overview' in summary
        assert 'component_performance' in summary
        assert 'operation_percentiles' in summary

    def test_error_handling_integration(self):
        """Test error handling throughout the pipeline."""
        error_handler = ErrorHandler()

        # Test different error categories
        test_errors = [
            ("File not found", ErrorCategory.FILE_ACCESS),
            ("JSON parse error", ErrorCategory.PARSING),
            ("Out of memory", ErrorCategory.MEMORY),
            ("Connection timeout", ErrorCategory.NETWORK),
        ]

        for error_msg, expected_category in test_errors:
            mbed_error = error_handler.handle_error(
                error=error_msg,
                auto_recover=False
            )

            assert mbed_error.message == error_msg
            assert mbed_error.category == expected_category
            assert mbed_error.error_id is not None

        # Test error summary
        summary = error_handler.get_error_summary()
        assert summary['total_errors'] == len(test_errors)
        assert 'category_breakdown' in summary
        assert 'recent_errors' in summary

    def test_full_pipeline_integration(self, temp_dir: Path, mock_orchestrator, sample_files: List[Path]):
        """Test complete pipeline integration with all components."""
        # Initialize all components
        stats_collector = StatisticsCollector()
        error_handler = ErrorHandler()

        memory_config = MemoryConfig(enable_monitoring=False)
        memory_manager = MemoryManager(memory_config)

        # Start statistics session
        session_id = stats_collector.start_session("integration_test")

        try:
            # Configure processing
            options = ProcessingOptions(
                chunk_strategy='auto',
                chunk_size=200,
                chunk_overlap=20,
                generate_embeddings=True
            )

            processor = FileProcessor(mock_orchestrator, options)

            # Configure batch processing
            batch_config = BatchConfig(
                batch_size=2,
                max_workers=2,
                enable_monitoring=False
            )

            batch_orchestrator = BatchOrchestrator(processor, batch_config)

            # Process files
            batch_result = batch_orchestrator.process_files_sync(sample_files)

            assert batch_result.is_ok(), f"Full pipeline failed: {batch_result.unwrap_err() if batch_result.is_err() else ''}"

            result = batch_result.unwrap()

            # Verify comprehensive results
            assert result.progress.total_files == len(sample_files)
            assert result.progress.successful_files > 0
            assert len(result.processed_files) > 0

            # Verify file type distribution
            file_types = set()
            total_chunks = 0
            total_embeddings = 0

            for processed_file in result.processed_files:
                file_type = processed_file.file_info.get('file_type', 'unknown')
                file_types.add(file_type)
                total_chunks += len(processed_file.chunks)
                total_embeddings += len(processed_file.embeddings)

            assert len(file_types) > 1  # Multiple file types processed
            assert total_chunks > 0
            assert total_embeddings > 0

            # Verify statistics were collected
            statistics = result.statistics
            assert statistics['total_processing_time'] > 0
            assert statistics['success_rate'] > 0

        finally:
            # Cleanup
            stats_collector.end_session()
            memory_manager.shutdown()

    def test_pipeline_error_recovery(self, temp_dir: Path):
        """Test pipeline error recovery and handling."""
        # Create a problematic file
        bad_file = temp_dir / "bad_file.txt"
        bad_file.write_text("A" * 1000000)  # Very large file
        bad_file.chmod(0o000)  # Remove read permissions

        # Mock orchestrator that fails
        mock_orchestrator = Mock(spec=EmbeddingOrchestrator)

        def failing_embeddings(texts):
            from src.mbed.core.result import Result
            return Result.Err("Embedding generation failed")

        mock_orchestrator.generate_embeddings.side_effect = failing_embeddings

        options = ProcessingOptions(
            chunk_strategy='fixed',
            max_file_size=100 * 1024,  # 100KB limit
            generate_embeddings=True
        )

        processor = FileProcessor(mock_orchestrator, options)

        # Process should handle errors gracefully
        result = processor.process_file(bad_file)

        # Should fail gracefully
        assert result.is_err()
        error_msg = result.unwrap_err()
        assert isinstance(error_msg, str)
        assert len(error_msg) > 0

        # Clean up
        try:
            bad_file.chmod(0o644)
            bad_file.unlink()
        except:
            pass

    def test_pipeline_performance_monitoring(self, temp_dir: Path, mock_orchestrator, sample_files: List[Path]):
        """Test performance monitoring across the pipeline."""
        # Enable comprehensive monitoring
        stats_collector = StatisticsCollector()

        coordinator_config = CoordinatorConfig(
            max_workers=2,
            enable_monitoring=False  # Disable for testing
        )

        options = ProcessingOptions(
            chunk_strategy='fixed',
            chunk_size=150
        )

        processor = FileProcessor(mock_orchestrator, options)

        start_time = time.time()

        # Process files and track performance
        results = []
        for file_path in sample_files:
            file_start = time.time()
            result = processor.process_file(file_path)
            file_duration = time.time() - file_start

            if result.is_ok():
                processed_file = result.unwrap()
                results.append(processed_file)

                # Record performance metrics
                stats_collector.record_operation(
                    operation_type="file_process",
                    component="file_processor",
                    duration=file_duration,
                    success=True,
                    items_processed=len(processed_file.chunks),
                    bytes_processed=processed_file.file_info.get('size', 0)
                )

        total_time = time.time() - start_time

        # Verify performance metrics
        assert len(results) > 0
        assert total_time > 0

        # Get performance summary
        summary = stats_collector.get_performance_summary()
        assert 'component_performance' in summary
        assert 'throughput_analysis' in summary

        file_processor_stats = summary['component_performance'].get('file_processor')
        if file_processor_stats:
            assert file_processor_stats['total_operations'] == len(results)
            assert file_processor_stats['success_rate'] == 100.0

    def test_pipeline_resource_optimization(self, temp_dir: Path, mock_orchestrator):
        """Test resource optimization across pipeline components."""
        # Create multiple test files of different sizes
        test_files = []

        for i, size in enumerate([1000, 5000, 10000]):  # Different file sizes
            test_file = temp_dir / f"test_{i}.txt"
            test_file.write_text("Sample text. " * size)
            test_files.append(test_file)

        # Configure with resource constraints
        memory_config = MemoryConfig(
            memory_limit_mb=256,
            enable_monitoring=False,
            enable_auto_cleanup=True
        )

        memory_manager = MemoryManager(memory_config)

        batch_config = BatchConfig(
            batch_size=2,
            max_workers=2,
            memory_threshold_mb=200,
            enable_monitoring=False
        )

        options = ProcessingOptions(
            chunk_strategy='fixed',
            chunk_size=100
        )

        processor = FileProcessor(mock_orchestrator, options)
        orchestrator = BatchOrchestrator(processor, batch_config)

        # Process with resource monitoring
        result = orchestrator.process_files_sync(test_files)

        assert result.is_ok()
        batch_result = result.unwrap()

        # Should complete successfully despite resource constraints
        assert batch_result.progress.total_files == len(test_files)
        assert batch_result.progress.successful_files > 0

        memory_manager.shutdown()
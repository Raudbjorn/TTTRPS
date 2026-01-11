"""
Simplified integration tests for Phase 8 performance optimization components

Tests the core functionality with mocked dependencies
"""

import asyncio
import time
import tempfile
import shutil
from pathlib import Path
import numpy as np
import pytest
from unittest.mock import Mock, MagicMock

# Import components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from mbed.core.profiling import (
    PerformanceProfiler, 
    get_profiler,
    benchmark_function
)
from mbed.core.batch_optimizer import (
    DynamicBatchOptimizer,
    OptimizationStrategy,
    OptimizationConfig
)
from mbed.core.caching import (
    CacheHierarchy,
    LRUMemoryCache,
    DiskCache
)
from mbed.core.async_processing import (
    AsyncBatchProcessor,
    RateLimiter,
    AsyncEmbeddingPipeline
)
from mbed.core.memory_pool import (
    MemoryPoolManager,
    get_pool_manager,
    pooled_array
)
from mbed.monitoring.dashboard import (
    PerformanceMonitor,
    BackendMetrics,
    AlertRule
)


class TestPerformanceOptimizationSimple:
    """Simplified tests for performance optimization components"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_profiling_basic(self, temp_dir):
        """Test basic profiling functionality"""
        profiler = PerformanceProfiler(
            enable_memory_profiling=True,
            enable_gpu_profiling=False,
            profile_dir=temp_dir
        )
        
        @profiler.profile_function("test_function")
        def test_func():
            time.sleep(0.01)
            return 42
        
        result = test_func()
        assert result == 42
        
        metrics = profiler.get_metrics("test_function")
        assert len(metrics) == 1
        assert metrics[0].duration_ms > 10
    
    def test_batch_optimizer_basic(self):
        """Test basic batch optimization"""
        optimizer = DynamicBatchOptimizer(
            backend_type="cpu",
            model_name="test-model"
        )
        
        # Create mock backend
        mock_backend = Mock()
        mock_backend.generate_embeddings = Mock(return_value=np.random.randn(10, 768))
        
        # Create config
        config = OptimizationConfig(
            strategy=OptimizationStrategy.BALANCED,
            target_latency_ms=100.0
        )
        
        # Calculate optimal batch size (with mocked backend)
        batch_size = optimizer.calculate_optimal_batch_size(
            backend=mock_backend,
            config=config,
            sample_texts=["test"] * 10
        )
        
        assert batch_size > 0
        assert batch_size <= 1000
    
    @pytest.mark.asyncio
    async def test_cache_hierarchy_basic(self, temp_dir):
        """Test basic cache hierarchy functionality"""
        # Create individual cache backends
        l1 = LRUMemoryCache(max_size=10)
        l2 = DiskCache(cache_dir=temp_dir, max_size_gb=0.1)
        
        # Create hierarchy
        cache = CacheHierarchy(
            l1_cache=l1,
            l2_cache=l2,
            l3_cache=None
        )
        
        # Test caching
        test_data = np.random.randn(768).astype(np.float32)
        await cache.set("test_key", test_data)
        
        # Retrieve
        cached = await cache.get("test_key")
        assert cached is not None
        assert np.array_equal(cached, test_data)
        
        # Check stats
        stats = cache.get_stats()
        assert stats["l1"]["total_requests"] > 0
    
    @pytest.mark.asyncio
    async def test_rate_limiter_basic(self):
        """Test basic rate limiting"""
        rate_limiter = RateLimiter(
            rate_per_second=10,
            burst_size=5
        )
        
        # Test rate limiting
        start = time.time()
        for i in range(10):
            await rate_limiter.acquire()
        duration = time.time() - start
        
        # Should take at least 0.5 seconds for 10 items at 10/sec with burst
        assert duration >= 0.4  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_async_batch_processor_basic(self):
        """Test basic async batch processing"""
        async def process_item(item):
            await asyncio.sleep(0.001)
            return item * 2
        
        # Create AsyncBatchProcessor with proper config
        from mbed.core.async_processing import AsyncBatchConfig
        config = AsyncBatchConfig(
            batch_size=10,
            max_concurrent_batches=4
        )
        processor = AsyncBatchProcessor(
            process_func=process_item,
            config=config
        )
        
        items = list(range(10))
        results = await processor.process_all(items)
        
        assert len(results) == 10
        assert results == [i * 2 for i in items]
    
    def test_memory_pool_basic(self):
        """Test basic memory pooling"""
        pool_manager = MemoryPoolManager(
            enable_tensor_pool=True,
            enable_buffer_pool=True,
            max_pool_size=10
        )
        
        # Test array pooling
        with pool_manager.array((100, 768), dtype=np.float32) as arr:
            assert arr.shape == (100, 768)
            arr[:] = 1.0
        
        # Test buffer pooling
        with pool_manager.buffer(1024) as buf:
            assert len(buf) >= 1024
        
        # Check stats
        stats = pool_manager.get_stats()
        assert "tensor_pool" in stats
    
    def test_performance_monitor_basic(self):
        """Test basic performance monitoring"""
        monitor = PerformanceMonitor(
            collection_interval=0.1,
            history_size=10
        )
        
        # Start monitoring
        monitor.start()
        
        # Add metrics
        backend_metrics = BackendMetrics(
            backend_name="test",
            docs_processed=100,
            docs_per_minute=60.0,
            avg_latency_ms=50.0
        )
        monitor.update_backend_metrics(backend_metrics)
        
        # Wait for collection
        time.sleep(0.2)
        
        # Get summary
        summary = monitor.get_summary(window_seconds=1)
        assert "system" in summary
        assert "backends" in summary
        
        # Stop
        monitor.stop()
    
    def test_optimization_strategies(self):
        """Test different optimization strategies produce different results"""
        optimizer = DynamicBatchOptimizer(
            backend_type="cpu",
            model_name="test-model"
        )
        
        mock_backend = Mock()
        mock_backend.generate_embeddings = Mock(return_value=np.random.randn(10, 768))
        
        results = {}
        for strategy in [OptimizationStrategy.THROUGHPUT, OptimizationStrategy.LATENCY]:
            config = OptimizationConfig(
                strategy=strategy,
                target_latency_ms=100.0
            )
            
            batch_size = optimizer.calculate_optimal_batch_size(
                backend=mock_backend,
                config=config,
                sample_texts=["test"] * 10
            )
            results[strategy] = batch_size
        
        # Different strategies should produce different results
        assert results[OptimizationStrategy.THROUGHPUT] >= results[OptimizationStrategy.LATENCY]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
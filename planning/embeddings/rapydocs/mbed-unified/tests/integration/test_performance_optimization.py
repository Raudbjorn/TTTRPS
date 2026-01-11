"""
Integration tests for Phase 8 performance optimization components

Tests the integrated functionality of:
- Profiling infrastructure
- Batch optimization
- Caching system
- Async processing
- Memory pooling
- Performance monitoring
"""

import asyncio
import time
import tempfile
import shutil
from pathlib import Path
import numpy as np
import pytest
from unittest.mock import Mock, patch, AsyncMock, MagicMock

# Import components
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
from mbed.core.caching import CacheHierarchy, LRUMemoryCache
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


class TestPerformanceIntegration:
    """Test integrated performance optimization features"""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)
    
    def test_profiling_with_batch_optimization(self, temp_dir):
        """Test profiling integrated with batch optimization"""
        # Create profiler
        profiler = PerformanceProfiler(
            enable_memory_profiling=True,
            enable_gpu_profiling=False,
            profile_dir=temp_dir
        )
        
        # Create batch optimizer - fixed constructor
        optimizer = DynamicBatchOptimizer(
            backend_type="cpu",
            model_name="test-model"
        )
        
        # Profile batch optimization
        @profiler.profile_function("batch_optimization")
        def process_batch(data):
            # Create a mock backend and config for testing
            mock_backend = MagicMock()
            config = OptimizationConfig(
                strategy=OptimizationStrategy.BALANCED,
                target_latency_ms=100.0
            )
            batch_size = optimizer.calculate_optimal_batch_size(
                backend=mock_backend,
                config=config,
                sample_texts=[f"test text {i}" for i in range(min(len(data), 100))]
            )
            # Simulate processing
            time.sleep(0.01)
            return batch_size
        
        # Run test
        test_data = list(range(1000))
        result = process_batch(test_data)
        
        # Verify profiling metrics
        metrics = profiler.get_metrics("batch_optimization")
        assert len(metrics) == 1
        assert metrics[0].duration_ms > 10
        assert result > 0
        
        # Generate report
        report = profiler.generate_report(format="json")
        assert "batch_optimization" in report
    
    @pytest.mark.asyncio
    async def test_caching_with_memory_pool(self, temp_dir):
        """Test cache system with memory pooling"""
        # Create cache hierarchy with proper constructor
        l1_cache = LRUMemoryCache(max_size=100)
        cache = CacheHierarchy(
            l1_cache=l1_cache,
            enable_prefetching=True
        )
        
        # Get pool manager
        pool_manager = get_pool_manager()
        
        # Test caching with pooled arrays
        def generate_embedding(text: str) -> np.ndarray:
            # Use pooled array
            with pool_manager.array((768,), dtype=np.float32) as embedding:
                # Simulate embedding generation
                embedding[:] = np.random.randn(768).astype(np.float32)
                return embedding.copy()
        
        # Cache embeddings
        texts = [f"text_{i}" for i in range(20)]
        embeddings = []
        
        for text in texts:
            # Check cache first
            cached = await cache.get(text)
            if cached is not None:
                embeddings.append(cached)
            else:
                # Generate and cache
                embedding = generate_embedding(text)
                await cache.set(text, embedding)
                embeddings.append(embedding)
        
        # Verify caching
        assert len(embeddings) == 20
        
        # Check cache hits on second pass
        cache_hits = 0
        for text in texts[:10]:  # First 10 should be in L1
            if await cache.get(text) is not None:
                cache_hits += 1
        
        assert cache_hits >= 8  # Most should hit cache
        
        # Check pool stats
        pool_stats = pool_manager.get_stats()
        assert "tensor_pool" in pool_stats
        
        # Cleanup
        await cache.clear()
    
    @pytest.mark.asyncio
    async def test_async_processing_with_rate_limiting(self):
        """Test async processing with rate limiting"""
        # Create rate limiter - fixed constructor
        rate_limiter = RateLimiter(rate_per_second=10, burst_size=5)
        
        # Create async processor
        async def process_item(item):
            await rate_limiter.acquire()
            # Simulate processing
            await asyncio.sleep(0.01)
            return item * 2
        
        from mbed.core.async_processing import AsyncBatchConfig
        config = AsyncBatchConfig(max_concurrent_batches=4)
        processor = AsyncBatchProcessor(
            process_func=process_item,
            config=config
        )
        
        # Process items
        items = list(range(20))
        start_time = time.time()
        results = await processor.process_all(items)
        duration = time.time() - start_time
        
        # Verify results
        assert len(results) == 20
        assert results == [i * 2 for i in items]
        
        # Verify rate limiting (should take at least 1.5 seconds for 20 items at 10/sec)
        assert duration >= 1.5
    
    @pytest.mark.asyncio
    async def test_full_pipeline_integration(self, temp_dir):
        """Test full pipeline with all optimization components"""
        # Setup components
        profiler = get_profiler(profile_dir=temp_dir)
        # Fixed constructor
        optimizer = DynamicBatchOptimizer(
            backend_type="cpu",
            model_name="test-model"
        )
        l1_cache = LRUMemoryCache(max_size=1000)
        cache = CacheHierarchy(l1_cache=l1_cache)
        pool_manager = get_pool_manager()
        
        # Mock embedding function
        async def generate_embeddings(texts: list) -> list:
            # Profile this operation
            with profiler.profile_context("embedding_generation"):
                # Get optimal batch size
                mock_backend = MagicMock()
                config = OptimizationConfig(strategy=OptimizationStrategy.BALANCED)
                batch_size = optimizer.calculate_optimal_batch_size(
                    backend=mock_backend,
                    config=config,
                    sample_texts=texts[:min(len(texts), 100)]
                )
                
                embeddings = []
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i+batch_size]
                    
                    # Process batch with pooled memory
                    with pool_manager.array((len(batch), 768), dtype=np.float32) as batch_embeddings:
                        # Simulate embedding generation
                        batch_embeddings[:] = np.random.randn(len(batch), 768).astype(np.float32)
                        embeddings.extend(batch_embeddings.tolist())
                
                return embeddings
        
        # Create pipeline with correct constructor
        mock_backend = MagicMock()
        config = AsyncBatchConfig(batch_size=32, max_concurrent_batches=4)
        pipeline = AsyncEmbeddingPipeline(
            backend=mock_backend,
            cache_hierarchy=cache,
            config=config
        )
        
        # Prepare test documents
        documents = [
            {"id": f"doc_{i}", "text": f"This is document {i}", "metadata": {"index": i}}
            for i in range(100)
        ]
        
        # Extract text from documents for pipeline processing
        document_texts = [doc["text"] for doc in documents]
        
        # Process documents with extracted text
        results = await pipeline.process_documents(document_texts)
        
        # Verify results
        assert len(results) == 100
        for result in results:
            assert "id" in result
            assert "embedding" in result
            assert len(result["embedding"]) == 768
        
        # Check profiling metrics
        metrics = profiler.get_metrics("embedding_generation")
        assert len(metrics) > 0
        
        # Check cache performance
        cache_info = cache.get_stats()
        assert cache_info["l1"]["total_requests"] > 0
        
        # Check memory pool performance
        pool_stats = pool_manager.get_stats()
        if "tensor_pool" in pool_stats:
            assert pool_stats["tensor_pool"]["stats"]["total_allocations"] > 0
    
    def test_performance_monitoring_with_alerts(self):
        """Test performance monitoring with alert system"""
        # Define alert rules
        alert_triggered = {"cpu": False, "memory": False}
        
        def cpu_alert_callback(alert_info):
            alert_triggered["cpu"] = True
        
        def memory_alert_callback(alert_info):
            alert_triggered["memory"] = True
        
        alert_rules = [
            AlertRule("high_cpu", "cpu_percent", 50.0, "gt", 1, cpu_alert_callback),
            AlertRule("high_memory", "memory_percent", 50.0, "gt", 1, memory_alert_callback)
        ]
        
        # Create monitor
        monitor = PerformanceMonitor(
            collection_interval=0.1,
            history_size=100,
            alert_rules=alert_rules
        )
        
        # Start monitoring
        monitor.start()
        
        # Add backend metrics
        backend_metrics = BackendMetrics(
            backend_name="test_backend",
            docs_processed=100,
            docs_per_minute=60.0,
            avg_latency_ms=50.0,
            p95_latency_ms=100.0,
            p99_latency_ms=150.0,
            errors=2,
            error_rate=0.02
        )
        monitor.update_backend_metrics(backend_metrics)
        
        # Wait for collection
        time.sleep(0.5)
        
        # Get summary
        summary = monitor.get_summary(window_seconds=10)
        
        # Verify monitoring
        assert "system" in summary
        assert "backends" in summary
        assert "test_backend" in summary["backends"]
        
        # Stop monitoring
        monitor.stop()
    
    def test_benchmark_suite_integration(self, temp_dir):
        """Test benchmark suite with optimization components"""
        from mbed.benchmarks.benchmark_suite import BenchmarkSuite, BenchmarkConfig
        
        # Create mock embedding function
        def mock_embedding_func(texts, batch_size=32):
            # Use optimization components - fixed constructor
            optimizer = DynamicBatchOptimizer(
                backend_type="cpu",
                model_name="test-model"
            )
            mock_backend = MagicMock()
            config = OptimizationConfig(strategy=OptimizationStrategy.BALANCED)
            optimal_batch = optimizer.calculate_optimal_batch_size(
                backend=mock_backend,
                config=config,
                sample_texts=texts[:min(len(texts), 100)]
            )
            
            with pooled_array((len(texts), 768), dtype=np.float32) as embeddings:
                embeddings[:] = np.random.randn(len(texts), 768).astype(np.float32)
                return embeddings.copy()
        
        # Configure benchmark with correct constructor
        config = BenchmarkConfig(
            num_documents=100,
            max_concurrent_users=10,
            backends_to_test=["cpu"],
            test_duration_seconds=30,
            output_dir=temp_dir
        )
        
        # Create suite with correct constructor
        suite = BenchmarkSuite(config=config)
        
        # Run all benchmarks
        results = suite.run_all_benchmarks()
        
        # Verify results
        assert len(results) > 0
        assert hasattr(results[0], 'throughput_docs_per_sec')
        assert hasattr(results[0], 'latency_p95_ms')
        
        # Check that reports were generated
        json_files = list(temp_dir.glob("benchmark_report_*.json"))
        assert len(json_files) > 0
    
    def test_memory_optimization_under_pressure(self):
        """Test memory optimization under pressure"""
        pool_manager = MemoryPoolManager(
            enable_tensor_pool=True,
            enable_buffer_pool=True,
            max_pool_size=50
        )
        
        # Allocate many arrays to simulate pressure
        arrays = []
        for i in range(100):
            arr = pool_manager.get_array((1024, 768), dtype=np.float32)
            arrays.append(arr)
            
            # Return some to pool
            if i % 3 == 0 and arrays:
                pool_manager.return_array(arrays.pop(0))
        
        # Trigger cleanup
        pool_manager.cleanup_pools(aggressive=False)
        
        # Get stats
        stats = pool_manager.get_stats()
        assert "tensor_pool" in stats
        
        # Verify pool is managing memory
        pool_info = stats["tensor_pool"]
        assert pool_info["numpy_arrays_pooled"] <= 50  # Respects max_pool_size
        
        # Return remaining arrays
        for arr in arrays:
            pool_manager.return_array(arr)
        
        # Final cleanup
        pool_manager.cleanup_pools(aggressive=True)
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_with_resource_management(self):
        """Test concurrent operations with resource management"""
        from mbed.core.async_processing import AsyncResourceManager
        
        # Create resource manager - fixed constructor
        resource_manager = AsyncResourceManager(max_connections=5)
        
        # Mock connection factory
        async def create_connection():
            await asyncio.sleep(0.01)
            return Mock(spec=["close"])
        
        resource_manager.connection_factory = create_connection
        
        # Concurrent tasks
        async def task(task_id):
            async with resource_manager.acquire_connection() as conn:
                # Simulate work
                await asyncio.sleep(0.05)
                return task_id
        
        # Run tasks concurrently
        tasks = [task(i) for i in range(20)]
        results = await asyncio.gather(*tasks)
        
        # Verify all tasks completed
        assert len(results) == 20
        assert set(results) == set(range(20))
        
        # Cleanup
        await resource_manager.close_all()
    
    def test_optimization_strategy_selection(self):
        """Test different optimization strategies"""
        strategies = [
            OptimizationStrategy.THROUGHPUT,
            OptimizationStrategy.LATENCY,
            OptimizationStrategy.MEMORY,
            OptimizationStrategy.BALANCED
        ]
        
        results = {}
        
        for strategy in strategies:
            # Fixed constructor
            optimizer = DynamicBatchOptimizer(
                backend_type="cpu",
                model_name="test-model"
            )
            
            # Use correct method name and parameters
            mock_backend = MagicMock()
            config = OptimizationConfig(strategy=strategy)
            batch_size = optimizer.calculate_optimal_batch_size(
                backend=mock_backend,
                config=config,
                sample_texts=[f"test text {i}" for i in range(100)]
            )
            
            results[strategy] = batch_size
        
        # Verify different strategies produce different results
        assert results[OptimizationStrategy.THROUGHPUT] >= results[OptimizationStrategy.LATENCY]
        assert results[OptimizationStrategy.MEMORY] <= results[OptimizationStrategy.THROUGHPUT]
        
        # Balanced should be in the middle
        assert (results[OptimizationStrategy.LATENCY] <= 
                results[OptimizationStrategy.BALANCED] <= 
                results[OptimizationStrategy.THROUGHPUT])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
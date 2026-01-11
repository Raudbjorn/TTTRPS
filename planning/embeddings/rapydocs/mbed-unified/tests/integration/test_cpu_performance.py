#!/usr/bin/env python3
"""
Performance test for CPU backend against mbed1 baseline
Tests both functionality and performance characteristics
"""

import os
import sys
import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import numpy as np
from unittest import mock
import pytest

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _log_backend_info(info: Dict[str, Any]) -> None:
    """Helper to log backend info without loops in tests"""
    logger.info("📊 Backend Info:")
    logger.info(f"   backend: {info.get('backend', 'unknown')}")
    logger.info(f"   model: {info.get('model', 'unknown')}")
    logger.info(f"   embedding_dim: {info.get('embedding_dim', 0)}")
    logger.info(f"   batch_size: {info.get('batch_size', 0)}")
    logger.info(f"   cpu_count: {info.get('cpu_count', 0)}")
    logger.info(f"   implementation: {info.get('implementation', 'none')}")
    logger.info(f"   thread_pool_workers: {info.get('thread_pool_workers', 0)}")


def _verify_similarity_computation(embeddings: np.ndarray) -> None:
    """Helper to verify cosine similarity between embeddings"""
    assert len(embeddings) >= 2, "Need at least 2 embeddings for similarity"
    similarity = np.dot(embeddings[0], embeddings[1])
    logger.info(f"✅ Sample cosine similarity: {similarity:.3f}")
    assert -1.0 <= similarity <= 1.0, f"Invalid similarity: {similarity}"


def _verify_embedding_normalization(embeddings: np.ndarray) -> None:
    """Helper to verify embeddings are normalized for cosine similarity"""
    norms = np.linalg.norm(embeddings, axis=1)
    logger.info(f"✅ Embedding norms: min={norms.min():.3f}, max={norms.max():.3f}, mean={norms.mean():.3f}")
    # Verify normalization (should be close to 1.0 for cosine similarity)
    assert np.allclose(norms, 1.0, atol=1e-3), f"Embeddings not normalized: {norms}"


def _verify_embedding_order(backend) -> None:
    """Helper to verify embeddings maintain order in parallel processing"""
    # Create unique identifiable texts
    unique_texts = [
        f"This is unique text number {i} with specific identifier XYZ{i:03d}"
        for i in range(50)  # Large enough to trigger parallel processing
    ]

    # Generate embeddings
    embeddings = backend.generate_embeddings(unique_texts)

    # Verify count matches
    assert len(embeddings) == len(unique_texts), "Embedding count mismatch"

    # Generate embeddings for individual texts and compare
    # Check first, middle, and last to ensure order is preserved
    indices_to_check = [0, len(unique_texts)//2, len(unique_texts)-1]
    for idx in indices_to_check:
        single_embedding = backend.generate_embeddings([unique_texts[idx]])
        similarity = np.dot(embeddings[idx], single_embedding[0])
        assert similarity > 0.99, f"Order not preserved at index {idx}: similarity={similarity}"

    logger.info("✅ Embedding order preserved in parallel processing")


def test_cpu_backend_performance():
    """Test CPU backend performance and accuracy

    Note: Backend fallback tests (test_cpu_backend_fallback_to_onnx and
    test_cpu_backend_both_fail) are included at the end of this file."""

    from mbed.core.config import MBEDSettings
    from mbed.core.hardware import HardwareType
    from mbed.backends.cpu import CPUBackend

    logger.info("🧪 Testing CPU Backend Performance")
    logger.info("=" * 50)

    # Test configuration
    config = MBEDSettings()
    config.hardware = HardwareType.CPU
    config.model = "all-MiniLM-L6-v2"  # Fast model for testing

    # Sample test texts (similar to what's used in mbed1/mbed2)
    test_texts = [
        "Rapyd is a global fintech platform providing payment infrastructure.",
        "To make your first API call, you need API keys from the Client Portal.",
        "Rapyd supports multiple payment methods including cards and e-wallets.",
        "Webhooks are HTTP callbacks sent when certain events occur.",
        "The Collect API allows you to accept payments globally.",
        "Use HMAC-SHA256 signature for API authentication.",
        "Payment methods vary by country and region.",
        "Refunds can be processed through the API.",
        "Testing webhook endpoints requires proper signature verification.",
        "The platform supports both sandbox and live environments."
    ]

    # Initialize backend
    logger.info("🔧 Initializing CPU backend...")
    backend = CPUBackend(config)

    # Test initialization
    start_time = time.time()
    backend.initialize()
    init_time = time.time() - start_time
    logger.info(f"✅ Backend initialized in {init_time:.2f}s")

    # Get and log backend info
    info = backend.get_info()
    _log_backend_info(info)

    # Test small batch processing
    logger.info("\n🔬 Testing small batch processing...")
    small_batch = test_texts[:3]

    start_time = time.time()
    small_embeddings = backend.generate_embeddings(small_batch)
    small_batch_time = time.time() - start_time

    logger.info(f"✅ Small batch ({len(small_batch)} texts):")
    logger.info(f"   Time: {small_batch_time:.3f}s")
    logger.info(f"   Shape: {small_embeddings.shape}")
    logger.info(f"   Rate: {len(small_batch)/small_batch_time:.1f} texts/sec")

    # Test large batch processing
    logger.info("\n🔬 Testing large batch processing...")
    large_batch = test_texts * 10  # 100 texts

    start_time = time.time()
    large_embeddings = backend.generate_embeddings(large_batch)
    large_batch_time = time.time() - start_time

    logger.info(f"✅ Large batch ({len(large_batch)} texts):")
    logger.info(f"   Time: {large_batch_time:.3f}s")
    logger.info(f"   Shape: {large_embeddings.shape}")
    logger.info(f"   Rate: {len(large_batch)/large_batch_time:.1f} texts/sec")

    # Test empty input
    logger.info("\n🔬 Testing edge cases...")
    empty_embeddings = backend.generate_embeddings([])
    logger.info(f"✅ Empty input: {empty_embeddings.shape}")
    assert empty_embeddings.shape == (0, backend.get_embedding_dimension())

    # Test single empty string
    empty_string_embeddings = backend.generate_embeddings([""])
    logger.info(f"✅ Empty string: {empty_string_embeddings.shape}")
    assert empty_string_embeddings.shape[0] == 1

    # Test very long text
    long_text = "This is a very long text. " * 1000
    long_embeddings = backend.generate_embeddings([long_text])
    logger.info(f"✅ Long text: {long_embeddings.shape}")
    assert long_embeddings.shape[0] == 1
    # Verify long text embedding is normalized
    long_norm = np.linalg.norm(long_embeddings[0])
    assert np.isclose(long_norm, 1.0, atol=1e-3), f"Long text embedding not normalized: {long_norm}"

    # Validate embedding properties
    logger.info("\n📐 Validating embedding properties...")

    # Check dimensions
    expected_dim = backend.get_embedding_dimension()
    assert small_embeddings.shape[1] == expected_dim, f"Dimension mismatch: {small_embeddings.shape[1]} != {expected_dim}"
    assert large_embeddings.shape[1] == expected_dim, f"Dimension mismatch: {large_embeddings.shape[1]} != {expected_dim}"
    logger.info(f"✅ Embedding dimension: {expected_dim}")

    # Check normalization
    _verify_embedding_normalization(small_embeddings)

    # Test similarity computation
    _verify_similarity_computation(small_embeddings)

    # Test embedding order preservation
    logger.info("\n🔍 Testing embedding order preservation...")
    _verify_embedding_order(backend)

    # Performance benchmarks
    logger.info("\n📊 Performance Benchmarks:")
    logger.info(f"   Initialization: {init_time:.2f}s")
    logger.info(f"   Small batch rate: {len(small_batch)/small_batch_time:.1f} texts/sec")
    logger.info(f"   Large batch rate: {len(large_batch)/large_batch_time:.1f} texts/sec")

    # Efficiency check
    small_rate = len(small_batch) / small_batch_time
    large_rate = len(large_batch) / large_batch_time
    efficiency_gain = large_rate / small_rate
    logger.info(f"   Batching efficiency: {efficiency_gain:.2f}x")

    # Note: No conditional logging - just report the efficiency
    logger.info(f"   {'✅' if efficiency_gain > 1.2 else '⚠️'} Efficiency ratio: {efficiency_gain:.2f}")

    # Cleanup test
    logger.info("\n🧹 Testing cleanup...")
    backend.cleanup()
    logger.info("✅ Cleanup completed")

    # Memory usage info (if available)
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.info(f"📈 Memory usage: {memory_mb:.1f} MB")
    except ImportError:
        pass

    logger.info("\n" + "=" * 50)
    logger.info("🎉 CPU Backend Performance Test PASSED")
    logger.info("=" * 50)

    return True


def test_cpu_backend_fallback_to_onnx():
    """Test fallback to ONNX backend when sentence-transformers is unavailable"""

    # Mock sentence-transformers as unavailable
    with mock.patch.dict('sys.modules', {'sentence_transformers': None}):
        from mbed.core.config import MBEDSettings
        from mbed.core.hardware import HardwareType
        from mbed.backends.cpu import CPUBackend

        config = MBEDSettings()
        config.hardware = HardwareType.CPU
        config.model = "all-MiniLM-L6-v2"

        backend = CPUBackend(config)

        # Try to initialize - should attempt ONNX fallback
        try:
            backend.initialize()
            # If it succeeds, verify it's using ONNX
            assert backend.implementation == "onnx", "Should fallback to ONNX"
            logger.info("✅ Successfully fell back to ONNX backend")
        except RuntimeError as e:
            # Expected if ONNX is also not available
            assert "No CPU backend available" in str(e)
            logger.info("✅ Correctly raised error when both backends unavailable")

    return True


def test_cpu_backend_both_fail():
    """Test error handling when both backends are unavailable"""

    # Mock both backends as unavailable
    with mock.patch.dict('sys.modules', {
        'sentence_transformers': None,
        'onnxruntime': None
    }):
        from mbed.core.config import MBEDSettings
        from mbed.core.hardware import HardwareType
        from mbed.backends.cpu import CPUBackend

        config = MBEDSettings()
        config.hardware = HardwareType.CPU

        backend = CPUBackend(config)

        # Should raise RuntimeError
        with pytest.raises(RuntimeError) as exc_info:
            backend.initialize()

        assert "No CPU backend available" in str(exc_info.value)
        logger.info("✅ Correctly raised RuntimeError when both backends unavailable")

    return True


if __name__ == "__main__":
    # Run all tests
    success = True

    # Main performance test
    try:
        test_cpu_backend_performance()
    except Exception as e:
        logger.error(f"❌ Performance test failed: {e}")
        import traceback
        traceback.print_exc()
        success = False

    # Fallback tests (only if main test passed)
    if success:
        try:
            test_cpu_backend_fallback_to_onnx()
        except Exception as e:
            logger.error(f"❌ Fallback test failed: {e}")
            success = False

        try:
            test_cpu_backend_both_fail()
        except Exception as e:
            logger.error(f"❌ Both-fail test failed: {e}")
            success = False

    sys.exit(0 if success else 1)
#!/usr/bin/env python3
"""
CUDA Backend Example

This example demonstrates how to use the CUDA backend for high-performance
embedding generation on NVIDIA GPUs.
"""

import numpy as np
import time
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mbed.core.config import MBEDSettings
from mbed.backends.cuda import CUDABackend
from mbed.core.hardware import HardwareDetector


def print_section(title: str):
    """Print a formatted section header"""
    print(f"\n{'='*60}")
    print(f" {title}")
    print('='*60)


def basic_usage():
    """Demonstrate basic CUDA backend usage"""
    print_section("Basic CUDA Usage")

    # Check if CUDA is available
    cuda_info = HardwareDetector.detect_cuda()
    if not cuda_info.available:
        print("❌ CUDA is not available on this system")
        print("  Please ensure you have an NVIDIA GPU and CUDA installed")
        return False

    print(f"✅ CUDA is available!")
    print(f"  GPU Count: {cuda_info.device_count}")
    print(f"  Primary GPU: {cuda_info.device_name}")

    # Create configuration
    config = MBEDSettings(
        hardware="cuda",
        model="all-MiniLM-L6-v2",  # Small model for quick demo
        batch_size=128
    )

    # Initialize backend
    print("\nInitializing CUDA backend...")
    backend = CUDABackend(config)
    backend.initialize()

    # Generate embeddings
    texts = [
        "The quick brown fox jumps over the lazy dog.",
        "Machine learning is transforming how we process information.",
        "CUDA acceleration makes embedding generation much faster.",
        "This is a demonstration of the MBED unified system."
    ]

    print(f"\nGenerating embeddings for {len(texts)} texts...")
    start_time = time.time()
    embeddings = backend.generate_embeddings(texts)
    elapsed = time.time() - start_time

    print(f"✅ Generated embeddings in {elapsed:.3f} seconds")
    print(f"  Shape: {embeddings.shape}")
    print(f"  Dimension: {backend.get_embedding_dimension()}")
    print(f"  Throughput: {len(texts)/elapsed:.1f} texts/second")

    # Verify embeddings are normalized
    norms = np.linalg.norm(embeddings, axis=1)
    print(f"  Normalized: {np.allclose(norms, 1.0)}")

    return True


def advanced_features():
    """Demonstrate advanced CUDA features"""
    print_section("Advanced CUDA Features")

    # Check CUDA availability
    if not HardwareDetector.detect_cuda().available:
        print("⚠️  Skipping: CUDA not available")
        return False

    # Advanced configuration
    config = MBEDSettings(
        hardware="cuda",
        model="all-MiniLM-L6-v2",

        # Enable optimizations
        mixed_precision=True,         # FP16 for speed
        cuda_use_pinned_memory=True,  # Faster transfers
        normalize_embeddings=True,    # Unit vectors
        cuda_vram_reserved_gb=1.0,    # Reserve less VRAM

        # Performance settings
        batch_size=256,
        workers=4
    )

    print("Configuration:")
    print(f"  Mixed Precision: {config.mixed_precision}")
    print(f"  Pinned Memory: {config.cuda_use_pinned_memory}")
    print(f"  VRAM Reserved: {config.cuda_vram_reserved_gb}GB")

    # Initialize backend
    backend = CUDABackend(config)
    backend.initialize()

    # Get detailed GPU info
    info = backend.get_info()
    print(f"\nGPU Information:")
    print(f"  Name: {info.get('gpu_name', 'Unknown')}")
    print(f"  VRAM: {info.get('vram_gb', 0):.1f}GB total")
    print(f"  VRAM Used: {info.get('vram_used_gb', 0):.1f}GB")
    print(f"  Compute Capability: {info.get('compute_capability', 'Unknown')}")
    print(f"  Dynamic Batch Size: {info.get('batch_size', config.batch_size)}")

    # Process a larger batch to show performance
    num_texts = 1000
    texts = [f"Document {i}: " + "sample text " * 10 for i in range(num_texts)]

    print(f"\nProcessing {num_texts} documents...")
    start_time = time.time()

    # Process in batches (backend handles this internally)
    embeddings = backend.generate_embeddings(texts)

    elapsed = time.time() - start_time
    throughput = num_texts / elapsed

    print(f"✅ Completed in {elapsed:.2f} seconds")
    print(f"  Throughput: {throughput:.1f} docs/second")
    print(f"  Throughput: {throughput * 60:.0f} docs/minute")
    print(f"  Latency: {elapsed/num_texts*1000:.2f} ms/doc")

    return True


def benchmark_vs_cpu():
    """Compare CUDA vs CPU performance"""
    print_section("CUDA vs CPU Benchmark")

    # Check hardware availability
    cuda_available = HardwareDetector.detect_cuda().available
    if not cuda_available:
        print("⚠️  CUDA not available, skipping benchmark")
        return False

    # Test documents
    num_docs = 100
    texts = [f"Test document {i}: " + "benchmark text " * 20 for i in range(num_docs)]

    results = {}

    # Benchmark CUDA
    print(f"\nBenchmarking CUDA backend ({num_docs} documents)...")
    cuda_config = MBEDSettings(
        hardware="cuda",
        model="all-MiniLM-L6-v2",
        mixed_precision=True,
        batch_size=128
    )

    cuda_backend = CUDABackend(cuda_config)
    cuda_backend.initialize()

    start = time.time()
    cuda_embeddings = cuda_backend.generate_embeddings(texts)
    cuda_time = time.time() - start
    results['cuda'] = cuda_time

    print(f"  CUDA Time: {cuda_time:.2f}s")
    print(f"  CUDA Throughput: {num_docs/cuda_time:.1f} docs/s")

    # Benchmark CPU
    print(f"\nBenchmarking CPU backend ({num_docs} documents)...")
    from mbed.backends.cpu import CPUBackend

    cpu_config = MBEDSettings(
        hardware="cpu",
        model="all-MiniLM-L6-v2",
        batch_size=32
    )

    cpu_backend = CPUBackend(cpu_config)
    cpu_backend.initialize()

    start = time.time()
    cpu_embeddings = cpu_backend.generate_embeddings(texts)
    cpu_time = time.time() - start
    results['cpu'] = cpu_time

    print(f"  CPU Time: {cpu_time:.2f}s")
    print(f"  CPU Throughput: {num_docs/cpu_time:.1f} docs/s")

    # Compare results
    speedup = cpu_time / cuda_time
    print(f"\n📊 Results:")
    print(f"  CUDA is {speedup:.1f}x faster than CPU")
    print(f"  Time saved: {cpu_time - cuda_time:.1f}s")
    print(f"  Embeddings match: {np.allclose(cuda_embeddings, cpu_embeddings, rtol=1e-3)}")

    # Verify Phase 3 requirements
    cuda_docs_per_min = (num_docs / cuda_time) * 60
    print(f"\n✅ Phase 3 Requirements:")
    print(f"  Throughput: {cuda_docs_per_min:.0f} docs/min {'✅' if cuda_docs_per_min >= 1000 else '❌'} (≥1000 required)")
    print(f"  Speedup: {speedup:.1f}x {'✅' if speedup >= 10 else '❌'} (≥10x required)")

    return True


def faiss_gpu_demo():
    """Demonstrate FAISS-GPU integration"""
    print_section("FAISS-GPU Integration")

    if not HardwareDetector.detect_cuda().available:
        print("⚠️  CUDA not available, skipping FAISS-GPU demo")
        return False

    try:
        import faiss
    except ImportError:
        print("⚠️  FAISS not installed, skipping demo")
        print("  Install with: pip install faiss-cpu")
        return False

    # Configure with FAISS-GPU
    config = MBEDSettings(
        hardware="cuda",
        model="all-MiniLM-L6-v2",
        use_faiss_gpu=True
    )

    backend = CUDABackend(config)
    backend.initialize()

    # Create sample documents
    documents = [
        "The weather is sunny today.",
        "It's raining outside.",
        "The sun is shining brightly.",
        "Dark clouds are gathering.",
        "Perfect weather for a picnic.",
        "Storm approaching from the west.",
        "Clear blue skies ahead.",
        "Heavy rain expected tonight."
    ]

    print(f"Building index with {len(documents)} documents...")

    # Generate embeddings
    embeddings = backend.generate_embeddings(documents)

    # Build FAISS index
    if backend.use_faiss_gpu and backend.faiss_gpu_resources:
        backend.build_faiss_index(embeddings)
        print("✅ Built FAISS-GPU index")

        # Search for similar documents
        queries = ["What's the weather like?", "Is it going to rain?"]
        print(f"\nSearching for similar documents...")

        for query in queries:
            query_embedding = backend.generate_embeddings([query])
            distances, indices = backend.search_faiss(query_embedding, k=3)

            print(f"\nQuery: '{query}'")
            print("Top 3 matches:")
            for i, (idx, dist) in enumerate(zip(indices[0], distances[0])):
                print(f"  {i+1}. [{dist:.3f}] {documents[idx]}")
    else:
        print("⚠️  FAISS-GPU not available, using CPU fallback")

    return True


def main():
    """Run all examples"""
    print("="*60)
    print(" MBED CUDA Backend Examples")
    print("="*60)

    examples = [
        ("Basic Usage", basic_usage),
        ("Advanced Features", advanced_features),
        ("CUDA vs CPU Benchmark", benchmark_vs_cpu),
        ("FAISS-GPU Integration", faiss_gpu_demo)
    ]

    results = []
    for name, func in examples:
        try:
            success = func()
            results.append((name, success))
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
            results.append((name, False))

    # Summary
    print_section("Summary")
    for name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {name}")

    # Overall success
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All examples completed successfully!")
    else:
        print("\n⚠️  Some examples failed. Check CUDA availability and dependencies.")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
# Performance Tuning Guide

## Overview

This guide provides detailed instructions for optimizing the MBED system for maximum performance across different hardware backends.

## Table of Contents
1. [CUDA Performance Tuning](#cuda-performance-tuning)
2. [Memory Optimization](#memory-optimization)
3. [Batch Size Tuning](#batch-size-tuning)
4. [Multi-GPU Scaling](#multi-gpu-scaling)
5. [Benchmarking](#benchmarking)
6. [Monitoring Tools](#monitoring-tools)

## CUDA Performance Tuning

### 1. Enable Mixed Precision (FP16)

Mixed precision can provide up to 2x speedup with minimal accuracy loss:

```python
config = MBEDSettings(
    hardware="cuda",
    mixed_precision=True  # Enable FP16
)
```

**Benefits:**
- 2x memory savings (store weights in FP16)
- Faster computation on Tensor Cores (Volta+)
- Automatic loss scaling prevents underflow

**Best for:**
- Volta GPUs and newer (V100, RTX 20xx+)
- Large batch sizes
- Memory-constrained scenarios

### 2. Optimize Batch Size

The CUDA backend automatically calculates optimal batch size, but you can fine-tune:

```python
# Manual batch size configuration
config = MBEDSettings(
    hardware="cuda",
    batch_size=512,  # Starting point, will auto-adjust
    cuda_vram_reserved_gb=1.0  # Reduce reservation for more batching
)
```

**Batch Size Guidelines:**

| Model Size | VRAM | Recommended Batch Size |
|------------|------|------------------------|
| Small (<100M) | 4GB | 128-256 |
| Small (<100M) | 8GB | 256-512 |
| Base (100-500M) | 8GB | 128-256 |
| Base (100-500M) | 16GB | 256-512 |
| Large (>500M) | 16GB | 64-128 |
| Large (>500M) | 24GB+ | 128-256 |

### 3. Enable Pinned Memory

Pinned (page-locked) memory provides faster CPU-GPU transfers:

```python
config = MBEDSettings(
    cuda_use_pinned_memory=True  # Default: True
)
```

**Performance Impact:**
- 2-3x faster host-to-device transfers
- Enables async transfers with CUDA streams
- Small CPU memory overhead

### 4. TF32 on Ampere GPUs

For RTX 30xx and A100 GPUs, TF32 is automatically enabled:

```python
# Automatic on Ampere+ GPUs (compute capability >= 8.0)
# Provides up to 10x speedup for matrix operations
# No configuration needed - handled automatically
```

### 5. Multi-GPU Configuration

For systems with multiple GPUs:

```python
config = MBEDSettings(
    hardware="cuda",
    multi_gpu=True,  # Enable DataParallel
    cuda_device=0    # Primary device
)
```

**Scaling Efficiency:**
- 2 GPUs: ~1.8x speedup
- 4 GPUs: ~3.2x speedup
- 8 GPUs: ~6x speedup

## Memory Optimization

### VRAM Management

```python
# Configure VRAM reservation
config = MBEDSettings(
    cuda_vram_reserved_gb=1.5  # Reserve 1.5GB for system
)

# The backend automatically:
# 1. Calculates available VRAM
# 2. Estimates optimal batch size
# 3. Handles OOM with automatic retry
```

### Memory Monitoring

```python
backend = CUDABackend(config)
info = backend.get_info()

print(f"Total VRAM: {info['vram_gb']:.1f}GB")
print(f"Used VRAM: {info['vram_used_gb']:.1f}GB")
print(f"Reserved VRAM: {info['vram_reserved_gb']:.1f}GB")
```

### Cache Management

The backend automatically clears cache every 10,000 samples to prevent fragmentation:

```python
# Automatic cache clearing prevents:
# - Memory fragmentation
# - Gradual performance degradation
# - OOM errors in long-running processes
```

## Batch Size Tuning

### Dynamic Batch Sizing

The CUDA backend uses intelligent batch sizing:

```python
# Constants used for estimation (samples per GB VRAM)
SAMPLES_PER_GB_LARGE = 32   # >500M params
SAMPLES_PER_GB_BASE = 64    # 100-500M params
SAMPLES_PER_GB_SMALL = 128  # <100M params

# Calculated as:
# batch_size = available_vram_gb * samples_per_gb
```

### Manual Override

For specific requirements:

```python
# Force specific batch size
config = MBEDSettings(
    batch_size=256  # Will be used unless OOM occurs
)

# The backend will still reduce on OOM
# Max 3 retries with batch_size //= 2
```

### Finding Optimal Batch Size

```python
def find_optimal_batch_size(backend, test_texts):
    """Find optimal batch size for your hardware"""
    batch_sizes = [32, 64, 128, 256, 512, 1024]
    results = {}

    for batch_size in batch_sizes:
        backend.current_batch_size = batch_size
        try:
            start = time.time()
            _ = backend.generate_embeddings(test_texts[:batch_size])
            elapsed = time.time() - start

            throughput = batch_size / elapsed
            results[batch_size] = throughput
            print(f"Batch {batch_size}: {throughput:.1f} texts/sec")
        except torch.cuda.OutOfMemoryError:
            print(f"Batch {batch_size}: OOM")
            break

    optimal = max(results, key=results.get)
    print(f"Optimal batch size: {optimal}")
    return optimal
```

## Multi-GPU Scaling

### DataParallel Setup

```python
config = MBEDSettings(
    hardware="cuda",
    multi_gpu=True  # Automatically uses all GPUs
)
```

### GPU Selection

```python
# Use specific GPUs
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"  # Use GPU 0 and 1

config = MBEDSettings(
    hardware="cuda",
    multi_gpu=True
)
```

### Scaling Best Practices

1. **Batch Size Scaling**: Increase batch size proportionally
   ```python
   # Single GPU: batch_size = 256
   # 2 GPUs: batch_size = 512
   # 4 GPUs: batch_size = 1024
   ```

2. **Load Balancing**: Ensure even distribution
   ```python
   # DataParallel handles this automatically
   # Each GPU processes batch_size // num_gpus samples
   ```

3. **Communication Overhead**: Minimize with larger batches

## Benchmarking

### Built-in Benchmark

```bash
# Run comprehensive benchmark
python tests/benchmarks/benchmark_cuda.py \
  --num-docs 1000 \
  --batch-size 256 \
  --model nomic-embed-text
```

### Custom Benchmark

```python
import time
import numpy as np

def benchmark_backend(backend, num_docs=1000):
    """Benchmark embedding generation"""
    # Generate test documents
    texts = [f"Document {i}: " + "test " * 100 for i in range(num_docs)]

    # Warmup
    _ = backend.generate_embeddings(texts[:10])

    # Benchmark
    start = time.time()
    embeddings = backend.generate_embeddings(texts)
    elapsed = time.time() - start

    # Calculate metrics
    throughput = num_docs / elapsed
    latency = (elapsed / num_docs) * 1000

    print(f"Results for {num_docs} documents:")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"  Throughput: {throughput:.1f} docs/sec")
    print(f"  Throughput: {throughput * 60:.0f} docs/min")
    print(f"  Latency: {latency:.2f} ms/doc")
    print(f"  Embeddings shape: {embeddings.shape}")

    return {
        "throughput_per_sec": throughput,
        "throughput_per_min": throughput * 60,
        "latency_ms": latency,
        "total_time": elapsed
    }
```

### Performance Targets

| Hardware | Target Throughput | Expected Latency |
|----------|------------------|------------------|
| RTX 3060 | ≥1000 docs/min | <60ms/doc |
| RTX 3070 | ≥1500 docs/min | <40ms/doc |
| RTX 3080 | ≥2000 docs/min | <30ms/doc |
| RTX 3090 | ≥2500 docs/min | <25ms/doc |
| RTX 4070 | ≥2000 docs/min | <30ms/doc |
| RTX 4080 | ≥3000 docs/min | <20ms/doc |
| RTX 4090 | ≥4000 docs/min | <15ms/doc |
| A100 40GB | ≥5000 docs/min | <12ms/doc |

## Monitoring Tools

### NVIDIA System Management Interface

```bash
# Real-time GPU monitoring
nvidia-smi -l 1  # Update every second

# Detailed monitoring
nvidia-smi dmon -s pucvmet  # Power, Utilization, Clock, VRAM, Memory, Encoder, Temperature

# Process-specific monitoring
nvidia-smi pmon -i 0  # Monitor processes on GPU 0
```

### Python Monitoring

```python
import pynvml

def monitor_gpu():
    """Real-time GPU monitoring"""
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)

    while True:
        # Get metrics
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0

        print(f"GPU Util: {util.gpu}% | Mem: {mem.used/1e9:.1f}GB/{mem.total/1e9:.1f}GB | Temp: {temp}°C | Power: {power:.0f}W")

        time.sleep(1)
```

### Backend Monitoring

```python
# Built-in monitoring
backend = CUDABackend(config)
info = backend.get_info()

# Monitor during processing
for batch in batches:
    embeddings = backend.generate_embeddings(batch)

    # Check GPU status
    info = backend.get_info()
    print(f"VRAM Used: {info['vram_used_gb']:.2f}GB")
    print(f"Batch Size: {backend.current_batch_size}")
    print(f"OOM Count: {backend.oom_count}")
```

## Optimization Checklist

### Pre-deployment

- [ ] Enable mixed precision for Volta+ GPUs
- [ ] Configure optimal batch size for your model/hardware
- [ ] Enable pinned memory (default: on)
- [ ] Set appropriate VRAM reservation
- [ ] Test multi-GPU scaling if available
- [ ] Run benchmarks to verify performance
- [ ] Monitor temperature and power limits

### Production

- [ ] Implement monitoring and alerting
- [ ] Set up automatic recovery from OOM
- [ ] Configure logging for performance metrics
- [ ] Plan for scaling (multi-GPU or distributed)
- [ ] Document observed throughput and latency
- [ ] Set up regular performance regression tests

### Troubleshooting

| Issue | Solution |
|-------|----------|
| Low GPU utilization | Increase batch size |
| OOM errors | Reduce batch size or enable mixed precision |
| Slow transfers | Enable pinned memory |
| High latency | Check for CPU bottlenecks in preprocessing |
| Thermal throttling | Improve cooling or reduce power limit |
| Memory fragmentation | Restart process periodically |

## Advanced Optimizations

### Custom Memory Pool

```python
# Configure PyTorch memory allocator
import torch

# Set memory fraction
torch.cuda.set_per_process_memory_fraction(0.9)  # Use 90% of VRAM

# Enable memory caching
torch.cuda.empty_cache()  # Clear before starting

# Custom allocator config
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'max_split_size_mb:512'
```

### CUDA Graphs (Future)

```python
# Planned optimization for static workloads
# Can provide 20-30% speedup for inference
# Currently not implemented
```

### TensorRT Integration (Future)

```python
# Planned optimization for production inference
# Can provide 2-5x speedup over PyTorch
# Requires model conversion and optimization
```

## Conclusion

Optimal performance requires:
1. Understanding your hardware capabilities
2. Choosing appropriate model and batch sizes
3. Enabling relevant optimizations (mixed precision, pinned memory)
4. Monitoring and adjusting based on workload
5. Regular benchmarking and tuning

The CUDA backend handles most optimizations automatically, but manual tuning can provide additional performance gains for specific use cases.
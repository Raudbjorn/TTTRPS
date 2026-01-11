# CUDA Backend Documentation

## Overview

The CUDA backend provides high-performance embedding generation on NVIDIA GPUs with advanced optimizations for maximum throughput and efficiency.

## Features

### Core Capabilities
- **NVIDIA GPU Acceleration**: Leverages CUDA for fast embedding generation
- **Automatic Hardware Detection**: Detects CUDA availability and GPU capabilities
- **Performance**: ≥1000 docs/min on RTX 3060, ≥10x speedup over CPU

### Advanced Optimizations
- **Dynamic Batch Sizing**: Automatically adjusts batch size based on available VRAM
- **Mixed Precision (FP16)**: Use half-precision for 2x memory savings and faster computation
- **Multi-GPU Support**: Distribute workload across multiple GPUs with DataParallel
- **CUDA Streams**: Overlapped CPU-GPU transfers for better throughput
- **Pinned Memory**: Faster host-device memory transfers
- **FAISS-GPU Integration**: GPU-accelerated vector operations
- **OOM Recovery**: Automatic batch size reduction on out-of-memory errors
- **TF32 on Ampere**: Automatic TF32 optimization for Ampere+ GPUs (RTX 30xx, A100)

## Installation

### Prerequisites
1. NVIDIA GPU with CUDA Compute Capability ≥ 3.5
2. CUDA Toolkit ≥ 11.0
3. NVIDIA Driver ≥ 450.x

### Install Dependencies
```bash
# Install CUDA dependencies
pip install torch>=2.0 --index-url https://download.pytorch.org/whl/cu118
pip install sentence-transformers>=3.0
pip install faiss-cpu>=1.7  # or faiss-gpu if available for your Python version
pip install nvidia-ml-py>=12.0  # For GPU monitoring

# Or install all CUDA dependencies at once
pip install -e ".[cuda]"
```

## Usage Examples

### Basic Usage

```python
from mbed.core.config import MBEDSettings
from mbed.backends.cuda import CUDABackend

# Create configuration
config = MBEDSettings(
    hardware="cuda",
    model="nomic-embed-text",
    batch_size=256
)

# Initialize backend
backend = CUDABackend(config)
backend.initialize()

# Generate embeddings
texts = [
    "This is a sample document.",
    "Another document for embedding.",
    "CUDA acceleration makes this fast!"
]
embeddings = backend.generate_embeddings(texts)

print(f"Shape: {embeddings.shape}")
print(f"Dimension: {backend.get_embedding_dimension()}")
```

### Advanced Configuration

```python
from mbed.core.config import MBEDSettings
from mbed.backends.cuda import CUDABackend

config = MBEDSettings(
    hardware="cuda",
    model="mxbai-embed-large",

    # CUDA-specific settings
    mixed_precision=True,         # Enable FP16
    multi_gpu=True,               # Use all GPUs
    use_faiss_gpu=True,           # GPU-accelerated FAISS
    cuda_device=0,                # Primary GPU device
    cuda_vram_reserved_gb=1.5,    # Reserve 1.5GB for system
    cuda_use_pinned_memory=True,  # Enable pinned memory
    normalize_embeddings=True,    # L2 normalize embeddings

    # Performance settings
    batch_size=512,               # Will be auto-adjusted
    workers=8
)

backend = CUDABackend(config)
backend.initialize()

# Get detailed GPU information
info = backend.get_info()
print(f"GPU: {info['gpu_name']}")
print(f"VRAM: {info['vram_gb']:.1f}GB")
print(f"VRAM Used: {info['vram_used_gb']:.1f}GB")
print(f"Compute Capability: {info['compute_capability']}")
print(f"Dynamic Batch Size: {info['batch_size']}")
print(f"Mixed Precision: {info['mixed_precision']}")
print(f"Multi-GPU: {info['multi_gpu']} ({info['gpu_count']} GPUs)")
```

### Processing Large Datasets

```python
import numpy as np
from pathlib import Path

def process_large_dataset(documents: list, backend: CUDABackend):
    """Process large dataset with progress tracking"""

    batch_size = backend.current_batch_size
    all_embeddings = []

    for i in range(0, len(documents), batch_size):
        batch = documents[i:i+batch_size]

        # Generate embeddings for batch
        embeddings = backend.generate_embeddings(batch)
        all_embeddings.append(embeddings)

        # Progress update
        processed = min(i + batch_size, len(documents))
        print(f"Processed {processed}/{len(documents)} documents")

        # The backend automatically handles OOM errors
        # and adjusts batch size if needed

    return np.vstack(all_embeddings)

# Example usage
documents = ["doc " + str(i) for i in range(10000)]
embeddings = process_large_dataset(documents, backend)
print(f"Generated {len(embeddings)} embeddings")
```

### FAISS-GPU Integration

```python
# Enable FAISS-GPU in configuration
config = MBEDSettings(
    hardware="cuda",
    use_faiss_gpu=True
)

backend = CUDABackend(config)
backend.initialize()

# Generate embeddings
documents = ["doc1", "doc2", "doc3", "doc4", "doc5"]
embeddings = backend.generate_embeddings(documents)

# Build FAISS index on GPU
backend.build_faiss_index(embeddings)

# Search using GPU-accelerated FAISS
query_texts = ["search query"]
query_embeddings = backend.generate_embeddings(query_texts)
distances, indices = backend.search_faiss(query_embeddings, k=3)

print(f"Top 3 matches: {indices[0]}")
print(f"Distances: {distances[0]}")
```

## Configuration Reference

### CUDA-Specific Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `mixed_precision` | bool | False | Enable FP16 mixed precision for faster processing |
| `multi_gpu` | bool | False | Enable DataParallel for multi-GPU systems |
| `use_faiss_gpu` | bool | False | Use FAISS-GPU for vector operations |
| `cuda_device` | int | 0 | CUDA device index to use |
| `cuda_vram_reserved_gb` | float | 2.0 | VRAM to reserve for system (GB) |
| `cuda_use_pinned_memory` | bool | True | Use pinned memory for faster transfers |
| `normalize_embeddings` | bool | True | Normalize embeddings to unit vectors |

### Environment Variables

All settings can be configured via environment variables with the `MBED_` prefix:

```bash
export MBED_HARDWARE=cuda
export MBED_MIXED_PRECISION=true
export MBED_MULTI_GPU=true
export MBED_CUDA_DEVICE=0
export MBED_CUDA_VRAM_RESERVED_GB=1.5
export MBED_CUDA_USE_PINNED_MEMORY=true
export MBED_NORMALIZE_EMBEDDINGS=true
```

## Performance Tuning

### Dynamic Batch Sizing

The CUDA backend automatically calculates optimal batch size based on:
1. Available VRAM
2. Model size (parameter count or name heuristics)
3. Reserved VRAM for system

Batch size constants (samples per GB of VRAM):
- Large models (>500M params): 32 samples/GB
- Base models (100-500M params): 64 samples/GB
- Small models (<100M params): 128 samples/GB

### Memory Management

1. **VRAM Reservation**: Reserve memory for system/other processes
   ```python
   config = MBEDSettings(cuda_vram_reserved_gb=1.5)  # Reserve 1.5GB
   ```

2. **Cache Clearing**: Automatic cache clearing every 10,000 samples to prevent fragmentation

3. **OOM Recovery**: Automatic batch size reduction on out-of-memory errors
   - Max 3 retry attempts
   - Batch size halved on each retry
   - Graceful error reporting if all retries fail

### Optimization Tips

1. **Enable Mixed Precision** for 2x memory savings:
   ```python
   config = MBEDSettings(mixed_precision=True)
   ```

2. **Use Pinned Memory** for faster CPU-GPU transfers:
   ```python
   config = MBEDSettings(cuda_use_pinned_memory=True)
   ```

3. **Multi-GPU Systems**:
   ```python
   config = MBEDSettings(multi_gpu=True)  # Use all available GPUs
   ```

4. **Ampere+ GPUs** (RTX 30xx, A100): TF32 is automatically enabled for better performance

## Troubleshooting

### Common Issues

#### CUDA Not Available
```
RuntimeError: CUDA is not available on this system
```
**Solution**:
- Verify NVIDIA driver: `nvidia-smi`
- Check CUDA installation: `nvcc --version`
- Ensure PyTorch CUDA support: `python -c "import torch; print(torch.cuda.is_available())"`

#### Out of Memory Errors
```
torch.cuda.OutOfMemoryError: CUDA out of memory
```
**Solution**:
- Reduce batch size
- Enable mixed precision
- Increase `cuda_vram_reserved_gb`
- Close other GPU applications

#### Slow Performance
**Solutions**:
- Enable mixed precision: `mixed_precision=True`
- Check GPU utilization: `nvidia-smi`
- Ensure using correct GPU: `cuda_device=0`
- Verify not using CPU fallback

### GPU Monitoring

Monitor GPU usage during processing:

```python
info = backend.get_info()
print(f"GPU Utilization: {info.get('gpu_utilization', 'N/A')}")
print(f"GPU Temperature: {info.get('gpu_temperature', 'N/A')}")
print(f"VRAM Used: {info['vram_used_gb']:.2f}GB / {info['vram_gb']:.2f}GB")
```

Or use `nvidia-smi` in another terminal:
```bash
watch -n 1 nvidia-smi
```

## Benchmarking

Run the included benchmark to verify performance:

```bash
python tests/benchmarks/benchmark_cuda.py --num-docs 1000
```

Expected results on RTX 3060:
- Throughput: ≥1000 docs/min
- Speedup vs CPU: ≥10x
- Latency: <60ms per document

## Hardware Requirements

### Minimum Requirements
- GPU: NVIDIA GPU with Compute Capability ≥ 3.5
- VRAM: 4GB minimum
- CUDA: Version 11.0 or higher
- Driver: Version 450.x or higher

### Recommended Specifications
- GPU: RTX 3060 or better
- VRAM: 8GB or more
- CUDA: Version 11.8 or 12.x
- Driver: Latest stable version

### Tested GPUs
- Consumer: RTX 3060, RTX 3070, RTX 3080, RTX 3090, RTX 4070, RTX 4080, RTX 4090
- Professional: A100, A6000, V100, T4
- Older: GTX 1080 Ti, RTX 2080 Ti (limited features)

## API Reference

### CUDABackend Class

```python
class CUDABackend(EmbeddingBackend):
    """CUDA-accelerated embedding backend for NVIDIA GPUs"""

    def __init__(self, config: MBEDSettings):
        """Initialize CUDA backend with configuration"""

    def initialize(self) -> None:
        """Initialize CUDA, load model, setup optimizations"""

    def generate_embeddings(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for text list"""

    def get_embedding_dimension(self) -> int:
        """Get embedding vector dimension"""

    def is_available(self) -> bool:
        """Check if CUDA is available"""

    def get_info(self) -> Dict[str, Any]:
        """Get detailed backend and GPU information"""

    def build_faiss_index(self, embeddings: np.ndarray) -> None:
        """Build FAISS-GPU index for similarity search"""

    def search_faiss(self, query_embeddings: np.ndarray, k: int = 10) -> Tuple[np.ndarray, np.ndarray]:
        """Search FAISS index for k nearest neighbors"""
```

## Contributing

Contributions to improve the CUDA backend are welcome! Areas of interest:
- TensorRT integration for inference optimization
- CUDA graphs for kernel optimization
- Custom CUDA kernels for specific operations
- Additional GPU monitoring metrics
- Performance profiling tools

## License

MIT License - See LICENSE file for details
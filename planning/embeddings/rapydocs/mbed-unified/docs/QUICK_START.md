# Quick Start Guide

Get up and running with MBED Unified in 5 minutes!

## Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Raudbjorn/rapydocs.git
cd rapydocs/mbed-unified
```

### 2. Install Dependencies

#### Option A: Using UV (Recommended - Fastest)
```bash
# UV auto-installs dependencies
uv run pytest  # This will install everything needed!
```

#### Option B: Using pip
```bash
# Basic installation
pip install -e .

# With CUDA support
pip install -e ".[cuda]"

# With all backends
pip install -e ".[all]"
```

## Quick Examples

### 1. Check Your Hardware
```bash
./mbed info --hardware
```

Output:
```
🖥️  Hardware Detection Results
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ CUDA: Available (NVIDIA GeForce RTX 3060)
❌ MPS: Not available
❌ OpenVINO: Not available
✅ CPU: Available (12 cores)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Recommended backend: cuda
```

### 2. Generate Embeddings (Python)

```python
from mbed.core.config import MBEDSettings
from mbed.backends.factory import BackendFactory

# Auto-detect best hardware
config = MBEDSettings(hardware="auto")
backend = BackendFactory.create(config)
backend.initialize()

# Generate embeddings
texts = ["Hello world", "MBED is fast!", "GPU acceleration rocks!"]
embeddings = backend.generate_embeddings(texts)

print(f"Generated {len(embeddings)} embeddings")
print(f"Dimension: {embeddings.shape[1]}")
```

### 3. CUDA-Accelerated Processing

```python
from mbed.core.config import MBEDSettings
from mbed.backends.cuda import CUDABackend

# Use CUDA with optimizations
config = MBEDSettings(
    hardware="cuda",
    mixed_precision=True,  # 2x faster
    batch_size=256
)

backend = CUDABackend(config)
backend.initialize()

# Process documents
documents = ["doc " + str(i) for i in range(1000)]
embeddings = backend.generate_embeddings(documents)

print(f"Processed {len(documents)} documents on GPU!")
```

### 4. Store in Vector Database

```python
from mbed.databases.chromadb import ChromaDBStore

# Initialize database
db = ChromaDBStore(
    path="./my_vectors",
    collection_name="documents"
)

# Store embeddings
db.add(
    embeddings=embeddings,
    texts=documents,
    ids=[f"doc_{i}" for i in range(len(documents))]
)

# Search
query = "Find similar documents"
query_embedding = backend.generate_embeddings([query])
results = db.search(query_embedding, k=5)

for doc, score in results:
    print(f"Score: {score:.3f} - {doc}")
```

## CLI Usage

### Basic Commands
```bash
# Show help
./mbed --help

# Show configuration
./mbed config

# Check development readiness
./mbed dev-check all

# Process files
./mbed process documents/ --hardware cuda
```

### Processing with CUDA
```bash
# Use CUDA with optimizations
./mbed process documents/ \
  --hardware cuda \
  --mixed-precision \
  --batch-size 256

# Multi-GPU processing
./mbed process large_dataset/ \
  --hardware cuda \
  --multi-gpu \
  --workers 16
```

## Environment Configuration

### Using .env File
Create a `.env` file in the project root:

```env
# Hardware settings
MBED_HARDWARE=cuda
MBED_MIXED_PRECISION=true
MBED_BATCH_SIZE=256

# CUDA specific
MBED_CUDA_DEVICE=0
MBED_CUDA_VRAM_RESERVED_GB=1.5
MBED_NORMALIZE_EMBEDDINGS=true

# Model settings
MBED_MODEL=nomic-embed-text

# Database
MBED_DATABASE=chromadb
MBED_DB_PATH=./vectors
```

### Using Environment Variables
```bash
export MBED_HARDWARE=cuda
export MBED_MIXED_PRECISION=true
export MBED_BATCH_SIZE=512

./mbed process documents/
```

## Testing Your Setup

### 1. Run Unit Tests
```bash
# With UV (auto-installs pytest)
uv run pytest tests/unit

# Or directly
python -m pytest tests/unit
```

### 2. Run Examples
```bash
# Basic example
python src/examples/basic_usage.py

# CUDA example
python src/examples/cuda_example.py
```

### 3. Run Benchmarks
```bash
# CUDA benchmark
python tests/benchmarks/benchmark_cuda.py --num-docs 1000

# Expected output:
# ✅ Throughput: 1500 docs/min (≥1000 required)
# ✅ Speedup: 12.3x faster than CPU (≥10x required)
```

## Common Use Cases

### 1. Document Processing Pipeline
```python
from pathlib import Path
from mbed.core.config import MBEDSettings
from mbed.backends.factory import BackendFactory
from mbed.databases.chromadb import ChromaDBStore

# Setup
config = MBEDSettings(hardware="auto")
backend = BackendFactory.create(config)
backend.initialize()

db = ChromaDBStore(path="./doc_vectors")

# Process documents
doc_dir = Path("./documents")
for doc_file in doc_dir.glob("*.txt"):
    text = doc_file.read_text()
    embedding = backend.generate_embeddings([text])
    db.add(
        embeddings=embedding,
        texts=[text],
        ids=[str(doc_file)]
    )

print(f"Processed {len(list(doc_dir.glob('*.txt')))} documents")
```

### 2. Similarity Search System
```python
def semantic_search(query: str, k: int = 5):
    """Search for similar documents"""
    # Generate query embedding
    query_emb = backend.generate_embeddings([query])

    # Search database
    results = db.search(query_emb, k=k)

    # Display results
    for i, (doc, score) in enumerate(results, 1):
        print(f"{i}. Score: {score:.3f}")
        print(f"   {doc[:100]}...")
```

### 3. Batch Processing with Progress
```python
from tqdm import tqdm

def process_large_dataset(texts: list, batch_size: int = 256):
    """Process large dataset with progress bar"""
    all_embeddings = []

    for i in tqdm(range(0, len(texts), batch_size)):
        batch = texts[i:i+batch_size]
        embeddings = backend.generate_embeddings(batch)
        all_embeddings.append(embeddings)

    return np.vstack(all_embeddings)
```

## Performance Tips

### For Maximum Speed
1. **Use CUDA**: 10-20x faster than CPU
2. **Enable Mixed Precision**: 2x speedup on modern GPUs
3. **Optimize Batch Size**: Larger = better throughput
4. **Use Pinned Memory**: Faster CPU-GPU transfers
5. **Multi-GPU**: Scale linearly with GPUs

### Configuration for Speed
```python
config = MBEDSettings(
    hardware="cuda",
    mixed_precision=True,
    multi_gpu=True,
    cuda_use_pinned_memory=True,
    batch_size=512,
    workers=16
)
```

## Troubleshooting

### CUDA Not Available
```bash
# Check CUDA installation
nvidia-smi
nvcc --version

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"
```

### Out of Memory
```python
# Reduce batch size
config = MBEDSettings(batch_size=64)

# Or enable mixed precision
config = MBEDSettings(mixed_precision=True)

# Or increase VRAM reservation
config = MBEDSettings(cuda_vram_reserved_gb=3.0)
```

### Slow Performance
1. Check GPU utilization: `nvidia-smi`
2. Enable optimizations: `mixed_precision=True`
3. Increase batch size if memory allows
4. Ensure using GPU not CPU: `hardware="cuda"`

## Next Steps

1. 📖 Read the [CUDA Backend Documentation](./CUDA_BACKEND.md)
2. 🚀 Check the [Performance Tuning Guide](./PERFORMANCE_TUNING.md)
3. 🧪 Run the benchmarks in `tests/benchmarks/`
4. 💡 Explore examples in `src/examples/`
5. 🔧 Customize configuration in `.env` or `pyproject.toml`

## Getting Help

- **Documentation**: See `docs/` directory
- **Examples**: Check `src/examples/`
- **Tests**: Review `tests/` for usage patterns
- **Issues**: Report at https://github.com/Raudbjorn/rapydocs/issues

Happy embedding! 🚀
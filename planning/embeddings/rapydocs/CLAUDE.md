# CLAUDE.md

This file provides guidance to Claude Code when working with this embedding generation library.

## Overview

This is a **text embedding generation library** focused on:
- **Parsing**: Multi-format document parsing (Python, JavaScript/TypeScript, Markdown, HTML, JSON)
- **Chunking**: Smart text chunking with multiple strategies for optimal embedding quality
- **Embedding Generation**: Multi-backend embedding generation with GPU acceleration
- **Vector Storage**: PostgreSQL/pgvector, ChromaDB, and FAISS backends

## Quick Start

```bash
# Install dependencies
pip install -e .              # Basic installation
pip install -e .[dev]         # With dev tools
pip install -e .[parsers]     # With tree-sitter parsers

# Run tests
python tests/run_tests.py

# Generate embeddings
./mbed file.py                # Single file
./mbed dir/                   # Directory
./mbed docs/ --chunk-strategy semantic  # With semantic chunking
```

## Project Structure

```
rapydocs/
├── src/
│   ├── embeddings/           # Core embedding pipeline
│   │   ├── parsers/          # Language-specific parsers
│   │   ├── chunking.py       # Basic text chunking
│   │   ├── enhanced_chunking.py  # Advanced chunking strategies
│   │   ├── semantic_chunking.py  # LLM-powered semantic chunking
│   │   ├── file_processor.py # Document processing pipeline
│   │   ├── universal_embeddings.py   # CPU fallback embeddings
│   │   ├── ollama_cuda_embeddings.py # Ollama/GPU embeddings
│   │   └── llm_preprocessor.py       # LLM preprocessing
│   ├── database/             # Vector storage backends
│   │   ├── postgres_embeddings.py    # PostgreSQL + pgvector
│   │   └── faiss_backend.py          # FAISS vector store
│   ├── core/                 # Configuration and logging
│   └── utils/                # Utilities and hardware detection
├── mbed-unified/             # Unified multi-backend implementation
│   ├── src/mbed/
│   │   ├── backends/         # CUDA, MPS, OpenVINO, CPU, Ollama
│   │   ├── databases/        # ChromaDB, FAISS, PostgreSQL
│   │   ├── pipeline/         # Chunking strategies
│   │   └── core/             # Hardware detection, config
│   └── tests/                # Comprehensive test suite
├── tests/                    # Integration tests
├── specs/                    # Technical specifications
└── mbed                      # CLI wrapper
```

## Key Modules

### Parsers (`src/embeddings/parsers/`)

| Parser | File Types | Features |
|--------|------------|----------|
| `PythonParser` | `.py` | AST-based, extracts functions/classes/docstrings |
| `JavaScriptParser` | `.js`, `.jsx`, `.ts`, `.tsx` | Tree-sitter AST, JSX support |
| `MarkdownParser` | `.md` | Structure-aware, preserves headers |
| `HTMLParser` | `.html`, `.htm` | DOM parsing, content extraction |
| `JSONParser` | `.json`, `.jsonl` | Semantic enhancement for embeddings |

### Chunking Strategies

```python
from src.embeddings.chunking import TextChunker, ChunkConfig

# Basic chunking with overlap
config = ChunkConfig(
    min_tokens=300,
    max_tokens=700,
    target_tokens=500,
    overlap_percent=0.15
)
chunker = TextChunker(config)
chunks = chunker.chunk_text(text, doc_id="my_doc")
```

**Available Strategies:**
- `fixed` - Fixed size chunks (default)
- `sentence` - Sentence-based splitting
- `paragraph` - Paragraph-based splitting
- `semantic` - LLM-powered semantic boundaries
- `hierarchical` - Nested section chunking
- `topic` - Topic-based clustering

### Embedding Backends

```python
# Ollama with GPU acceleration (recommended)
from src.embeddings.ollama_cuda_embeddings import OllamaEmbeddingFunction
emb_fn = OllamaEmbeddingFunction(model_name="nomic-embed-text")
embeddings = emb_fn(["text1", "text2"])

# Universal CPU fallback
from src.embeddings.universal_embeddings import UniversalEmbeddings
embeddings = UniversalEmbeddings(model_name="all-MiniLM-L6-v2")
```

### Hardware Detection

```python
from mbed.core.hardware import HardwareDetector, HardwareType

# Auto-detect best available hardware
best = HardwareDetector.select_best()  # CUDA > MPS > OpenVINO > CPU

# Check specific hardware
cuda_cap = HardwareDetector.detect_cuda()
if cuda_cap.available:
    print(f"CUDA: {cuda_cap.details}")
```

## CLI Usage

```bash
# Basic processing
./mbed file.py                         # Single file
./mbed dir/                            # Directory recursively
./mbed file1.py file2.md dir/          # Multiple inputs

# Chunking strategies
./mbed docs/ --chunk-strategy semantic     # LLM-powered
./mbed docs/ --chunk-strategy paragraph    # Paragraph-based
./mbed docs/ --chunk-size 700 --chunk-overlap 100

# Database backends
./mbed files/ --db chromadb --db-path ./my_db
./mbed files/ --db postgres://user:pass@host/db
./mbed files/ --db faiss --db-path ./faiss_index

# Performance
./mbed files/ --workers 8 --batch-size 200
./mbed files/ --gpu                    # Force GPU

# LLM preprocessing
./mbed data.json --preprocess --llm-model llama3.2:latest
```

## Testing

```bash
# Main test suite
python tests/run_tests.py

# Unified mbed tests (recommended)
cd mbed-unified/
uv run pytest                     # All tests
uv run pytest tests/unit          # Unit tests only
uv run pytest --cov=src/mbed      # With coverage
```

## Architecture

### Embedding Pipeline Flow

```
Input File
    │
    ▼
┌─────────────────┐
│  MIME Detection │  python-magic, filetype, mimetypes
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Parser Select  │  Based on file extension/MIME type
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Parse File    │  Language-specific AST parsing
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Chunk Text     │  Strategy-based chunking with overlap
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Preprocess  │  Optional: semantic enrichment
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Embed Chunks  │  Multi-backend: Ollama/CUDA/CPU
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Store Vectors  │  PostgreSQL/ChromaDB/FAISS
└─────────────────┘
```

### Hardware Backend Priority

```
CUDA (NVIDIA GPU)
    ↓ fallback
MPS (Apple Silicon)
    ↓ fallback
OpenVINO (Intel GPU)
    ↓ fallback
CPU (sentence-transformers)
```

## Configuration

### Environment Variables

```bash
# PostgreSQL (for pgvector storage)
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5432
POSTGRES_DB=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=<password>

# Logging
RAPYDOCS_LOG_DIR=/path/to/logs

# Ollama (for embedding generation)
OLLAMA_AUTO_DELETE_COLLECTIONS=true  # Auto-cleanup incompatible collections
```

### Embedding Models

| Model | Dimensions | Backend | Notes |
|-------|------------|---------|-------|
| `nomic-embed-text` | 768 | Ollama | Default, good quality |
| `mxbai-embed-large` | 1024 | Ollama | Higher quality, slower |
| `all-MiniLM-L6-v2` | 384 | CPU | Fast fallback |

## Key Implementation Details

### Chunking with Overlap

The chunking system uses token-aware splitting with configurable overlap:

```python
ChunkConfig(
    min_tokens=300,      # Minimum chunk size
    max_tokens=700,      # Maximum chunk size
    target_tokens=500,   # Ideal target
    overlap_percent=0.15 # 15% overlap for context
)
```

### Parser Fallback Chain

```
Tree-sitter AST parsing
    ↓ if unavailable
Regex-based parsing
    ↓ if fails
Raw text extraction
```

### Vector Index Optimization

For PostgreSQL/pgvector, IVFFlat index uses dynamic `lists` parameter:
- Calculated as `N/1000` where N = number of vectors
- Minimum 1, maximum 1000
- Auto-recreates index when parameter changes

## Dependencies

### Required
- `chromadb` - Vector storage
- `tiktoken` - Token counting
- `requests` - HTTP client for Ollama

### Optional
- `sentence-transformers` - CPU embeddings
- `python-magic` - MIME detection
- `tree-sitter` - AST parsing
- `psycopg2` - PostgreSQL
- `faiss-cpu` / `faiss-gpu` - FAISS backend
- `torch` - GPU acceleration

## Troubleshooting

### Ollama Not Available
```bash
# Start Ollama service
ollama serve &

# Pull embedding model
ollama pull nomic-embed-text
```

### ChromaDB Installation Issues
```bash
# If UV fails, use pip directly
python -m pip install --break-system-packages chromadb
```

### GPU Not Detected
```bash
# Check CUDA
nvidia-smi

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Check MPS (Apple Silicon)
python -c "import torch; print(torch.backends.mps.is_available())"
```

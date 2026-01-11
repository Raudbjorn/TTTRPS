# Embedding Generation Pipeline

A Python library for generating vector embeddings from documents (PDF, EPUB, MOBI) and storing them in ChromaDB for semantic search.

## Overview

This codebase implements a complete document-to-embedding pipeline with hybrid search capabilities. It was extracted from a larger TTRPG Assistant project, retaining only the core embedding generation functionality.

## Architecture

```
Document (PDF/EPUB/MOBI)
         │
         ▼
┌─────────────────────────┐
│    Document Parsing     │  ← pdf_parser.py, ebook_parser.py, document_parser.py
│  (Extract text/tables)  │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│    Content Chunking     │  ← content_chunker.py
│ (Semantic boundaries)   │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│  Embedding Generation   │  ← embedding_generator.py, ollama_provider.py
│ (Sentence Transformers  │
│       or Ollama)        │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│    Vector Storage       │  ← database.py (ChromaDB)
│  (ChromaDB with HNSW)   │
└─────────────────────────┘
         │
         ▼
┌─────────────────────────┐
│    Hybrid Search        │  ← hybrid_search.py, search_service.py
│ (Semantic + BM25)       │
└─────────────────────────┘
```

## Key Components

### 1. Document Processing (`src/pdf_processing/`)

**pipeline.py** - Main orchestrator
- `DocumentProcessingPipeline`: Coordinates the entire document→embedding workflow
- Supports PDF, EPUB, MOBI formats
- Handles large file processing with size-based parameter adjustment

**pdf_parser.py / ebook_parser.py / document_parser.py** - Content extraction
- Extracts text, tables, and metadata from documents
- `UnifiedDocumentParser`: Auto-detects format and routes to appropriate parser
- Handles file deduplication via SHA256 hashing

**content_chunker.py** - Intelligent chunking
- `ContentChunker`: Splits documents at semantic boundaries
- Detects content types: rules, tables, stat blocks, spells, monsters
- Configurable chunk size and overlap (default: 1000 chars, 200 overlap)
- Preserves section/subsection hierarchy

**embedding_generator.py** - Vector generation
- `EmbeddingGenerator`: Core embedding class
- Supports two backends:
  - **Sentence Transformers** (default): `all-MiniLM-L6-v2` model, 384-dim embeddings
  - **Ollama** (local): `nomic-embed-text`, `mxbai-embed-large`, etc.
- Batch processing with configurable batch size
- Automatic normalization for cosine similarity

**ollama_provider.py** - Local Ollama integration
- `OllamaEmbeddingProvider`: Wraps Ollama API for local embeddings
- Model management: list, pull, check availability
- Parallel batch generation with ThreadPoolExecutor

**adaptive_learning.py** - Pattern learning
- `AdaptiveLearningSystem`: Learns document structure patterns per game system
- Improves extraction accuracy over time

### 2. Vector Database (`src/core/`)

**database.py** - ChromaDB integration
- `ChromaDBManager`: Manages vector collections and operations
- Collections: `rulebooks`, `flavor_sources`, `campaigns`, `sessions`, `personalities`
- Persistent storage in `./data/chromadb/`
- CRUD operations with embedding support

### 3. Search (`src/search/`)

**hybrid_search.py** - Hybrid search engine
- `HybridSearchEngine`: Combines semantic and keyword search
- Semantic: ChromaDB vector similarity (default weight: 0.7)
- Keyword: BM25 ranking (default weight: 0.3)
- Automatic index initialization and persistence

**search_service.py** - High-level search API
- Result ranking and filtering
- Metadata-based filtering

**query_processor.py / query_clarification.py / query_completion.py** - Query enhancement
- Query normalization and expansion
- Ambiguous query resolution
- Auto-completion

**cache_manager.py** - Result caching
- LRU cache for search results
- Configurable TTL and size limits

### 4. Configuration (`config/`)

**settings.py** - Centralized configuration via Pydantic
- Environment variable support with `.env` file
- Key settings:
  - `CHROMA_DB_PATH`: Vector database location
  - `EMBEDDING_MODEL`: Sentence Transformer model name
  - `USE_OLLAMA_EMBEDDINGS`: Toggle Ollama backend
  - `SEMANTIC_WEIGHT` / `KEYWORD_WEIGHT`: Search balance

**logging_config.py** - Structured logging with structlog

## Usage

### Basic Document Processing

```python
from src.pdf_processing.pipeline import DocumentProcessingPipeline

# Initialize pipeline (prompts for Ollama model selection)
pipeline = DocumentProcessingPipeline()

# Or specify model directly
pipeline = DocumentProcessingPipeline(
    model_name="nomic-embed-text",  # Use specific Ollama model
    prompt_for_ollama=False
)

# Process a document
result = await pipeline.process_document(
    document_path="rulebook.pdf",
    rulebook_name="Player's Handbook",
    system="D&D 5e",
    source_type="rulebook"
)
```

### Direct Embedding Generation

```python
from src.pdf_processing.embedding_generator import EmbeddingGenerator
from src.pdf_processing.content_chunker import ContentChunk

# Initialize with Sentence Transformers (default)
generator = EmbeddingGenerator()

# Or use Ollama
generator = EmbeddingGenerator(model_name="nomic-embed-text", use_ollama=True)

# Generate single embedding
embedding = generator.generate_single_embedding("Your text here")

# Generate batch embeddings
chunks = [...]  # List of ContentChunk objects
embeddings = generator.generate_embeddings(chunks)
```

### Hybrid Search

```python
from src.search.hybrid_search import HybridSearchEngine

engine = HybridSearchEngine()

# Search with hybrid ranking
results = engine.search(
    query="fireball spell damage",
    collection="rulebooks",
    n_results=5
)

for result in results:
    print(f"Score: {result.combined_score:.3f}")
    print(f"Content: {result.content[:200]}...")
```

## Dependencies

Core dependencies (see `requirements.txt`):
- `sentence-transformers>=2.3.0` - Embedding models
- `chromadb>=0.4.22` - Vector database
- `rank-bm25>=0.2.2` - BM25 keyword search
- `torch>=2.0.0` - ML framework
- `pypdf>=6.0.0`, `pdfplumber>=0.10.0` - PDF parsing
- `ollama>=0.4.0` - Local Ollama client
- `pydantic>=2.5.0`, `pydantic-settings>=2.1.0` - Configuration

## Environment Variables

```bash
# Embedding configuration
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_BATCH_SIZE=32
USE_OLLAMA_EMBEDDINGS=false
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_BASE_URL=http://localhost:11434

# Search weights
SEMANTIC_WEIGHT=0.7
KEYWORD_WEIGHT=0.3

# Storage
CHROMA_DB_PATH=./data/chromadb
CACHE_DIR=./data/cache

# Chunking
MAX_CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## Directory Structure

```
.
├── config/
│   ├── settings.py          # Pydantic settings
│   └── logging_config.py    # Logging setup
├── src/
│   ├── pdf_processing/
│   │   ├── pipeline.py           # Main orchestrator
│   │   ├── embedding_generator.py # Embedding generation
│   │   ├── ollama_provider.py    # Ollama integration
│   │   ├── content_chunker.py    # Document chunking
│   │   ├── pdf_parser.py         # PDF extraction
│   │   ├── ebook_parser.py       # EPUB/MOBI extraction
│   │   ├── document_parser.py    # Unified parser
│   │   └── adaptive_learning.py  # Pattern learning
│   ├── search/
│   │   ├── hybrid_search.py      # Semantic + keyword search
│   │   ├── search_service.py     # Search API
│   │   ├── query_processor.py    # Query enhancement
│   │   └── cache_manager.py      # Result caching
│   ├── core/
│   │   ├── database.py           # ChromaDB manager
│   │   └── result_pattern.py     # Error handling patterns
│   └── utils/
│       ├── file_size_handler.py  # Large file handling
│       └── security.py           # Input validation
├── tests/
│   ├── unit/
│   │   ├── pdf_processing/       # Embedding tests
│   │   └── search/               # Search tests
│   └── integration/              # Integration tests
├── data/
│   ├── chromadb/                 # Vector database
│   └── cache/                    # Search cache
├── requirements.txt
└── CLAUDE.md
```

# LLMWare Embedding Pipeline - Architecture Overview

This is a stripped-down version of LLMWare focused exclusively on:
- **Document Parsing** - Converting files to text chunks
- **Persistence** - Storing parsed content in databases
- **Embedding Generation** - Creating vector embeddings
- **Chunking/Pre-processing** - Smart text segmentation

All LLM inference, agents, prompts, and unrelated features have been removed.

---

## Core Modules

### 1. `parsers.py` (~4,200 lines) - Document Parsing & Text Extraction

**Purpose:** Convert unstructured documents into indexed text chunks.

**Key Classes:**

| Class | Purpose |
|-------|---------|
| `Parser` | Main orchestrator for all document types |
| `ImageParser` | OCR for images (JPG, PNG) using Tesseract |
| `VoiceParser` | Audio processing (WAV, MP3, M4A) |
| `TextParser` | Plain text, CSV, JSON, Markdown, TSV |
| `WikiParser` | Wikipedia article fetching |
| `DialogParser` | Dialog/conversation files |

**Supported File Formats:**
- PDF (native parsing via libpdf_llmware.so)
- Office: DOCX, PPTX, XLSX (via liboffice_llmware.so)
- Text: TXT, CSV, JSON, JSONL, MD, TSV, HTML
- Images: JPG, JPEG, PNG (with OCR)
- Audio: WAV, MP3, M4A, MP4

**Chunking Parameters:**
```python
chunk_size=400        # Target text block size (characters)
max_chunk_size=600    # Maximum before forced split
smart_chunking=1      # Sentence-boundary aware splitting
get_images=True       # Extract images from documents
get_tables=True       # Extract and index tables
```

**Output Schema (per block):**
```python
{
    "block_ID": int,           # Unique block identifier
    "doc_ID": int,             # Parent document ID
    "content_type": str,       # "text", "table", etc.
    "file_type": str,          # "pdf", "docx", etc.
    "text_block": str,         # The actual text content
    "header_text": str,        # Header/title if extracted
    "table_block": list,       # Structured table data
    "coords_x/y/cx/cy": int,   # Position coordinates
    "file_source": str,        # Original filename
    "author_or_speaker": str,  # Metadata
    "created_date": str,       # Document creation date
    "embedding_flags": dict,   # Embedding status
    # ... additional metadata fields
}
```

---

### 2. `embeddings.py` (~2,700 lines) - Vector Database Abstraction

**Purpose:** Abstract interface for storing and searching embeddings across multiple vector database backends.

**Key Classes:**

| Class | Purpose |
|-------|---------|
| `EmbeddingHandler` | High-level CRUD interface for embeddings |
| `EmbeddingMilvus` | Milvus vector DB implementation |
| `EmbeddingFAISS` | Facebook AI Similarity Search |
| `EmbeddingLanceDB` | LanceDB implementation |
| `EmbeddingPinecone` | Pinecone cloud service |
| `EmbeddingQdrant` | Qdrant vector DB |
| `EmbeddingPGVector` | PostgreSQL with pgvector |
| `EmbeddingRedis` | Redis with vector search |
| `EmbeddingNeo4j` | Neo4j graph database |
| `EmbeddingChromaDB` | ChromaDB embedded DB |
| `EmbeddingMongoAtlas` | MongoDB Atlas Vector Search |
| `_EmbeddingUtils` | Common utilities |

**Core Operations:**
```python
handler = EmbeddingHandler(library)

# Create embeddings for library content
handler.create_new_embedding(
    embedding_model_name="all-MiniLM-L6-v2",
    vector_db="chromadb"  # or milvus, faiss, pinecone, etc.
)

# Search by semantic similarity
results = handler.search_index(
    query_text="find relevant documents",
    result_count=10
)

# Delete embeddings
handler.delete_embedding(embedding_name)
```

---

### 3. `library.py` (~1,450 lines) - Document Collection Management

**Purpose:** Core interface for organizing parsed text blocks and managing library metadata.

**Key Classes:**

| Class | Purpose |
|-------|---------|
| `Library` | Main class for managing document collections |
| `LibraryCatalog` | Administrative interface for library lifecycle |

**Core Operations:**
```python
# Create a new library
library = Library().create_new_library("my_docs")

# Add files to library (auto-parses based on file type)
library.add_files(input_folder_path="/path/to/docs")

# Get parsed blocks
blocks = library.get_all_library_blocks()

# Export library
library.export_library_to_json_file("backup.json")
```

**Directory Structure Created:**
```
llmware_data/
├── accounts/
│   └── {account_name}/
│       └── {library_name}/
│           ├── blocks/          # Parsed text blocks
│           ├── images/          # Extracted images
│           ├── embedding/       # Vector indices
│           └── datasets/        # Export datasets
```

---

### 4. `resources.py` (~5,200 lines) - Text Database Abstraction & Persistence

**Purpose:** Abstract layer for text index databases where chunks are stored.

**Key Classes:**

| Class | Purpose |
|-------|---------|
| `CollectionRetrieval` | Query interface abstraction |
| `CollectionWriter` | Write interface for blocks |
| `MongoRetrieval` | MongoDB text indexing |
| `PGRetrieval` | PostgreSQL text storage |
| `SQLiteRetrieval` | SQLite text storage (default) |
| `ParserState` | Tracks parsing job progress |
| `QueryState` | Tracks query execution state |
| `CustomTable` | SQL table creation/management |
| `CloudBucketManager` | AWS S3 integration |

**Database Options:**
- **SQLite** (default) - No setup required, file-based
- **MongoDB** - Document-oriented, scalable
- **PostgreSQL** - Full ACID, enterprise-grade

---

### 5. `util.py` (~2,200 lines) - Utilities & Text Processing

**Purpose:** Helper functions including the critical TextChunker for smart text segmentation.

**Key Classes:**

| Class | Purpose |
|-------|---------|
| `TextChunker` | Smart text chunking algorithm |
| `Utilities` | General-purpose utilities |
| `CorpTokenizer` | Whitespace-based tokenizer |
| `LocalTokenizer` | Manages tokenizer.json files |
| `Sources` | Citation and source tracking |

**TextChunker Algorithm:**
```python
# "Chisel approach" - starts at max size, looks back for natural boundaries
chunker = TextChunker(
    max_char_size=600,        # Maximum chunk size
    look_back_char_range=300  # How far back to look for sentence end
)

chunks = chunker.convert_text_to_chunks(long_text)
# Result: 90%+ of chunks end on sentence boundaries
```

**Boundary Detection Priority:**
1. Period followed by space (`. `)
2. Double newlines (`\n\n`)
3. Single newlines (`\n`)
4. Whitespace (forced split at max_char_size)

---

### 6. `retrieval.py` (~1,750 lines) - Query & Semantic Search

**Purpose:** Execute queries against libraries using text and semantic search.

**Key Classes:**

| Class | Purpose |
|-------|---------|
| `Query` | Main query interface |

**Query Types:**
```python
query = Query(library)

# Text-based search (keyword, phrase)
results = query.text_query("search terms")

# Semantic/vector search
results = query.semantic_query("find similar content")

# Hybrid search (combines both)
results = query.hybrid_search("query", use_weights=True)

# With filters
results = query.text_query(
    "search",
    filter_dict={"file_type": "pdf"}
)
```

---

### 7. `configs.py` (~1,200 lines) - Global Configuration

**Purpose:** Centralized configuration management.

**Key Classes:**

| Class | Purpose |
|-------|---------|
| `LLMWareConfig` | Central configuration object |
| `MongoConfig` | MongoDB connection settings |
| `PostgresConfig` | PostgreSQL connection settings |
| `SQLiteConfig` | SQLite settings |
| `MilvusConfig` | Milvus vector DB settings |
| `ChromaDBConfig` | ChromaDB settings |
| (+ configs for Pinecone, Qdrant, Neo4j, etc.) |

**Configuration Example:**
```python
from llmware.configs import LLMWareConfig

# Set default vector database
LLMWareConfig().set_active_db("chromadb")

# Set paths
LLMWareConfig().set_llmware_path("/custom/path")
```

---

### 8. `models.py` (large, but mostly unused for embedding-only)

**Purpose:** Model loading and inference. For embedding-only use, the relevant classes are:

| Class | Purpose |
|-------|---------|
| `HFEmbeddingModel` | HuggingFace/Sentence Transformers |
| `OpenAIEmbeddingModel` | OpenAI embedding API |
| `ONNXEmbeddingModel` | ONNX Runtime embeddings |
| `OVEmbeddingModel` | OpenVINO embeddings |
| `HFReRankerModel` | Cross-encoder reranking |
| `ModelCatalog` | Model registry and loading |

**Note:** This file contains many LLM inference classes that are not used in embedding-only workflows. They remain for compatibility but can be ignored.

---

### 9. `model_configs.py` (~240 lines, stripped)

**Purpose:** Embedding model catalog with pre-configured models.

**Available Embedding Models:**
- `all-MiniLM-L6-v2` - 384 dims, 512 context
- `all-mpnet-base-v2` - 768 dims, 514 context
- `industry-bert-*` - Domain-specific (insurance, contracts, SEC, loans)
- `nomic-embed-text-v1` - 768 dims, 8192 context
- `jina-embeddings-v2-*` - 512-768 dims, 8192 context
- `bge-*-en-v1.5` - 384-1024 dims, 512 context
- `gte-*` - 384-1024 dims, 512 context
- `text-embedding-ada-002` (OpenAI) - 1536 dims
- `text-embedding-3-*` (OpenAI) - 1536-3072 dims

---

## Compiled Libraries (`lib/`)

Platform-specific native libraries for document parsing:

```
lib/
├── linux/x86_64/llmware/
│   ├── libpdf_llmware.so      # PDF parsing
│   ├── liboffice_llmware.so   # Office doc parsing
│   └── libgraph_llmware.so    # Graph parsing
├── darwin/arm64/              # macOS ARM
└── windows/                   # Windows
```

---

## Data Flow: Document to Embedding

```
1. INGEST
   ┌─────────────────┐
   │ PDF/DOCX/TXT... │
   └────────┬────────┘
            ▼
2. PARSE (parsers.py)
   ┌─────────────────┐
   │ Parser.parse_*  │ → Extracts text, tables, metadata
   │ TextChunker     │ → Splits into ~400 char chunks
   └────────┬────────┘
            ▼
3. PERSIST (resources.py, library.py)
   ┌─────────────────┐
   │ CollectionWriter│ → Stores blocks in SQLite/Mongo/PG
   │ Library         │ → Manages collections, metadata
   └────────┬────────┘
            ▼
4. EMBED (embeddings.py, models.py)
   ┌─────────────────┐
   │ EmbeddingHandler│ → Generates vectors for each block
   │ HFEmbeddingModel│ → Sentence Transformers, OpenAI, etc.
   └────────┬────────┘
            ▼
5. STORE VECTORS
   ┌─────────────────┐
   │ EmbeddingMilvus │
   │ EmbeddingFAISS  │ → Stores vectors in chosen backend
   │ EmbeddingChroma │
   └────────┬────────┘
            ▼
6. SEARCH (retrieval.py)
   ┌─────────────────┐
   │ Query           │ → Semantic search over embeddings
   │ semantic_query  │ → Returns ranked results
   └─────────────────┘
```

---

## Quick Start Example

```python
from llmware.library import Library
from llmware.retrieval import Query

# 1. Create library and parse documents
library = Library().create_new_library("my_knowledge_base")
library.add_files("/path/to/documents")

# 2. Generate embeddings
library.install_new_embedding(
    embedding_model_name="all-MiniLM-L6-v2",
    vector_db="chromadb"
)

# 3. Search
query = Query(library)
results = query.semantic_query("What is the return policy?", result_count=5)

for r in results:
    print(f"Score: {r['score']:.3f}")
    print(f"Text: {r['text'][:200]}...")
    print(f"Source: {r['file_source']}")
    print("---")
```

---

## Examples Directory

- `examples/Parsing/` - Document parsing examples
- `examples/Embedding/` - Vector embedding examples
- `examples/Retrieval/` - Query and search examples
- `examples/Getting_Started/` - Basic library usage
- `examples/Models/` - Embedding model usage

---

## Tests

- `tests/embeddings/` - Vector DB tests
- `tests/library/` - Library functionality
- `tests/retrieval/` - Query tests
- `tests/configs/` - Configuration tests

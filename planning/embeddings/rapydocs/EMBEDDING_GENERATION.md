# Embedding Generation System

This document explains the embedding generation pipeline, its components, and how they work together.

## System Overview

The embedding generation system transforms text documents into dense vector representations (embeddings) that capture semantic meaning. These embeddings enable similarity search, clustering, and other vector-based operations.

```
                    ┌─────────────────────────────────────────────────────┐
                    │              EMBEDDING GENERATION PIPELINE           │
                    └─────────────────────────────────────────────────────┘
                                            │
         ┌──────────────────────────────────┼──────────────────────────────────┐
         │                                  │                                  │
         ▼                                  ▼                                  ▼
┌─────────────────┐              ┌─────────────────┐              ┌─────────────────┐
│   PARSING       │              │   CHUNKING      │              │   EMBEDDING     │
│   LAYER         │              │   LAYER         │              │   LAYER         │
├─────────────────┤              ├─────────────────┤              ├─────────────────┤
│ • Python AST    │      →       │ • Fixed size    │      →       │ • Ollama/GPU    │
│ • JS Tree-sitter│              │ • Sentence      │              │ • CPU fallback  │
│ • Markdown      │              │ • Semantic      │              │ • Multi-model   │
│ • HTML/JSON     │              │ • Hierarchical  │              │                 │
└─────────────────┘              └─────────────────┘              └─────────────────┘
                                            │
                                            ▼
                              ┌─────────────────────────┐
                              │    VECTOR STORAGE       │
                              ├─────────────────────────┤
                              │ • PostgreSQL + pgvector │
                              │ • ChromaDB              │
                              │ • FAISS                 │
                              └─────────────────────────┘
```

## 1. Parsing Layer

### Purpose
Convert raw files into structured text that's optimized for embedding generation.

### Components

#### BaseParser (`src/embeddings/parsers/base_parser.py`)
Abstract base class defining the parser interface:

```python
class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: str, filepath: str) -> ParseResult:
        """Parse content and return structured data"""

    @abstractmethod
    def can_parse(self, filepath: str, content: str) -> bool:
        """Check if parser can handle this file"""
```

Key features:
- Input sanitization (null bytes, binary detection)
- Size limits (10MB default)
- Error-as-value pattern via `ParseResult`

#### Language-Specific Parsers

| Parser | Implementation | Output |
|--------|---------------|--------|
| **PythonParser** | Python `ast` module | Functions, classes, docstrings, imports |
| **JavaScriptParser** | Tree-sitter AST | Functions, classes, JSX components, exports |
| **MarkdownParser** | Regex + structure detection | Headers, code blocks, sections |
| **HTMLParser** | BeautifulSoup/lxml | Text content, structure, metadata |
| **JSONParser** | Semantic enhancement | Flattened keys, expanded values |

### Data Structures

```python
@dataclass
class CodeBlock:
    type: str           # function, class, method
    name: str           # identifier
    content: str        # source code
    docstring: str      # documentation
    signature: str      # function signature
    start_line: int
    end_line: int

@dataclass
class ParsedFile:
    filepath: str
    language: Language
    blocks: List[CodeBlock]
    imports: List[str]
    exports: List[str]
    metadata: Dict[str, Any]
```

## 2. Chunking Layer

### Purpose
Split parsed content into optimal-sized chunks for embedding generation.

### Why Chunking Matters

1. **Token Limits**: Embedding models have input limits (typically 512-8192 tokens)
2. **Semantic Coherence**: Chunks should represent complete thoughts
3. **Retrieval Quality**: Smaller, focused chunks improve search precision
4. **Overlap**: Context preservation across chunk boundaries

### Chunking Strategies

#### Fixed Size (`chunking.py`)
```python
config = ChunkConfig(
    min_tokens=300,
    max_tokens=700,
    target_tokens=500,
    overlap_percent=0.15
)
```

#### Sentence-Based
Splits on sentence boundaries using regex with abbreviation handling:
```python
sentences = re.split(r'(?<=[.!?])\s+', text)
```

#### Semantic Chunking (`semantic_chunking.py`)
Uses LLM to identify natural topic boundaries:
```python
class SemanticChunker:
    def find_semantic_boundaries(self, text: str) -> List[int]:
        # Markdown headers, numbered lists, section titles
        patterns = [r'^#{1,6}\s+', r'^\d+\.\s+', r'^[A-Z][^.!?]*:$']
```

#### Hierarchical Chunking
Preserves document structure with nested sections:
```python
def chunk_with_sections(self, text, doc_id):
    boundaries = self.find_semantic_boundaries(text)
    # Keep sections as units, sub-chunk if too large
```

### Overlap Mechanism

Chunks include context from the previous chunk:
```
Chunk 1: [A B C D E F G H I J]
                    ↓ overlap
Chunk 2:       [G H I J K L M N O P]
                          ↓ overlap
Chunk 3:             [M N O P Q R S T U V]
```

Benefits:
- Preserves context across boundaries
- Improves retrieval for queries spanning chunks
- 15% overlap is typical (configurable)

## 3. Embedding Layer

### Purpose
Transform text chunks into dense vector representations.

### Hardware Backends

The system auto-detects and uses the best available hardware:

```python
class HardwareDetector:
    @classmethod
    def select_best(cls) -> HardwareType:
        priority = [
            HardwareType.CUDA,      # NVIDIA GPU
            HardwareType.MPS,       # Apple Silicon
            HardwareType.OPENVINO,  # Intel GPU
            HardwareType.CPU        # Fallback
        ]
```

#### CUDA Backend (`mbed-unified/src/mbed/backends/cuda.py`)
- Dynamic batch sizing based on VRAM
- Pinned memory for CPU↔GPU transfers
- Mixed precision (FP16) support
- Multi-GPU via DataParallel
- OOM handling with automatic batch reduction

#### Ollama Backend (`src/embeddings/ollama_cuda_embeddings.py`)
```python
class OllamaEmbeddingFunction:
    def __call__(self, input: List[str]) -> List[List[float]]:
        response = requests.post(
            f"{self.base_url}/api/embeddings",
            json={"model": self.model_name, "prompt": text}
        )
        return response.json()['embedding']
```

Features:
- Parallel processing with configurable concurrency
- Automatic service startup
- Failure tracking with fallback

#### CPU Backend (`src/embeddings/universal_embeddings.py`)
Uses sentence-transformers for pure CPU execution:
```python
class UniversalEmbeddings:
    def __init__(self, model_name="all-MiniLM-L6-v2"):
        self.embedding_function = SentenceTransformerEmbeddingFunction(
            model_name=f"sentence-transformers/{model_name}"
        )
```

### Embedding Models

| Model | Dimensions | Speed | Quality | Use Case |
|-------|------------|-------|---------|----------|
| `nomic-embed-text` | 768 | Fast | Good | General purpose |
| `mxbai-embed-large` | 1024 | Medium | Better | Higher accuracy needed |
| `all-MiniLM-L6-v2` | 384 | Very Fast | Basic | CPU-only, quick tests |

### Batch Processing

For efficiency, embeddings are generated in batches:
```python
def generate_embeddings(self, texts: List[str]) -> np.ndarray:
    batch_size = 50  # Configurable
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        embeddings.extend(self.model.encode(batch))
```

## 4. Storage Layer

### PostgreSQL + pgvector

Schema:
```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE file_embeddings (
    id SERIAL PRIMARY KEY,
    file_id INTEGER REFERENCES processed_files(id),
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(768),  -- Dimension matches model
    metadata JSONB,
    UNIQUE(file_id, chunk_index)
);

-- IVFFlat index for approximate nearest neighbor search
CREATE INDEX ON file_embeddings
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);  -- N/1000 rule
```

### ChromaDB

```python
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.create_collection(
    name="embeddings",
    embedding_function=embedding_function,
    metadata={"hnsw:space": "cosine"}
)

# Add documents (embeddings auto-generated)
collection.add(
    documents=["text1", "text2"],
    metadatas=[{"source": "file1"}, {"source": "file2"}],
    ids=["id1", "id2"]
)
```

### FAISS

```python
from src.database.faiss_backend import FAISSBackend

backend = FAISSBackend(dimension=768, index_type="IVF")
backend.add(embeddings, metadata)
results = backend.search(query_embedding, k=10)
```

## 5. Pre-processing (Optional)

### LLM Preprocessing (`src/embeddings/llm_preprocessor.py`)

Enriches content before embedding for better semantic capture:

```python
class LLMPreprocessor:
    def preprocess(self, content: str, content_type: str) -> str:
        if content_type == "json":
            return self.expand_json_semantics(content)
        elif content_type == "code":
            return self.add_code_context(content)
```

Use cases:
- JSON: Expand abbreviated keys, add field descriptions
- Code: Add docstring summaries, explain complex logic
- Structured data: Flatten hierarchies, add context

## 6. Complete Pipeline Example

```python
from src.embeddings.file_processor import FileProcessor
from src.embeddings.chunking import TextChunker, ChunkConfig

# Configure
db_config = {
    "host": "127.0.0.1",
    "port": 5432,
    "database": "embeddings",
    "user": "postgres",
    "password": "secret"
}

# Initialize
processor = FileProcessor(db_config, use_largest_model=True)

# Process file
result = processor.process_file(Path("document.py"))
# Returns: ProcessedFile with content, parsed_data, chunks, embeddings

# Save to database
processor.save_to_database(result)
```

### CLI Usage

```bash
# Basic: parse, chunk, embed, store
./mbed document.py --db chromadb --db-path ./vectors

# Advanced: semantic chunking with LLM preprocessing
./mbed docs/ \
    --chunk-strategy semantic \
    --preprocess \
    --llm-model llama3.2:latest \
    --db postgres://user:pass@localhost/db \
    --workers 8
```

## 7. Performance Considerations

### Batch Size Tuning

| Hardware | Recommended Batch Size |
|----------|----------------------|
| CPU | 32-64 |
| GPU 8GB VRAM | 128-256 |
| GPU 16GB+ VRAM | 256-512 |

### Memory Management

- Stream large files instead of loading entirely
- Clear GPU cache periodically
- Use connection pooling for database

### Index Optimization

For pgvector IVFFlat:
```
lists = max(1, min(1000, N / 1000))
```
Where N = number of vectors. Rebuild index when parameter changes significantly.

## 8. Error Handling

The system uses error-as-value pattern:

```python
@dataclass
class ParseResult:
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    warnings: List[str] = None
```

Fallback chain:
1. Primary parser fails → Try regex-based fallback
2. Embedding generation fails → Retry with smaller batch
3. GPU OOM → Reduce batch size, retry
4. Service unavailable → Queue for retry

## Summary

The embedding generation system is a modular pipeline:

1. **Parse**: Extract structured content from files
2. **Chunk**: Split into optimal-sized pieces with overlap
3. **Preprocess** (optional): Enrich content with LLM
4. **Embed**: Generate vectors using best available hardware
5. **Store**: Persist in vector database for retrieval

Each layer is independent and configurable, allowing optimization for different use cases (speed vs. quality, GPU vs. CPU, etc.).

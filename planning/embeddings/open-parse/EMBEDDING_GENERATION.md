# Open-Parse: Embedding Generation Pipeline

This document explains how Open-Parse transforms PDF documents into embedding-ready chunks for RAG (Retrieval-Augmented Generation) systems.

## Pipeline Overview

```
PDF Document
     |
     v
+--------------------+
| DocumentParser     |  Entry point: doc_parser.py
+--------------------+
     |
     +--> Text Extraction (pdfminer or pymupdf)
     |         |
     |         v
     |    TextElement objects with:
     |      - Markdown-formatted text
     |      - Bounding boxes (spatial position)
     |      - Token counts (tiktoken cl100k_base)
     |
     +--> Table Extraction (pymupdf/table-transformers/unitable)
     |         |
     |         v
     |    TableElement objects with:
     |      - HTML or Markdown table content
     |      - Bounding boxes
     |      - Token counts
     |
     +--> Image Extraction
               |
               v
          ImageElement objects with:
            - Base64-encoded image data
            - Bounding boxes
            - Fixed 512-token placeholder
     |
     v
+--------------------+
| IngestionPipeline  |  Chunking & preprocessing: processing/ingest.py
+--------------------+
     |
     v
+--------------------+
| Node objects       |  Embedding-ready chunks: schemas.py
+--------------------+
     |
     v
ParsedDocument (ready for embedding generation)
```

## Core Components

### 1. Document Parsing (`doc_parser.py`)

The `DocumentParser` class orchestrates extraction:

```python
from openparse import DocumentParser

parser = DocumentParser(
    processing_pipeline=BasicIngestionPipeline(),  # or SemanticIngestionPipeline
    table_args={"parsing_algorithm": "pymupdf"}    # or "table-transformers", "unitable"
)
parsed_doc = parser.parse("document.pdf", ocr=False)
```

**Output**: `ParsedDocument` containing `Node` objects ready for embedding.

### 2. Data Schemas (`schemas.py`)

#### Element Types (extracted content)

| Type | Purpose | Embedding Text Source |
|------|---------|----------------------|
| `TextElement` | Text blocks with markdown formatting | `.embed_text` property |
| `TableElement` | Tables as HTML/Markdown | `.embed_text` property |
| `ImageElement` | Base64 images | `.embed_text` (placeholder) |

#### Node (embedding unit)

A `Node` is the fundamental unit for embedding generation:

```python
class Node:
    elements: Tuple[TextElement | TableElement | ImageElement, ...]
    embedding: Optional[List[float]]  # Populated by SemanticIngestionPipeline

    @property
    def text(self) -> str:  # Concatenated, markdown-formatted content

    @property
    def tokens(self) -> int:  # Sum of element tokens (tiktoken cl100k_base)
```

**Key properties for embedding**:
- `.text`: Full text content for embedding input
- `.tokens`: Token count for chunking decisions
- `.embedding`: Vector storage (populated by semantic pipeline)
- `.variant`: Content types (`{"text"}`, `{"table"}`, `{"image"}`, or combinations)

### 3. Ingestion Pipelines (`processing/ingest.py`)

#### BasicIngestionPipeline (Heuristic-based)

Fast, deterministic chunking using spatial and structural heuristics:

```python
transformations = [
    RemoveTextInsideTables(),      # Prevent duplication
    CombineSlicedImages(),         # Reconstruct split images
    RemoveFullPageStubs(),         # Remove low-value elements
    CombineNodesSpatially(),       # Group nearby elements
    CombineHeadingsWithClosestText(), # Associate headings
    CombineBullets(),              # Group bullet points
    RemoveMetadataElements(),      # Remove page numbers, headers
    RemoveRepeatedElements(),      # Deduplicate
    RemoveNodesBelowNTokens(),     # Filter small chunks
]
```

#### SemanticIngestionPipeline (Embedding-based)

Uses OpenAI embeddings to merge semantically related nodes:

```python
from openparse.processing import SemanticIngestionPipeline

pipeline = SemanticIngestionPipeline(
    openai_api_key="sk-...",
    model="text-embedding-3-large",  # or text-embedding-3-small, ada-002
    min_tokens=256,   # Minimum chunk size
    max_tokens=1024,  # Maximum chunk size
)
```

**Process**:
1. Apply basic heuristic transforms
2. Generate embeddings for each node (batched, 256/call)
3. Compute cosine similarity between adjacent nodes
4. Merge nodes where `similarity >= min_similarity` and `combined_tokens <= max_tokens`
5. Repeat until no more merges possible

### 4. Token Management (`utils.py`, `consts.py`)

```python
# Token counting (tiktoken cl100k_base - OpenAI's tokenizer)
from openparse.utils import num_tokens
count = num_tokens("Some text")

# Default chunk size limits
TOKENIZATION_LOWER_LIMIT = 256   # Minimum desirable chunk size
TOKENIZATION_UPPER_LIMIT = 1024  # Maximum desirable chunk size
```

## Embedding Generation Workflow

### Option A: External Embedding (Most Common)

Parse first, embed separately:

```python
from openparse import DocumentParser

parser = DocumentParser()
parsed_doc = parser.parse("document.pdf")

# Extract text for embedding
texts = [node.text for node in parsed_doc.nodes]

# Embed with your preferred service
embeddings = your_embedding_service.embed(texts)

# Store embeddings back (optional)
for node, embedding in zip(parsed_doc.nodes, embeddings):
    node.embedding = embedding
```

### Option B: Integrated Semantic Pipeline

Embeddings generated during parsing for semantic chunking:

```python
from openparse import DocumentParser
from openparse.processing import SemanticIngestionPipeline

pipeline = SemanticIngestionPipeline(
    openai_api_key="sk-...",
    model="text-embedding-3-large",
)

parser = DocumentParser(processing_pipeline=pipeline)
parsed_doc = parser.parse("document.pdf")

# Nodes already have embeddings from semantic merging process
# (Note: These are used internally for merging decisions)
```

### Option C: LlamaIndex Integration

Direct export to LlamaIndex format:

```python
parsed_doc = parser.parse("document.pdf")

# Convert to LlamaIndex nodes with relationships
li_nodes = parsed_doc.to_llama_index_nodes()

# Use with LlamaIndex embedding models
from llama_index.embeddings.openai import OpenAIEmbedding
embed_model = OpenAIEmbedding()

for node in li_nodes:
    node.embedding = embed_model.get_text_embedding(node.text)
```

## Chunk Quality Factors

### What Makes Good Chunks

1. **Token bounds**: 256-1024 tokens (configurable)
2. **Semantic coherence**: Headings with their content, bullet lists together
3. **Structural preservation**: Tables as units, images with context
4. **Reading order**: Nodes sorted by page/position for logical flow

### Processing Steps Explained

| Transform | Purpose | Impact on Embeddings |
|-----------|---------|---------------------|
| `RemoveTextInsideTables` | Prevents duplicate content | Cleaner, unique chunks |
| `CombineNodesSpatially` | Groups visually related content | Semantic coherence |
| `CombineHeadingsWithClosestText` | Associates titles with content | Better retrieval |
| `CombineBullets` | Keeps bullet lists together | Complete context |
| `RemoveMetadataElements` | Removes page numbers, footers | Less noise |
| `RemoveNodesBelowNTokens` | Filters tiny chunks | Quality threshold |
| `CombineNodesSemantically` | Merges similar content | Optimal chunk sizes |

## File Structure (Embedding-Relevant)

```
src/openparse/
├── doc_parser.py          # Main entry point
├── schemas.py             # Node, TextElement, TableElement, ImageElement
├── utils.py               # num_tokens() - tiktoken counting
├── consts.py              # Token limits, delimiters
├── processing/
│   ├── ingest.py          # Pipeline orchestration
│   ├── basic_transforms.py # Heuristic chunking steps
│   └── semantic_transforms.py # Embedding-based merging (OpenAI)
├── text/                  # Text extraction (pdfminer, pymupdf)
├── tables/                # Table extraction (3 algorithms)
└── pdf.py                 # PDF file handling
```

## Configuration Reference

### Token Limits

```python
# In consts.py or when creating pipelines
TOKENIZATION_LOWER_LIMIT = 256   # Chunks below this are filtered
TOKENIZATION_UPPER_LIMIT = 1024  # Chunks won't exceed this
```

### Semantic Pipeline Parameters

```python
SemanticIngestionPipeline(
    openai_api_key="...",
    model="text-embedding-3-large",  # Embedding model
    min_tokens=256,                  # Minimum chunk size
    max_tokens=1024,                 # Maximum chunk size
)

CombineNodesSemantically(
    embedding_client=OpenAIEmbeddings(...),
    min_similarity=0.6,    # Cosine similarity threshold for merging
    max_tokens=512,        # Max combined tokens
)
```

### Table Parsing (affects embedding content)

```python
# PyMuPDF (fast, built-in)
{"parsing_algorithm": "pymupdf", "table_output_format": "markdown"}

# Table Transformers (ML-based detection)
{"parsing_algorithm": "table-transformers", "min_table_confidence": 0.7}

# UniTable (state-of-the-art, requires model weights)
{"parsing_algorithm": "unitable", "min_table_confidence": 0.7}
```

## Key Takeaways

1. **Nodes are the embedding unit**: Each `Node` contains one or more elements and exposes `.text` for embedding input and `.tokens` for size management.

2. **Two pipeline modes**:
   - `BasicIngestionPipeline`: Fast heuristics, no external API calls
   - `SemanticIngestionPipeline`: Uses OpenAI embeddings internally for intelligent merging

3. **Flexible embedding integration**: Parse once, embed with any service. The `.embedding` field on nodes can store vectors from any source.

4. **Token-aware chunking**: Uses tiktoken (cl100k_base) for accurate token counting compatible with OpenAI models.

5. **Preservation of structure**: Markdown formatting, table structure, and spatial relationships inform chunking decisions.

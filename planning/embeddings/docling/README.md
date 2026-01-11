# Docling - Document Parsing for Embedding Pipelines

This is a stripped-down version of [Docling](https://github.com/docling-project/docling) containing only the components necessary for document parsing and chunking in embedding generation workflows.

## Embedding Generation Pipeline Overview

Docling provides the **parsing** and **chunking** stages of an embedding pipeline:

```
                        DOCLING HANDLES THIS
                   ┌──────────────────────────────┐
                   │                              │
┌──────────┐   ┌───▼────┐   ┌─────────┐   ┌───────▼───────┐   ┌──────────────┐
│ Document │ → │ Parser │ → │ DocType │ → │   Chunker     │ → │ Text Chunks  │
│ (PDF,    │   │        │   │Document │   │ (Hierarchical │   │ with         │
│ DOCX...) │   └────────┘   └─────────┘   │  or Hybrid)   │   │ Metadata     │
└──────────┘                              └───────────────┘   └──────┬───────┘
                                                                     │
                   EXTERNAL EMBEDDING MODEL                          │
                   ┌──────────────────────────────┐                  │
                   │                              │                  │
               ┌───▼────┐   ┌─────────────┐   ┌───▼───┐
               │Sentence│ → │   Vector    │ → │Vector │
               │ Trans. │   │  Embeddings │   │  DB   │
               └────────┘   └─────────────┘   └───────┘
```

## Components Included

### 1. Document Backends (`docling/backend/`)
Parsers for various document formats:
- **PDF**: `pypdfium2_backend.py`, `docling_parse_v4_backend.py`
- **Office**: `msword_backend.py`, `msexcel_backend.py`, `mspowerpoint_backend.py`
- **Web**: `html_backend.py`, `md_backend.py`
- **Data**: `csv_backend.py`, `json/docling_json_backend.py`
- **Scientific**: `xml/jats_backend.py` (JATS), `xml/uspto_backend.py` (patents)
- **Images**: `image_backend.py`
- **Other**: `asciidoc_backend.py`, `webvtt_backend.py`, `mets_gbs_backend.py`

### 2. Processing Pipelines (`docling/pipeline/`)
- `simple_pipeline.py` - Direct conversion for structured formats (DOCX, HTML, etc.)
- `standard_pdf_pipeline.py` - ML-enhanced PDF processing with layout detection
- `threaded_standard_pdf_pipeline.py` - Production-ready concurrent PDF processing
- `vlm_pipeline.py` - Vision-Language Model pipeline for complex documents

### 3. ML Models (`docling/models/`)
Used during document processing:
- **Layout Detection**: Identifies text, tables, figures, headings, etc.
- **Reading Order**: Determines logical reading sequence
- **Table Structure**: Extracts table cells and structure
- **OCR**: Multiple OCR engines (Tesseract, EasyOCR, RapidOCR, macOS native)
- **Code/Formula Detection**: Identifies code blocks and math formulas
- **Picture Classification**: Distinguishes figures from photographs

### 4. Chunking (`docling/chunking/`)
Re-exports from `docling-core`:
- `HierarchicalChunker` - Chunks by document structure (sections, paragraphs)
- `HybridChunker` - Combines structural and token-based chunking

### 5. Data Models (`docling/datamodel/`)
Type definitions and configuration:
- `document.py` - `InputDocument`, `ConversionResult`, `Page`
- `base_models.py` - Enums for formats, status, options
- `pipeline_options.py` - Configuration for each pipeline type

## Usage Example

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker

# 1. PARSE: Convert document to structured representation
converter = DocumentConverter()
result = converter.convert("path/to/document.pdf")
doc = result.document

# 2. CHUNK: Split into embedding-ready chunks
chunker = HybridChunker(tokenizer="sentence-transformers/all-MiniLM-L6-v2")
chunks = list(chunker.chunk(doc))

# 3. EMBED: Use external embedding model (not included in Docling)
# Example with sentence-transformers:
#   from sentence_transformers import SentenceTransformer
#   model = SentenceTransformer("all-MiniLM-L6-v2")
#   embeddings = model.encode([chunk.text for chunk in chunks])

# Each chunk contains:
for chunk in chunks:
    print(f"Text: {chunk.text[:100]}...")
    print(f"Metadata: {chunk.meta}")  # page numbers, headings, etc.
```

## Chunk Metadata

Each chunk includes metadata useful for RAG applications:
- `doc_items` - Source document elements
- `headings` - Section hierarchy
- `captions` - Associated captions
- Page numbers and bounding boxes (for PDFs)

## Dependencies

Key dependencies from `pyproject.toml`:
- `docling-core` - Core document model and chunkers
- `docling-parse` - PDF parsing
- `pypdfium2` - PDF rendering
- Various ML libraries for layout/OCR/table models

## What's NOT Included

This stripped version removes:
- CLI interface
- Documentation (`docs/`)
- Test suite (`tests/`)
- CI/CD configurations
- ASR (audio) pipeline
- Structured extraction pipeline
- Experimental features

## For Full Embedding Pipeline

To complete the embedding pipeline, you'll need:

1. **Embedding Model** (not in Docling):
   - `sentence-transformers` for local models
   - OpenAI, Cohere, or other embedding APIs

2. **Vector Database**:
   - ChromaDB, Pinecone, Weaviate, Milvus, pgvector, etc.

3. **RAG Framework** (optional):
   - LangChain, LlamaIndex, Haystack all have Docling integrations

## License

MIT License - see original Docling project for details.

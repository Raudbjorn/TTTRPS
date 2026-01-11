# RAGFlow Embedding Pipeline

This is a stripped-down version of RAGFlow focused solely on **document parsing and embedding generation**. All web UI, API servers, agents, chat functionality, and deployment infrastructure have been removed.

## Project Structure

```
ragflow/
├── common/           # Shared utilities
├── deepdoc/          # Document parsing (PDF, DOCX, etc.)
│   ├── parser/       # Format-specific parsers
│   └── vision/       # OCR and layout recognition
└── rag/              # RAG processing pipeline
    ├── app/          # Document-type chunking strategies
    ├── flow/         # Pipeline components
    ├── llm/          # Model interfaces (embedding, OCR, rerank)
    ├── nlp/          # Tokenization and chunking algorithms
    └── utils/        # File/storage utilities
```

## Embedding Generation Pipeline

The embedding pipeline follows this flow:

```
Document → Parse → Chunk/Split → Tokenize → Embed → Vector Output
```

### 1. Document Parsing (`deepdoc/`)

Extracts text and structure from various document formats:

| Parser | File Types | Key Features |
|--------|-----------|--------------|
| `pdf_parser.py` | PDF | Layout analysis, table extraction, OCR |
| `docx_parser.py` | DOCX | Paragraphs, tables, images |
| `excel_parser.py` | XLSX/XLS | Sheet parsing, cell extraction |
| `html_parser.py` | HTML | DOM parsing, text extraction |
| `markdown_parser.py` | MD | Structured markdown parsing |
| `txt_parser.py` | TXT | Plain text with encoding detection |
| `json_parser.py` | JSON | Structured data extraction |

**Vision components** (`deepdoc/vision/`):
- `ocr.py` - Optical character recognition
- `layout_recognizer.py` - Document layout detection
- `table_structure_recognizer.py` - Table structure extraction

### 2. Chunking/Splitting (`rag/nlp/` + `rag/app/`)

Text is split into chunks using various strategies:

**Core chunking functions** (`rag/nlp/__init__.py`):
- `naive_merge()` - Token-based merging with delimiter support
- `hierarchical_merge()` - Structure-aware merging using bullet patterns
- `tree_merge()` - Tree-based hierarchical chunking
- `naive_merge_with_images()` - Chunking with image preservation

**Document-type strategies** (`rag/app/`):
- `naive.py` - General-purpose chunking (default)
- `paper.py` - Academic paper structure
- `book.py` - Book/chapter structure
- `laws.py` - Legal document structure
- `qa.py` - Q&A pair extraction
- `table.py` - Tabular data handling
- `resume.py` - Resume/CV parsing

### 3. Tokenization (`rag/nlp/rag_tokenizer.py`)

Converts text to tokens for embedding:
- `tokenize()` - Standard tokenization
- `fine_grained_tokenize()` - Fine-grained token splitting
- Handles CJK, English, and mixed-language text

### 4. Embedding Generation (`rag/llm/embedding_model.py`)

Supports 30+ embedding providers through a unified interface:

```python
class Base(ABC):
    def encode(self, texts: list) -> tuple[np.ndarray, int]:
        """Encode texts to embeddings, return (vectors, token_count)"""

    def encode_queries(self, text: str) -> tuple[np.ndarray, int]:
        """Encode a single query text"""
```

**Supported Providers**:
- **OpenAI**: `OpenAIEmbed` - text-embedding-ada-002, text-embedding-3-*
- **Azure**: `AzureEmbed` - Azure OpenAI embeddings
- **Ollama**: `OllamaEmbed` - Local Ollama models
- **HuggingFace**: `HuggingFaceEmbed` - TEI server interface
- **Jina**: `JinaMultiVecEmbed` - Jina v2/v3/v4 (multimodal)
- **Cohere**: `CoHereEmbed` - Cohere embed models
- **Gemini**: `GeminiEmbed` - Google text-embedding-004
- **Mistral**: `MistralEmbed` - Mistral embed
- **Voyage**: `VoyageEmbed` - Voyage AI
- **Bedrock**: `BedrockEmbed` - AWS Bedrock (Amazon/Cohere)
- **NVIDIA**: `NvidiaEmbed` - NVIDIA NIM
- **Local**: `LocalAIEmbed`, `LmStudioEmbed`, `XinferenceEmbed`
- **Chinese**: `QWenEmbed`, `ZhipuEmbed`, `BaiChuanEmbed`, `BaiduYiyanEmbed`
- **Others**: SiliconFlow, TogetherAI, Replicate, GPUStack, etc.

## Key Code Patterns

### Chunking with Token Limits

```python
from rag.nlp import naive_merge

chunks = naive_merge(
    sections,              # List of (text, position) tuples
    chunk_token_num=512,   # Max tokens per chunk
    delimiter="\n.;!?",    # Split delimiters
    overlapped_percent=0.1 # Chunk overlap (0-1)
)
```

### Embedding Generation

```python
from rag.llm.embedding_model import OpenAIEmbed

model = OpenAIEmbed(
    key="sk-...",
    model_name="text-embedding-3-small",
    base_url="https://api.openai.com/v1"
)

vectors, token_count = model.encode(["text to embed"])
query_vec, tokens = model.encode_queries("search query")
```

### Document Parsing

```python
from deepdoc.parser import PdfParser

parser = PdfParser()
sections, tables = parser(
    pdf_bytes,
    from_page=0,
    to_page=100,
    callback=progress_callback
)
```

## Dependencies

Key Python packages (see `pyproject.toml`):
- `numpy` - Vector operations
- `tiktoken` - Token counting
- `openai` - OpenAI API client
- `ollama` - Ollama client
- `python-docx` - DOCX parsing
- `pdfplumber`/`pymupdf` - PDF parsing
- `Pillow` - Image processing
- `chardet` - Encoding detection

## Refactoring Notes

This codebase was extracted from RAGFlow and has some residual dependencies:

1. **API imports** - Files like `rag/flow/tokenizer/tokenizer.py` and `rag/app/naive.py` import from `api.db.services.*` which no longer exist. These need to be refactored to:
   - Accept embedding model instances directly
   - Remove tenant/knowledgebase service dependencies

2. **Pipeline class** - `rag/flow/pipeline.py` depends on the agent Canvas and task services. For standalone use, create a simpler orchestrator.

3. **Storage** - `rag/utils/` contains storage connectors (MinIO, S3, etc.) that may not be needed for pure embedding generation.

## Usage Recommendations

For embedding-only use:
1. Use `deepdoc/parser/` directly for document parsing
2. Use `rag/nlp/` chunking functions directly
3. Instantiate embedding models from `rag/llm/embedding_model.py` directly
4. Skip the flow pipeline unless you need the full orchestration

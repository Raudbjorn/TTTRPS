# Unified MBED Command - Technical Design

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Interface                        │
│                  (Click + UV runner)                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  Core Orchestrator                       │
│         (Hardware detection & routing)                   │
└────────┬───────────┬───────────┬───────────┬───────────┘
         │           │           │           │
    ┌────▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
    │  CUDA   │ │OpenVINO│ │  MPS   │ │  CPU   │
    │ Backend │ │Backend │ │Backend │ │Backend │
    └────┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
         │           │           │           │
┌────────▼───────────▼───────────▼───────────▼───────────┐
│              Embedding Pipeline                         │
│    (Chunking → Encoding → Storage → Indexing)          │
└─────────────────────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                Vector Database Layer                     │
│      (ChromaDB | PostgreSQL | FAISS | Qdrant)          │
└─────────────────────────────────────────────────────────┘
```

## Directory Structure

```
mbed-unified/
├── src/
│   ├── mbed/
│   │   ├── __init__.py
│   │   ├── __main__.py           # Entry point
│   │   ├── cli.py                # Click CLI definition
│   │   ├── core/
│   │   │   ├── orchestrator.py   # Main routing logic
│   │   │   ├── hardware.py       # Hardware detection
│   │   │   ├── config.py         # Configuration management
│   │   │   └── state.py          # State persistence
│   │   ├── backends/
│   │   │   ├── base.py           # Abstract backend
│   │   │   ├── cuda.py           # NVIDIA GPU backend
│   │   │   ├── openvino.py       # Intel GPU backend
│   │   │   ├── mps.py            # Apple Silicon backend
│   │   │   └── cpu.py            # CPU-only backend
│   │   ├── pipeline/
│   │   │   ├── chunker.py        # Chunking strategies
│   │   │   ├── encoder.py        # Embedding generation
│   │   │   ├── storage.py        # Vector DB abstraction
│   │   │   └── search.py         # Search & retrieval
│   │   ├── models/
│   │   │   ├── registry.py       # Model registry
│   │   │   ├── ollama.py         # Ollama integration
│   │   │   └── huggingface.py    # HF integration
│   │   ├── databases/
│   │   │   ├── base.py           # Abstract DB interface
│   │   │   ├── chroma.py         # ChromaDB adapter
│   │   │   ├── postgres.py       # PostgreSQL+pgvector
│   │   │   ├── faiss.py          # FAISS adapter
│   │   │   └── qdrant.py         # Qdrant adapter
│   │   ├── servers/
│   │   │   ├── mcp.py            # MCP server
│   │   │   └── api.py            # REST API server
│   │   └── utils/
│   │       ├── uv.py             # UV package manager
│   │       ├── logging.py        # Unified rich logging (rich + enrich)
│   │       └── progress.py       # Progress tracking with rich
│   └── parsers/                  # File parsers (from branches)
│       ├── python_parser.py
│       ├── typescript_parser.py
│       ├── rust_parser.py
│       └── ...
├── tests/
│   ├── unit/
│   ├── integration/
│   └── benchmarks/
├── mbed0/                        # Source from main branch
├── mbed1/                        # Source from _1 branch
├── mbed2/                        # Source from _1_2 branch
├── mbed3/                        # Source from _1_2_3 branch
├── pyproject.toml               # UV-compatible project file
├── Requirements.md
├── Design.md
└── Tasks.md
```

## Core Components

### 1. Hardware Detection & Routing

```python
class HardwareDetector:
    """Detects available hardware acceleration"""
    
    def detect() -> List[HardwareType]:
        available = []
        if cuda_available():
            available.append(HardwareType.CUDA)
        if openvino_available():
            available.append(HardwareType.OPENVINO)
        if mps_available():
            available.append(HardwareType.MPS)
        available.append(HardwareType.CPU)  # Always available
        return available
    
    def select_optimal(available: List[HardwareType]) -> HardwareType:
        # Priority: CUDA > MPS > OpenVINO > CPU
        priority = [HardwareType.CUDA, HardwareType.MPS, 
                   HardwareType.OPENVINO, HardwareType.CPU]
        for hw in priority:
            if hw in available:
                return hw
```

### 2. Backend Abstraction

```python
class EmbeddingBackend(ABC):
    """Abstract base for all acceleration backends"""
    
    @abstractmethod
    def initialize(self, model_name: str, **kwargs):
        """Initialize the backend with model"""
        
    @abstractmethod
    def encode(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for texts"""
        
    @abstractmethod
    def encode_batch(self, texts: List[str], batch_size: int) -> np.ndarray:
        """Batch encoding with optimal size for backend"""
        
    @property
    @abstractmethod
    def optimal_batch_size(self) -> int:
        """Backend-specific optimal batch size"""
        
    @property
    @abstractmethod
    def supports_async(self) -> bool:
        """Whether backend supports async operations"""
```

### 3. UV Integration

```python
class UVManager:
    """Manages UV package operations"""
    
    def __init__(self):
        self.ensure_uv_installed()
        
    def ensure_uv_installed(self):
        """Install UV if not present"""
        if not shutil.which('uv'):
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'uv'])
            
    def create_venv(self, path: Path):
        """Create UV-managed virtual environment"""
        subprocess.run(['uv', 'venv', str(path)])
        
    def install_dependencies(self, requirements: List[str]):
        """Install packages using UV (3-5x faster than pip)"""
        subprocess.run(['uv', 'pip', 'install'] + requirements)
```

### 4. Pipeline Architecture

```python
class EmbeddingPipeline:
    """Manages the full embedding generation pipeline"""
    
    def __init__(self, backend: EmbeddingBackend, 
                 chunker: ChunkingStrategy,
                 storage: VectorStore):
        self.backend = backend
        self.chunker = chunker
        self.storage = storage
        
    async def process_files(self, files: List[Path]) -> ProcessingResult:
        # Stage 1: Chunking
        chunks = await self.chunker.chunk_files(files)
        
        # Stage 2: Embedding
        embeddings = await self.backend.encode_batch(
            [c.text for c in chunks],
            batch_size=self.backend.optimal_batch_size
        )
        
        # Stage 3: Storage
        await self.storage.store_embeddings(chunks, embeddings)
        
        # Stage 4: Indexing
        await self.storage.build_index()
        
        return ProcessingResult(...)
```

### 5. State Management

```python
class ProcessingState:
    """Manages resumable processing state"""
    
    def __init__(self, state_file: Path = Path('.mbed_state.pkl')):
        self.state_file = state_file
        self.processed_files = set()
        self.last_checkpoint = None
        self.model_config = {}
        
    def checkpoint(self):
        """Save current state for resume"""
        with open(self.state_file, 'wb') as f:
            pickle.dump({
                'processed_files': self.processed_files,
                'last_checkpoint': datetime.now(),
                'model_config': self.model_config
            }, f)
            
    def can_resume(self) -> bool:
        """Check if resumable state exists"""
        return self.state_file.exists()
```

## Hardware-Specific Code Paths

### Divergence Points

The codebase diverges at these key points based on hardware:

1. **Model Loading**
   - CUDA: Uses torch.cuda, requires VRAM management
   - OpenVINO: Uses openvino.runtime, requires model conversion
   - MPS: Uses torch.mps, requires Metal Performance Shaders
   - CPU: Uses standard torch or ONNX runtime

2. **Batch Processing**
   - CUDA: Large batches (256-512), parallel processing
   - OpenVINO: Medium batches (64-128), INT8 quantization
   - MPS: Medium batches (128-256), unified memory
   - CPU: Small batches (16-32), thread pooling

3. **Memory Management**
   - CUDA: VRAM allocation, pinned memory transfers
   - OpenVINO: Shared memory, zero-copy where possible
   - MPS: Unified memory architecture, automatic
   - CPU: RAM-based, memory mapping for large files

### Hardware-Agnostic Features

These features remain consistent across all backends:

1. **CLI Interface**: All commands and flags
2. **Chunking Strategies**: Text splitting logic
3. **Vector Database Operations**: Storage and retrieval
4. **File Parsing**: Language-specific parsers
5. **Progress Tracking**: UI and logging
6. **State Management**: Checkpointing and resume

## Configuration Management

```yaml
# .mbed/config.yaml
version: "1.0"
defaults:
  model: "nomic-embed-text"
  database: "chroma"
  hardware: "auto"  # auto, cuda, openvino, mps, cpu
  
processing:
  chunk_size: 512
  chunk_overlap: 128
  batch_size: "auto"  # Backend determines optimal
  max_workers: 4
  
storage:
  chroma:
    persist_directory: ".mbed/chroma"
    collection_name: "embeddings"
  postgres:
    connection_string: "postgresql://..."
    vector_dimension: 768
  
models:
  nomic-embed-text:
    dimension: 768
    provider: "ollama"
  mxbai-embed-large:
    dimension: 1024
    provider: "ollama"
```

## Migration Strategy

### From Existing Branches

1. **Extract Common Code**: Identify shared functionality
2. **Isolate Hardware-Specific**: Move to backend modules
3. **Unified Interface**: Create consistent API across backends
4. **Test Coverage**: Ensure all paths tested independently

### Database Migration

```python
class MigrationManager:
    """Handles migration between vector databases"""
    
    async def migrate(self, source: VectorStore, target: VectorStore):
        # Export from source
        embeddings = await source.export_all()
        
        # Transform if needed
        if source.dimension != target.dimension:
            embeddings = self.transform_dimensions(embeddings)
            
        # Import to target
        await target.import_batch(embeddings)
        
        # Verify integrity
        assert await source.count() == await target.count()
```

## Testing Strategy

### Test Migration Approach

Tests will be migrated incrementally from source branches (mbed0-3) as features are implemented:

```python
# Test organization
tests/
├── migrated/           # Tests from original branches
│   ├── mbed0/         # Tests from main branch
│   ├── mbed1/         # Tests from _1 branch
│   ├── mbed2/         # Tests from _1_2 branch
│   └── mbed3/         # Tests from _1_2_3 branch
├── unified/           # New unified tests
│   ├── unit/          # Unit tests for unified code
│   ├── integration/   # Cross-backend integration
│   └── regression/    # Combined regression suite
└── hardware/          # Hardware-specific tests
    ├── cuda/
    ├── openvino/
    ├── mps/
    └── cpu/
```

### Migration Process

1. **Identify relevant tests** from mbed0-3 for current feature
2. **Copy tests** to migrated/ directory with branch prefix
3. **Adapt tests** for unified interfaces
4. **Run tests** to verify feature completeness
5. **Enhance tests** for new unified capabilities
6. **Move to unified/** once fully integrated

### Test Coverage Requirements

```python
# coverage.py configuration
[run]
source = src/
omit = */tests/*, */mbed0/*, */mbed1/*, */mbed2/*, */mbed3/*

[report]
fail_under = 90
show_missing = True

[html]
directory = coverage_html/
```

### Unit Tests
- Hardware detection mocking
- Backend abstraction compliance
- Pipeline stage isolation
- State management edge cases
- **Migrated parser tests from each branch**
- **Migrated chunking tests from each branch**

### Integration Tests
- End-to-end processing per backend
- Database adapter verification
- Model loading and inference
- CLI command validation
- **Cross-branch feature compatibility**
- **Migrated workflow tests from each branch**

### Performance Benchmarks
- Files per minute by hardware
- Memory usage profiling
- Startup time measurement
- Query latency testing
- **Performance regression from branch baselines**
- **Hardware-specific optimization validation**

### Test-Driven Migration

Each phase includes test migration as a prerequisite:

```python
# Example: Before implementing CUDA backend
def test_cuda_backend_from_main():
    """Migrated from mbed0/test_ollama_cuda.py"""
    # Original test adapted for unified interface
    backend = CUDABackend()
    assert backend.optimal_batch_size == 512
    
def test_cuda_vram_management():
    """New test for unified architecture"""
    backend = CUDABackend()
    backend.check_vram()
    assert backend.can_process_batch(256)
```

## Unified Logging Architecture

### Rich-Based Logging System

The unified logging system uses **rich**, **rich-click**, and **enrich** for beautiful, consistent terminal output across all components:

```python
from src.core.logging import logger, create_progress, hardware_status

# Component-specific logger
log = logger.get_logger(__name__)

# Beautiful progress bars
with create_progress() as progress:
    task = progress.add_task("Processing files...", total=100)
    for i in range(100):
        progress.update(task, advance=1)

# Hardware-specific status output
hardware_status("cuda", "ready", {
    "vram_gb": 24.0,
    "cuda_version": "11.8"
})
```

### Features:
- **Rich Tracebacks**: Beautiful, informative exception output with local variables
- **Structured Logging**: Consistent log format with colors and icons
- **Progress Tracking**: Multiple concurrent progress bars with time estimates
- **Hardware Status**: Formatted tables for hardware detection results
- **Code Highlighting**: Syntax highlighting for code snippets in output
- **Panels & Tables**: Rich formatting for structured data display

### Log Levels & Styling:
- **DEBUG**: Dim white - Detailed diagnostic information
- **INFO**: Cyan - General informational messages
- **WARNING**: Yellow with ⚠️ icon - Warning messages
- **ERROR**: Bold red with ❌ icon - Error messages
- **SUCCESS**: Bold green with ✅ icon - Success confirmations

### CLI Integration:
- **rich-click**: Enhanced Click CLI with markdown support in help text
- **Colored help**: Commands, options, and arguments with distinct colors
- **Progress spinners**: Non-blocking progress indicators for long operations
- **Error panels**: Formatted error messages with helpful suggestions

## Security Considerations

1. **No eval() or exec()**: All dynamic code eliminated
2. **Input Validation**: All user inputs sanitized
3. **Dependency Pinning**: Exact versions in pyproject.toml
4. **Network Isolation**: Optional offline mode
5. **Secret Management**: No hardcoded credentials

## Extensibility Points

### Plugin System

```python
class PluginRegistry:
    """Manages third-party extensions"""
    
    def register_model(self, name: str, provider: ModelProvider):
        """Add custom embedding model"""
        
    def register_chunker(self, name: str, strategy: ChunkingStrategy):
        """Add custom chunking strategy"""
        
    def register_database(self, name: str, adapter: VectorStore):
        """Add custom vector database"""
```

### Custom Backends

Third parties can add new acceleration backends by:
1. Implementing `EmbeddingBackend` interface
2. Registering with `HardwareDetector`
3. Providing optimal parameters

## Performance Targets

| Metric | CPU | OpenVINO | MPS | CUDA |
|--------|-----|----------|-----|------|
| Files/min | 100 | 300 | 400 | 500 |
| Batch size | 32 | 128 | 256 | 512 |
| RAM usage | 2GB | 3GB | 4GB | 2GB |
| VRAM usage | N/A | Shared | Shared | 6GB |
| Startup time | 2s | 3s | 2.5s | 4s |
| Query latency | 50ms | 30ms | 25ms | 20ms |

## Development Workflow

1. **Branch Strategy**
   - `main`: Stable releases
   - `develop`: Integration branch
   - `feature/*`: New features
   - `hardware/*`: Backend-specific work

2. **Testing Requirements**
   - All PRs must pass CPU tests (GitHub Actions)
   - Hardware-specific tests run on dedicated runners
   - Performance regression tests on merge to develop

3. **Release Process**
   - Semantic versioning (MAJOR.MINOR.PATCH)
   - Changelog generation from commits
   - Binary distributions via UV
   - Docker images for each backend
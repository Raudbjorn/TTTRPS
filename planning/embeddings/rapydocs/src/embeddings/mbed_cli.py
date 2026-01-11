#!/usr/bin/env python3
"""
mbed - Advanced embedding generation CLI with comprehensive RAG features

Enhanced Features:
- Multiple embedding models (Ollama, BGE-M3, Sentence Transformers)
- LLM preprocessing for structured data
- Advanced chunking strategies (fixed, semantic, hierarchical, topic-based)
- Multiple database backends (ChromaDB, PostgreSQL, FAISS)
- Hardware acceleration (CUDA, Apple Silicon, Intel GPU)
- Batch processing with parallel execution
- Comprehensive error handling and recovery
- Progress tracking and resumable processing
- File filtering and exclusion patterns
"""

import os
import sys
import json
import argparse
import logging
import tempfile
import requests
import subprocess
import platform
import hashlib
import time
import shutil
import multiprocessing
import pickle
import signal
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Set
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from urllib.parse import urlparse

# Optional imports with graceful fallback
try:
    from tqdm import tqdm
except ImportError:
    # Simple progress bar fallback
    class tqdm:
        def __init__(self, *args, **kwargs):
            self.total = kwargs.get('total', 0)
            self.n = 0
            self.desc = kwargs.get('desc', '')
            print(f"{self.desc}: Starting...")
        
        def update(self, n=1):
            self.n += n
            if self.total > 0 and self.n % max(1, self.total // 10) == 0:
                print(f"{self.desc}: {self.n}/{self.total} ({100*self.n/self.total:.0f}%)")
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            if self.total > 0:
                print(f"{self.desc}: Complete ({self.n}/{self.total})")

try:
    import aiofiles
except ImportError:
    aiofiles = None

try:
    import asyncio
except ImportError:
    asyncio = None

# Try importing advanced modules with specific error handling
module_import_errors = {}

try:
    from .llm_preprocessor import LLMPreprocessor, PreprocessorConfig, ProcessingMode
except ImportError as e:
    module_import_errors['LLMPreprocessor'] = str(e)
    LLMPreprocessor = None
    PreprocessorConfig = None
    ProcessingMode = None

try:
    from .semantic_chunking import SemanticChunker, SemanticChunkConfig, ChunkingStrategy
except ImportError as e:
    module_import_errors['SemanticChunker'] = str(e)
    SemanticChunker = None
    SemanticChunkConfig = None
    ChunkingStrategy = None

try:
    from .enhanced_chunking import EnhancedChunker, EnhancedChunkConfig
except ImportError as e:
    module_import_errors['EnhancedChunker'] = str(e)
    EnhancedChunker = None
    EnhancedChunkConfig = None

try:
    from .bge_m3_embeddings import BGEM3Embeddings, HybridBGEM3Retriever
except ImportError as e:
    module_import_errors['BGEM3Embeddings'] = str(e)
    BGEM3Embeddings = None
    HybridBGEM3Retriever = None

try:
    from .embeddings_factory import detect_best_backend, create_embeddings
except ImportError as e:
    module_import_errors['embeddings_factory'] = str(e)
    detect_best_backend = None
    create_embeddings = None

# Define fallback ChunkingStrategy if not imported
if ChunkingStrategy is None:
    class ChunkingStrategy(Enum):
        """Available chunking strategies"""
        FIXED_SIZE = "fixed_size"
        SEMANTIC = "semantic"
        HIERARCHICAL = "hierarchical"
        SENTENCE_BASED = "sentence_based"
        PARAGRAPH_BASED = "paragraph_based"
        TOPIC_BASED = "topic_based"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.environ.get('MBED_LOG_FILE', 'mbed.log'), mode='a')
    ]
)
logger = logging.getLogger(__name__)

# Log import issues if any
if module_import_errors:
    for module, error in module_import_errors.items():
        logger.debug(f"Optional module {module} not available: {error}")


class ModelType(Enum):
    """Available embedding model types"""
    OLLAMA = "ollama"
    BGE_M3 = "bge-m3"
    SENTENCE_TRANSFORMERS = "sentence-transformers"
    OPENAI = "openai"
    COHERE = "cohere"


class DatabaseType(Enum):
    """Available database backends"""
    CHROMADB = "chromadb"
    POSTGRESQL = "postgresql"
    FAISS = "faiss"
    QDRANT = "qdrant"
    MILVUS = "milvus"
    WEAVIATE = "weaviate"


@dataclass
class MbedConfig:
    """Comprehensive configuration for mbed CLI"""
    # Model settings
    model_type: ModelType = ModelType.OLLAMA
    model_name: str = "nomic-embed-text"
    ollama_host: str = "http://localhost:11434"

    # Preprocessing settings
    enable_preprocessing: bool = False
    preprocessing_model: str = "llama3.2:latest"
    preprocessing_cache: bool = True
    expand_keys: bool = True
    generate_summaries: bool = True

    # Chunking settings
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.FIXED_SIZE
    enable_enhanced_chunking: bool = False
    min_chunk_size: int = 200
    max_chunk_size: int = 800
    target_chunk_size: int = 500
    chunk_overlap: int = 50
    add_entity_headers: bool = True

    # Database settings
    database_type: DatabaseType = DatabaseType.CHROMADB
    database_url: str = ""
    database_path: str = ""
    collection_name: str = "documents"

    # Processing settings
    batch_size: int = 100
    max_workers: int = 4
    use_gpu: bool = True
    device: str = "auto"  # auto, cuda, mps, cpu
    timeout_seconds: int = 300

    # File processing settings
    recursive: bool = True
    follow_symlinks: bool = False
    exclude_patterns: List[str] = field(default_factory=lambda: [
        ".git", "__pycache__", "node_modules", ".venv", "venv",
        "*.pyc", "*.pyo", "*.pyd", ".DS_Store", "*.so", "*.dylib"
    ])
    include_extensions: List[str] = field(default_factory=lambda: [
        ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".cpp", ".c", ".h",
        ".rs", ".go", ".rb", ".php", ".cs", ".swift", ".kt", ".scala",
        ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".xml", ".html"
    ])
    max_file_size_mb: int = 10

    # Advanced features
    enable_hybrid_search: bool = False
    enable_reranking: bool = False
    enable_metadata_extraction: bool = True

    # Performance settings
    cache_embeddings: bool = True
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache" / "mbed")

    # Output settings
    verbose: bool = False
    quiet: bool = False
    dry_run: bool = False
    show_progress: bool = True
    output_format: str = "json"  # json, csv, table


class ProcessingState:
    """Manages processing state for resumable operations"""
    
    def __init__(self, state_file: Optional[Path] = None):
        if state_file is None:
            state_file = Path('.mbed_state.pkl')
        self.state_file = state_file
        self.processed_files: Set[str] = set()
        self.failed_files: Dict[str, str] = {}
        self.load_state()
    
    def load_state(self):
        """Load previous processing state"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'rb') as f:
                    state = pickle.load(f)
                    self.processed_files = state.get('processed_files', set())
                    self.failed_files = state.get('failed_files', {})
                logger.info(f"Loaded state: {len(self.processed_files)} files already processed")
            except (pickle.PickleError, OSError, KeyError) as e:
                logger.warning(f"Could not load state file: {e}")
    
    def save_state(self):
        """Save current processing state"""
        try:
            with open(self.state_file, 'wb') as f:
                pickle.dump({
                    'processed_files': self.processed_files,
                    'failed_files': self.failed_files,
                    'timestamp': datetime.now().isoformat()
                }, f)
        except (pickle.PickleError, OSError) as e:
            logger.error(f"Could not save state: {e}")
    
    def mark_processed(self, file_path: str):
        """Mark file as processed"""
        self.processed_files.add(str(file_path))
        if str(file_path) in self.failed_files:
            del self.failed_files[str(file_path)]
    
    def mark_failed(self, file_path: str, error: str):
        """Mark file as failed"""
        self.failed_files[str(file_path)] = error
    
    def is_processed(self, file_path: str) -> bool:
        """Check if file was already processed"""
        return str(file_path) in self.processed_files
    
    def clear(self):
        """Clear all state"""
        self.processed_files.clear()
        self.failed_files.clear()
        if self.state_file.exists():
            try:
                self.state_file.unlink()
            except OSError as e:
                logger.warning(f"Could not remove state file: {e}")


class DependencyManager:
    """Simplified dependency manager"""

    @staticmethod
    def ensure_uv() -> bool:
        """Check if uv is available"""
        return shutil.which('uv') is not None

    @staticmethod
    def get_python_executable() -> str:
        """Get the Python executable path"""
        return sys.executable

    @staticmethod
    def install_package(package: str, use_uv: bool = True) -> bool:
        """Install a single package"""
        python_exe = DependencyManager.get_python_executable()
        
        if use_uv and DependencyManager.ensure_uv():
            cmd = ['uv', 'pip', 'install', package]
        else:
            cmd = [python_exe, '-m', 'pip', 'install', package]

        try:
            subprocess.run(cmd, capture_output=True, check=True, timeout=300)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError) as e:
            logger.debug(f"Failed to install {package}: {e}")
            return False

    @staticmethod
    def check_required_dependencies():
        """Check and install only critical dependencies"""
        required = ['chromadb', 'requests', 'numpy', 'tqdm']
        missing = []
        
        for package in required:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing.append(package)
        
        if missing:
            logger.info(f"Installing required packages: {', '.join(missing)}")
            for package in missing:
                if not DependencyManager.install_package(package):
                    logger.error(f"Failed to install required package: {package}")
                    return False
        
        return True


class FileProcessor:
    """Enhanced file processor with filtering and validation"""

    def __init__(self, config: MbedConfig):
        self.config = config
        self.excluded_dirs = set()
        self.included_extensions = set(config.include_extensions)

        # Compile exclusion patterns safely
        self.exclude_regexes = []
        for pattern in config.exclude_patterns:
            try:
                if '*' in pattern or '?' in pattern:
                    # Convert glob to regex
                    regex_pattern = pattern.replace('.', r'\.')
                    regex_pattern = regex_pattern.replace('*', '.*')
                    regex_pattern = regex_pattern.replace('?', '.')
                    self.exclude_regexes.append(re.compile(regex_pattern))
                else:
                    # Treat as literal string
                    self.excluded_dirs.add(pattern)
            except re.error as e:
                logger.warning(f"Invalid exclusion pattern '{pattern}': {e}")

    def should_process_file(self, file_path: Path) -> bool:
        """Check if file should be processed"""
        try:
            # Check file size
            file_stat = file_path.stat()
            if file_stat.st_size > self.config.max_file_size_mb * 1024 * 1024:
                logger.debug(f"Skipping large file: {file_path}")
                return False

            # Check extension
            if self.included_extensions and file_path.suffix.lower() not in self.included_extensions:
                return False

            # Check exclusion patterns
            path_str = str(file_path)

            # Check directory exclusions
            for part in file_path.parts:
                if part in self.excluded_dirs:
                    return False

            # Check regex patterns
            for regex in self.exclude_regexes:
                if regex.search(path_str):
                    return False

            return True
        except (OSError, AttributeError) as e:
            logger.debug(f"Error checking file {file_path}: {e}")
            return False

    def find_files(self, path: Path) -> List[Path]:
        """Find all files to process"""
        files = []

        try:
            if path.is_file():
                if self.should_process_file(path):
                    files.append(path)
            elif path.is_dir():
                if self.config.recursive:
                    pattern = "**/*"
                else:
                    pattern = "*"

                for file_path in path.glob(pattern):
                    if file_path.is_file() and self.should_process_file(file_path):
                        files.append(file_path)
        except (OSError, PermissionError) as e:
            logger.error(f"Error accessing path {path}: {e}")

        return files


class MbedCLI:
    """Main CLI class with comprehensive error handling"""

    def __init__(self, config: MbedConfig):
        self.config = config
        self.stats = {
            'files_processed': 0,
            'chunks_created': 0,
            'embeddings_generated': 0,
            'errors': 0,
            'skipped': 0,
            'start_time': time.time()
        }
        
        # Initialize components
        self.file_processor = FileProcessor(config)
        self.state = None
        if not config.dry_run:
            self.state = ProcessingState()
        
        self.database = None
        self.preprocessor = None
        self.chunker = None
        
        # Setup cache directory
        if config.cache_embeddings:
            try:
                config.cache_dir.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                logger.warning(f"Could not create cache directory: {e}")
        
        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize processing components with error handling"""
        # Initialize preprocessor
        if self.config.enable_preprocessing and LLMPreprocessor and PreprocessorConfig:
            try:
                preprocessor_config = PreprocessorConfig(
                    model_name=self.config.preprocessing_model,
                    enable_key_expansion=self.config.expand_keys,
                    enable_summary=self.config.generate_summaries,
                    cache_enabled=self.config.preprocessing_cache,
                    cache_dir=self.config.cache_dir / "preprocessing"
                )
                self.preprocessor = LLMPreprocessor(preprocessor_config)
                logger.info("LLM preprocessor initialized")
            except Exception as e:
                logger.warning(f"Could not initialize preprocessor: {e}")

        # Initialize chunker
        if self.config.enable_enhanced_chunking and EnhancedChunker and EnhancedChunkConfig:
            try:
                # OVERLAP FIX: Calculate overlap percentage correctly
                overlap_percent = min(0.5, self.config.chunk_overlap / self.config.target_chunk_size)
                chunker_config = EnhancedChunkConfig(
                    min_tokens=self.config.min_chunk_size,
                    max_tokens=self.config.max_chunk_size,
                    target_tokens=self.config.target_chunk_size,
                    overlap_percent=overlap_percent,
                    add_entity_headers=self.config.add_entity_headers
                )
                self.chunker = EnhancedChunker(chunker_config)
                logger.info("Enhanced chunker initialized")
            except Exception as e:
                logger.warning(f"Could not initialize enhanced chunker: {e}")
        elif SemanticChunker and SemanticChunkConfig:
            try:
                chunker_config = SemanticChunkConfig(
                    min_chunk_size=self.config.min_chunk_size,
                    max_chunk_size=self.config.max_chunk_size,
                    target_chunk_size=self.config.target_chunk_size,
                    overlap_size=self.config.chunk_overlap,
                    strategy=self.config.chunking_strategy
                )
                self.chunker = SemanticChunker(chunker_config)
                logger.info("Semantic chunker initialized")
            except Exception as e:
                logger.warning(f"Could not initialize semantic chunker: {e}")

        # Initialize database
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database backend with proper error handling"""
        if self.config.database_type == DatabaseType.CHROMADB:
            try:
                import chromadb
                
                # Use configured path or default
                db_path = self.config.database_path or str(self.config.cache_dir / "chromadb")
                client = chromadb.PersistentClient(path=db_path)
                
                self.database = client.get_or_create_collection(
                    name=self.config.collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                logger.info(f"ChromaDB initialized at {db_path}")
            except ImportError:
                logger.error("ChromaDB not installed. Please install with: pip install chromadb")
                logger.error("Or use the mbed wrapper which automatically handles dependencies.")
                raise RuntimeError("ChromaDB not available - please install manually or use the mbed wrapper")
            except Exception as e:
                logger.error(f"Failed to initialize ChromaDB: {e}")
                raise
        
        elif self.config.database_type == DatabaseType.POSTGRESQL:
            logger.info("PostgreSQL backend selected (implementation needed)")
        elif self.config.database_type == DatabaseType.FAISS:
            logger.info("FAISS backend selected (implementation needed)")
        else:
            logger.warning(f"Unknown database type: {self.config.database_type}")

    def _should_preprocess(self, file_path: Path) -> bool:
        """Check if file should be preprocessed"""
        structured_extensions = {'.json', '.xml', '.yaml', '.yml', '.toml'}
        return file_path.suffix.lower() in structured_extensions

    def _chunk_content(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Chunk content using configured strategy with fallback"""
        chunks = []

        # Try advanced chunking first
        if self.chunker:
            try:
                if hasattr(self.chunker, 'chunk_with_enhancement'):
                    # Enhanced chunker
                    doc_metadata = {
                        'file_path': str(file_path),
                        'file_name': file_path.name,
                        'file_type': file_path.suffix
                    }
                    enhanced_chunks = self.chunker.chunk_with_enhancement(
                        content,
                        doc_id=hashlib.sha256(str(file_path).encode()).hexdigest()[:16],
                        doc_metadata=doc_metadata
                    )
                    chunks = enhanced_chunks
                else:
                    # Semantic chunker
                    semantic_chunks = self.chunker.chunk_text(content)
                    chunks = [
                        {
                            'content': chunk.text if hasattr(chunk, 'text') else str(chunk),
                            'metadata': {
                                'chunk_id': getattr(chunk, 'chunk_id', f'chunk_{i}'),
                                'file_path': str(file_path)
                            }
                        }
                        for i, chunk in enumerate(semantic_chunks)
                    ]
            except Exception as e:
                logger.warning(f"Advanced chunking failed for {file_path}: {e}")
                chunks = []

        # Fallback to simple chunking if needed
        if not chunks:
            chunks = self._simple_chunk(content, file_path)

        return chunks

    def _simple_chunk(self, content: str, file_path: Path) -> List[Dict[str, Any]]:
        """Simple fixed-size chunking fallback with proper error handling"""
        chunks = []
        
        try:
            # Split into sentences for better boundaries
            sentences = re.split(r'(?<=[.!?])\s+', content)
            
            current_chunk = []
            current_size = 0
            chunk_index = 0
            
            for sentence in sentences:
                sentence_size = len(sentence.split())
                
                # If adding this sentence would exceed target size and we have content
                if current_size + sentence_size > self.config.target_chunk_size and current_chunk:
                    chunk_text = ' '.join(current_chunk)
                    chunks.append({
                        'content': chunk_text,
                        'metadata': {
                            'file_path': str(file_path),
                            'chunk_index': chunk_index,
                            'chunk_size': len(chunk_text)
                        }
                    })
                    
                    # Reset for the next chunk, keeping the last sentence for overlap
                    if self.config.chunk_overlap > 0 and current_chunk:
                        current_chunk = [current_chunk[-1]]
                        current_size = self.count_tokens(current_chunk[0])
                    else:
                        current_chunk = []
                        current_size = 0
                    chunk_index += 1
                
                current_chunk.append(sentence)
                current_size += sentence_size
            
            # Add final chunk
            if current_chunk:
                chunk_text = ' '.join(current_chunk)
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'file_path': str(file_path),
                        'chunk_index': chunk_index,
                        'chunk_size': len(chunk_text)
                    }
                })
                
        except Exception as e:
            logger.error(f"Chunking failed for {file_path}: {e}")
            # Ultimate fallback: split by word count
            words = content.split()
            chunk_size = self.config.target_chunk_size
            
            for i in range(0, len(words), chunk_size):
                chunk_words = words[i:i + chunk_size]
                chunk_text = ' '.join(chunk_words)
                chunks.append({
                    'content': chunk_text,
                    'metadata': {
                        'file_path': str(file_path),
                        'chunk_index': i // chunk_size,
                        'chunk_size': len(chunk_text)
                    }
                })

        return chunks

    def _generate_embeddings(self, chunks: List[Dict[str, Any]]) -> List[List[float]]:
        """Generate embeddings with proper error handling and no random fallback"""
        embeddings = []

        # Try BGE-M3 first if available
        if BGEM3Embeddings and self.config.model_type == ModelType.BGE_M3:
            try:
                embedder = BGEM3Embeddings(
                    model_name=self.config.model_name,
                    use_dense=True,
                    normalize=True
                )
                for chunk in chunks:
                    embedding = embedder.embed_text(chunk['content'])
                    if isinstance(embedding, dict) and 'dense' in embedding:
                        embeddings.append(embedding['dense'].tolist() if hasattr(embedding['dense'], 'tolist') else embedding['dense'])
                    else:
                        embeddings.append(embedding)
                return embeddings
            except Exception as e:
                logger.warning(f"BGE-M3 embedding failed: {e}")

        # Try Ollama
        if self.config.model_type == ModelType.OLLAMA:
            try:
                import ollama
                for chunk in chunks:
                    response = ollama.embeddings(
                        model=self.config.model_name,
                        prompt=chunk['content']
                    )
                    embeddings.append(response['embedding'])
                return embeddings
            except Exception as e:
                logger.warning(f"Ollama embedding failed: {e}")

        # Try sentence transformers
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')  # Fallback model
            texts = [chunk['content'] for chunk in chunks]
            embeddings = model.encode(texts).tolist()
            return embeddings
        except Exception as e:
            logger.warning(f"Sentence transformers failed: {e}")

        # No random embeddings - fail instead
        logger.error("No embedding method available. Install ollama, sentence-transformers, or other supported backends.")
        raise RuntimeError("No embedding method available")

    def _store_embeddings(self, chunks: List[Dict], embeddings: List, file_path: Path):
        """Store embeddings in database with proper error handling"""
        if not self.database or self.config.dry_run:
            return

        try:
            # Prepare data for ChromaDB
            documents = [chunk['content'] for chunk in chunks]
            metadatas = [chunk.get('metadata', {}) for chunk in chunks]
            
            # Ensure metadata doesn't contain None values
            for metadata in metadatas:
                metadata.update({
                    'file_name': file_path.name,
                    'file_extension': file_path.suffix,
                    'processing_time': datetime.now().isoformat()
                })
                # Remove None values
                metadata = {k: v for k, v in metadata.items() if v is not None}
            
            ids = [f"{hashlib.sha256(str(file_path).encode()).hexdigest()[:8]}_{i}" 
                   for i in range(len(chunks))]

            # Store in batches
            batch_size = self.config.batch_size
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                batch_embs = embeddings[i:i+batch_size] if embeddings else None

                if batch_embs:
                    self.database.add(
                        documents=batch_docs,
                        embeddings=batch_embs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                else:
                    self.database.add(
                        documents=batch_docs,
                        metadatas=batch_metas,
                        ids=batch_ids
                    )
                    
        except Exception as e:
            logger.error(f"Failed to store embeddings for {file_path}: {e}")
            raise

    def process_file(self, file_path: Path) -> Dict[str, Any]:
        """Process a single file with comprehensive error handling"""
        result = {
            'file': str(file_path),
            'status': 'pending',
            'chunks': 0,
            'embeddings': 0,
            'errors': []
        }

        # Check if already processed
        if self.state and self.state.is_processed(str(file_path)):
            result['status'] = 'skipped'
            self.stats['skipped'] += 1
            return result

        try:
            # Read file content
            # Try UTF-8 first, then fall back to latin-1 if needed
            try:
                content = file_path.read_text(encoding='utf-8')
            except UnicodeDecodeError:
                logger.debug(f"Could not decode {file_path} as utf-8, trying latin-1.")
                content = file_path.read_text(encoding='latin-1', errors='ignore')
            if not content.strip():
                result['status'] = 'empty'
                if self.state:
                    self.state.mark_processed(str(file_path))
                return result

            # Apply preprocessing if enabled
            if self.preprocessor and self._should_preprocess(file_path):
                try:
                    processed_content = self.preprocessor.preprocess(content)
                    content = processed_content
                    result['preprocessed'] = True
                except Exception as e:
                    logger.debug(f"Preprocessing failed for {file_path}: {e}")
                    result['preprocessed'] = False

            # Apply chunking
            chunks = self._chunk_content(content, file_path)
            result['chunks'] = len(chunks)

            # Generate embeddings
            embeddings = self._generate_embeddings(chunks)
            result['embeddings'] = len(embeddings)

            # Store in database
            if not self.config.dry_run:
                self._store_embeddings(chunks, embeddings, file_path)

            result['status'] = 'success'
            self.stats['files_processed'] += 1
            self.stats['chunks_created'] += len(chunks)
            self.stats['embeddings_generated'] += len(embeddings)

            # Mark as processed
            if self.state:
                self.state.mark_processed(str(file_path))

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            result['status'] = 'error'
            result['errors'].append(str(e))
            self.stats['errors'] += 1
            
            if self.state:
                self.state.mark_failed(str(file_path), str(e))

        return result

    def process_directory(self, dir_path: Path) -> Dict[str, Any]:
        """Process directory with parallel processing and proper error handling"""
        # Find all files
        files = self.file_processor.find_files(dir_path)
        logger.info(f"Found {len(files)} files to process in {dir_path}")

        if not files:
            return {
                'directory': str(dir_path),
                'files_found': 0,
                'files_processed': 0,
                'files_failed': 0,
                'results': []
            }

        # Process files in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(self.process_file, file_path): file_path
                for file_path in files
            }

            # Process results with progress bar
            with tqdm(total=len(files), desc="Processing files", disable=self.config.quiet) as pbar:
                for future in as_completed(futures):
                    file_path = futures[future]
                    try:
                        result = future.result(timeout=self.config.timeout_seconds)
                        results.append(result)
                        pbar.update(1)

                        # Save state periodically
                        if self.state and len(results) % 50 == 0:
                            self.state.save_state()

                    except Exception as e:
                        logger.error(f"Failed to process {file_path}: {e}")
                        self.stats['errors'] += 1
                        results.append({
                            'file': str(file_path),
                            'status': 'error',
                            'error': str(e)
                        })
                        pbar.update(1)

        # Final state save
        if self.state:
            self.state.save_state()

        # Calculate statistics
        successful = sum(1 for r in results if r['status'] == 'success')
        failed = sum(1 for r in results if r['status'] == 'error')

        return {
            'directory': str(dir_path),
            'files_found': len(files),
            'files_processed': successful,
            'files_failed': failed,
            'total_chunks': self.stats['chunks_created'],
            'total_embeddings': self.stats['embeddings_generated'],
            'results': results
        }

    def process_url(self, url: str) -> Dict[str, Any]:
        """Process content from URL with proper error handling"""
        result = {
            'url': url,
            'status': 'pending'
        }

        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")

            # Fetch content
            response = requests.get(
                url, 
                timeout=self.config.timeout_seconds,
                headers={'User-Agent': 'mbed-cli/3.0'}
            )
            response.raise_for_status()

            # Create temporary file
            content_type = response.headers.get('Content-Type', '')
            suffix = '.json' if 'json' in content_type else '.txt'

            with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as tmp_file:
                tmp_file.write(response.text)
                tmp_path = Path(tmp_file.name)

            # Process the temporary file
            try:
                file_result = self.process_file(tmp_path)
                result.update(file_result)
                result['content_type'] = content_type
                result['content_length'] = len(response.text)
            finally:
                tmp_path.unlink(missing_ok=True)

        except (requests.RequestException, ValueError, OSError) as e:
            logger.error(f"Failed to process URL {url}: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            self.stats['errors'] += 1

        return result

    def print_statistics(self):
        """Print processing statistics"""
        elapsed = time.time() - self.stats['start_time']

        print("\n" + "="*60)
        print("Processing Statistics:")
        print("="*60)
        print(f"Files processed:     {self.stats['files_processed']:,}")
        print(f"Files skipped:       {self.stats['skipped']:,}")
        print(f"Chunks created:      {self.stats['chunks_created']:,}")
        print(f"Embeddings generated: {self.stats['embeddings_generated']:,}")
        print(f"Errors encountered:  {self.stats['errors']:,}")
        print(f"Total time:          {elapsed:.2f} seconds")

        if self.stats['files_processed'] > 0:
            avg_time = elapsed / self.stats['files_processed']
            print(f"Average time/file:   {avg_time:.3f} seconds")
            print(f"Processing rate:     {self.stats['files_processed']/elapsed:.1f} files/sec")

        if self.stats['chunks_created'] > 0:
            avg_chunks = self.stats['chunks_created'] / max(1, self.stats['files_processed'])
            print(f"Average chunks/file: {avg_chunks:.1f}")

        # Database statistics
        if self.database:
            try:
                count = self.database.count()
                print(f"\nDatabase statistics:")
                print(f"Total documents:     {count:,}")
            except Exception as e:
                logger.debug(f"Could not get database count: {e}")

        print("="*60)


def create_argument_parser() -> argparse.ArgumentParser:
    """Create comprehensive argument parser with proper defaults"""
    parser = argparse.ArgumentParser(
        description='mbed - Advanced embedding generation CLI with comprehensive RAG features',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single file
  mbed file.py

  # Process directory recursively
  mbed --recursive --chunk-strategy semantic /path/to/project/

  # Use specific model and database path
  mbed --model llama3.2 --db-path ./my_embeddings /path/to/docs/

  # Process with preprocessing
  mbed --preprocess --chunk-overlap 100 data.json

Environment Variables:
  OLLAMA_HOST       Ollama server URL (default: http://localhost:11434)
  MBED_LOG_FILE     Log file path (default: mbed.log)
        """
    )

    # Positional arguments
    parser.add_argument(
        'inputs',
        nargs='+',
        help='Files, directories, or URLs to process'
    )

    # Model configuration
    model_group = parser.add_argument_group('Model Configuration')
    model_group.add_argument(
        '--model-type',
        choices=['ollama', 'bge-m3', 'sentence-transformers'],
        default='ollama',
        help='Embedding model type (default: ollama)'
    )
    model_group.add_argument(
        '--model',
        default='nomic-embed-text',
        help='Model name (default: nomic-embed-text)'
    )
    model_group.add_argument(
        '--ollama-host',
        default=os.environ.get('OLLAMA_HOST', 'http://localhost:11434'),
        help='Ollama server URL'
    )

    # Preprocessing options
    preprocess_group = parser.add_argument_group('Preprocessing Options')
    preprocess_group.add_argument(
        '--preprocess',
        action='store_true',
        help='Enable LLM preprocessing for structured data'
    )
    preprocess_group.add_argument(
        '--preprocessing-model',
        default='llama3.2:latest',
        help='Model for preprocessing'
    )
    preprocess_group.add_argument(
        '--no-cache',
        action='store_true',
        help='Disable preprocessing cache'
    )

    # Chunking options
    chunk_group = parser.add_argument_group('Chunking Configuration')
    chunk_group.add_argument(
        '--chunk-strategy',
        choices=['fixed', 'semantic', 'hierarchical', 'sentence', 'paragraph', 'topic'],
        default='fixed',
        help='Chunking strategy (default: fixed)'
    )
    chunk_group.add_argument(
        '--chunk-size',
        type=int,
        default=500,
        help='Target chunk size in tokens (default: 500)'
    )
    chunk_group.add_argument(
        '--chunk-overlap',
        type=int,
        default=50,
        help='Overlap between chunks in tokens (default: 50)'
    )
    chunk_group.add_argument(
        '--enhanced-chunking',
        action='store_true',
        help='Use enhanced chunking with entity headers'
    )

    # Database options
    db_group = parser.add_argument_group('Database Configuration')
    db_group.add_argument(
        '--db',
        choices=['chromadb', 'postgresql', 'faiss'],
        default='chromadb',
        help='Database backend (default: chromadb)'
    )
    db_group.add_argument(
        '--db-path',
        help='Database storage path'
    )
    db_group.add_argument(
        '--collection',
        default='documents',
        help='Collection/table name (default: documents)'
    )

    # Processing options
    process_group = parser.add_argument_group('Processing Options')
    process_group.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Batch size for database operations (default: 100)'
    )
    process_group.add_argument(
        '--workers',
        type=int,
        default=min(4, multiprocessing.cpu_count()),
        help='Number of parallel workers'
    )
    process_group.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='Processing timeout in seconds (default: 300)'
    )

    # File processing options
    file_group = parser.add_argument_group('File Processing')
    file_group.add_argument(
        '--recursive', '-r',
        action='store_true',
        help='Process directories recursively'
    )
    file_group.add_argument(
        '--exclude',
        action='append',
        default=[],
        help='Exclude patterns (can be used multiple times)'
    )
    file_group.add_argument(
        '--include-ext',
        action='append',
        default=[],
        help='Include only these extensions'
    )
    file_group.add_argument(
        '--max-file-size',
        type=int,
        default=10,
        help='Maximum file size in MB (default: 10)'
    )

    # Output options
    output_group = parser.add_argument_group('Output Options')
    output_group.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    output_group.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress non-error output'
    )
    output_group.add_argument(
        '--dry-run',
        action='store_true',
        help='Process files without saving to database'
    )
    output_group.add_argument(
        '--no-progress',
        action='store_true',
        help='Disable progress bar'
    )

    # System options
    system_group = parser.add_argument_group('System Options')
    system_group.add_argument(
        '--cache-dir',
        type=Path,
        default=Path.home() / '.cache' / 'mbed',
        help='Cache directory'
    )
    system_group.add_argument(
        '--no-deps',
        action='store_true',
        help='Skip dependency checking'
    )
    system_group.add_argument(
        '--resume',
        action='store_true',
        help='Resume from previous state'
    )
    system_group.add_argument(
        '--clear-state',
        action='store_true',
        help='Clear previous processing state'
    )

    return parser


def setup_signal_handlers(cli: MbedCLI):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(sig, frame):
        logger.info("\nReceived interrupt signal. Saving state...")
        if cli.state:
            cli.state.save_state()
        logger.info(f"State saved. Processed {cli.stats['files_processed']} files.")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


def main():
    """Enhanced main entry point with comprehensive error handling"""
    # Parse arguments
    parser = create_argument_parser()
    args = parser.parse_args()

    # Set logging level
    if args.quiet:
        logging.getLogger().setLevel(logging.ERROR)
    elif args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Check dependencies unless skipped
    if not args.no_deps:
        if not DependencyManager.check_required_dependencies():
            logger.error("Failed to install required dependencies")
            return 1

    try:
        # Create configuration from arguments
        config = MbedConfig()

        # Model configuration
        config.model_type = ModelType(args.model_type)
        config.model_name = args.model
        config.ollama_host = args.ollama_host

        # Preprocessing configuration
        config.enable_preprocessing = args.preprocess
        config.preprocessing_model = args.preprocessing_model
        config.preprocessing_cache = not args.no_cache

        # Chunking configuration
        strategy_map = {
            'fixed': ChunkingStrategy.FIXED_SIZE,
            'semantic': ChunkingStrategy.SEMANTIC,
            'hierarchical': ChunkingStrategy.HIERARCHICAL,
            'sentence': ChunkingStrategy.SENTENCE_BASED,
            'paragraph': ChunkingStrategy.PARAGRAPH_BASED,
            'topic': ChunkingStrategy.TOPIC_BASED
        }
        config.chunking_strategy = strategy_map.get(args.chunk_strategy, ChunkingStrategy.FIXED_SIZE)
        config.enable_enhanced_chunking = args.enhanced_chunking
        config.target_chunk_size = args.chunk_size
        config.chunk_overlap = args.chunk_overlap

        # Database configuration
        config.database_type = DatabaseType(args.db)
        config.database_path = args.db_path or ""
        config.collection_name = args.collection

        # Processing configuration
        config.batch_size = args.batch_size
        config.max_workers = args.workers
        config.timeout_seconds = args.timeout

        # File processing configuration
        config.recursive = args.recursive
        if args.exclude:
            config.exclude_patterns.extend(args.exclude)
        if args.include_ext:
            config.include_extensions = args.include_ext
        config.max_file_size_mb = args.max_file_size

        # Output configuration
        config.verbose = args.verbose
        config.quiet = args.quiet
        config.show_progress = not args.no_progress and not args.quiet
        config.dry_run = args.dry_run

        # System configuration
        config.cache_dir = args.cache_dir

        # Initialize CLI
        cli = MbedCLI(config)

        # Setup signal handlers
        setup_signal_handlers(cli)

        # Handle state management
        if args.clear_state and cli.state:
            cli.state.clear()
            logger.info("Cleared previous processing state")

        # Process inputs
        all_results = []
        for input_path in args.inputs:
            # Check if input is URL
            if input_path.startswith(('http://', 'https://')):
                result = cli.process_url(input_path)
                all_results.append(result)
            else:
                path = Path(input_path).resolve()
                if path.is_file():
                    result = cli.process_file(path)
                    all_results.append(result)
                elif path.is_dir():
                    result = cli.process_directory(path)
                    all_results.append(result)
                else:
                    logger.error(f"Invalid input: {input_path}")
                    return 1

        # Print statistics
        if not args.quiet:
            cli.print_statistics()

        # Return appropriate exit code
        return 1 if cli.stats['errors'] > 0 else 0

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
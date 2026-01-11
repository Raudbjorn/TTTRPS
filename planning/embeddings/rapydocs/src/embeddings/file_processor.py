"""
File processor with comprehensive MIME type detection, parsing, and embedding generation
"""

import os
import json
import mimetypes
import hashlib
import zipfile
import tarfile
import gzip
import bz2
import lzma
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
import subprocess
import tempfile
import shutil

# Database imports
import psycopg2
from psycopg2 import pool
from psycopg2.extras import Json, RealDictCursor
from contextlib import contextmanager
import atexit

# File detection libraries
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False

try:
    import filetype
    FILETYPE_AVAILABLE = True
except ImportError:
    FILETYPE_AVAILABLE = False

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False

# Document parsing libraries
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    import markdown
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import toml
    TOML_AVAILABLE = True
except ImportError:
    TOML_AVAILABLE = False

# Import our modules
try:
    # Try relative imports first (when installed as package)
    from .parsers import (
        BaseParser, ParseResult, ParsedFile, Language,
        PythonParser, JavaScriptParser, MarkdownParser,
        HTMLParser, JSONParser
    )
    
    # Optional: Ollama embeddings (requires chromadb)
    try:
        from .ollama_cuda_embeddings import OllamaEmbeddingFunction
        OLLAMA_AVAILABLE = True
    except ImportError:
        OLLAMA_AVAILABLE = False
        OllamaEmbeddingFunction = None
        
except ImportError:
    # Fallback to absolute imports for development
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from src.embeddings.parsers import (
        BaseParser, ParseResult, ParsedFile, Language,
        PythonParser, JavaScriptParser, MarkdownParser,
        HTMLParser, JSONParser
    )
    
    # Optional: Ollama embeddings (requires chromadb)
    try:
        from src.embeddings.ollama_cuda_embeddings import OllamaEmbeddingFunction
        OLLAMA_AVAILABLE = True
    except ImportError:
        OLLAMA_AVAILABLE = False
        OllamaEmbeddingFunction = None

from ..utils.logging_config import get_logger
logger = get_logger(__name__)


@dataclass
class FileInfo:
    """Comprehensive file information"""
    path: str
    name: str
    extension: str
    size: int
    mime_type: str
    encoding: Optional[str] = None
    hash: Optional[str] = None
    is_binary: bool = False
    is_archive: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class ProcessedFile:
    """Result of processing a file"""
    file_info: FileInfo
    content: Optional[str] = None
    parsed_data: Optional[Dict] = None
    embeddings: Optional[List[float]] = None
    chunks: Optional[List[Dict]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        result = {
            "file_info": self.file_info.to_dict(),
            "content": self.content[:1000] if self.content else None,  # Truncate for storage
            "parsed_data": self.parsed_data,
            "has_embeddings": self.embeddings is not None,
            "chunks_count": len(self.chunks) if self.chunks else 0,
            "error": self.error
        }
        return result


class FileProcessor:
    """Main file processor with MIME detection, parsing, and embedding generation"""
    
    def __init__(self, db_config: Dict[str, Any], use_largest_model: bool = True, pool_min_connections: int = 2, pool_max_connections: int = 10, ivfflat_lists: Optional[int] = None):
        self.db_config = db_config
        self.pool_min_connections = pool_min_connections
        self.pool_max_connections = pool_max_connections
        self.ivfflat_lists = ivfflat_lists  # Will be calculated dynamically if None
        
        # Initialize database connection pool
        self.connection_pool = None
        self._init_connection_pool()
        
        # Register cleanup on exit
        atexit.register(self._cleanup_connection_pool)
        
        # Initialize parsers
        self.parsers = {
            Language.PYTHON: PythonParser(),
            Language.JAVASCRIPT: JavaScriptParser(),
        }
        
        # Initialize markdown parser (not language-specific, so we handle it separately)
        self.markdown_parser = MarkdownParser()
        
        # Initialize HTML parser
        self.html_parser = HTMLParser()
        
        # Initialize JSON parser with semantic enhancement
        self.json_parser = JSONParser(enhance_for_embeddings=True)
        
        # Initialize embeddings with largest available model (if available)
        if OLLAMA_AVAILABLE:
            try:
                if use_largest_model:
                    # mxbai-embed-large has 1024 dimensions
                    self.embedding_function = OllamaEmbeddingFunction(model_name="mxbai-embed-large")
                    self.embedding_dim = 1024
                else:
                    self.embedding_function = OllamaEmbeddingFunction(model_name="nomic-embed-text")
                    self.embedding_dim = 768
            except ImportError as e:
                logger.warning(f"Ollama embeddings not available: {e}. Embeddings will be skipped.")
                self.embedding_function = None
                self.embedding_dim = 768  # Default dimension
        else:
            logger.warning("Ollama embeddings not available (chromadb not installed). Embeddings will be skipped.")
            self.embedding_function = None
            self.embedding_dim = 768  # Default dimension
        
        # Supported archive formats
        self.archive_extensions = {
            '.zip', '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2',
            '.tar.xz', '.txz', '.gz', '.bz2', '.xz', '.7z', '.rar'
        }
        
        # Text-based MIME types
        self.text_mime_types = {
            'text/', 'application/json', 'application/xml', 'application/javascript',
            'application/typescript', 'application/x-python', 'application/x-ruby',
            'application/x-php', 'application/x-sh', 'application/x-yaml',
            'application/toml', 'application/sql'
        }
        
        self._init_database()
    
    def _init_connection_pool(self):
        """Initialize database connection pool"""
        try:
            # Create a connection pool with configurable min and max connections
            self.connection_pool = psycopg2.pool.SimpleConnectionPool(
                self.pool_min_connections, self.pool_max_connections,
                host=self.db_config['host'],
                port=self.db_config['port'],
                database=self.db_config['database'],
                user=self.db_config['user'],
                password=self.db_config['password']
            )
            logger.info(f"Database connection pool initialized (min: {self.pool_min_connections}, max: {self.pool_max_connections})")
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            self.connection_pool = None
    
    def _cleanup_connection_pool(self):
        """Clean up connection pool on exit"""
        if self.connection_pool:
            self.connection_pool.closeall()
            logger.info("Database connection pool closed")
    
    @contextmanager
    def get_db_connection(self):
        """Get database connection from pool with context manager"""
        conn = None
        try:
            if self.connection_pool:
                conn = self.connection_pool.getconn()
            else:
                # Fallback to direct connection if pool is not available
                conn = psycopg2.connect(**self.db_config)
            yield conn
        finally:
            if conn:
                if self.connection_pool:
                    self.connection_pool.putconn(conn)
                else:
                    conn.close()
    
    def _init_database(self):
        """Initialize database tables"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                # Create main files table
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS processed_files (
                        id SERIAL PRIMARY KEY,
                        file_path TEXT UNIQUE NOT NULL,
                        file_name TEXT NOT NULL,
                        file_hash TEXT,
                        mime_type TEXT,
                        encoding TEXT,
                        size BIGINT,
                        is_binary BOOLEAN DEFAULT FALSE,
                        content TEXT,
                        parsed_data JSONB,
                        metadata JSONB,
                        processing_error TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create embeddings table with vector extension
                cur.execute("""
                    CREATE EXTENSION IF NOT EXISTS vector
                """)
                
                cur.execute(f"""
                    CREATE TABLE IF NOT EXISTS file_embeddings (
                        id SERIAL PRIMARY KEY,
                        file_id INTEGER REFERENCES processed_files(id) ON DELETE CASCADE,
                        chunk_index INTEGER NOT NULL,
                        chunk_text TEXT NOT NULL,
                        embedding vector({self.embedding_dim}),
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(file_id, chunk_index)
                    )
                """)
                
                # Create index for similarity search
                # The 'lists' parameter is calculated based on dataset size
                # Recommended: N/1000 for datasets up to 1M vectors, where N = number of vectors
                if self.ivfflat_lists is None:
                    # Dynamically calculate 'lists' based on existing data
                    cur.execute("SELECT COUNT(*) FROM file_embeddings")
                    n_vectors = cur.fetchone()[0]
                    # Use N/1000 rule with minimum of 1 and maximum of 1000
                    calculated_lists = max(1, min(1000, n_vectors // 1000)) if n_vectors > 0 else 100
                    logger.info(f"Calculated IVFFlat lists parameter: {calculated_lists} (based on {n_vectors} vectors)")
                else:
                    calculated_lists = self.ivfflat_lists
                    logger.info(f"Using configured IVFFlat lists parameter: {calculated_lists}")
                
                # Drop existing index if lists parameter needs to change
                cur.execute("""
                    SELECT indexdef FROM pg_indexes 
                    WHERE indexname = 'file_embeddings_embedding_idx'
                """)
                existing_index = cur.fetchone()
                
                if existing_index:
                    # Check if lists parameter differs
                    existing_def = existing_index[0]
                    existing_lists = None
                    if 'lists' in existing_def:
                        import re
                        match = re.search(r'lists\s*=\s*(\d+)', existing_def)
                        if match:
                            existing_lists = int(match.group(1))
                    
                    if existing_lists != calculated_lists:
                        logger.info(f"Recreating index with new lists parameter (was {existing_lists}, now {calculated_lists})")
                        cur.execute("DROP INDEX IF EXISTS file_embeddings_embedding_idx")
                
                # Create or recreate index with appropriate lists parameter
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS file_embeddings_embedding_idx 
                    ON file_embeddings USING ivfflat (embedding vector_cosine_ops)
                    WITH (lists = {calculated_lists})
                """)
                
                conn.commit()
    
    def detect_mime_type(self, file_path: Path) -> Tuple[str, Optional[str]]:
        """Detect MIME type and encoding using multiple methods"""
        mime_type = "application/octet-stream"
        encoding = None
        
        # Try python-magic
        if MAGIC_AVAILABLE:
            try:
                mime = magic.Magic(mime=True)
                mime_type = mime.from_file(str(file_path))
                
                # Get encoding
                enc_magic = magic.Magic(mime_encoding=True)
                encoding = enc_magic.from_file(str(file_path))
            except Exception as e:
                logger.debug(f"Magic detection failed: {e}")
        
        # Try filetype
        if FILETYPE_AVAILABLE and mime_type == "application/octet-stream":
            try:
                kind = filetype.guess(str(file_path))
                if kind:
                    mime_type = kind.mime
            except Exception as e:
                logger.debug(f"Filetype detection failed: {e}")
        
        # Fallback to mimetypes
        if mime_type == "application/octet-stream":
            guessed = mimetypes.guess_type(str(file_path))
            if guessed[0]:
                mime_type = guessed[0]
        
        # Detect encoding for text files
        if self._is_text_mime(mime_type) and not encoding and CHARDET_AVAILABLE:
            try:
                with open(file_path, 'rb') as f:
                    raw = f.read(10000)  # Read first 10KB
                    result = chardet.detect(raw)
                    if result['confidence'] > 0.7:
                        encoding = result['encoding']
            except Exception as e:
                logger.debug(f"Chardet detection failed: {e}")
        
        return mime_type, encoding or 'utf-8'
    
    def _is_text_mime(self, mime_type: str) -> bool:
        """Check if MIME type indicates text content"""
        return any(mime_type.startswith(t) for t in self.text_mime_types)
    
    def calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA256 hash of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def extract_archive(self, archive_path: Path, extract_dir: Path) -> List[Path]:
        """Extract archive and return list of extracted files"""
        extracted_files = []
        
        try:
            if archive_path.suffix == '.zip':
                with zipfile.ZipFile(archive_path, 'r') as zf:
                    zf.extractall(extract_dir)
                    extracted_files = [extract_dir / name for name in zf.namelist()]
            
            elif archive_path.suffix in ['.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz']:
                mode = 'r'
                if archive_path.suffix in ['.tar.gz', '.tgz']:
                    mode = 'r:gz'
                elif archive_path.suffix in ['.tar.bz2', '.tbz2']:
                    mode = 'r:bz2'
                elif archive_path.suffix in ['.tar.xz', '.txz']:
                    mode = 'r:xz'
                
                with tarfile.open(archive_path, mode) as tf:
                    tf.extractall(extract_dir)
                    extracted_files = [extract_dir / member.name for member in tf.getmembers()]
            
            elif archive_path.suffix == '.gz' and not '.tar' in archive_path.name:
                # Single file gzip
                output_path = extract_dir / archive_path.stem
                with gzip.open(archive_path, 'rb') as gz_file:
                    with open(output_path, 'wb') as out_file:
                        out_file.write(gz_file.read())
                extracted_files = [output_path]
            
            elif archive_path.suffix == '.bz2':
                # Single file bzip2
                output_path = extract_dir / archive_path.stem
                with bz2.open(archive_path, 'rb') as bz2_file:
                    with open(output_path, 'wb') as out_file:
                        out_file.write(bz2_file.read())
                extracted_files = [output_path]
            
            elif archive_path.suffix == '.xz':
                # Single file xz
                output_path = extract_dir / archive_path.stem
                with lzma.open(archive_path, 'rb') as xz_file:
                    with open(output_path, 'wb') as out_file:
                        out_file.write(xz_file.read())
                extracted_files = [output_path]
            
            else:
                # Try 7z or rar with external tools
                if shutil.which('7z'):
                    subprocess.run(['7z', 'x', str(archive_path), f'-o{extract_dir}'], 
                                 check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    extracted_files = list(extract_dir.rglob('*'))
                else:
                    logger.warning(f"Unsupported archive format: {archive_path.suffix}")
        
        except Exception as e:
            logger.error(f"Failed to extract {archive_path}: {e}")
        
        return [f for f in extracted_files if f.is_file()]
    
    def parse_content(self, file_path: Path, mime_type: str, encoding: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Parse file content based on MIME type"""
        content = None
        parsed_data = None
        
        try:
            # Handle code files
            if mime_type in ['text/x-python', 'application/x-python'] or file_path.suffix == '.py':
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                parser = self.parsers[Language.PYTHON]
                result = parser.parse(content, str(file_path))
                if result.success:
                    parsed_data = result.data.to_dict() if hasattr(result.data, 'to_dict') else result.data
            
            elif mime_type in ['application/javascript', 'text/javascript'] or file_path.suffix in ['.js', '.jsx', '.ts', '.tsx']:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                parser = self.parsers[Language.JAVASCRIPT]
                result = parser.parse(content, str(file_path))
                if result.success:
                    parsed_data = result.data.to_dict() if hasattr(result.data, 'to_dict') else result.data
            
            # Handle PDF files
            elif mime_type == 'application/pdf' and PYPDF2_AVAILABLE:
                content = self.extract_pdf_text(file_path)
                parsed_data = {"type": "pdf", "pages": len(content.split('\n\n')) if content else 0}
            
            # Handle Word documents
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'] and DOCX_AVAILABLE:
                content = self.extract_docx_text(file_path)
                parsed_data = {"type": "docx"}
            
            # Handle HTML with advanced parser
            elif (mime_type in ['text/html', 'application/xhtml+xml'] or 
                  file_path.suffix in ['.html', '.htm', '.xhtml'] or
                  (content and self.html_parser.can_parse(str(file_path), content))):
                if not content:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                
                result = self.html_parser.parse(content, str(file_path))
                if result.success and result.data:
                    parsed_data = result.data.to_dict()
                    parsed_data["parser_type"] = "advanced_html"
                else:
                    parsed_data = {"type": "html", "parser_error": result.error if result else "HTML parsing failed"}
            
            # Handle Markdown with advanced parser
            elif file_path.suffix in ['.md', '.markdown'] or (content and self.markdown_parser.can_parse(str(file_path), content)):
                if not content:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                
                result = self.markdown_parser.parse(content, str(file_path))
                if result.success and result.data:
                    parsed_data = result.data.to_dict()
                    parsed_data["parser_type"] = "advanced_markdown"
                else:
                    # Fallback to basic markdown processing
                    if MARKDOWN_AVAILABLE:
                        parsed_data = {"type": "markdown", "html": markdown.markdown(content)}
                    else:
                        parsed_data = {"type": "markdown", "parser_error": result.error if result else "No markdown processor available"}
            
            # Handle JSON with advanced parser
            elif (mime_type == 'application/json' or 
                  file_path.suffix in ['.json', '.jsonl', '.ndjson', '.geojson'] or
                  (content and self.json_parser.can_parse(str(file_path), content))):
                if not content:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                
                result = self.json_parser.parse(content, str(file_path))
                if result.success and result.data:
                    parsed_data = result.data.to_dict()
                    parsed_data["parser_type"] = "advanced_json"
                    # Add the raw JSON data for reference
                    try:
                        parsed_data["raw_data"] = json.loads(content) if file_path.suffix != '.jsonl' else None
                    except json.JSONDecodeError:
                        parsed_data["raw_data"] = None
                else:
                    # Fallback to basic JSON parsing
                    try:
                        raw_json = json.loads(content)
                        parsed_data = {"type": "json", "data": raw_json}
                    except json.JSONDecodeError as e:
                        parsed_data = {"type": "json", "parser_error": str(e)}
            
            # Handle YAML
            elif file_path.suffix in ['.yaml', '.yml'] and YAML_AVAILABLE:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    parsed_data = yaml.safe_load(content)
            
            # Handle TOML
            elif file_path.suffix == '.toml' and TOML_AVAILABLE:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                    parsed_data = toml.loads(content)
            
            # Handle plain text
            elif self._is_text_mime(mime_type):
                with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                    content = f.read()
                parsed_data = {"type": "text"}
            
            # Fallback heuristic for unknown files
            else:
                content, parsed_data = self.apply_fallback_heuristic(file_path, mime_type, encoding)
        
        except Exception as e:
            logger.error(f"Failed to parse {file_path}: {e}")
            # Try fallback
            content, parsed_data = self.apply_fallback_heuristic(file_path, mime_type, encoding)
        
        return content, parsed_data
    
    def extract_pdf_text(self, file_path: Path) -> Optional[str]:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = []
                for page in reader.pages:
                    text.append(page.extract_text())
                return '\n\n'.join(text)
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return None
    
    def extract_docx_text(self, file_path: Path) -> Optional[str]:
        """Extract text from Word document"""
        try:
            doc = docx.Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return '\n'.join(text)
        except Exception as e:
            logger.error(f"Failed to extract DOCX text: {e}")
            return None
    
    def apply_fallback_heuristic(self, file_path: Path, mime_type: str, encoding: str) -> Tuple[Optional[str], Optional[Dict]]:
        """Apply fallback heuristic for unknown file types"""
        content = None
        parsed_data = {"type": "unknown", "mime_type": mime_type, "fallback": True}
        
        try:
            # Try to read as text
            with open(file_path, 'rb') as f:
                raw_content = f.read(1024 * 100)  # Read first 100KB
            
            # Check if it looks like text
            text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
            is_text = all(c in text_chars for c in raw_content[:512])
            
            if is_text:
                try:
                    content = raw_content.decode(encoding, errors='replace')
                    
                    # Try to identify structure
                    lines = content.split('\n')
                    parsed_data["lines"] = len(lines)
                    
                    # Check for common patterns
                    if any('function' in line or 'def ' in line or 'class ' in line for line in lines[:50]):
                        parsed_data["probable_code"] = True
                    
                    if any('<' in line and '>' in line for line in lines[:20]):
                        parsed_data["probable_markup"] = True
                    
                    # Look for configuration patterns
                    if any('=' in line or ':' in line for line in lines[:20]):
                        parsed_data["probable_config"] = True
                
                except Exception as e:
                    logger.debug(f"Failed to decode as text: {e}")
            else:
                # Binary file - store metadata only
                parsed_data["binary"] = True
                parsed_data["size"] = len(raw_content)
                
                # Try to identify by magic bytes
                magic_bytes = raw_content[:8]
                if magic_bytes.startswith(b'%PDF'):
                    parsed_data["probable_type"] = "pdf"
                elif magic_bytes.startswith(b'\x89PNG'):
                    parsed_data["probable_type"] = "png"
                elif magic_bytes.startswith(b'\xff\xd8\xff'):
                    parsed_data["probable_type"] = "jpeg"
                elif magic_bytes.startswith(b'GIF8'):
                    parsed_data["probable_type"] = "gif"
                elif magic_bytes.startswith(b'PK\x03\x04'):
                    parsed_data["probable_type"] = "zip_or_office"
        
        except Exception as e:
            logger.error(f"Fallback heuristic failed: {e}")
            parsed_data["error"] = str(e)
        
        # Store fallback analysis
        self._update_fallback_log(file_path, mime_type, parsed_data)
        
        return content, parsed_data
    
    def _update_fallback_log(self, file_path: Path, mime_type: str, analysis: Dict):
        """Update fallback heuristic log for improvement"""
        # Use a proper log directory - either configured or in temp directory
        log_dir = Path(os.getenv("RAPYDOCS_LOG_DIR", tempfile.gettempdir()))
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / "rapydocs_fallback_heuristic_log.jsonl"
        
        try:
            with open(log_file, 'a') as f:
                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "file": str(file_path),
                    "extension": file_path.suffix,
                    "mime_type": mime_type,
                    "analysis": analysis
                }
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            logger.debug(f"Failed to update fallback log at {log_file}: {e}")
    
    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
        """Split text into overlapping chunks for embedding"""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap
        
        return chunks
    
    def process_file(self, file_path: Path) -> ProcessedFile:
        """Process a single file"""
        logger.info(f"Processing: {file_path}")
        
        # Get file info
        mime_type, encoding = self.detect_mime_type(file_path)
        file_hash = self.calculate_file_hash(file_path)
        
        file_info = FileInfo(
            path=str(file_path),
            name=file_path.name,
            extension=file_path.suffix,
            size=file_path.stat().st_size,
            mime_type=mime_type,
            encoding=encoding,
            hash=file_hash,
            is_binary=not self._is_text_mime(mime_type),
            is_archive=file_path.suffix.lower() in self.archive_extensions
        )
        
        # Parse content
        content, parsed_data = self.parse_content(file_path, mime_type, encoding)
        
        # Generate embeddings if we have content
        embeddings = None
        chunks = []
        if content and self.embedding_function:
            text_chunks = self.chunk_text(content)
            if text_chunks:
                try:
                    chunk_embeddings = self.embedding_function(text_chunks)
                    chunks = [
                        {
                            "text": chunk,
                            "embedding": emb,
                            "index": i
                        }
                        for i, (chunk, emb) in enumerate(zip(text_chunks, chunk_embeddings))
                    ]
                    # Use first chunk embedding as file embedding
                    embeddings = chunk_embeddings[0] if chunk_embeddings else None
                except Exception as e:
                    logger.error(f"Failed to generate embeddings: {e}")
        
        return ProcessedFile(
            file_info=file_info,
            content=content,
            parsed_data=parsed_data,
            embeddings=embeddings,
            chunks=chunks
        )
    
    def save_to_database(self, processed_file: ProcessedFile):
        """Save processed file to PostgreSQL"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                # Insert or update file record
                cur.execute("""
                    INSERT INTO processed_files (
                        file_path, file_name, file_hash, mime_type, encoding,
                        size, is_binary, content, parsed_data, metadata, processing_error
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (file_path) DO UPDATE SET
                        file_hash = EXCLUDED.file_hash,
                        mime_type = EXCLUDED.mime_type,
                        encoding = EXCLUDED.encoding,
                        size = EXCLUDED.size,
                        content = EXCLUDED.content,
                        parsed_data = EXCLUDED.parsed_data,
                        metadata = EXCLUDED.metadata,
                        processing_error = EXCLUDED.processing_error,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """, (
                    processed_file.file_info.path,
                    processed_file.file_info.name,
                    processed_file.file_info.hash,
                    processed_file.file_info.mime_type,
                    processed_file.file_info.encoding,
                    processed_file.file_info.size,
                    processed_file.file_info.is_binary,
                    processed_file.content,
                    Json(processed_file.parsed_data) if processed_file.parsed_data else None,
                    Json(processed_file.file_info.metadata),
                    processed_file.error
                ))
                
                file_id = cur.fetchone()[0]
                
                # Insert embeddings
                if processed_file.chunks:
                    for chunk in processed_file.chunks:
                        cur.execute("""
                            INSERT INTO file_embeddings (
                                file_id, chunk_index, chunk_text, embedding, metadata
                            ) VALUES (%s, %s, %s, %s, %s)
                            ON CONFLICT (file_id, chunk_index) DO UPDATE SET
                                chunk_text = EXCLUDED.chunk_text,
                                embedding = EXCLUDED.embedding,
                                metadata = EXCLUDED.metadata
                        """, (
                            file_id,
                            chunk['index'],
                            chunk['text'][:5000],  # Limit text size
                            chunk['embedding'].tolist() if hasattr(chunk['embedding'], 'tolist') else chunk['embedding'],
                            Json({"length": len(chunk['text'])})
                        ))
                
                conn.commit()
                logger.info(f"Saved {processed_file.file_info.name} to database (ID: {file_id})")
    
    def process_directory(self, directory: Path, recursive: bool = True):
        """Process all files in a directory"""
        pattern = '**/*' if recursive else '*'
        
        for file_path in directory.glob(pattern):
            if file_path.is_file():
                try:
                    # Check if it's an archive
                    if file_path.suffix.lower() in self.archive_extensions:
                        logger.info(f"Extracting archive: {file_path}")
                        with tempfile.TemporaryDirectory() as temp_dir:
                            extracted_files = self.extract_archive(file_path, Path(temp_dir))
                            for extracted_file in extracted_files:
                                try:
                                    processed = self.process_file(extracted_file)
                                    self.save_to_database(processed)
                                except Exception as e:
                                    logger.error(f"Failed to process extracted file {extracted_file}: {e}")
                    else:
                        processed = self.process_file(file_path)
                        self.save_to_database(processed)
                
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")


def main():
    """Main entry point for processing files"""
    # Database configuration
    db_config = {
        "host": os.getenv("POSTGRES_HOST", "127.0.0.1"),  # Use IPv4 instead of localhost
        "port": int(os.getenv("POSTGRES_PORT", "5432")),  # Configurable port with default
        "database": os.getenv("POSTGRES_DB", "postgres"),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres")
    }
    
    # Initialize processor with largest model
    processor = FileProcessor(db_config, use_largest_model=True)
    
    # Process the more_data directory
    more_data_dir = Path("more_data")
    if more_data_dir.exists():
        logger.info(f"Processing files in {more_data_dir}")
        processor.process_directory(more_data_dir, recursive=True)
    else:
        logger.error(f"Directory {more_data_dir} not found")
    
    logger.info("Processing complete!")


if __name__ == "__main__":
    main()
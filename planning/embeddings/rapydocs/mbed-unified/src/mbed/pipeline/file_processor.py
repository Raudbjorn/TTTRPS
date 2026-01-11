"""
File processing pipeline coordinating format detection, chunking, and embedding generation
"""

import os
import mimetypes
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from ..core.result import Result
from ..core.orchestrator import EmbeddingOrchestrator, ProcessedFile
from .chunker import ChunkConfig, ChunkerFactory
from ..config import MBEDSettings

logger = logging.getLogger(__name__)


@dataclass
class FileInfo:
    """File information and metadata."""
    path: Path
    name: str
    size: int
    mime_type: Optional[str]
    encoding: str = 'utf-8'
    file_type: str = 'unknown'
    language: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProcessingOptions:
    """Options for file processing."""
    chunk_strategy: str = 'fixed'
    chunk_size: int = 500
    chunk_overlap: int = 50
    preserve_structure: bool = True
    extract_metadata: bool = True
    generate_embeddings: bool = True
    store_results: bool = True
    skip_binary: bool = True
    max_file_size: int = 10 * 1024 * 1024  # 10MB default
    supported_formats: Optional[List[str]] = None


class FileProcessor:
    """Comprehensive file processing pipeline."""

    def __init__(self, orchestrator: EmbeddingOrchestrator, options: ProcessingOptions):
        self.orchestrator = orchestrator
        self.options = options
        self.supported_text_formats = {
            'text/plain': 'text',
            'text/markdown': 'markdown',
            'text/x-python': 'python',
            'text/javascript': 'javascript',
            'application/javascript': 'javascript',
            'text/x-typescript': 'typescript',
            'application/json': 'json',
            'application/xml': 'xml',
            'text/xml': 'xml',
            'text/html': 'html',
            'text/css': 'css',
            'text/x-java-source': 'java',
            'text/x-c': 'c',
            'text/x-c++': 'cpp',
            'text/x-csharp': 'csharp',
            'application/x-yaml': 'yaml',
            'text/x-yaml': 'yaml',
            'application/toml': 'toml',
            'text/x-rst': 'rst'
        }

    def process_file(self, file_path: Union[str, Path]) -> Result[ProcessedFile, str]:
        """Process a single file through the complete pipeline."""
        try:
            # Convert to Path object
            path = Path(file_path)

            # Gather file information
            file_info_result = self._get_file_info(path)
            if file_info_result.is_err():
                return file_info_result

            file_info = file_info_result.unwrap()

            # Check if file should be processed
            should_process_result = self._should_process_file(file_info)
            if should_process_result.is_err():
                return should_process_result

            # Read file content
            content_result = self._read_file_content(file_info)
            if content_result.is_err():
                return content_result

            content = content_result.unwrap()

            # Process content through pipeline
            return self._process_content(file_info, content)

        except Exception as e:
            return Result.Err(f"File processing failed for {file_path}: {str(e)}")

    def process_files(self, file_paths: List[Union[str, Path]]) -> Result[List[ProcessedFile], str]:
        """Process multiple files."""
        processed_files = []
        errors = []

        for file_path in file_paths:
            result = self.process_file(file_path)
            if result.is_ok():
                processed_files.append(result.unwrap())
            else:
                errors.append(f"{file_path}: {result.unwrap_err()}")
                logger.error(f"Failed to process {file_path}: {result.unwrap_err()}")

        if errors and not processed_files:
            # All files failed
            return Result.Err(f"All files failed to process: {'; '.join(errors[:5])}")
        elif errors:
            # Some files failed, log warnings but continue
            logger.warning(f"{len(errors)} files failed to process")

        return Result.Ok(processed_files)

    def process_directory(
        self, directory: Union[str, Path], recursive: bool = True, pattern: str = "*"
    ) -> Result[List[ProcessedFile], str]:
        """Process all files in a directory."""
        try:
            dir_path = Path(directory)

            if not dir_path.exists():
                return Result.Err(f"Directory does not exist: {directory}")

            if not dir_path.is_dir():
                return Result.Err(f"Path is not a directory: {directory}")

            # Collect files to process
            if recursive:
                file_paths = list(dir_path.rglob(pattern))
            else:
                file_paths = list(dir_path.glob(pattern))

            # Filter to only files (not directories)
            file_paths = [p for p in file_paths if p.is_file()]

            if not file_paths:
                return Result.Ok([])

            logger.info(f"Processing {len(file_paths)} files from {directory}")

            # Process files
            return self.process_files(file_paths)

        except Exception as e:
            return Result.Err(f"Directory processing failed: {str(e)}")

    def _get_file_info(self, path: Path) -> Result[FileInfo, str]:
        """Gather comprehensive file information."""
        try:
            if not path.exists():
                return Result.Err(f"File does not exist: {path}")

            if not path.is_file():
                return Result.Err(f"Path is not a file: {path}")

            stat = path.stat()
            size = stat.st_size

            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(path))

            # Determine file type and language
            file_type = self._determine_file_type(path, mime_type)
            language = self._determine_language(path, mime_type, file_type)

            # Gather additional metadata
            metadata = {
                'modified_time': stat.st_mtime,
                'created_time': stat.st_ctime,
                'extension': path.suffix.lower(),
                'parent_directory': path.parent.name
            }

            file_info = FileInfo(
                path=path,
                name=path.name,
                size=size,
                mime_type=mime_type,
                file_type=file_type,
                language=language,
                metadata=metadata
            )

            return Result.Ok(file_info)

        except Exception as e:
            return Result.Err(f"Failed to get file info: {str(e)}")

    def _determine_file_type(self, path: Path, mime_type: Optional[str]) -> str:
        """Determine the file type from path and MIME type."""
        if mime_type and mime_type in self.supported_text_formats:
            return self.supported_text_formats[mime_type]

        # Check by extension
        extension = path.suffix.lower()
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.cxx': 'cpp',
            '.cc': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.json': 'json',
            '.xml': 'xml',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.md': 'markdown',
            '.markdown': 'markdown',
            '.rst': 'rst',
            '.txt': 'text',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'ini',
            '.conf': 'text',
            '.log': 'text'
        }

        return extension_map.get(extension, 'text')

    def _determine_language(self, path: Path, mime_type: Optional[str], file_type: str) -> Optional[str]:
        """Determine the programming language if applicable."""
        if file_type in ['python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'csharp']:
            return file_type

        # Additional language detection based on file patterns
        if path.name.lower() in ['dockerfile', 'makefile']:
            return path.name.lower()

        if path.suffix.lower() in ['.sh', '.bash']:
            return 'shell'

        if path.suffix.lower() in ['.sql']:
            return 'sql'

        return None

    def _should_process_file(self, file_info: FileInfo) -> Result[None, str]:
        """Determine if file should be processed based on options."""
        # Check file size
        if file_info.size > self.options.max_file_size:
            return Result.Err(f"File too large: {file_info.size} bytes (max: {self.options.max_file_size})")

        # Check if binary file should be skipped
        if self.options.skip_binary and self._is_binary_file(file_info):
            return Result.Err("Binary file skipped")

        # Check supported formats
        if self.options.supported_formats:
            if file_info.file_type not in self.options.supported_formats:
                return Result.Err(f"Unsupported format: {file_info.file_type}")

        return Result.Ok(None)

    def _is_binary_file(self, file_info: FileInfo) -> bool:
        """Check if file is likely binary."""
        # Check MIME type
        if file_info.mime_type:
            if file_info.mime_type.startswith(('image/', 'audio/', 'video/', 'application/')):
                # But allow some text-based application types
                text_application_types = [
                    'application/json',
                    'application/xml',
                    'application/javascript',
                    'application/x-yaml'
                ]
                if file_info.mime_type not in text_application_types:
                    return True

        # Check by extension
        binary_extensions = {
            '.exe', '.dll', '.so', '.dylib',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico',
            '.mp3', '.wav', '.ogg', '.flac',
            '.mp4', '.avi', '.mkv', '.mov',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.bz2', '.7z',
            '.bin', '.dat', '.db', '.sqlite'
        }

        return file_info.path.suffix.lower() in binary_extensions

    def _read_file_content(self, file_info: FileInfo) -> Result[str, str]:
        """Read file content with appropriate encoding."""
        try:
            # Try to read with UTF-8 first
            try:
                content = file_info.path.read_text(encoding='utf-8')
                file_info.encoding = 'utf-8'
                return Result.Ok(content)
            except UnicodeDecodeError:
                # Try other common encodings
                encodings = ['latin-1', 'cp1252', 'iso-8859-1']
                for encoding in encodings:
                    try:
                        content = file_info.path.read_text(encoding=encoding)
                        file_info.encoding = encoding
                        logger.warning(f"File {file_info.path} read with {encoding} encoding")
                        return Result.Ok(content)
                    except UnicodeDecodeError:
                        continue

                return Result.Err("Could not decode file with any supported encoding")

        except Exception as e:
            return Result.Err(f"Failed to read file content: {str(e)}")

    def _process_content(self, file_info: FileInfo, content: str) -> Result[ProcessedFile, str]:
        """Process file content through the complete pipeline."""
        try:
            # Create chunk configuration
            chunk_config = ChunkConfig(
                size=self.options.chunk_size,
                overlap=self.options.chunk_overlap
            )

            # Get appropriate chunker
            chunker_result = self._get_chunker(file_info, chunk_config)
            if chunker_result.is_err():
                return chunker_result

            chunker = chunker_result.unwrap()

            # Chunk the content
            chunks_result = chunker.chunk(content, chunk_config)
            if chunks_result.is_err():
                return Result.Err(f"Chunking failed: {chunks_result.unwrap_err()}")

            chunks = chunks_result.unwrap()

            # Generate embeddings if requested
            embeddings = []
            if self.options.generate_embeddings and chunks and self.orchestrator.backend:
                embedding_texts = [chunk.text for chunk in chunks]

                # Use orchestrator backend to generate embeddings
                embedding_result = self.orchestrator.backend.generate_embeddings(embedding_texts)
                if embedding_result.is_ok():
                    embeddings = embedding_result.unwrap()
                else:
                    logger.warning(f"Embedding generation failed: {embedding_result.unwrap_err()}")
            elif self.options.generate_embeddings and not self.orchestrator.backend:
                logger.warning("Backend not available for embedding generation")

            # Create processed file result
            processed_file = ProcessedFile(
                path=file_info.path,
                file_type=file_info.file_type,
                chunks=chunks,
                metadata={
                    'name': file_info.name,
                    'size': file_info.size,
                    'mime_type': file_info.mime_type,
                    'language': file_info.language,
                    'encoding': file_info.encoding,
                    'chunk_strategy': self.options.chunk_strategy,
                    'chunk_count': len(chunks),
                    'embedding_count': len(embeddings),
                    **file_info.metadata
                },
                embeddings=embeddings,
                processing_time=time.time() - start_time
            )

            return Result.Ok(processed_file)

        except Exception as e:
            return Result.Err(f"Content processing failed: {str(e)}")

    def _get_chunker(self, file_info: FileInfo, config: ChunkConfig) -> Result[Any, str]:
        """Get appropriate chunker based on file type and options."""
        strategy = self.options.chunk_strategy

        # Auto-select strategy based on file type if using 'auto'
        if strategy == 'auto':
            strategy = self._auto_select_strategy(file_info)

        # Get chunker from factory
        try:
            chunker = ChunkerFactory.create(strategy, config)
            return Result.Ok(chunker)
        except KeyError:
            return Result.Err(f"Unknown chunking strategy: {strategy}")
        except Exception as e:
            return Result.Err(f"Failed to create chunker: {str(e)}")

    def _auto_select_strategy(self, file_info: FileInfo) -> str:
        """Automatically select chunking strategy based on file characteristics."""
        file_type = file_info.file_type
        language = file_info.language
        size = file_info.size

        # Code files - use code-aware chunking
        if language in ['python', 'javascript', 'typescript', 'java', 'c', 'cpp', 'csharp']:
            return 'code'

        # Structured documents - use hierarchical or semantic
        if file_type in ['markdown', 'rst', 'html']:
            if size > 5000:  # Large documents benefit from hierarchical
                return 'hierarchical'
            else:
                return 'semantic'

        # JSON/XML - use semantic for better structure understanding
        if file_type in ['json', 'xml', 'yaml']:
            return 'semantic'

        # Large text files - use paragraph chunking
        if file_type == 'text' and size > 10000:
            return 'paragraph'

        # Small files or unknown types - use sentence chunking
        if size < 2000:
            return 'sentence'

        # Default to fixed-size for everything else
        return 'fixed'

    def get_supported_formats(self) -> List[str]:
        """Get list of supported file formats."""
        return list(self.supported_text_formats.values())

    def get_file_stats(self, file_paths: List[Union[str, Path]]) -> Dict[str, Any]:
        """Get statistics about files to be processed."""
        stats = {
            'total_files': len(file_paths),
            'total_size': 0,
            'file_types': {},
            'languages': {},
            'binary_files': 0,
            'processable_files': 0,
            'too_large_files': 0
        }

        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists() or not path.is_file():
                continue

            file_info_result = self._get_file_info(path)
            if file_info_result.is_err():
                continue

            file_info = file_info_result.unwrap()

            stats['total_size'] += file_info.size

            # Count file types
            file_type = file_info.file_type
            stats['file_types'][file_type] = stats['file_types'].get(file_type, 0) + 1

            # Count languages
            if file_info.language:
                language = file_info.language
                stats['languages'][language] = stats['languages'].get(language, 0) + 1

            # Check if processable
            if self._is_binary_file(file_info):
                stats['binary_files'] += 1
            elif file_info.size > self.options.max_file_size:
                stats['too_large_files'] += 1
            else:
                stats['processable_files'] += 1

        return stats
"""
code_parser.py - Main entry point with intelligent file detection and parser routing

Dependencies:
    pip install python-magic filetype chardet tiktoken
    
Optional but recommended:
    pip install apache-tika  # For comprehensive file analysis
"""

import json
import logging
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, Union, Type
from dataclasses import dataclass

# File detection libraries
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
    logging.warning("python-magic not available - install with: pip install python-magic")

try:
    import filetype
    FILETYPE_AVAILABLE = True
except ImportError:
    FILETYPE_AVAILABLE = False
    logging.warning("filetype not available - install with: pip install filetype")

try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
    logging.warning("chardet not available - install with: pip install chardet")

try:
    from tika import parser as tika_parser
    from tika import config as tika_config
    # Suppress Tika's verbose logging
    tika_config.log_config['handlers']['console']['level'] = 'ERROR'
    TIKA_AVAILABLE = True
except ImportError:
    TIKA_AVAILABLE = False
    logging.info("Apache Tika not available - install with: pip install apache-tika")

from base_parser import BaseParser, ParseResult, ParsedFile, Language
from python_parser import PythonParser
from javascript_parser import JavaScriptParser


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FileAnalysis:
    """Comprehensive file analysis results"""
    path: Path
    extension: str
    size: int
    
    # MIME types from different sources
    mime_magic: Optional[str] = None
    mime_filetype: Optional[str] = None
    mime_mimetypes: Optional[str] = None
    mime_tika: Optional[str] = None
    
    # File properties
    encoding: Optional[str] = None
    confidence: float = 0.0
    shebang: Optional[str] = None
    binary: bool = False
    
    # Content analysis
    content_sample: Optional[str] = None
    tika_metadata: Optional[Dict] = None
    language_hints: List[str] = None
    
    def __post_init__(self):
        if self.language_hints is None:
            self.language_hints = []
    
    def get_best_mime_type(self) -> Optional[str]:
        """Get the most likely MIME type from all sources"""
        # Priority order: Tika > Magic > Filetype > mimetypes
        for mime in [self.mime_tika, self.mime_magic, self.mime_filetype, self.mime_mimetypes]:
            if mime and mime != 'application/octet-stream':
                return mime
        return None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for debugging"""
        return {
            "path": str(self.path),
            "extension": self.extension,
            "size": self.size,
            "encoding": self.encoding,
            "best_mime": self.get_best_mime_type(),
            "mime_types": {
                "magic": self.mime_magic,
                "filetype": self.mime_filetype,
                "mimetypes": self.mime_mimetypes,
                "tika": self.mime_tika
            },
            "binary": self.binary,
            "has_shebang": bool(self.shebang),
            "language_hints": self.language_hints,
            "confidence": self.confidence
        }


class FileDetector:
    """Comprehensive file type detection using multiple libraries"""
    
    def __init__(self, use_tika: bool = True):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.use_tika = use_tika and TIKA_AVAILABLE
        
        # Initialize magic if available
        if MAGIC_AVAILABLE:
            try:
                self.magic_mime = magic.Magic(mime=True)
                self.magic_file = magic.Magic()
            except Exception as e:
                self.logger.warning(f"Failed to initialize python-magic: {e}")
                self.magic_mime = None
                self.magic_file = None
        else:
            self.magic_mime = None
            self.magic_file = None
        
        # Language detection patterns
        self.language_patterns = {
            Language.PYTHON: {
                'extensions': {'.py', '.pyw', '.pyi', '.pyc', '.pyo'},
                'mimes': {'text/x-python', 'application/x-python', 'text/x-script.python'},
                'patterns': ['def ', 'class ', 'import ', 'from ', '__init__', 'self.', 'print('],
                'shebang': ['python', 'python3', 'python2']
            },
            Language.JAVASCRIPT: {
                'extensions': {'.js', '.jsx', '.mjs', '.cjs'},
                'mimes': {'application/javascript', 'text/javascript', 'application/x-javascript'},
                'patterns': ['function ', 'const ', 'let ', 'var ', '=>', 'console.', 'require('],
                'shebang': ['node', 'nodejs']
            },
            Language.TYPESCRIPT: {
                'extensions': {'.ts', '.tsx', '.d.ts'},
                'mimes': {'application/typescript', 'text/typescript'},
                'patterns': ['interface ', 'type ', 'enum ', ': string', ': number', '<T>'],
                'shebang': ['ts-node', 'deno']
            },
            Language.RUST: {
                'extensions': {'.rs'},
                'mimes': {'text/x-rust', 'text/rust'},
                'patterns': ['fn ', 'impl ', 'struct ', 'enum ', 'trait ', 'use ', 'pub ', 'mod '],
                'shebang': ['rustc', 'rust-script']
            },
            Language.GO: {
                'extensions': {'.go'},
                'mimes': {'text/x-go', 'application/x-go'},
                'patterns': ['package ', 'func ', 'import ', 'var ', 'const ', 'type ', 'interface{'],
                'shebang': ['go run']
            }
        }
    
    def analyze_file(self, filepath: str) -> ParseResult:
        """Perform comprehensive file analysis"""
        try:
            path = Path(filepath)
            
            if not path.exists():
                return ParseResult(False, error=f"File not found: {filepath}")
            
            if not path.is_file():
                return ParseResult(False, error=f"Not a file: {filepath}")
            
            analysis = FileAnalysis(
                path=path,
                extension=path.suffix.lower(),
                size=path.stat().st_size
            )
            
            # Detect MIME types using multiple methods
            self._detect_mime_types(path, analysis)
            
            # Detect encoding and read sample
            self._detect_encoding_and_content(path, analysis)
            
            # Use Apache Tika if available for comprehensive analysis
            if self.use_tika:
                self._analyze_with_tika(path, analysis)
            
            # Analyze content for language hints
            if analysis.content_sample:
                self._detect_language_hints(analysis)
            
            # Calculate confidence score
            self._calculate_confidence(analysis)
            
            return ParseResult(True, data=analysis)
            
        except Exception as e:
            error_msg = f"Error analyzing file {filepath}: {str(e)}"
            self.logger.error(error_msg)
            return ParseResult(False, error=error_msg)
    
    def _detect_mime_types(self, path: Path, analysis: FileAnalysis):
        """Detect MIME types using various libraries"""
        
        # python-magic
        if self.magic_mime:
            try:
                analysis.mime_magic = self.magic_mime.from_file(str(path))
            except Exception as e:
                self.logger.debug(f"Magic MIME detection failed: {e}")
        
        # filetype library
        if FILETYPE_AVAILABLE:
            try:
                kind = filetype.guess(str(path))
                if kind:
                    analysis.mime_filetype = kind.mime
            except Exception as e:
                self.logger.debug(f"Filetype detection failed: {e}")
        
        # mimetypes standard library
        try:
            mime, _ = mimetypes.guess_type(str(path))
            if mime:
                analysis.mime_mimetypes = mime
        except Exception as e:
            self.logger.debug(f"Mimetypes detection failed: {e}")
    
    def _detect_encoding_and_content(self, path: Path, analysis: FileAnalysis):
        """Detect file encoding and read content sample"""
        
        # Try to read as binary first
        try:
            with open(path, 'rb') as f:
                raw_sample = f.read(8192)  # Read first 8KB
                
                # Check if binary
                analysis.binary = self._is_binary(raw_sample)
                
                if not analysis.binary:
                    # Detect encoding
                    if CHARDET_AVAILABLE:
                        detection = chardet.detect(raw_sample)
                        analysis.encoding = detection.get('encoding', 'utf-8')
                        analysis.confidence = detection.get('confidence', 0.0)
                    else:
                        analysis.encoding = 'utf-8'
                    
                    # Try to decode
                    try:
                        text = raw_sample.decode(analysis.encoding or 'utf-8')
                        analysis.content_sample = text
                        
                        # Check for shebang
                        lines = text.splitlines()
                        if lines and lines[0].startswith('#!'):
                            analysis.shebang = lines[0]
                    except UnicodeDecodeError:
                        # Try with latin-1 as fallback
                        try:
                            text = raw_sample.decode('latin-1')
                            analysis.content_sample = text
                            analysis.encoding = 'latin-1'
                        except Exception:
                            analysis.binary = True
                            
        except Exception as e:
            self.logger.debug(f"Failed to read file content: {e}")
    
    def _analyze_with_tika(self, path: Path, analysis: FileAnalysis):
        """Use Apache Tika for comprehensive file analysis"""
        try:
            # Parse with Tika
            parsed = tika_parser.from_file(str(path))
            
            if parsed:
                # Get metadata
                metadata = parsed.get('metadata', {})
                analysis.tika_metadata = metadata
                
                # Get MIME type
                if 'Content-Type' in metadata:
                    analysis.mime_tika = metadata['Content-Type']
                
                # Get content if not already available
                if not analysis.content_sample and 'content' in parsed:
                    content = parsed['content']
                    if content:
                        analysis.content_sample = content[:8192]
                
                # Get language hints from Tika
                if 'language' in metadata:
                    analysis.language_hints.append(f"tika:{metadata['language']}")
                    
        except Exception as e:
            self.logger.debug(f"Tika analysis failed: {e}")
    
    def _detect_language_hints(self, analysis: FileAnalysis):
        """Detect programming language hints from content"""
        if not analysis.content_sample:
            return
        
        sample = analysis.content_sample[:2000]  # Check first 2KB
        
        for language, config in self.language_patterns.items():
            score = 0
            
            # Check extension
            if analysis.extension in config['extensions']:
                score += 10
                analysis.language_hints.append(f"ext:{language.value}")
            
            # Check MIME type
            best_mime = analysis.get_best_mime_type()
            if best_mime and best_mime in config['mimes']:
                score += 8
                analysis.language_hints.append(f"mime:{language.value}")
            
            # Check shebang
            if analysis.shebang:
                for shebang_hint in config['shebang']:
                    if shebang_hint in analysis.shebang.lower():
                        score += 9
                        analysis.language_hints.append(f"shebang:{language.value}")
                        break
            
            # Check patterns
            pattern_matches = sum(1 for pattern in config['patterns'] if pattern in sample)
            if pattern_matches >= 3:
                score += pattern_matches
                analysis.language_hints.append(f"pattern:{language.value}({pattern_matches})")
    
    def _calculate_confidence(self, analysis: FileAnalysis):
        """Calculate overall confidence score"""
        confidence = 0.0
        
        # Extension match
        if analysis.extension:
            confidence += 0.3
        
        # MIME type detection
        mime_count = sum(1 for m in [analysis.mime_magic, analysis.mime_filetype, 
                                     analysis.mime_mimetypes, analysis.mime_tika] if m)
        confidence += mime_count * 0.15
        
        # Language hints
        if analysis.language_hints:
            confidence += min(len(analysis.language_hints) * 0.1, 0.3)
        
        # Encoding confidence (from chardet)
        if hasattr(analysis, 'confidence') and analysis.confidence > 0:
            confidence += analysis.confidence * 0.1
        
        analysis.confidence = min(confidence, 1.0)
    
    def _is_binary(self, data: bytes) -> bool:
        """Check if data appears to be binary"""
        if not data:
            return False
        
        # Check for null bytes
        if b'\x00' in data:
            return True
        
        # Count non-text characters
        text_chars = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)))
        non_text = sum(1 for byte in data if byte not in text_chars)
        
        # If more than 30% non-text, likely binary
        return (non_text / len(data)) > 0.3


class ParserRouter:
    """Intelligent router for selecting appropriate parser based on file analysis"""
    
    def __init__(self, use_tika: bool = True):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.detector = FileDetector(use_tika=use_tika)
        self._parsers: Dict[Language, BaseParser] = {}
        
        # Register default parsers
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """Register built-in parsers"""
        self.register_parser(Language.PYTHON, PythonParser())
        
        js_parser = JavaScriptParser()
        self.register_parser(Language.JAVASCRIPT, js_parser)
        self.register_parser(Language.TYPESCRIPT, js_parser)  # Same parser handles both
    
    def register_parser(self, language: Language, parser: BaseParser):
        """Register a parser for a language"""
        self._parsers[language] = parser
        self.logger.info(f"Registered parser for {language.value}")
    
    def select_parser(self, analysis: FileAnalysis) -> Optional[BaseParser]:
        """Select the best parser based on file analysis"""
        
        # Count votes for each language
        language_scores = {}
        
        for hint in analysis.language_hints:
            if ':' in hint:
                source, lang_info = hint.split(':', 1)
                
                # Extract language name
                if '(' in lang_info:
                    lang_name = lang_info.split('(')[0]
                else:
                    lang_name = lang_info
                
                # Try to match with Language enum
                for language in Language:
                    if language.value == lang_name:
                        # Weight different sources differently
                        weight = {
                            'ext': 10,
                            'shebang': 9,
                            'mime': 8,
                            'pattern': 5,
                            'tika': 7
                        }.get(source, 1)
                        
                        language_scores[language] = language_scores.get(language, 0) + weight
        
        # Select language with highest score
        if language_scores:
            best_language = max(language_scores.items(), key=lambda x: x[1])[0]
            
            if best_language in self._parsers:
                parser = self._parsers[best_language]
                self.logger.info(f"Selected {parser.__class__.__name__} for {analysis.path} (confidence: {analysis.confidence:.2f})")
                return parser
        
        # Fallback: ask each parser if it can handle the file
        if analysis.content_sample:
            for language, parser in self._parsers.items():
                try:
                    if parser.can_parse(str(analysis.path), analysis.content_sample):
                        self.logger.info(f"Fallback: {parser.__class__.__name__} can parse {analysis.path}")
                        return parser
                except Exception as e:
                    self.logger.debug(f"Parser {parser.__class__.__name__} check failed: {e}")
        
        return None
    
    def parse_file(self, filepath: str) -> ParseResult:
        """Parse a file using intelligent parser selection"""
        # Analyze the file
        analysis_result = self.detector.analyze_file(filepath)
        if not analysis_result.success:
            return analysis_result
        
        analysis = analysis_result.data
        
        # Skip binary files
        if analysis.binary:
            return ParseResult(False, error=f"Binary file detected: {filepath}")
        
        # Select parser
        parser = self.select_parser(analysis)
        if not parser:
            self.logger.warning(f"No parser found for {filepath}")
            self.logger.debug(f"File analysis: {analysis.to_dict()}")
            return ParseResult(False, error=f"No parser available for {filepath}")
        
        # Read full content
        try:
            content = analysis.path.read_text(encoding=analysis.encoding or 'utf-8')
        except Exception as e:
            return ParseResult(False, error=f"Failed to read file: {str(e)}")
        
        # Parse the file
        self.logger.info(f"Parsing {filepath} with {parser.__class__.__name__}")
        return parser.parse(content, filepath)


class CodeParser:
    """Main interface for code parsing with intelligent routing"""
    
    def __init__(self, use_tika: bool = True):
        """
        Initialize the code parser
        
        Args:
            use_tika: Whether to use Apache Tika for file analysis (if available)
        """
        self.router = ParserRouter(use_tika=use_tika)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Log available detection libraries
        self._log_capabilities()
    
    def _log_capabilities(self):
        """Log available detection capabilities"""
        capabilities = []
        
        if MAGIC_AVAILABLE:
            capabilities.append("python-magic")
        if FILETYPE_AVAILABLE:
            capabilities.append("filetype")
        if CHARDET_AVAILABLE:
            capabilities.append("chardet")
        if TIKA_AVAILABLE:
            capabilities.append("Apache Tika")
        
        if capabilities:
            self.logger.info(f"Available detection libraries: {', '.join(capabilities)}")
        else:
            self.logger.warning("No advanced detection libraries available - using basic detection only")
    
    def register_parser(self, language: Language, parser: BaseParser):
        """Register a new parser"""
        self.router.register_parser(language, parser)
        return ParseResult(True)
    
    def parse_file(self, filepath: str, output_path: Optional[str] = None) -> ParseResult:
        """Parse a single file and optionally save to JSON"""
        result = self.router.parse_file(filepath)
        
        if result.success and output_path:
            save_result = self._save_json(result.data, output_path)
            if not save_result.success:
                return save_result
        
        return result
    
    def analyze_file(self, filepath: str) -> ParseResult:
        """Get detailed file analysis without parsing"""
        return self.router.detector.analyze_file(filepath)
    
    def parse_directory(self, directory: str, output_path: Optional[str] = None, 
                       recursive: bool = True, extensions: List[str] = None,
                       skip_binary: bool = True) -> ParseResult:
        """
        Parse all supported files in a directory
        
        Args:
            directory: Directory path to parse
            output_path: Optional path to save JSON output
            recursive: Whether to parse subdirectories
            extensions: List of extensions to filter (e.g., ['.py', '.js'])
            skip_binary: Whether to skip binary files
        """
        try:
            path = Path(directory)
            
            if not path.exists():
                return ParseResult(False, error=f"Directory not found: {directory}")
            
            if not path.is_dir():
                return ParseResult(False, error=f"Not a directory: {directory}")
            
            results = []
            errors = []
            skipped = []
            
            # Get all files
            pattern = '**/*' if recursive else '*'
            files = list(path.glob(pattern))
            
            self.logger.info(f"Found {len(files)} items in {directory}")
            
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                # Filter by extension if specified
                if extensions and file_path.suffix.lower() not in extensions:
                    skipped.append(str(file_path))
                    continue
                
                # Skip obviously non-code files
                skip_extensions = {'.pyc', '.pyo', '.class', '.jar', '.exe', '.dll', '.so', 
                                  '.zip', '.tar', '.gz', '.jpg', '.png', '.gif', '.pdf'}
                if file_path.suffix.lower() in skip_extensions:
                    skipped.append(str(file_path))
                    continue
                
                # Analyze file first
                if skip_binary:
                    analysis = self.router.detector.analyze_file(str(file_path))
                    if analysis.success and analysis.data.binary:
                        skipped.append(str(file_path))
                        continue
                
                # Try to parse the file
                result = self.parse_file(str(file_path))
                if result.success:
                    results.append(result.data)
                    if result.warnings:
                        for warning in result.warnings:
                            errors.append(f"{file_path}: {warning}")
                else:
                    errors.append(f"{file_path}: {result.error}")
            
            # Log summary
            self.logger.info(f"Successfully parsed {len(results)} files")
            if errors:
                self.logger.warning(f"Encountered {len(errors)} errors")
            if skipped:
                self.logger.info(f"Skipped {len(skipped)} files")
            
            # Save if requested
            if results and output_path:
                save_result = self._save_json(results, output_path)
                if not save_result.success:
                    return save_result
            
            return ParseResult(
                success=True,
                data=results,
                warnings=errors if errors else None
            )
            
        except Exception as e:
            error_msg = f"Error parsing directory {directory}: {str(e)}"
            self.logger.error(error_msg)
            return ParseResult(False, error=error_msg)
    
    def _save_json(self, data: Union[ParsedFile, List[ParsedFile]], output_path: str) -> ParseResult:
        """Save parsed data to JSON file"""
        try:
            # Convert to dictionary
            if isinstance(data, list):
                json_data = [item.to_dict() if hasattr(item, 'to_dict') else item 
                            for item in data]
            else:
                json_data = data.to_dict() if hasattr(data, 'to_dict') else data
            
            # Save to file
            path = Path(output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Saved JSON to {output_path}")
            return ParseResult(True)
            
        except Exception as e:
            error_msg = f"Failed to save JSON: {str(e)}"
            self.logger.error(error_msg)
            return ParseResult(False, error=error_msg)
    
    def create_embeddings_dataset(self, parsed_files: List[ParsedFile], 
                                 chunk_size: int = 512,
                                 include_context: bool = True) -> List[Dict]:
        """
        Convert parsed files into chunks suitable for embedding generation
        
        Args:
            parsed_files: List of parsed file objects
            chunk_size: Approximate size of each chunk in characters
            include_context: Whether to include contextual information
        
        Returns:
            List of dictionaries ready for embedding generation
        """
        chunks = []
        
        for file_data in parsed_files:
            if not isinstance(file_data, ParsedFile):
                self.logger.warning(f"Skipping non-ParsedFile object: {type(file_data)}")
                continue
            
            file_path = file_data.filepath
            
            for block in file_data.blocks:
                # Create metadata for the chunk
                metadata = {
                    "file_path": file_path,
                    "language": file_data.language.value if hasattr(file_data.language, 'value') else str(file_data.language),
                    "block_type": block.type,
                    "block_name": block.name,
                    "start_line": block.start_line,
                    "end_line": block.end_line,
                    "has_docstring": bool(block.docstring)
                }
                
                # Add additional metadata
                if block.metadata:
                    for key, value in block.metadata.items():
                        if key not in metadata:
                            metadata[key] = value
                
                # Create the text content for embedding
                text_parts = []
                
                if include_context:
                    # Add contextual information
                    text_parts.append(f"File: {Path(file_path).name}")
                    text_parts.append(f"Language: {metadata['language']}")
                    text_parts.append(f"Type: {block.type}")
                    text_parts.append(f"Name: {block.name}")
                    
                    if block.signature:
                        text_parts.append(f"Signature: {block.signature}")
                    
                    if block.docstring:
                        text_parts.append(f"Documentation: {block.docstring}")
                
                # Add the actual code
                text_parts.append(f"Code:\n{block.content}")
                
                text = "\n".join(text_parts)
                
                # Split into smaller chunks if necessary
                if len(text) > chunk_size:
                    # Split by lines to avoid breaking code mid-line
                    lines = text.split('\n')
                    current_chunk = []
                    current_size = 0
                    chunk_index = 0
                    
                    for line in lines:
                        line_size = len(line) + 1  # +1 for newline
                        
                        if current_size + line_size > chunk_size and current_chunk:
                            # Save current chunk
                            chunk_text = '\n'.join(current_chunk)
                            chunks.append({
                                "text": chunk_text,
                                "metadata": {**metadata, "chunk_index": chunk_index}
                            })
                            chunk_index += 1
                            current_chunk = [line]
                            current_size = line_size
                        else:
                            current_chunk.append(line)
                            current_size += line_size
                    
                    # Add remaining chunk
                    if current_chunk:
                        chunk_text = '\n'.join(current_chunk)
                        chunks.append({
                            "text": chunk_text,
                            "metadata": {**metadata, "chunk_index": chunk_index}
                        })
                else:
                    chunks.append({
                        "text": text,
                        "metadata": metadata
                    })
        
        self.logger.info(f"Created {len(chunks)} embedding chunks from {len(parsed_files)} files")
        return chunks

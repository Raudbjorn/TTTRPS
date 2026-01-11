"""
base_parser.py - Core abstractions and data structures for code parsing
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from abc import ABC, abstractmethod

from ...utils.logging_config import get_logger
from ...utils.common import check_optional_dependency

logger = get_logger(__name__)


class ParseError(Exception):
    """Custom exception for parse errors"""
    pass


class Language(Enum):
    """Supported programming languages"""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    RUST = "rust"
    GO = "go"
    UNKNOWN = "unknown"


@dataclass
class ParseResult:
    """Result wrapper for parse operations - implements error as value pattern"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
    
    def add_warning(self, warning: str):
        """Add a warning to the result"""
        if self.warnings is None:
            self.warnings = []
        self.warnings.append(warning)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "warnings": self.warnings
        }


@dataclass
class CodeBlock:
    """Represents a parsed code block"""
    type: str  # function, class, method, struct, interface, etc.
    name: str
    content: str
    docstring: Optional[str] = None
    signature: Optional[str] = None
    start_line: int = 0
    end_line: int = 0
    language: str = ""
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)


@dataclass
class ParsedFile:
    """Container for all parsed elements from a file"""
    filepath: str
    language: Language
    blocks: List[CodeBlock]
    imports: List[str]
    exports: List[str]
    global_vars: List[str]
    parse_errors: List[str]
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        result = {
            "filepath": self.filepath,
            "language": self.language.value,
            "blocks": [block.to_dict() for block in self.blocks],
            "imports": self.imports,
            "exports": self.exports,
            "global_vars": self.global_vars,
            "parse_errors": self.parse_errors,
            "metadata": self.metadata
        }
        return result
    
    @classmethod
    def empty(cls, filepath: str, language: Language) -> 'ParsedFile':
        """Create an empty ParsedFile instance"""
        return cls(
            filepath=filepath,
            language=language,
            blocks=[],
            imports=[],
            exports=[],
            global_vars=[],
            parse_errors=[],
            metadata={}
        )


class BaseParser(ABC):
    """Abstract base class for language-specific parsers"""
    
    # Configuration constants
    DEFAULT_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB default
    BINARY_DETECTION_THRESHOLD = 0.3  # 30% non-text characters indicates binary
    
    def __init__(self, max_file_size: int = None):
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self.max_file_size = max_file_size if max_file_size is not None else self.DEFAULT_MAX_FILE_SIZE
    
    @abstractmethod
    def parse(self, content: str, filepath: str) -> ParseResult:
        """Parse code content and return structured data"""
        pass
    
    @abstractmethod
    def can_parse(self, filepath: str, content: str) -> bool:
        """Check if this parser can handle the given file"""
        pass
    
    def sanitize_input(self, content: str) -> ParseResult:
        """Sanitize and validate input content"""
        try:
            if not content:
                return ParseResult(False, error="Empty content provided")
            
            if not isinstance(content, str):
                return ParseResult(False, error=f"Invalid content type: {type(content)}")
            
            # Remove null bytes and other problematic characters
            content = content.replace('\x00', '')
            
            # Check for reasonable size
            if len(content) > self.max_file_size:
                return ParseResult(False, error=f"Content too large: {len(content)} bytes (max: {self.max_file_size})")
            
            # Check for binary content
            if self._is_binary(content):
                return ParseResult(False, error="Binary content detected")
            
            return ParseResult(True, data=content)
            
        except Exception as e:
            self.logger.error(f"Sanitization failed: {e}")
            return ParseResult(False, error=str(e))
    
    def _is_binary(self, content: str, sample_size: int = 8192) -> bool:
        """Check if content appears to be binary"""
        # Check first sample_size bytes for binary indicators
        sample = content[:sample_size]
        
        # Count non-text characters
        non_text_chars = sum(1 for char in sample 
                           if ord(char) < 32 and char not in '\n\r\t')
        
        # If more than threshold % non-text, likely binary
        return (non_text_chars / len(sample)) > self.BINARY_DETECTION_THRESHOLD if sample else False
    
    def extract_line_context(self, content: str, line_no: int, context_lines: int = 2) -> str:
        """Extract lines around a specific line number for context"""
        lines = content.splitlines()
        start = max(0, line_no - context_lines - 1)
        end = min(len(lines), line_no + context_lines)
        return '\n'.join(lines[start:end])

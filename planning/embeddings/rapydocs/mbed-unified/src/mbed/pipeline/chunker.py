"""
Chunking strategy interface and factory
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import hashlib
import logging

from ..core.result import Result

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata."""
    text: str
    metadata: Dict[str, Any]
    start_idx: int
    end_idx: int
    chunk_id: str
    overlap_prev: Optional[int] = None
    overlap_next: Optional[int] = None

    def __post_init__(self):
        """Generate chunk ID if not provided."""
        if not self.chunk_id:
            # Generate deterministic ID from content
            content_hash = hashlib.md5(self.text.encode()).hexdigest()[:8]
            self.chunk_id = f"chunk_{content_hash}_{self.start_idx}"


@dataclass
class ChunkConfig:
    """Configuration for chunking operations."""
    size: int = 500
    overlap: int = 50
    strategy_specific: Dict[str, Any] = None

    def __post_init__(self):
        if self.strategy_specific is None:
            self.strategy_specific = {}


class ChunkingStrategy(ABC):
    """Abstract base for all chunking strategies."""

    def __init__(self, config: ChunkConfig):
        """Initialize with configuration."""
        self.config = config
        validation = self.validate_config(config)
        if validation.is_err():
            raise ValueError(f"Invalid configuration: {validation.unwrap_err()}")

    @abstractmethod
    def chunk(self, text: str, config: ChunkConfig) -> Result[List[Chunk], str]:
        """
        Chunk text according to strategy.

        Args:
            text: Input text to chunk
            config: Chunking configuration

        Returns:
            Result.Ok(chunks) or Result.Err(error_message)
        """
        pass

    @abstractmethod
    def validate_config(self, config: ChunkConfig) -> Result[None, str]:
        """Validate configuration for this strategy."""
        pass

    def preprocess(self, text: str) -> str:
        """Optional preprocessing step."""
        return text.strip()

    def generate_chunk_id(self, text: str, index: int) -> str:
        """Generate deterministic chunk ID."""
        content_hash = hashlib.md5(text.encode()).hexdigest()[:8]
        return f"{self.__class__.__name__.lower()}_{content_hash}_{index}"


class ChunkerFactory:
    """Factory for creating chunking strategies."""

    _strategies: Dict[str, type] = {}

    @classmethod
    def register(cls, name: str, strategy_class: type):
        """Register a new chunking strategy."""
        cls._strategies[name] = strategy_class
        logger.debug(f"Registered chunking strategy: {name}")

    @classmethod
    def create(cls, strategy: str, config: ChunkConfig) -> ChunkingStrategy:
        """Create a chunking strategy instance."""
        if strategy not in cls._strategies:
            available = list(cls._strategies.keys())
            raise ValueError(f"Unknown strategy: {strategy}. Available: {available}")

        strategy_class = cls._strategies[strategy]
        return strategy_class(config)

    @classmethod
    def list_available(cls) -> List[str]:
        """List available chunking strategies."""
        return list(cls._strategies.keys())


# Import and register all strategies when module loads
def _register_strategies():
    """Register all available chunking strategies."""
    try:
        from .strategies.fixed_chunker import FixedSizeChunker
        ChunkerFactory.register('fixed', FixedSizeChunker)
    except ImportError as e:
        logger.debug(f"Could not load fixed chunker: {e}")

    try:
        from .strategies.sentence_chunker import SentenceChunker
        ChunkerFactory.register('sentence', SentenceChunker)
    except ImportError as e:
        logger.debug(f"Could not load sentence chunker: {e}")

    try:
        from .strategies.paragraph_chunker import ParagraphChunker
        ChunkerFactory.register('paragraph', ParagraphChunker)
    except ImportError as e:
        logger.debug(f"Could not load paragraph chunker: {e}")

    try:
        from .strategies.semantic_chunker import SemanticChunker
        ChunkerFactory.register('semantic', SemanticChunker)
    except ImportError as e:
        logger.debug(f"Could not load semantic chunker: {e}")

    try:
        from .strategies.hierarchical_chunker import HierarchicalChunker
        ChunkerFactory.register('hierarchical', HierarchicalChunker)
    except ImportError as e:
        logger.debug(f"Could not load hierarchical chunker: {e}")

    try:
        from .strategies.topic_chunker import TopicChunker
        ChunkerFactory.register('topic', TopicChunker)
    except ImportError as e:
        logger.debug(f"Could not load topic chunker: {e}")

    try:
        from .strategies.code_chunker import CodeChunker
        ChunkerFactory.register('code', CodeChunker)
    except ImportError as e:
        logger.debug(f"Could not load code chunker: {e}")


# Register strategies on module load
_register_strategies()
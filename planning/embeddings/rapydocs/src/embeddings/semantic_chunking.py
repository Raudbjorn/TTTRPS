"""
Semantic chunking module for intelligent text segmentation.

This module provides advanced chunking strategies that understand semantic boundaries
and create contextually meaningful chunks for superior embedding generation.

Key Features:
- Pattern-based semantic boundary detection (LLM support planned)
- Topic-based chunking
- Context preservation across chunks
- Hierarchical chunking for nested structures
- Smart overlap management
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import numpy as np
from collections import deque

try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

try:
    import nltk
    from nltk.tokenize import sent_tokenize, word_tokenize
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from .llm_preprocessor import LLMPreprocessor, PreprocessorConfig

logger = logging.getLogger(__name__)


class ChunkingStrategy(Enum):
    """Available chunking strategies"""
    FIXED_SIZE = "fixed_size"
    SENTENCE_BASED = "sentence_based"
    PARAGRAPH_BASED = "paragraph_based"
    SEMANTIC = "semantic"
    HIERARCHICAL = "hierarchical"
    TOPIC_BASED = "topic_based"


@dataclass
class SemanticChunkConfig:
    """Configuration for semantic chunking"""
    # Size constraints
    min_chunk_size: int = 200
    max_chunk_size: int = 800
    target_chunk_size: int = 500

    # Overlap settings
    overlap_tokens: int = 50
    contextual_overlap: bool = True

    # Semantic settings
    use_llm_boundaries: bool = False  # Not yet implemented
    preserve_paragraphs: bool = True
    preserve_code_blocks: bool = True
    merge_short_chunks: bool = True

    # Hierarchical settings
    enable_hierarchical: bool = False
    max_hierarchy_depth: int = 3

    # Topic detection
    enable_topic_detection: bool = False
    min_topic_similarity: float = 0.7

    # Performance settings
    batch_size: int = 10
    cache_boundaries: bool = True


class SemanticBoundary:
    """Represents a semantic boundary in text"""

    def __init__(self, position: int, strength: float, boundary_type: str):
        self.position = position
        self.strength = strength  # 0.0 to 1.0
        self.boundary_type = boundary_type  # paragraph, section, topic, etc.


@dataclass
class SemanticChunk:
    """Represents a semantic chunk with metadata"""
    text: str
    start_pos: int
    end_pos: int
    chunk_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[np.ndarray] = None
    topic: Optional[str] = None
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = field(default_factory=list)


class SemanticChunker:
    """Advanced semantic chunking with LLM support"""

    def __init__(
        self,
        config: Optional[SemanticChunkConfig] = None,
        llm_preprocessor: Optional[LLMPreprocessor] = None
    ):
        """Initialize semantic chunker"""
        self.config = config or SemanticChunkConfig()
        self.llm_preprocessor = llm_preprocessor

        # Initialize tokenizer
        if TIKTOKEN_AVAILABLE:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        else:
            self.tokenizer = None
            logger.warning("tiktoken not available, using simple word-based tokenization")

        # Initialize NLP tools
        self._init_nlp_tools()

        # Cache for boundaries
        self._boundary_cache = {}

        logger.info("Semantic chunker initialized")

    def _init_nlp_tools(self):
        """Initialize NLP tools if available"""
        # Try to initialize NLTK
        if NLTK_AVAILABLE:
            try:
                nltk.data.find('tokenizers/punkt')
            except LookupError:
                logger.info("Downloading NLTK punkt tokenizer...")
                nltk.download('punkt', quiet=True)

        # Try to initialize spaCy
        if SPACY_AVAILABLE:
            try:
                import spacy
                self.nlp = spacy.load("en_core_web_sm")
            except Exception as e:
                logger.warning(f"Could not load spaCy model: {e}")
                self.nlp = None
        else:
            self.nlp = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Simple word-based fallback
            return len(text.split())

    def chunk_text(
        self,
        text: str,
        strategy: ChunkingStrategy = ChunkingStrategy.SEMANTIC,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[SemanticChunk]:
        """
        Chunk text using specified strategy.

        Args:
            text: Text to chunk
            strategy: Chunking strategy to use
            metadata: Optional metadata to attach to chunks

        Returns:
            List of semantic chunks
        """
        if strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(text, metadata)
        elif strategy == ChunkingStrategy.SENTENCE_BASED:
            return self._chunk_by_sentences(text, metadata)
        elif strategy == ChunkingStrategy.PARAGRAPH_BASED:
            return self._chunk_by_paragraphs(text, metadata)
        elif strategy == ChunkingStrategy.SEMANTIC:
            return self._chunk_semantic(text, metadata)
        elif strategy == ChunkingStrategy.HIERARCHICAL:
            return self._chunk_hierarchical(text, metadata)
        elif strategy == ChunkingStrategy.TOPIC_BASED:
            return self._chunk_by_topics(text, metadata)
        else:
            logger.warning(f"Unknown strategy {strategy}, using fixed size")
            return self._chunk_fixed_size(text, metadata)

    def _chunk_fixed_size(self, text: str, metadata: Optional[Dict] = None) -> List[SemanticChunk]:
        """Simple fixed-size chunking with overlap"""
        chunks = []
        words = text.split()

        start_idx = 0
        chunk_idx = 0

        while start_idx < len(words):
            # Calculate chunk size
            end_idx = min(start_idx + self.config.target_chunk_size, len(words))

            # Create chunk text
            chunk_text = " ".join(words[start_idx:end_idx])

            # Add overlap from previous chunk if not first chunk
            if chunk_idx > 0 and self.config.overlap_tokens > 0:
                overlap_start = max(0, start_idx - self.config.overlap_tokens)
                overlap_text = " ".join(words[overlap_start:start_idx])
                chunk_text = overlap_text + " " + chunk_text

            # Create chunk
            chunk = SemanticChunk(
                text=chunk_text,
                start_pos=start_idx,
                end_pos=end_idx,
                chunk_id=self._generate_chunk_id(chunk_text, chunk_idx),
                metadata=metadata or {}
            )
            chunks.append(chunk)

            # Move to next chunk with overlap
            start_idx = end_idx - self.config.overlap_tokens if self.config.overlap_tokens > 0 else end_idx
            chunk_idx += 1

        return chunks

    def _chunk_by_sentences(self, text: str, metadata: Optional[Dict] = None) -> List[SemanticChunk]:
        """Chunk by sentences with smart boundaries"""
        # Get sentences with positions
        if NLTK_AVAILABLE:
            sentences = sent_tokenize(text)
        else:
            # Simple sentence splitting
            sentences = re.split(r'(?<=[.!?])\s+', text)

        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_idx = 0
        current_start_pos = 0
        text_position = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)
            sentence_start = text.find(sentence, text_position)
            sentence_end = sentence_start + len(sentence)
            text_position = sentence_end

            # Check if adding this sentence exceeds max size
            if current_tokens + sentence_tokens > self.config.max_chunk_size and current_chunk:
                # Create chunk
                chunk_text = " ".join(current_chunk)
                chunk = SemanticChunk(
                    text=chunk_text,
                    start_pos=current_start_pos,
                    end_pos=text_position,
                    chunk_id=self._generate_chunk_id(chunk_text, chunk_idx),
                    metadata=metadata or {}
                )
                chunks.append(chunk)

                # Start new chunk with overlap
                if self.config.contextual_overlap and current_chunk:
                    # Keep last sentence as overlap
                    current_chunk = [current_chunk[-1], sentence]
                    current_tokens = self.count_tokens(current_chunk[0]) + sentence_tokens
                else:
                    current_chunk = [sentence]
                    current_tokens = sentence_tokens

                chunk_idx += 1
            else:
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Add remaining chunk
        if current_chunk:
            chunk_text = " ".join(current_chunk)
            chunk = SemanticChunk(
                text=chunk_text,
                start_pos=0,
                end_pos=0,
                chunk_id=self._generate_chunk_id(chunk_text, chunk_idx),
                metadata=metadata or {}
            )
            chunks.append(chunk)

        return chunks

    def _chunk_by_paragraphs(self, text: str, metadata: Optional[Dict] = None) -> List[SemanticChunk]:
        """Chunk by paragraphs"""
        # Split by double newlines or multiple spaces
        paragraphs = re.split(r'\n\n+|\r\n\r\n+', text)

        chunks = []
        current_chunk = []
        current_tokens = 0
        chunk_idx = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = self.count_tokens(para)

            # Check if paragraph is too large by itself
            if para_tokens > self.config.max_chunk_size:
                # Need to split this paragraph
                if current_chunk:
                    # Save current chunk first
                    chunk_text = "\n\n".join(current_chunk)
                    chunk = SemanticChunk(
                        text=chunk_text,
                        start_pos=0,
                        end_pos=0,
                        chunk_id=self._generate_chunk_id(chunk_text, chunk_idx),
                        metadata=metadata or {}
                    )
                    chunks.append(chunk)
                    chunk_idx += 1
                    current_chunk = []
                    current_tokens = 0

                # Split large paragraph by sentences
                para_chunks = self._chunk_by_sentences(para, metadata)
                chunks.extend(para_chunks)

            elif current_tokens + para_tokens > self.config.max_chunk_size and current_chunk:
                # Create chunk
                chunk_text = "\n\n".join(current_chunk)
                chunk = SemanticChunk(
                    text=chunk_text,
                    start_pos=0,
                    end_pos=0,
                    chunk_id=self._generate_chunk_id(chunk_text, chunk_idx),
                    metadata=metadata or {}
                )
                chunks.append(chunk)

                # Start new chunk
                current_chunk = [para]
                current_tokens = para_tokens
                chunk_idx += 1
            else:
                current_chunk.append(para)
                current_tokens += para_tokens

        # Add remaining chunk
        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            chunk = SemanticChunk(
                text=chunk_text,
                start_pos=0,
                end_pos=0,
                chunk_id=self._generate_chunk_id(chunk_text, chunk_idx),
                metadata=metadata or {}
            )
            chunks.append(chunk)

        return chunks

    def _chunk_semantic(self, text: str, metadata: Optional[Dict] = None) -> List[SemanticChunk]:
        """Advanced semantic chunking using LLM for boundary detection"""
        # First detect semantic boundaries
        boundaries = self._detect_semantic_boundaries(text)

        # Create chunks based on boundaries
        chunks = []
        chunk_idx = 0

        # Sort boundaries by position
        boundaries.sort(key=lambda b: b.position)

        # Add start and end boundaries
        boundaries.insert(0, SemanticBoundary(0, 1.0, "start"))
        boundaries.append(SemanticBoundary(len(text), 1.0, "end"))

        # Create chunks between strong boundaries
        i = 0
        while i < len(boundaries) - 1:
            start_pos = boundaries[i].position

            # Find next suitable boundary
            current_tokens = 0
            j = i + 1

            while j < len(boundaries):
                end_pos = boundaries[j].position
                chunk_text = text[start_pos:end_pos].strip()
                current_tokens = self.count_tokens(chunk_text)

                # Check if we should stop here
                if current_tokens >= self.config.min_chunk_size:
                    if (current_tokens <= self.config.max_chunk_size or
                        boundaries[j].strength >= 0.8 or
                        j == len(boundaries) - 1):
                        break

                j += 1

            # Create chunk
            end_pos = boundaries[j].position
            chunk_text = text[start_pos:end_pos].strip()

            if chunk_text:
                # Add contextual overlap if enabled
                if self.config.contextual_overlap and chunks:
                    overlap = self._create_contextual_overlap(chunks[-1].text)
                    chunk_text = overlap + " " + chunk_text

                chunk = SemanticChunk(
                    text=chunk_text,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    chunk_id=self._generate_chunk_id(chunk_text, chunk_idx),
                    metadata={
                        **(metadata or {}),
                        "boundary_type": boundaries[j].boundary_type,
                        "boundary_strength": boundaries[j].strength
                    }
                )
                chunks.append(chunk)
                chunk_idx += 1

            i = j

        # Merge short chunks if enabled
        if self.config.merge_short_chunks:
            chunks = self._merge_short_chunks(chunks)

        return chunks

    def _detect_semantic_boundaries(self, text: str) -> List[SemanticBoundary]:
        """Detect semantic boundaries in text"""
        boundaries = []

        # Check cache
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        if self.config.cache_boundaries and text_hash in self._boundary_cache:
            return self._boundary_cache[text_hash]

        # Detect paragraph boundaries
        para_positions = [m.start() for m in re.finditer(r'\n\n+', text)]
        for pos in para_positions:
            boundaries.append(SemanticBoundary(pos, 0.7, "paragraph"))

        # Detect section boundaries (headers)
        header_patterns = [
            (r'^#+\s+.*$', 0.9, "header"),  # Markdown headers
            (r'^[A-Z][A-Z\s]+$', 0.8, "title"),  # All caps titles
            (r'^\d+\.[\s\d.]*\s+\w+', 0.8, "numbered_section"),  # Numbered sections
        ]

        for pattern, strength, boundary_type in header_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                boundaries.append(SemanticBoundary(match.start(), strength, boundary_type))

        # Detect code block boundaries
        code_blocks = re.finditer(r'```[\s\S]*?```', text)
        for block in code_blocks:
            boundaries.append(SemanticBoundary(block.start(), 0.9, "code_start"))
            boundaries.append(SemanticBoundary(block.end(), 0.9, "code_end"))

        # Use LLM for advanced boundary detection if available
        if self.config.use_llm_boundaries and self.llm_preprocessor:
            llm_boundaries = self._detect_boundaries_with_llm(text)
            boundaries.extend(llm_boundaries)

        # Cache results
        if self.config.cache_boundaries:
            self._boundary_cache[text_hash] = boundaries

        return boundaries

    def _detect_boundaries_with_llm(self, text: str) -> List[SemanticBoundary]:
        """Use LLM to detect semantic boundaries

        TODO: Implement actual LLM-based boundary detection.
        This is a placeholder for future implementation.
        """
        if not self.llm_preprocessor:
            return []

        # Create prompt for boundary detection
        prompt = f"""
        Identify major semantic boundaries in the following text.
        Mark positions where the topic, context, or narrative significantly changes.
        Return positions as line numbers or approximate character positions.

        Text:
        {text[:2000]}...  # Truncate for prompt

        Boundaries:
        """

        try:
            # This would need proper implementation with the LLM
            # For now, return empty list
            return []
        except Exception as e:
            logger.error(f"LLM boundary detection failed: {e}")
            return []

    def _chunk_hierarchical(self, text: str, metadata: Optional[Dict] = None) -> List[SemanticChunk]:
        """Create hierarchical chunks with parent-child relationships"""
        # First create top-level chunks
        top_chunks = self._chunk_by_paragraphs(text, metadata)

        all_chunks = []

        for parent_chunk in top_chunks:
            # Add parent chunk
            all_chunks.append(parent_chunk)

            # If parent is too large, create child chunks
            if self.count_tokens(parent_chunk.text) > self.config.target_chunk_size:
                child_chunks = self._chunk_by_sentences(parent_chunk.text, metadata)

                # Set parent-child relationships
                for child in child_chunks:
                    child.parent_chunk_id = parent_chunk.chunk_id
                    parent_chunk.child_chunk_ids.append(child.chunk_id)
                    all_chunks.append(child)

        return all_chunks

    def _chunk_by_topics(self, text: str, metadata: Optional[Dict] = None) -> List[SemanticChunk]:
        """Chunk by detected topics"""
        # This would require topic modeling or LLM-based topic detection
        # For now, fall back to semantic chunking
        return self._chunk_semantic(text, metadata)

    def _create_contextual_overlap(self, prev_chunk_text: str) -> str:
        """Create contextual overlap from previous chunk"""
        if not prev_chunk_text:
            return ""

        # Get last sentences from previous chunk
        if NLTK_AVAILABLE:
            sentences = sent_tokenize(prev_chunk_text)
        else:
            sentences = re.split(r'(?<=[.!?])\s+', prev_chunk_text)

        if not sentences:
            return ""

        # Use last 1-2 sentences as overlap
        overlap_sentences = sentences[-2:] if len(sentences) > 1 else sentences
        return " ".join(overlap_sentences)

    def _merge_short_chunks(self, chunks: List[SemanticChunk]) -> List[SemanticChunk]:
        """Merge chunks that are too short"""
        if not chunks:
            return chunks

        merged_chunks = []
        current_chunk = chunks[0]

        for next_chunk in chunks[1:]:
            current_tokens = self.count_tokens(current_chunk.text)

            if current_tokens < self.config.min_chunk_size:
                # Merge with next chunk
                combined_text = current_chunk.text + "\n\n" + next_chunk.text
                combined_tokens = self.count_tokens(combined_text)

                if combined_tokens <= self.config.max_chunk_size:
                    # Merge chunks
                    current_chunk = SemanticChunk(
                        text=combined_text,
                        start_pos=current_chunk.start_pos,
                        end_pos=next_chunk.end_pos,
                        chunk_id=current_chunk.chunk_id,
                        metadata={**current_chunk.metadata, **next_chunk.metadata}
                    )
                else:
                    # Can't merge, keep separate
                    merged_chunks.append(current_chunk)
                    current_chunk = next_chunk
            else:
                merged_chunks.append(current_chunk)
                current_chunk = next_chunk

        # Add last chunk
        merged_chunks.append(current_chunk)

        return merged_chunks

    def _generate_chunk_id(self, text: str, index: int) -> str:
        """Generate unique chunk ID"""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"chunk_{index}_{text_hash}"


def main():
    """Example usage of semantic chunking"""
    # Sample text
    sample_text = """
    # Introduction to Machine Learning

    Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves.

    ## Types of Machine Learning

    There are three main types of machine learning:

    ### Supervised Learning
    In supervised learning, the algorithm learns from labeled training data. Each training example consists of an input object and a desired output value. The algorithm analyzes the training data and produces an inferred function.

    ### Unsupervised Learning
    Unsupervised learning algorithms work with unlabeled data. The system tries to learn the patterns and structure from the data without any supervision. Common techniques include clustering and dimensionality reduction.

    ### Reinforcement Learning
    Reinforcement learning is about taking suitable action to maximize reward in a particular situation. It is employed by various software and machines to find the best possible behavior or path in a specific situation.

    ## Applications

    Machine learning has numerous applications across various industries:
    - Healthcare: Disease diagnosis and drug discovery
    - Finance: Fraud detection and risk assessment
    - Transportation: Autonomous vehicles and route optimization
    - Retail: Recommendation systems and demand forecasting
    """

    # Initialize chunker
    config = SemanticChunkConfig(
        min_chunk_size=100,
        max_chunk_size=300,
        target_chunk_size=200,
        preserve_paragraphs=True,
        merge_short_chunks=True
    )
    chunker = SemanticChunker(config)

    # Test different strategies
    strategies = [
        ChunkingStrategy.FIXED_SIZE,
        ChunkingStrategy.SENTENCE_BASED,
        ChunkingStrategy.PARAGRAPH_BASED,
        ChunkingStrategy.SEMANTIC
    ]

    for strategy in strategies:
        print(f"\n{'='*50}")
        print(f"Strategy: {strategy.value}")
        print('='*50)

        chunks = chunker.chunk_text(sample_text, strategy)

        for i, chunk in enumerate(chunks, 1):
            print(f"\nChunk {i} ({chunker.count_tokens(chunk.text)} tokens):")
            print(f"ID: {chunk.chunk_id}")
            print(f"Text preview: {chunk.text[:100]}...")
            if chunk.metadata:
                print(f"Metadata: {chunk.metadata}")


if __name__ == "__main__":
    main()
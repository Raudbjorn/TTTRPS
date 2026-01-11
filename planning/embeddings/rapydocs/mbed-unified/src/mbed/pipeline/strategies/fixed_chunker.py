"""
Fixed-size chunking strategy with token-aware boundaries
"""

import re
import logging
from typing import List, Dict, Any, Optional
from ..chunker import ChunkingStrategy, Chunk, ChunkConfig
from ...core.result import Result

logger = logging.getLogger(__name__)


class FixedSizeChunker(ChunkingStrategy):
    """Simple fixed-size chunking with configurable overlap."""

    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.tokenizer = None
        self._setup_tokenizer()

    def _setup_tokenizer(self):
        """Setup tokenizer with fallback."""
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.debug("Using tiktoken for token counting")
        except ImportError:
            logger.debug("tiktoken not available, falling back to word-based counting")
            self.tokenizer = None

    def chunk(self, text: str, config: ChunkConfig) -> Result[List[Chunk], str]:
        """Chunk text using fixed-size strategy with sentence boundaries."""
        # Validate inputs
        if not text or not text.strip():
            return Result.Ok([])

        validation = self.validate_config(config)
        if validation.is_err():
            return validation

        try:
            # Preprocess text
            processed_text = self.preprocess(text)

            # Try sentence-aware chunking first
            try:
                chunks = self._chunk_with_sentences(processed_text, config)
            except Exception as e:
                logger.warning(f"Sentence-aware chunking failed: {e}, falling back to simple chunking")
                chunks = self._chunk_simple(processed_text, config)

            return Result.Ok(chunks)

        except Exception as e:
            return Result.Err(f"Fixed chunking failed: {str(e)}")

    def _chunk_with_sentences(self, text: str, config: ChunkConfig) -> List[Chunk]:
        """Chunk text with sentence boundary awareness."""
        # Split into sentences
        sentences = self._split_sentences(text)

        if not sentences:
            return []

        chunks = []
        current_idx = 0
        chunk_index = 0

        # Calculate overlap in tokens/characters
        overlap_size = self._calculate_overlap(config)

        while current_idx < len(sentences):
            # Find boundary for this chunk
            boundary_idx = self._find_chunk_boundary(
                sentences[current_idx:],
                config.size
            )

            # Ensure at least one sentence per chunk
            if boundary_idx == 0:
                boundary_idx = 1

            # Extract sentences for this chunk
            chunk_sentences = sentences[current_idx:current_idx + boundary_idx]
            chunk_text = " ".join(chunk_sentences)

            # Add overlap from previous chunk if not first
            overlap_prev = None
            if chunks and overlap_size > 0:
                prev_chunk = chunks[-1]
                overlap_text = self._extract_overlap(prev_chunk.text, overlap_size, from_end=True)
                if overlap_text:
                    chunk_text = overlap_text + " " + chunk_text
                    overlap_prev = self._count_tokens_or_chars(overlap_text)

            # Add overlap for next chunk if not last
            overlap_next = None
            if current_idx + boundary_idx < len(sentences):
                next_overlap = self._extract_overlap(chunk_text, overlap_size, from_end=False)
                if next_overlap:
                    overlap_next = self._count_tokens_or_chars(next_overlap)

            # Calculate positions
            start_idx = sum(len(s) + 1 for s in sentences[:current_idx])
            end_idx = start_idx + sum(len(s) + 1 for s in chunk_sentences) - 1

            # Create chunk
            chunk = Chunk(
                text=chunk_text.strip(),
                metadata={
                    'strategy': 'fixed',
                    'token_count': self._count_tokens_or_chars(chunk_text),
                    'sentence_count': len(chunk_sentences),
                    'chunk_index': chunk_index,
                    'start_sentence_idx': current_idx,
                    'end_sentence_idx': current_idx + boundary_idx,
                    'has_prev_overlap': overlap_prev is not None,
                    'has_next_overlap': overlap_next is not None
                },
                start_idx=start_idx,
                end_idx=end_idx,
                chunk_id=self.generate_chunk_id(chunk_text, chunk_index),
                overlap_prev=overlap_prev,
                overlap_next=overlap_next
            )

            chunks.append(chunk)

            # Move to next chunk position
            current_idx += boundary_idx
            chunk_index += 1

            # Safety check to prevent infinite loops
            if chunk_index > 10000:
                logger.warning("Maximum chunk limit reached, stopping chunking")
                break

        return chunks

    def _chunk_simple(self, text: str, config: ChunkConfig) -> List[Chunk]:
        """Simple character-based chunking fallback."""
        chunks = []
        chunk_size = config.size * 4  # Rough character approximation
        overlap_size = config.overlap * 4

        chunk_index = 0
        start = 0

        while start < len(text):
            # Calculate end position
            end = min(start + chunk_size, len(text))

            # Try to find a better boundary (space, punctuation)
            if end < len(text):
                # Look backwards for a good break point
                for i in range(min(100, end - start)):
                    if text[end - i - 1] in [' ', '.', '!', '?', '\n']:
                        end = end - i
                        break

            # Extract chunk text
            chunk_text = text[start:end].strip()

            if not chunk_text:
                break

            # Calculate overlaps
            overlap_prev = overlap_size if chunk_index > 0 else None
            overlap_next = overlap_size if end < len(text) else None

            # Create chunk
            chunk = Chunk(
                text=chunk_text,
                metadata={
                    'strategy': 'fixed_simple',
                    'char_count': len(chunk_text),
                    'chunk_index': chunk_index,
                    'fallback_method': True
                },
                start_idx=start,
                end_idx=end,
                chunk_id=self.generate_chunk_id(chunk_text, chunk_index),
                overlap_prev=overlap_prev,
                overlap_next=overlap_next
            )

            chunks.append(chunk)

            # Move to next position
            start = end - overlap_size if end < len(text) else end
            chunk_index += 1

            # Safety check
            if chunk_index > 10000:
                logger.warning("Maximum chunk limit reached, stopping simple chunking")
                break

        return chunks

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences with abbreviation handling."""
        # Handle common abbreviations
        abbreviations = [
            'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Sr.', 'Jr.',
            'Ph.D.', 'M.D.', 'B.A.', 'M.A.', 'B.S.', 'M.S.',
            'etc.', 'vs.', 'i.e.', 'e.g.', 'Inc.', 'Corp.', 'Ltd.',
            'U.S.', 'U.K.', 'U.S.A.'
        ]

        # Temporarily replace periods in abbreviations
        processed_text = text
        for abbr in abbreviations:
            processed_text = processed_text.replace(abbr, abbr.replace('.', '@@@'))

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', processed_text)

        # Restore periods in abbreviations
        sentences = [s.replace('@@@', '.').strip() for s in sentences if s.strip()]

        return sentences

    def _find_chunk_boundary(self, sentences: List[str], target_size: int) -> int:
        """Find optimal boundary for chunk based on target size."""
        current_count = 0
        best_idx = 1  # At least one sentence
        best_diff = float('inf')

        for i, sentence in enumerate(sentences):
            sentence_count = self._count_tokens_or_chars(sentence)
            current_count += sentence_count

            diff = abs(current_count - target_size)
            if diff < best_diff:
                best_diff = diff
                best_idx = i + 1

            # Stop if we significantly exceed target
            if current_count > target_size * 1.5:
                break

        return best_idx

    def _count_tokens_or_chars(self, text: str) -> int:
        """Count tokens if tokenizer available, otherwise characters/4."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Rough approximation: 4 characters per token
            return len(text) // 4

    def _calculate_overlap(self, config: ChunkConfig) -> int:
        """Calculate overlap size in tokens/characters."""
        return config.overlap

    def _extract_overlap(self, text: str, overlap_size: int, from_end: bool = False) -> str:
        """Extract overlap text from beginning or end of chunk."""
        if not text:
            return ""

        if self.tokenizer:
            # Token-based overlap
            tokens = self.tokenizer.encode(text)
            if from_end:
                overlap_tokens = tokens[-overlap_size:] if len(tokens) > overlap_size else tokens
            else:
                overlap_tokens = tokens[:overlap_size]
            return self.tokenizer.decode(overlap_tokens)
        else:
            # Character-based overlap (rough)
            char_overlap = overlap_size * 4
            if from_end:
                return text[-char_overlap:] if len(text) > char_overlap else text
            else:
                return text[:char_overlap]

    def validate_config(self, config: ChunkConfig) -> Result[None, str]:
        """Validate configuration for fixed-size chunking."""
        if config.size <= 0:
            return Result.Err("Chunk size must be positive")

        if config.overlap < 0:
            return Result.Err("Overlap cannot be negative")

        if config.overlap >= config.size:
            return Result.Err("Overlap must be less than chunk size")

        # Warn about very small or large chunks
        if config.size < 50:
            logger.warning("Very small chunk size may result in poor embedding quality")

        if config.size > 2000:
            logger.warning("Very large chunk size may exceed model limits")

        return Result.Ok(None)


# Registration handled in chunker.py to avoid circular imports
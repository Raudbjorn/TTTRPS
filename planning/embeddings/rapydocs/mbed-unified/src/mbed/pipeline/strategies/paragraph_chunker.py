"""
Paragraph-based chunking strategy with structure preservation
"""

import re
import logging
from typing import List, Dict, Any, Optional
from ..chunker import ChunkingStrategy, Chunk, ChunkConfig
from ...core.result import Result

logger = logging.getLogger(__name__)


class ParagraphChunker(ChunkingStrategy):
    """Paragraph-based chunking with document structure preservation."""

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
        """Chunk text using paragraph-based strategy with structure preservation."""
        # Validate inputs
        if not text or not text.strip():
            return Result.Ok([])

        validation = self.validate_config(config)
        if validation.is_err():
            return validation

        try:
            # Preprocess text
            processed_text = self.preprocess(text)

            # Split into paragraphs
            paragraphs = self._split_paragraphs(processed_text)

            if not paragraphs:
                return Result.Ok([])

            # Create chunks with paragraph boundaries
            chunks = self._chunk_by_paragraphs(paragraphs, config)

            return Result.Ok(chunks)

        except Exception as e:
            return Result.Err(f"Paragraph chunking failed: {str(e)}")

    def _split_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs using comprehensive boundary detection."""
        # Primary pattern from mbed2: double newlines with Windows/Unix support
        paragraphs = re.split(r'\n\n+|\r\n\r\n+', text)

        # Clean and filter paragraphs
        cleaned_paragraphs = []
        for para in paragraphs:
            # Strip whitespace but preserve internal structure
            cleaned_para = para.strip()
            if cleaned_para:
                cleaned_paragraphs.append(cleaned_para)

        return cleaned_paragraphs

    def _chunk_by_paragraphs(self, paragraphs: List[str], config: ChunkConfig) -> List[Chunk]:
        """Create chunks by combining paragraphs within token limits."""
        chunks = []
        current_paragraphs = []
        current_tokens = 0
        chunk_index = 0

        for para_idx, paragraph in enumerate(paragraphs):
            para_tokens = self._count_tokens(paragraph)

            # Handle oversized paragraphs by sentence splitting
            if para_tokens > config.size:
                # First, save current chunk if we have content
                if current_paragraphs:
                    chunk = self._create_chunk_from_paragraphs(
                        current_paragraphs, chunk_index, config
                    )
                    chunks.append(chunk)
                    chunk_index += 1
                    current_paragraphs = []
                    current_tokens = 0

                # Split oversized paragraph by sentences
                oversized_chunks = self._handle_oversized_paragraph(
                    paragraph, chunk_index, config
                )
                chunks.extend(oversized_chunks)
                chunk_index += len(oversized_chunks)

            elif current_tokens + para_tokens > config.size and current_paragraphs:
                # Current chunk would exceed size limit
                chunk = self._create_chunk_from_paragraphs(
                    current_paragraphs, chunk_index, config
                )
                chunks.append(chunk)

                # Start new chunk with overlap if configured
                if config.overlap > 0 and chunks:
                    overlap_paras = self._get_overlap_paragraphs(
                        current_paragraphs, config.overlap
                    )
                    current_paragraphs = overlap_paras + [paragraph]
                    current_tokens = sum(self._count_tokens(p) for p in current_paragraphs)
                else:
                    current_paragraphs = [paragraph]
                    current_tokens = para_tokens

                chunk_index += 1
            else:
                # Add paragraph to current chunk
                current_paragraphs.append(paragraph)
                current_tokens += para_tokens

            # Safety check
            if chunk_index > 10000:
                logger.warning("Maximum chunk limit reached, stopping paragraph chunking")
                break

        # Create final chunk if we have remaining paragraphs
        if current_paragraphs:
            chunk = self._create_chunk_from_paragraphs(
                current_paragraphs, chunk_index, config
            )
            chunks.append(chunk)

        # Post-process: merge short chunks if configured
        if len(chunks) > 1:
            chunks = self._merge_short_chunks(chunks, config)

        return chunks

    def _handle_oversized_paragraph(
        self, paragraph: str, base_chunk_index: int, config: ChunkConfig
    ) -> List[Chunk]:
        """Handle paragraphs that exceed max chunk size by sentence splitting."""
        try:
            # Try to split by sentences while preserving paragraph structure
            sentences = self._split_sentences(paragraph)

            if not sentences:
                # Fallback: create single chunk even if oversized
                return [self._create_chunk_from_text(
                    paragraph, base_chunk_index, 'paragraph_oversized'
                )]

            # Create sentence-based chunks from paragraph
            chunks = []
            current_sentences = []
            current_tokens = 0
            sub_chunk_index = 0

            for sentence in sentences:
                sentence_tokens = self._count_tokens(sentence)

                if current_sentences and current_tokens + sentence_tokens > config.size:
                    # Create chunk from current sentences
                    chunk_text = " ".join(current_sentences)
                    chunk = self._create_chunk_from_text(
                        chunk_text, base_chunk_index + sub_chunk_index,
                        'paragraph_split'
                    )
                    chunks.append(chunk)

                    current_sentences = [sentence]
                    current_tokens = sentence_tokens
                    sub_chunk_index += 1
                else:
                    current_sentences.append(sentence)
                    current_tokens += sentence_tokens

            # Handle remaining sentences
            if current_sentences:
                chunk_text = " ".join(current_sentences)
                chunk = self._create_chunk_from_text(
                    chunk_text, base_chunk_index + sub_chunk_index,
                    'paragraph_split'
                )
                chunks.append(chunk)

            return chunks

        except Exception as e:
            logger.warning(f"Failed to split oversized paragraph: {e}")
            # Fallback: return as single chunk
            return [self._create_chunk_from_text(
                paragraph, base_chunk_index, 'paragraph_oversized_fallback'
            )]

    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitting for oversized paragraph handling."""
        # Basic sentence splitting with abbreviation handling
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _create_chunk_from_paragraphs(
        self, paragraphs: List[str], chunk_index: int, config: ChunkConfig
    ) -> Chunk:
        """Create a Chunk object from a list of paragraphs."""
        # Join paragraphs preserving structure with double newlines
        chunk_text = "\n\n".join(paragraphs)

        # Calculate overlaps
        overlap_prev = None
        overlap_next = None

        if chunk_index > 0 and config.overlap > 0:
            overlap_text = "\n\n".join(
                self._get_overlap_paragraphs(paragraphs, config.overlap)
            )
            overlap_prev = self._count_tokens(overlap_text) if overlap_text else None

        # Calculate positions (approximate)
        start_idx = 0
        end_idx = len(chunk_text)

        return Chunk(
            text=chunk_text,
            metadata={
                'strategy': 'paragraph',
                'token_count': self._count_tokens(chunk_text),
                'paragraph_count': len(paragraphs),
                'chunk_index': chunk_index,
                'avg_paragraph_length': sum(len(p) for p in paragraphs) // len(paragraphs),
                'has_prev_overlap': overlap_prev is not None,
                'structure_preserved': True
            },
            start_idx=start_idx,
            end_idx=end_idx,
            chunk_id=self.generate_chunk_id(chunk_text, chunk_index),
            overlap_prev=overlap_prev,
            overlap_next=overlap_next
        )

    def _create_chunk_from_text(
        self, text: str, chunk_index: int, chunk_type: str
    ) -> Chunk:
        """Create a Chunk object from raw text (for oversized paragraph handling)."""
        return Chunk(
            text=text,
            metadata={
                'strategy': chunk_type,
                'token_count': self._count_tokens(text),
                'chunk_index': chunk_index,
                'structure_preserved': False
            },
            start_idx=0,
            end_idx=len(text),
            chunk_id=self.generate_chunk_id(text, chunk_index)
        )

    def _get_overlap_paragraphs(
        self, paragraphs: List[str], overlap_tokens: int, from_end: bool = True
    ) -> List[str]:
        """Get paragraphs for overlap from beginning or end of paragraph list."""
        if not paragraphs or overlap_tokens <= 0:
            return []

        overlap_paragraphs = []
        current_tokens = 0

        # Select paragraphs for overlap
        para_iter = reversed(paragraphs) if from_end else paragraphs

        for paragraph in para_iter:
            para_tokens = self._count_tokens(paragraph)
            if current_tokens + para_tokens <= overlap_tokens:
                if from_end:
                    overlap_paragraphs.insert(0, paragraph)
                else:
                    overlap_paragraphs.append(paragraph)
                current_tokens += para_tokens
            else:
                break

        return overlap_paragraphs

    def _merge_short_chunks(self, chunks: List[Chunk], config: ChunkConfig) -> List[Chunk]:
        """Merge chunks that are too short with adjacent chunks."""
        if len(chunks) <= 1:
            return chunks

        merged_chunks = []
        i = 0
        min_tokens = max(config.size // 3, 150)  # Minimum for paragraph chunks

        while i < len(chunks):
            current_chunk = chunks[i]
            current_tokens = current_chunk.metadata.get('token_count', 0)

            # If chunk is too short and we can merge with next
            if (current_tokens < min_tokens and i + 1 < len(chunks)):
                next_chunk = chunks[i + 1]
                next_tokens = next_chunk.metadata.get('token_count', 0)

                # Only merge if combined size is reasonable
                if current_tokens + next_tokens <= config.size * 1.2:
                    # Merge chunks preserving paragraph structure
                    merged_text = current_chunk.text + "\n\n" + next_chunk.text
                    merged_paras = (
                        current_chunk.metadata.get('paragraph_count', 1) +
                        next_chunk.metadata.get('paragraph_count', 1)
                    )

                    merged_chunk = Chunk(
                        text=merged_text,
                        metadata={
                            'strategy': 'paragraph_merged',
                            'token_count': self._count_tokens(merged_text),
                            'paragraph_count': merged_paras,
                            'chunk_index': current_chunk.metadata.get('chunk_index', i),
                            'merged_from': [
                                current_chunk.metadata.get('chunk_index', i),
                                next_chunk.metadata.get('chunk_index', i + 1)
                            ],
                            'structure_preserved': True
                        },
                        start_idx=current_chunk.start_idx,
                        end_idx=next_chunk.end_idx,
                        chunk_id=self.generate_chunk_id(merged_text, i)
                    )

                    merged_chunks.append(merged_chunk)
                    i += 2  # Skip both chunks
                else:
                    merged_chunks.append(current_chunk)
                    i += 1
            else:
                merged_chunks.append(current_chunk)
                i += 1

        return merged_chunks

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken or word-based fallback."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Word-based approximation
            return len(text.split())

    def validate_config(self, config: ChunkConfig) -> Result[None, str]:
        """Validate configuration for paragraph-based chunking."""
        if config.size <= 0:
            return Result.Err("Chunk size must be positive")

        if config.overlap < 0:
            return Result.Err("Overlap cannot be negative")

        if config.overlap >= config.size:
            return Result.Err("Overlap must be less than chunk size")

        # Paragraph-specific warnings
        if config.size < 200:
            logger.warning("Small chunk size may not contain complete paragraphs")

        if config.size > 3000:
            logger.warning("Very large chunk size may reduce paragraph boundary benefits")

        if config.overlap > config.size * 0.4:
            logger.warning("Large overlap may cause excessive paragraph redundancy")

        return Result.Ok(None)


# Registration handled in chunker.py to avoid circular imports
"""
Sentence-based chunking strategy with intelligent boundary detection
"""

import re
import logging
from typing import List, Dict, Any, Optional
from ..chunker import ChunkingStrategy, Chunk, ChunkConfig
from ...core.result import Result

logger = logging.getLogger(__name__)


class SentenceChunker(ChunkingStrategy):
    """Sentence-based chunking with smart boundary optimization."""

    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.tokenizer = None
        self.nltk_available = False
        self._setup_dependencies()

    def _setup_dependencies(self):
        """Setup tokenizer and NLTK with fallbacks."""
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.debug("Using tiktoken for token counting")
        except ImportError:
            logger.debug("tiktoken not available, falling back to word-based counting")
            self.tokenizer = None

        try:
            from nltk.tokenize import sent_tokenize
            import nltk
            # Try to use punkt tokenizer
            nltk.data.find('tokenizers/punkt')
            self.sent_tokenize = sent_tokenize
            self.nltk_available = True
            logger.debug("Using NLTK for sentence tokenization")
        except (ImportError, LookupError):
            logger.debug("NLTK not available or punkt tokenizer missing, using regex fallback")
            self.nltk_available = False

    def chunk(self, text: str, config: ChunkConfig) -> Result[List[Chunk], str]:
        """Chunk text using sentence-based strategy with smart boundaries."""
        # Validate inputs
        if not text or not text.strip():
            return Result.Ok([])

        validation = self.validate_config(config)
        if validation.is_err():
            return validation

        try:
            # Preprocess text
            processed_text = self.preprocess(text)

            # Split into sentences
            sentences = self._split_sentences(processed_text)

            if not sentences:
                return Result.Ok([])

            # Create chunks with sentence boundaries
            chunks = self._chunk_by_sentences(sentences, config)

            return Result.Ok(chunks)

        except Exception as e:
            return Result.Err(f"Sentence chunking failed: {str(e)}")

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences using NLTK or regex fallback."""
        if self.nltk_available:
            try:
                sentences = self.sent_tokenize(text)
                return [s.strip() for s in sentences if s.strip()]
            except Exception as e:
                logger.warning(f"NLTK sentence tokenization failed: {e}, falling back to regex")

        # Regex-based sentence splitting with abbreviation handling
        return self._split_sentences_regex(text)

    def _split_sentences_regex(self, text: str) -> List[str]:
        """Regex-based sentence splitting with comprehensive abbreviation handling."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Extended abbreviation list from mbed1 analysis
        abbreviations = [
            'Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Sr.', 'Jr.',
            'Ph.D.', 'M.D.', 'B.A.', 'M.A.', 'B.S.', 'M.S.', 'D.D.S.',
            'Inc.', 'Corp.', 'Co.', 'L.L.C.', 'Ltd.', 'LLC.',
            'U.S.', 'U.K.', 'U.S.A.', 'U.K.',
            'e.g.', 'i.e.', 'etc.', 'vs.', 'v.', 'cf.', 'al.',
            'Jan.', 'Feb.', 'Mar.', 'Apr.', 'Jun.', 'Jul.',
            'Aug.', 'Sep.', 'Sept.', 'Oct.', 'Nov.', 'Dec.'
        ]

        # Temporarily replace periods in abbreviations
        processed_text = text
        for abbr in abbreviations:
            processed_text = processed_text.replace(abbr, abbr.replace('.', '@@@'))

        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', processed_text)

        # Restore abbreviations and clean up
        sentences = [s.replace('@@@', '.').strip() for s in sentences if s.strip()]

        return sentences

    def _chunk_by_sentences(self, sentences: List[str], config: ChunkConfig) -> List[Chunk]:
        """Create chunks by combining sentences within token limits."""
        chunks = []
        current_sentences = []
        current_tokens = 0
        chunk_index = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            # Check if adding this sentence would exceed max tokens
            if current_sentences and current_tokens + sentence_tokens > config.size:
                # Create chunk from current sentences
                chunk = self._create_chunk_from_sentences(
                    current_sentences, chunk_index, config, sentences
                )
                chunks.append(chunk)

                # Start new chunk with overlap if configured
                if config.overlap > 0 and chunks:
                    overlap_sentences = self._get_overlap_sentences(
                        current_sentences, config.overlap
                    )
                    current_sentences = overlap_sentences + [sentence]
                    current_tokens = sum(self._count_tokens(s) for s in current_sentences)
                else:
                    current_sentences = [sentence]
                    current_tokens = sentence_tokens

                chunk_index += 1
            else:
                # Add sentence to current chunk
                current_sentences.append(sentence)
                current_tokens += sentence_tokens

            # Safety check to prevent infinite loops
            if chunk_index > 10000:
                logger.warning("Maximum chunk limit reached, stopping sentence chunking")
                break

        # Create final chunk if we have remaining sentences
        if current_sentences:
            chunk = self._create_chunk_from_sentences(
                current_sentences, chunk_index, config, sentences
            )
            chunks.append(chunk)

        # Post-process: merge short chunks if configured
        if len(chunks) > 1:
            chunks = self._merge_short_chunks(chunks, config)

        return chunks

    def _create_chunk_from_sentences(
        self, sentences: List[str], chunk_index: int, config: ChunkConfig, all_sentences: List[str]
    ) -> Chunk:
        """Create a Chunk object from a list of sentences."""
        chunk_text = " ".join(sentences).strip()

        # Calculate overlaps
        overlap_prev = None
        overlap_next = None

        if chunk_index > 0 and config.overlap > 0:
            overlap_prev = self._count_tokens(
                " ".join(self._get_overlap_sentences(sentences, config.overlap))
            )

        if chunk_index < len(all_sentences) - len(sentences) and config.overlap > 0:
            overlap_next = self._count_tokens(
                " ".join(self._get_overlap_sentences(sentences, config.overlap, from_end=False))
            )

        # Calculate positions (approximate)
        start_idx = 0
        end_idx = len(chunk_text)

        return Chunk(
            text=chunk_text,
            metadata={
                'strategy': 'sentence',
                'token_count': self._count_tokens(chunk_text),
                'sentence_count': len(sentences),
                'chunk_index': chunk_index,
                'avg_sentence_length': sum(len(s) for s in sentences) // len(sentences),
                'has_prev_overlap': overlap_prev is not None,
                'has_next_overlap': overlap_next is not None
            },
            start_idx=start_idx,
            end_idx=end_idx,
            chunk_id=self.generate_chunk_id(chunk_text, chunk_index),
            overlap_prev=overlap_prev,
            overlap_next=overlap_next
        )

    def _get_overlap_sentences(
        self, sentences: List[str], overlap_tokens: int, from_end: bool = True
    ) -> List[str]:
        """Get sentences for overlap from beginning or end of sentence list."""
        if not sentences or overlap_tokens <= 0:
            return []

        overlap_sentences = []
        current_tokens = 0

        # Select sentences for overlap
        sentence_iter = reversed(sentences) if from_end else sentences

        for sentence in sentence_iter:
            sentence_tokens = self._count_tokens(sentence)
            if current_tokens + sentence_tokens <= overlap_tokens:
                if from_end:
                    overlap_sentences.insert(0, sentence)
                else:
                    overlap_sentences.append(sentence)
                current_tokens += sentence_tokens
            else:
                break

        return overlap_sentences

    def _merge_short_chunks(self, chunks: List[Chunk], config: ChunkConfig) -> List[Chunk]:
        """Merge chunks that are too short with adjacent chunks."""
        if len(chunks) <= 1:
            return chunks

        merged_chunks = []
        i = 0
        min_tokens = max(config.size // 3, 100)  # Minimum 1/3 of target size

        while i < len(chunks):
            current_chunk = chunks[i]
            current_tokens = current_chunk.metadata.get('token_count', 0)

            # If chunk is too short and we can merge with next
            if (current_tokens < min_tokens and i + 1 < len(chunks)):
                next_chunk = chunks[i + 1]
                next_tokens = next_chunk.metadata.get('token_count', 0)

                # Only merge if combined size is reasonable
                if current_tokens + next_tokens <= config.size * 1.2:
                    # Merge chunks
                    merged_text = current_chunk.text + " " + next_chunk.text
                    merged_sentences = (
                        current_chunk.metadata.get('sentence_count', 1) +
                        next_chunk.metadata.get('sentence_count', 1)
                    )

                    merged_chunk = Chunk(
                        text=merged_text.strip(),
                        metadata={
                            'strategy': 'sentence_merged',
                            'token_count': self._count_tokens(merged_text),
                            'sentence_count': merged_sentences,
                            'chunk_index': current_chunk.metadata.get('chunk_index', i),
                            'merged_from': [
                                current_chunk.metadata.get('chunk_index', i),
                                next_chunk.metadata.get('chunk_index', i + 1)
                            ]
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
        """Validate configuration for sentence-based chunking."""
        if config.size <= 0:
            return Result.Err("Chunk size must be positive")

        if config.overlap < 0:
            return Result.Err("Overlap cannot be negative")

        if config.overlap >= config.size:
            return Result.Err("Overlap must be less than chunk size")

        # Sentence-specific warnings
        if config.size < 100:
            logger.warning("Very small chunk size may not contain complete sentences")

        if config.size > 2000:
            logger.warning("Very large chunk size may reduce sentence boundary benefits")

        if config.overlap > config.size * 0.5:
            logger.warning("Large overlap may cause excessive redundancy")

        return Result.Ok(None)


# Registration handled in chunker.py to avoid circular imports
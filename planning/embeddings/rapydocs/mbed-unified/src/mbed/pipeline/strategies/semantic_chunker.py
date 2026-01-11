"""
Semantic chunking strategy with LLM-powered boundary detection
"""

import re
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional, NamedTuple
from dataclasses import dataclass
from ..chunker import ChunkingStrategy, Chunk, ChunkConfig
from ...core.result import Result

logger = logging.getLogger(__name__)


@dataclass
class SemanticBoundary:
    """Represents a semantic boundary with strength and type."""
    position: int
    strength: float  # 0.0 to 1.0
    boundary_type: str
    metadata: Optional[Dict[str, Any]] = None

    def __hash__(self):
        """Make hashable by excluding mutable metadata."""
        return hash((self.position, self.strength, self.boundary_type))

    def __eq__(self, other):
        """Equality comparison for deduplication."""
        if not isinstance(other, SemanticBoundary):
            return False
        return (self.position == other.position and
                self.strength == other.strength and
                self.boundary_type == other.boundary_type)


class SemanticChunker(ChunkingStrategy):
    """Semantic chunking with intelligent boundary detection and LLM integration."""

    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.tokenizer = None
        self.llm_available = False
        self.boundary_cache = {}  # Cache for boundary detection
        self._setup_dependencies()

    def _setup_dependencies(self):
        """Setup tokenizer and LLM integration with fallbacks."""
        try:
            import tiktoken
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
            logger.debug("Using tiktoken for token counting")
        except ImportError:
            logger.debug("tiktoken not available, falling back to word-based counting")
            self.tokenizer = None

        # Check for LLM availability (Ollama)
        try:
            import ollama
            self.ollama_client = ollama
            self.llm_available = True
            logger.debug("Ollama client available for semantic boundary detection")
        except ImportError:
            logger.debug("Ollama not available, using pattern-based boundaries only")
            self.llm_available = False

    def chunk(self, text: str, config: ChunkConfig) -> Result[List[Chunk], str]:
        """Chunk text using semantic boundary detection."""
        # Validate inputs
        if not text or not text.strip():
            return Result.Ok([])

        validation = self.validate_config(config)
        if validation.is_err():
            return validation

        try:
            # Preprocess text
            processed_text = self.preprocess(text)

            # Detect semantic boundaries
            boundaries = self._detect_semantic_boundaries(processed_text)

            # Create chunks based on semantic boundaries
            chunks = self._create_semantic_chunks(processed_text, boundaries, config)

            return Result.Ok(chunks)

        except Exception as e:
            return Result.Err(f"Semantic chunking failed: {str(e)}")

    def _detect_semantic_boundaries(self, text: str) -> List[SemanticBoundary]:
        """Detect semantic boundaries using multiple strategies."""
        # Check cache first
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        if text_hash in self.boundary_cache:
            return self.boundary_cache[text_hash]

        boundaries = []

        # 1. Paragraph boundaries (strength: 0.7)
        para_positions = [m.start() for m in re.finditer(r'\n\n+', text)]
        for pos in para_positions:
            boundaries.append(SemanticBoundary(pos, 0.7, "paragraph"))

        # 2. Header patterns with variable strength
        header_patterns = [
            (r'^#+\s+.*$', 0.9, "markdown_header"),     # Markdown headers
            (r'^[A-Z][A-Z\s]+$', 0.8, "title"),         # All caps titles
            (r'^\d+\.[\s\d.]*\s+\w+', 0.8, "numbered_section"),  # Numbered sections
            (r'^[A-Z][a-z]+.*:$', 0.6, "subtitle"),     # Subtitle patterns
        ]

        for pattern, strength, boundary_type in header_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                boundaries.append(SemanticBoundary(
                    match.start(), strength, boundary_type,
                    metadata={'matched_text': match.group()}
                ))

        # 3. Code block boundaries (strength: 0.9)
        code_patterns = [
            (r'```[\s\S]*?```', 0.9, "code_block"),      # Fenced code blocks
            (r'^[ \t]{4,}.*$', 0.6, "indented_code"),    # Indented code
        ]

        for pattern, strength, boundary_type in code_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                boundaries.append(SemanticBoundary(match.start(), strength, boundary_type))

        # 4. List boundaries
        list_patterns = [
            (r'^[-*+]\s+', 0.5, "bullet_list"),         # Bullet lists
            (r'^\d+\.\s+', 0.5, "numbered_list"),       # Numbered lists
        ]

        for pattern, strength, boundary_type in list_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                boundaries.append(SemanticBoundary(match.start(), strength, boundary_type))

        # 5. Topic transition indicators
        topic_patterns = [
            (r'\b(however|furthermore|moreover|therefore|consequently)\b', 0.4, "transition"),
            (r'\b(in conclusion|to summarize|finally)\b', 0.6, "conclusion_marker"),
            (r'\b(for example|for instance|such as)\b', 0.3, "example_marker"),
        ]

        for pattern, strength, boundary_type in topic_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                boundaries.append(SemanticBoundary(match.start(), strength, boundary_type))

        # 6. LLM-based boundary detection (if available)
        if self.llm_available and len(text) > 1000:  # Only for larger texts
            try:
                llm_boundaries = self._detect_boundaries_with_llm(text)
                boundaries.extend(llm_boundaries)
            except Exception as e:
                logger.warning(f"LLM boundary detection failed: {e}")

        # Sort boundaries by position and remove duplicates
        # Sort and deduplicate boundaries by position, keeping the one with highest strength
        boundaries.sort(key=lambda b: (b.position, -b.strength))
        unique_boundaries = []
        last_pos = -1
        for b in boundaries:
            if b.position > last_pos:
                unique_boundaries.append(b)
                last_pos = b.position
        boundaries = unique_boundaries

        # Cache results
        self.boundary_cache[text_hash] = boundaries

        return boundaries

    def _detect_boundaries_with_llm(self, text: str) -> List[SemanticBoundary]:
        """Use LLM to detect semantic boundaries in text."""
        if not self.llm_available:
            return []

        # Truncate text for prompt efficiency
        text_sample = text[:2000] if len(text) > 2000 else text

        prompt = f"""Analyze the following text and identify major semantic boundaries where the topic, context, or narrative significantly changes.

For each boundary, provide:
1. Approximate position (as percentage of text)
2. Confidence score (0.0-1.0)
3. Reason for the boundary

Text to analyze:
{text_sample}

Please respond with JSON format:
{{"boundaries": [{{"position_percent": 0.25, "confidence": 0.8, "reason": "topic shift from X to Y"}}]}}"""

        try:
            response = self.ollama_client.generate(
                model=self.config.strategy_specific.get("llm_model", "llama3.2:latest"),
                prompt=prompt,
                options={
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 500
                }
            )

            # Parse LLM response
            response_text = response.get('response', '').strip()

            # Extract JSON from response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                boundary_data = json.loads(json_match.group())

                boundaries = []
                for boundary_info in boundary_data.get('boundaries', []):
                    position_percent = boundary_info.get('position_percent', 0)
                    confidence = boundary_info.get('confidence', 0.5)
                    reason = boundary_info.get('reason', 'LLM detected boundary')

                    # Convert percentage to absolute position
                    position = int(len(text) * position_percent)

                    boundaries.append(SemanticBoundary(
                        position, confidence, "llm_detected",
                        metadata={'reason': reason, 'llm_generated': True}
                    ))

                return boundaries

        except Exception as e:
            logger.warning(f"LLM boundary detection error: {e}")

        return []

    def _create_semantic_chunks(
        self, text: str, boundaries: List[SemanticBoundary], config: ChunkConfig
    ) -> List[Chunk]:
        """Create chunks based on detected semantic boundaries."""
        if not boundaries:
            # Fallback to simple paragraph chunking
            return self._fallback_paragraph_chunking(text, config)

        chunks = []
        current_start = 0
        chunk_index = 0

        # Sort boundaries by position
        sorted_boundaries = sorted(boundaries, key=lambda b: b.position)

        # Find optimal chunk boundaries based on size constraints
        for i, boundary in enumerate(sorted_boundaries):
            current_text = text[current_start:boundary.position].strip()
            current_tokens = self._count_tokens(current_text)

            # Check if we should create a chunk here
            should_chunk = (
                current_tokens >= config.size * 0.7 or  # Minimum size reached
                boundary.strength >= 0.8 or  # Strong semantic boundary
                current_tokens >= config.size  # Size limit reached
            )

            if should_chunk and current_text:
                chunk = self._create_semantic_chunk(
                    current_text, chunk_index, boundary, config
                )
                chunks.append(chunk)

                current_start = boundary.position
                chunk_index += 1

            # Safety check
            if chunk_index > 10000:
                logger.warning("Maximum chunk limit reached in semantic chunking")
                break

        # Handle remaining text
        if current_start < len(text):
            remaining_text = text[current_start:].strip()
            if remaining_text:
                chunk = self._create_semantic_chunk(
                    remaining_text, chunk_index, None, config
                )
                chunks.append(chunk)

        # Post-process: merge short chunks and add overlaps
        chunks = self._post_process_semantic_chunks(chunks, config)

        return chunks

    def _create_semantic_chunk(
        self, text: str, chunk_index: int, boundary: Optional[SemanticBoundary], config: ChunkConfig
    ) -> Chunk:
        """Create a semantic chunk with rich metadata."""
        metadata = {
            'strategy': 'semantic',
            'token_count': self._count_tokens(text),
            'chunk_index': chunk_index,
            'character_count': len(text),
        }

        # Add boundary information
        if boundary:
            metadata.update({
                'boundary_strength': boundary.strength,
                'boundary_type': boundary.boundary_type,
                'semantic_confidence': boundary.strength
            })

            if boundary.metadata:
                metadata.update({f'boundary_{k}': v for k, v in boundary.metadata.items()})

        # Detect content types
        content_features = self._analyze_content_features(text)
        metadata.update(content_features)

        return Chunk(
            text=text,
            metadata=metadata,
            start_idx=0,  # Will be updated in post-processing
            end_idx=len(text),
            chunk_id=self.generate_chunk_id(text, chunk_index)
        )

    def _analyze_content_features(self, text: str) -> Dict[str, Any]:
        """Analyze content features for rich metadata."""
        features = {}

        # Code detection
        features['has_code'] = bool(re.search(r'```|^[ \t]{4,}', text, re.MULTILINE))

        # List detection
        features['has_lists'] = bool(re.search(r'^[-*+\d]\s+', text, re.MULTILINE))

        # Header detection
        features['has_headers'] = bool(re.search(r'^#+\s+|^[A-Z][A-Z\s]+$', text, re.MULTILINE))

        # URL detection
        features['has_urls'] = bool(re.search(r'https?://', text))

        # Question detection
        features['has_questions'] = bool(re.search(r'\?', text))

        # Technical terms (basic detection)
        tech_patterns = [r'\bAPI\b', r'\bJSON\b', r'\bHTTP\b', r'\bSQL\b', r'\bGIT\b']
        features['technical_content'] = any(re.search(pattern, text, re.IGNORECASE) for pattern in tech_patterns)

        return features

    def _post_process_semantic_chunks(self, chunks: List[Chunk], config: ChunkConfig) -> List[Chunk]:
        """Post-process chunks: merge short ones and add contextual overlaps."""
        if not chunks:
            return chunks

        processed_chunks = []
        min_tokens = max(config.size // 4, 100)

        i = 0
        while i < len(chunks):
            current_chunk = chunks[i]
            current_tokens = current_chunk.metadata.get('token_count', 0)

            # Merge very short chunks with next chunk
            if (current_tokens < min_tokens and i + 1 < len(chunks)):
                next_chunk = chunks[i + 1]
                next_tokens = next_chunk.metadata.get('token_count', 0)

                if current_tokens + next_tokens <= config.size * 1.3:
                    # Merge chunks
                    merged_text = current_chunk.text + "\n\n" + next_chunk.text
                    merged_metadata = current_chunk.metadata.copy()
                    merged_metadata.update({
                        'token_count': current_tokens + next_tokens,
                        'merged_chunks': True,
                        'original_indices': [current_chunk.metadata.get('chunk_index'),
                                           next_chunk.metadata.get('chunk_index')]
                    })

                    merged_chunk = Chunk(
                        text=merged_text,
                        metadata=merged_metadata,
                        start_idx=current_chunk.start_idx,
                        end_idx=next_chunk.end_idx,
                        chunk_id=self.generate_chunk_id(merged_text, i)
                    )

                    processed_chunks.append(merged_chunk)
                    i += 2
                    continue

            processed_chunks.append(current_chunk)
            i += 1

        # Add contextual overlaps if configured
        if config.overlap > 0:
            processed_chunks = self._add_contextual_overlaps(processed_chunks, config)

        return processed_chunks

    def _add_contextual_overlaps(self, chunks: List[Chunk], config: ChunkConfig) -> List[Chunk]:
        """Add contextual overlaps between consecutive chunks."""
        if len(chunks) <= 1:
            return chunks

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # Create contextual overlap from previous chunk
            overlap_text = self._extract_contextual_overlap(prev_chunk.text, config.overlap)

            if overlap_text:
                # Update current chunk with overlap
                current_chunk.text = overlap_text + "\n\n" + current_chunk.text
                current_chunk.metadata['has_contextual_overlap'] = True
                current_chunk.metadata['overlap_tokens'] = self._count_tokens(overlap_text)

        return chunks

    def _extract_contextual_overlap(self, text: str, overlap_tokens: int) -> str:
        """Extract contextual overlap preserving sentence boundaries."""
        sentences = re.split(r'(?<=[.!?])\s+', text)

        overlap_sentences = []
        current_tokens = 0

        # Take sentences from the end
        for sentence in reversed(sentences):
            sentence_tokens = self._count_tokens(sentence)
            if current_tokens + sentence_tokens <= overlap_tokens:
                overlap_sentences.insert(0, sentence)
                current_tokens += sentence_tokens
            else:
                break

        return " ".join(overlap_sentences).strip()

    def _fallback_paragraph_chunking(self, text: str, config: ChunkConfig) -> List[Chunk]:
        """Fallback to paragraph-based chunking if no semantic boundaries found."""
        paragraphs = re.split(r'\n\n+', text)
        chunks = []
        current_paras = []
        current_tokens = 0
        chunk_index = 0

        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)

            if current_tokens + para_tokens > config.size and current_paras:
                # Create chunk
                chunk_text = "\n\n".join(current_paras)
                chunk = Chunk(
                    text=chunk_text,
                    metadata={
                        'strategy': 'semantic_fallback',
                        'token_count': current_tokens,
                        'chunk_index': chunk_index
                    },
                    start_idx=0,
                    end_idx=len(chunk_text),
                    chunk_id=self.generate_chunk_id(chunk_text, chunk_index)
                )
                chunks.append(chunk)

                current_paras = [paragraph]
                current_tokens = para_tokens
                chunk_index += 1
            else:
                current_paras.append(paragraph)
                current_tokens += para_tokens

        # Handle remaining paragraphs
        if current_paras:
            chunk_text = "\n\n".join(current_paras)
            chunk = Chunk(
                text=chunk_text,
                metadata={
                    'strategy': 'semantic_fallback',
                    'token_count': current_tokens,
                    'chunk_index': chunk_index
                },
                start_idx=0,
                end_idx=len(chunk_text),
                chunk_id=self.generate_chunk_id(chunk_text, chunk_index)
            )
            chunks.append(chunk)

        return chunks

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken or word-based fallback."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            return len(text.split())

    def validate_config(self, config: ChunkConfig) -> Result[None, str]:
        """Validate configuration for semantic chunking."""
        if config.size <= 0:
            return Result.Err("Chunk size must be positive")

        if config.overlap < 0:
            return Result.Err("Overlap cannot be negative")

        if config.overlap >= config.size:
            return Result.Err("Overlap must be less than chunk size")

        # Semantic-specific warnings
        if config.size < 300:
            logger.warning("Small chunk size may reduce semantic boundary effectiveness")

        if config.size > 2000:
            logger.warning("Very large chunks may lose semantic coherence")

        return Result.Ok(None)


# Registration handled in chunker.py to avoid circular imports
"""
Topic-based chunking strategy using semantic similarity and topic detection
"""

import re
import logging
import hashlib
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter, defaultdict
from ..chunker import ChunkingStrategy, Chunk, ChunkConfig
from ...core.result import Result

logger = logging.getLogger(__name__)


class TopicChunker(ChunkingStrategy):
    """Topic-based chunking using keyword extraction and semantic similarity."""

    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.tokenizer = None
        self.topic_cache = {}  # Cache for topic detection
        self.stopwords = self._get_stopwords()
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

    def _get_stopwords(self) -> Set[str]:
        """Get common English stopwords."""
        return {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'over', 'under', 'within', 'without',
            'is', 'was', 'are', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they',
            'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their',
            'what', 'where', 'when', 'why', 'how', 'who', 'which', 'can', 'all', 'any',
            'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not',
            'only', 'own', 'same', 'so', 'than', 'too', 'very'
        }

    def chunk(self, text: str, config: ChunkConfig) -> Result[List[Chunk], str]:
        """Chunk text using topic-based strategy with semantic similarity."""
        # Validate inputs
        if not text or not text.strip():
            return Result.Ok([])

        validation = self.validate_config(config)
        if validation.is_err():
            return validation

        try:
            # Preprocess text
            processed_text = self.preprocess(text)

            # Split into candidate segments (sentences or short paragraphs)
            segments = self._create_candidate_segments(processed_text)

            if not segments:
                return Result.Ok([])

            # Extract topics for each segment
            segment_topics = self._extract_segment_topics(segments)

            # Group segments by topic similarity
            topic_groups = self._group_segments_by_topic(segments, segment_topics, config)

            # Create chunks from topic groups
            chunks = self._create_topic_chunks(topic_groups, config)

            return Result.Ok(chunks)

        except Exception as e:
            return Result.Err(f"Topic chunking failed: {str(e)}")

    def _create_candidate_segments(self, text: str) -> List[str]:
        """Split text into candidate segments for topic analysis."""
        # Try multiple splitting strategies
        segments = []

        # 1. Split by paragraphs first
        paragraphs = re.split(r'\n\n+', text)

        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)

            # If paragraph is small enough, use as segment
            if para_tokens <= 200:  # Configurable threshold
                segments.append(paragraph.strip())
            else:
                # Split large paragraphs into sentences
                sentences = self._split_sentences(paragraph)

                # Group sentences into segments of reasonable size
                current_segment = []
                current_tokens = 0

                for sentence in sentences:
                    sentence_tokens = self._count_tokens(sentence)

                    if current_tokens + sentence_tokens <= 200 and current_segment:
                        current_segment.append(sentence)
                        current_tokens += sentence_tokens
                    else:
                        if current_segment:
                            segments.append(" ".join(current_segment))
                        current_segment = [sentence]
                        current_tokens = sentence_tokens

                # Add final segment
                if current_segment:
                    segments.append(" ".join(current_segment))

        return [seg for seg in segments if seg.strip()]

    def _split_sentences(self, text: str) -> List[str]:
        """Simple sentence splitting for topic analysis."""
        # Basic sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_segment_topics(self, segments: List[str]) -> List[Dict[str, float]]:
        """Extract topic keywords and scores for each segment."""
        segment_topics = []

        for segment in segments:
            # Check cache first
            segment_hash = hashlib.sha256(segment.encode()).hexdigest()[:16]
            if segment_hash in self.topic_cache:
                segment_topics.append(self.topic_cache[segment_hash])
                continue

            # Extract keywords and calculate topic scores
            topics = self._extract_keywords_and_topics(segment)

            # Cache results
            self.topic_cache[segment_hash] = topics
            segment_topics.append(topics)

        return segment_topics

    def _extract_keywords_and_topics(self, text: str) -> Dict[str, float]:
        """Extract keywords and calculate topic relevance scores."""
        topics = {}

        # 1. Extract potential keywords (nouns, proper nouns, technical terms)
        words = self._extract_significant_words(text)

        # 2. Calculate TF-IDF-like scores for topic relevance
        word_counts = Counter(words)
        total_words = len(words)

        # 3. Identify technical/domain-specific terms
        tech_patterns = {
            'api': r'\b(API|REST|GraphQL|HTTP|JSON|XML|endpoint|request|response)\b',
            'database': r'\b(SQL|database|table|query|index|PostgreSQL|MySQL|MongoDB)\b',
            'programming': r'\b(function|class|method|variable|algorithm|code|script|library)\b',
            'web': r'\b(HTML|CSS|JavaScript|browser|website|web|URL|domain|server)\b',
            'security': r'\b(authentication|authorization|encryption|security|token|password)\b',
            'payment': r'\b(payment|transaction|card|bank|invoice|billing|checkout|currency)\b',
            'business': r'\b(customer|client|business|service|product|company|organization)\b',
            'data': r'\b(data|analytics|report|metric|statistics|analysis|insight)\b'
        }

        # Calculate scores for each topic category
        for topic_name, pattern in tech_patterns.items():
            matches = len(re.findall(pattern, text, re.IGNORECASE))
            if matches > 0:
                # Score based on frequency and text length
                score = min(matches / max(total_words * 0.1, 1), 1.0)
                topics[topic_name] = score

        # 4. Add keyword-based topics
        for word, count in word_counts.most_common(10):  # Top 10 keywords
            if len(word) > 3 and word.lower() not in self.stopwords:
                # Calculate relative frequency
                frequency = count / total_words
                topics[f"keyword_{word.lower()}"] = frequency

        # 5. Detect named entities (basic pattern matching)
        entity_patterns = {
            'company': r'\b[A-Z][a-z]+ (?:Inc|Corp|LLC|Ltd|Company|Systems|Technologies)\b',
            'person': r'\b(?:Mr|Ms|Mrs|Dr)\.\s+[A-Z][a-z]+ [A-Z][a-z]+\b',
            'location': r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*(?:,\s+[A-Z]{2}|\s+City|\s+State)\b',
            'product': r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:API|SDK|Platform|Service)\b'
        }

        for entity_type, pattern in entity_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                topics[f"entity_{entity_type}"] = min(len(matches) * 0.3, 1.0)

        return topics

    def _extract_significant_words(self, text: str) -> List[str]:
        """Extract significant words for topic analysis."""
        # Remove common markup and clean text
        cleaned_text = re.sub(r'[^\w\s-]', ' ', text)
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text)

        # Extract words, filtering out stopwords and short words
        words = []
        for word in cleaned_text.split():
            word = word.lower().strip('-')
            if (len(word) > 2 and
                word not in self.stopwords and
                not word.isdigit() and
                re.match(r'^[a-z]+$', word)):
                words.append(word)

        return words

    def _group_segments_by_topic(
        self, segments: List[str], segment_topics: List[Dict[str, float]], config: ChunkConfig
    ) -> List[List[Tuple[str, Dict[str, float]]]]:
        """Group segments by topic similarity."""
        if not segments:
            return []

        # Create initial groups
        groups = []
        current_group = [(segments[0], segment_topics[0])]
        current_group_topics = segment_topics[0].copy()

        min_similarity = 0.3  # Minimum topic similarity threshold
        max_group_size = config.size  # Maximum tokens per group

        for i in range(1, len(segments)):
            segment = segments[i]
            topics = segment_topics[i]

            # Calculate similarity with current group
            similarity = self._calculate_topic_similarity(current_group_topics, topics)

            # Calculate current group size
            current_size = sum(self._count_tokens(seg[0]) for seg in current_group)
            new_segment_size = self._count_tokens(segment)

            # Decide whether to add to current group or start new one
            should_group = (
                similarity >= min_similarity and
                current_size + new_segment_size <= max_group_size
            )

            if should_group:
                # Add to current group and update group topics
                current_group.append((segment, topics))
                current_group_topics = self._merge_topic_scores(current_group_topics, topics)
            else:
                # Start new group
                groups.append(current_group)
                current_group = [(segment, topics)]
                current_group_topics = topics.copy()

        # Add final group
        if current_group:
            groups.append(current_group)

        return groups

    def _calculate_topic_similarity(self, topics1: Dict[str, float], topics2: Dict[str, float]) -> float:
        """Calculate cosine similarity between two topic dictionaries."""
        if not topics1 or not topics2:
            return 0.0

        # Get all unique topics
        all_topics = set(topics1.keys()) | set(topics2.keys())

        if not all_topics:
            return 0.0

        # Calculate cosine similarity
        dot_product = sum(topics1.get(topic, 0) * topics2.get(topic, 0) for topic in all_topics)
        magnitude1 = sum(score ** 2 for score in topics1.values()) ** 0.5
        magnitude2 = sum(score ** 2 for score in topics2.values()) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _merge_topic_scores(self, topics1: Dict[str, float], topics2: Dict[str, float]) -> Dict[str, float]:
        """Merge two topic score dictionaries by averaging."""
        merged = topics1.copy()

        for topic, score in topics2.items():
            if topic in merged:
                # Average the scores
                merged[topic] = (merged[topic] + score) / 2
            else:
                # Add new topic with reduced weight
                merged[topic] = score * 0.5

        return merged

    def _create_topic_chunks(
        self, topic_groups: List[List[Tuple[str, Dict[str, float]]]], config: ChunkConfig
    ) -> List[Chunk]:
        """Create chunks from topic groups."""
        chunks = []

        for group_idx, group in enumerate(topic_groups):
            # Combine segments in group
            group_texts = [segment[0] for segment in group]
            group_topics = [segment[1] for segment in group]

            # Create chunk text
            chunk_text = "\n\n".join(group_texts).strip()

            if not chunk_text:
                continue

            # Calculate dominant topics for metadata
            combined_topics = {}
            for topics in group_topics:
                for topic, score in topics.items():
                    if topic in combined_topics:
                        combined_topics[topic] = max(combined_topics[topic], score)
                    else:
                        combined_topics[topic] = score

            # Get top topics
            top_topics = sorted(combined_topics.items(), key=lambda x: x[1], reverse=True)[:5]

            # Create metadata
            metadata = {
                'strategy': 'topic',
                'token_count': self._count_tokens(chunk_text),
                'segment_count': len(group_texts),
                'chunk_index': group_idx,
                'dominant_topics': {topic: score for topic, score in top_topics},
                'topic_coherence': self._calculate_group_coherence(group_topics),
                'has_technical_content': any(topic.startswith(('api', 'database', 'programming', 'web'))
                                           for topic, _ in top_topics)
            }

            # Add topic labels for easy identification
            topic_labels = [topic.replace('keyword_', '').replace('entity_', '')
                          for topic, _ in top_topics[:3]]
            metadata['topic_labels'] = topic_labels

            chunk = Chunk(
                text=chunk_text,
                metadata=metadata,
                start_idx=0,
                end_idx=len(chunk_text),
                chunk_id=self.generate_chunk_id(chunk_text, group_idx)
            )

            chunks.append(chunk)

        # Post-process: add overlaps if configured
        if config.overlap > 0:
            chunks = self._add_topic_overlaps(chunks, config)

        return chunks

    def _calculate_group_coherence(self, group_topics: List[Dict[str, float]]) -> float:
        """Calculate how coherent the topics are within a group."""
        if len(group_topics) <= 1:
            return 1.0

        # Calculate average pairwise similarity
        total_similarity = 0
        comparisons = 0

        for i in range(len(group_topics)):
            for j in range(i + 1, len(group_topics)):
                similarity = self._calculate_topic_similarity(group_topics[i], group_topics[j])
                total_similarity += similarity
                comparisons += 1

        return total_similarity / comparisons if comparisons > 0 else 0.0

    def _add_topic_overlaps(self, chunks: List[Chunk], config: ChunkConfig) -> List[Chunk]:
        """Add topic-aware overlaps between consecutive chunks."""
        if len(chunks) <= 1:
            return chunks

        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            current_chunk = chunks[i]

            # Find topically relevant overlap
            prev_segments = prev_chunk.text.split('\n\n')
            overlap_text = self._find_topically_relevant_overlap(
                prev_segments, current_chunk.metadata.get('dominant_topics', {}), config.overlap
            )

            if overlap_text:
                current_chunk.text = overlap_text + "\n\n" + current_chunk.text
                current_chunk.metadata['has_topic_overlap'] = True
                current_chunk.metadata['overlap_tokens'] = self._count_tokens(overlap_text)

        return chunks

    def _find_topically_relevant_overlap(
        self, prev_segments: List[str], target_topics: Dict[str, float], overlap_tokens: int
    ) -> str:
        """Find the most topically relevant overlap from previous segments."""
        if not prev_segments or not target_topics:
            return ""

        # Score each segment for topic relevance
        segment_scores = []
        for segment in prev_segments:
            segment_topics = self._extract_keywords_and_topics(segment)
            relevance = self._calculate_topic_similarity(segment_topics, target_topics)
            segment_scores.append((segment, relevance))

        # Sort by relevance and select segments within token limit
        segment_scores.sort(key=lambda x: x[1], reverse=True)

        overlap_segments = []
        current_tokens = 0

        for segment, score in segment_scores:
            segment_tokens = self._count_tokens(segment)
            if current_tokens + segment_tokens <= overlap_tokens:
                overlap_segments.append(segment)
                current_tokens += segment_tokens
            else:
                break

        return "\n\n".join(overlap_segments)

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken or word-based fallback."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            return len(text.split())

    def validate_config(self, config: ChunkConfig) -> Result[None, str]:
        """Validate configuration for topic-based chunking."""
        if config.size <= 0:
            return Result.Err("Chunk size must be positive")

        if config.overlap < 0:
            return Result.Err("Overlap cannot be negative")

        if config.overlap >= config.size:
            return Result.Err("Overlap must be less than chunk size")

        # Topic-specific warnings
        if config.size < 400:
            logger.warning("Small chunk size may not capture topic coherence effectively")

        if config.size > 4000:
            logger.warning("Very large chunks may mix multiple topics")

        return Result.Ok(None)


# Registration handled in chunker.py to avoid circular imports
"""
Hierarchical chunking strategy with parent-child relationships
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from ..chunker import ChunkingStrategy, Chunk, ChunkConfig
from ...core.result import Result

logger = logging.getLogger(__name__)


@dataclass
class HierarchicalChunk(Chunk):
    """Extended chunk with hierarchical relationships."""
    parent_chunk_id: Optional[str] = None
    child_chunk_ids: List[str] = field(default_factory=list)
    hierarchy_level: int = 0
    section_title: Optional[str] = None


class HierarchicalChunker(ChunkingStrategy):
    """Hierarchical chunking with multi-level parent-child relationships."""

    def __init__(self, config: ChunkConfig):
        super().__init__(config)
        self.tokenizer = None
        self.max_hierarchy_depth = 3  # Configurable depth
        self.min_child_size = 100  # Minimum tokens for child chunks
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
        """Chunk text using hierarchical strategy with parent-child relationships."""
        # Validate inputs
        if not text or not text.strip():
            return Result.Ok([])

        validation = self.validate_config(config)
        if validation.is_err():
            return validation

        try:
            # Preprocess text
            processed_text = self.preprocess(text)

            # Detect document structure
            structure = self._analyze_document_structure(processed_text)

            # Create hierarchical chunks
            chunks = self._create_hierarchical_chunks(processed_text, structure, config)

            # Convert to base Chunk objects for consistency
            base_chunks = self._convert_to_base_chunks(chunks)

            return Result.Ok(base_chunks)

        except Exception as e:
            return Result.Err(f"Hierarchical chunking failed: {str(e)}")

    def _analyze_document_structure(self, text: str) -> Dict[str, Any]:
        """Analyze document structure to identify hierarchical sections."""
        structure = {
            'headers': [],
            'sections': [],
            'code_blocks': [],
            'lists': []
        }

        # Detect headers with hierarchy levels
        header_patterns = [
            (r'^(#+)\s+(.*)$', 'markdown_header'),          # # ## ### etc.
            (r'^(.+)\n=+\s*$', 'setext_h1'),                # Setext H1 (underlined with =)
            (r'^(.+)\n-+\s*$', 'setext_h2'),                # Setext H2 (underlined with -)
            (r'^([A-Z][A-Z\s]{2,})\s*$', 'caps_title'),     # ALL CAPS TITLES
            (r'^(\d+\.[\d.]*)\s+(.+)$', 'numbered_section'), # 1.1 Section Title
        ]

        for pattern, header_type in header_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                header_info = {
                    'type': header_type,
                    'position': match.start(),
                    'end_position': match.end(),
                    'text': match.group().strip(),
                    'level': self._determine_header_level(match, header_type)
                }

                if header_type in ['markdown_header', 'numbered_section'] and len(match.groups()) > 1:
                    header_info['title'] = match.group(2).strip()
                else:
                    header_info['title'] = match.group(1).strip() if match.groups() else match.group().strip()

                structure['headers'].append(header_info)

        # Sort headers by position
        structure['headers'].sort(key=lambda h: h['position'])

        # Detect code blocks
        code_patterns = [
            (r'```[\s\S]*?```', 'fenced_code'),
            (r'^[ \t]{4,}.*$', 'indented_code')
        ]

        for pattern, code_type in code_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                structure['code_blocks'].append({
                    'type': code_type,
                    'position': match.start(),
                    'end_position': match.end(),
                    'text': match.group()
                })

        # Detect lists for better section boundaries
        list_patterns = [
            (r'^[-*+]\s+.*$', 'bullet_list'),
            (r'^\d+\.\s+.*$', 'numbered_list')
        ]

        for pattern, list_type in list_patterns:
            for match in re.finditer(pattern, text, re.MULTILINE):
                structure['lists'].append({
                    'type': list_type,
                    'position': match.start(),
                    'end_position': match.end()
                })

        return structure

    def _determine_header_level(self, match, header_type: str) -> int:
        """Determine the hierarchical level of a header."""
        if header_type == 'markdown_header':
            return len(match.group(1))  # Count # symbols
        elif header_type == 'setext_h1':
            return 1
        elif header_type == 'setext_h2':
            return 2
        elif header_type == 'caps_title':
            return 1
        elif header_type == 'numbered_section':
            # Count dots in numbering (1.1.1 = level 3)
            numbering = match.group(1)
            return numbering.count('.') + 1
        else:
            return 1

    def _create_hierarchical_chunks(
        self, text: str, structure: Dict[str, Any], config: ChunkConfig
    ) -> List[HierarchicalChunk]:
        """Create hierarchical chunks based on document structure."""
        if not structure['headers']:
            # No headers found, fallback to paragraph-based hierarchy
            return self._create_paragraph_hierarchy(text, config)

        chunks = []
        headers = structure['headers']

        # Create sections based on headers
        for i, header in enumerate(headers):
            # Determine section boundaries
            section_start = header['position']
            section_end = headers[i + 1]['position'] if i + 1 < len(headers) else len(text)

            section_text = text[section_start:section_end].strip()

            if not section_text:
                continue

            # Create parent chunk for this section
            parent_chunk = self._create_parent_chunk(
                section_text, header, len(chunks), config
            )
            chunks.append(parent_chunk)

            # Create child chunks if parent is too large
            if self._count_tokens(section_text) > config.size:
                child_chunks = self._create_child_chunks(
                    section_text, parent_chunk, header, config
                )
                chunks.extend(child_chunks)

        return chunks

    def _create_paragraph_hierarchy(self, text: str, config: ChunkConfig) -> List[HierarchicalChunk]:
        """Create hierarchy based on paragraph structure when no headers are found."""
        paragraphs = re.split(r'\n\n+', text)
        chunks = []
        current_parent_paras = []
        current_tokens = 0
        chunk_index = 0

        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)

            # Check if we should create a parent chunk
            if current_tokens + para_tokens > config.size and current_parent_paras:
                # Create parent chunk
                parent_text = "\n\n".join(current_parent_paras)
                parent_chunk = HierarchicalChunk(
                    text=parent_text,
                    metadata={
                        'strategy': 'hierarchical_paragraph',
                        'hierarchy_level': 0,
                        'token_count': current_tokens,
                        'paragraph_count': len(current_parent_paras),
                        'chunk_index': chunk_index,
                        'section_title': f"Section {chunk_index + 1}"
                    },
                    start_idx=0,
                    end_idx=len(parent_text),
                    chunk_id=self.generate_chunk_id(parent_text, chunk_index),
                    hierarchy_level=0
                )
                chunks.append(parent_chunk)

                # Create child chunks if parent is large
                if current_tokens > config.size:
                    child_chunks = self._create_sentence_children(
                        parent_text, parent_chunk, config
                    )
                    chunks.extend(child_chunks)

                current_parent_paras = [paragraph]
                current_tokens = para_tokens
                chunk_index += 1
            else:
                current_parent_paras.append(paragraph)
                current_tokens += para_tokens

        # Handle remaining paragraphs
        if current_parent_paras:
            parent_text = "\n\n".join(current_parent_paras)
            parent_chunk = HierarchicalChunk(
                text=parent_text,
                metadata={
                    'strategy': 'hierarchical_paragraph',
                    'hierarchy_level': 0,
                    'token_count': current_tokens,
                    'paragraph_count': len(current_parent_paras),
                    'chunk_index': chunk_index,
                    'section_title': f"Section {chunk_index + 1}"
                },
                start_idx=0,
                end_idx=len(parent_text),
                chunk_id=self.generate_chunk_id(parent_text, chunk_index),
                hierarchy_level=0
            )
            chunks.append(parent_chunk)

        return chunks

    def _create_parent_chunk(
        self, section_text: str, header: Dict[str, Any], chunk_index: int, config: ChunkConfig
    ) -> HierarchicalChunk:
        """Create a parent chunk for a document section."""
        token_count = self._count_tokens(section_text)

        metadata = {
            'strategy': 'hierarchical_section',
            'hierarchy_level': 0,
            'token_count': token_count,
            'chunk_index': chunk_index,
            'section_title': header.get('title', f"Section {chunk_index + 1}"),
            'header_type': header.get('type', 'unknown'),
            'header_level': header.get('level', 1),
            'has_children': token_count > config.size
        }

        return HierarchicalChunk(
            text=section_text,
            metadata=metadata,
            start_idx=header.get('position', 0),
            end_idx=header.get('end_position', len(section_text)),
            chunk_id=self.generate_chunk_id(section_text, chunk_index),
            hierarchy_level=0,
            section_title=header.get('title')
        )

    def _create_child_chunks(
        self, section_text: str, parent_chunk: HierarchicalChunk,
        header: Dict[str, Any], config: ChunkConfig
    ) -> List[HierarchicalChunk]:
        """Create child chunks for an oversized parent section."""
        # Try paragraph-based chunking first
        paragraphs = re.split(r'\n\n+', section_text)

        if len(paragraphs) > 1:
            return self._create_paragraph_children(section_text, parent_chunk, config)
        else:
            # Fallback to sentence-based chunking
            return self._create_sentence_children(section_text, parent_chunk, config)

    def _create_paragraph_children(
        self, section_text: str, parent_chunk: HierarchicalChunk, config: ChunkConfig
    ) -> List[HierarchicalChunk]:
        """Create child chunks based on paragraph boundaries."""
        paragraphs = re.split(r'\n\n+', section_text)
        child_chunks = []
        current_paras = []
        current_tokens = 0
        child_index = 0

        for paragraph in paragraphs:
            para_tokens = self._count_tokens(paragraph)

            if current_tokens + para_tokens > config.size and current_paras:
                # Create child chunk
                child_text = "\n\n".join(current_paras)
                child_chunk = self._create_child_chunk(
                    child_text, parent_chunk, child_index, 'paragraph_child'
                )
                child_chunks.append(child_chunk)

                # Update parent-child relationships
                parent_chunk.child_chunk_ids.append(child_chunk.chunk_id)
                child_chunk.parent_chunk_id = parent_chunk.chunk_id

                current_paras = [paragraph]
                current_tokens = para_tokens
                child_index += 1
            else:
                current_paras.append(paragraph)
                current_tokens += para_tokens

        # Handle remaining paragraphs
        if current_paras:
            child_text = "\n\n".join(current_paras)
            child_chunk = self._create_child_chunk(
                child_text, parent_chunk, child_index, 'paragraph_child'
            )
            child_chunks.append(child_chunk)
            parent_chunk.child_chunk_ids.append(child_chunk.chunk_id)
            child_chunk.parent_chunk_id = parent_chunk.chunk_id

        return child_chunks

    def _create_sentence_children(
        self, section_text: str, parent_chunk: HierarchicalChunk, config: ChunkConfig
    ) -> List[HierarchicalChunk]:
        """Create child chunks based on sentence boundaries."""
        sentences = re.split(r'(?<=[.!?])\s+', section_text)
        child_chunks = []
        current_sentences = []
        current_tokens = 0
        child_index = 0

        for sentence in sentences:
            sentence_tokens = self._count_tokens(sentence)

            if current_tokens + sentence_tokens > config.size and current_sentences:
                # Create child chunk
                child_text = " ".join(current_sentences)
                child_chunk = self._create_child_chunk(
                    child_text, parent_chunk, child_index, 'sentence_child'
                )
                child_chunks.append(child_chunk)

                # Update parent-child relationships
                parent_chunk.child_chunk_ids.append(child_chunk.chunk_id)
                child_chunk.parent_chunk_id = parent_chunk.chunk_id

                current_sentences = [sentence]
                current_tokens = sentence_tokens
                child_index += 1
            else:
                current_sentences.append(sentence)
                current_tokens += sentence_tokens

        # Handle remaining sentences
        if current_sentences:
            child_text = " ".join(current_sentences)
            child_chunk = self._create_child_chunk(
                child_text, parent_chunk, child_index, 'sentence_child'
            )
            child_chunks.append(child_chunk)
            parent_chunk.child_chunk_ids.append(child_chunk.chunk_id)
            child_chunk.parent_chunk_id = parent_chunk.chunk_id

        return child_chunks

    def _create_child_chunk(
        self, text: str, parent_chunk: HierarchicalChunk,
        child_index: int, chunk_type: str
    ) -> HierarchicalChunk:
        """Create a child chunk with inherited metadata."""
        # Inherit metadata from parent
        parent_metadata = parent_chunk.metadata.copy()

        child_metadata = {
            'strategy': f'hierarchical_{chunk_type}',
            'hierarchy_level': 1,
            'token_count': self._count_tokens(text),
            'chunk_index': child_index,
            'parent_section': parent_metadata.get('section_title', 'Unknown'),
            'parent_chunk_id': parent_chunk.chunk_id,
            'inherited_metadata': {
                k: v for k, v in parent_metadata.items()
                if k in ['header_type', 'header_level', 'section_title']
            }
        }

        chunk_id = f"{parent_chunk.chunk_id}_child_{child_index}"

        return HierarchicalChunk(
            text=text,
            metadata=child_metadata,
            start_idx=0,
            end_idx=len(text),
            chunk_id=chunk_id,
            hierarchy_level=1,
            section_title=parent_chunk.section_title,
            parent_chunk_id=parent_chunk.chunk_id
        )

    def _convert_to_base_chunks(self, hierarchical_chunks: List[HierarchicalChunk]) -> List[Chunk]:
        """Convert HierarchicalChunk objects to base Chunk objects for API consistency."""
        base_chunks = []

        for h_chunk in hierarchical_chunks:
            # Add hierarchical metadata to base chunk
            metadata = h_chunk.metadata.copy()
            metadata.update({
                'parent_chunk_id': h_chunk.parent_chunk_id,
                'child_chunk_ids': h_chunk.child_chunk_ids,
                'hierarchy_level': h_chunk.hierarchy_level,
                'section_title': h_chunk.section_title
            })

            base_chunk = Chunk(
                text=h_chunk.text,
                metadata=metadata,
                start_idx=h_chunk.start_idx,
                end_idx=h_chunk.end_idx,
                chunk_id=h_chunk.chunk_id,
                overlap_prev=h_chunk.overlap_prev,
                overlap_next=h_chunk.overlap_next
            )

            base_chunks.append(base_chunk)

        return base_chunks

    def _count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken or word-based fallback."""
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            return len(text.split())

    def validate_config(self, config: ChunkConfig) -> Result[None, str]:
        """Validate configuration for hierarchical chunking."""
        if config.size <= 0:
            return Result.Err("Chunk size must be positive")

        if config.overlap < 0:
            return Result.Err("Overlap cannot be negative")

        # Hierarchical-specific validations
        if config.size < 200:
            logger.warning("Small chunk size may not benefit from hierarchical structure")

        if config.size > 3000:
            logger.warning("Very large chunks may create too few hierarchy levels")

        return Result.Ok(None)


# Registration handled in chunker.py to avoid circular imports
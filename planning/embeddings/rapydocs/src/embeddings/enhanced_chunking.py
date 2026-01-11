#!/usr/bin/env python3
"""
Enhanced chunking with entity qualifiers and metadata headers.
Improves retrieval by adding context to each chunk.
"""

import re
import hashlib
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import tiktoken

logger = logging.getLogger(__name__)


@dataclass 
class EnhancedChunkConfig:
    """Configuration for enhanced chunking"""
    min_tokens: int = 300
    max_tokens: int = 700
    target_tokens: int = 500
    overlap_percent: float = 0.15
    add_entity_headers: bool = True
    add_section_context: bool = True
    repeat_qualifiers: bool = True
    extract_metadata: bool = True


class EntityExtractor:
    """Extract entities and qualifiers from text"""
    
    def __init__(self):
        """Initialize with patterns for entity extraction"""
        
        # Patterns for different entity types
        self.location_patterns = [
            r'\b(?:in|at|near|from)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',
            r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*),\s*[A-Z][a-z]+\b',  # City, Country
        ]
        
        self.type_patterns = {
            'beach': [
                r'(black|white|golden|pink|red|volcanic|coral)\s+sand',
                r'(basaltic|limestone|quartz|shell)\s+beach',
                r'(tropical|rocky|pebble|glass)\s+beach'
            ],
            'api': [
                r'(REST|GraphQL|SOAP|gRPC)\s+API',
                r'(payment|authentication|user|data)\s+API',
                r'(public|private|internal|external)\s+API'
            ],
            'database': [
                r'(SQL|NoSQL|relational|graph)\s+database',
                r'(PostgreSQL|MySQL|MongoDB|Redis|Cassandra)',
                r'(ACID|BASE|eventual)\s+consistency'
            ]
        }
        
        self.qualifier_patterns = [
            r'\b(very|extremely|highly|somewhat|slightly|partially)\s+(\w+)',
            r'\b(\w+)\s+(certified|verified|confirmed|validated)',
            r'\b(official|unofficial|experimental|beta|stable)\s+(\w+)'
        ]
    
    def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities and qualifiers from text"""
        
        entities = {
            'locations': [],
            'types': {},
            'qualifiers': [],
            'key_phrases': []
        }
        
        # Extract locations
        for pattern in self.location_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities['locations'].extend([m for m in matches if len(m) > 2])
        
        # Extract type-specific entities
        for category, patterns in self.type_patterns.items():
            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    if category not in entities['types']:
                        entities['types'][category] = []
                    entities['types'][category].extend(matches)
        
        # Extract qualifiers
        for pattern in self.qualifier_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            entities['qualifiers'].extend(matches)
        
        # Extract key phrases (noun phrases)
        key_phrases = self._extract_key_phrases(text)
        entities['key_phrases'] = key_phrases[:5]  # Top 5
        
        return entities
    
    def _extract_key_phrases(self, text: str) -> List[str]:
        """Extract key noun phrases"""
        
        # Simple noun phrase extraction
        # Pattern: (adjective)* (noun)+
        pattern = r'\b(?:[A-Z][a-z]+\s+)?(?:[a-z]+\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b'
        phrases = re.findall(pattern, text)
        
        # Filter and rank
        filtered = []
        for phrase in phrases:
            if 3 < len(phrase) < 50 and ' ' in phrase:
                filtered.append(phrase)
        
        # Return unique phrases
        return list(dict.fromkeys(filtered))


class MetadataEnricher:
    """Enrich chunks with metadata and context"""
    
    def __init__(self):
        """Initialize enricher"""
        self.entity_extractor = EntityExtractor()
    
    def enrich_chunk(self,
                     chunk_text: str,
                     doc_metadata: Dict[str, Any],
                     chunk_index: int,
                     section_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Enrich chunk with metadata and entity headers.
        
        Args:
            chunk_text: Raw chunk text
            doc_metadata: Document-level metadata
            chunk_index: Index of chunk in document
            section_title: Title of containing section
        
        Returns:
            Enriched chunk dictionary
        """
        
        # Extract entities from chunk
        entities = self.entity_extractor.extract_entities(chunk_text)
        
        # Build chunk header
        header_parts = []
        
        # Add document title if available
        if doc_metadata.get('title'):
            header_parts.append(f"[Document: {doc_metadata['title']}]")
        
        # Add section if available
        if section_title:
            header_parts.append(f"[Section: {section_title}]")
        
        # Add location if found
        if entities['locations']:
            locations_str = ', '.join(entities['locations'][:2])
            header_parts.append(f"[Location: {locations_str}]")
        
        # Add type qualifiers
        for category, values in entities['types'].items():
            if values:
                type_str = ', '.join(set(values[:2]))
                header_parts.append(f"[{category.title()}: {type_str}]")
        
        # Add chunk number
        header_parts.append(f"[Chunk {chunk_index + 1}]")
        
        # Build final header
        header = ' '.join(header_parts)
        
        # Create enriched text with header
        if header:
            enriched_text = f"{header}\n\n{chunk_text}"
        else:
            enriched_text = chunk_text
        
        # Build metadata
        chunk_metadata = {
            'chunk_index': chunk_index,
            'has_header': bool(header),
            'entities': entities,
            'section': section_title,
            **doc_metadata  # Include all doc metadata
        }
        
        return {
            'content': enriched_text,
            'original_content': chunk_text,
            'header': header,
            'metadata': chunk_metadata
        }


class EnhancedChunker:
    """Enhanced chunker with entity qualifiers and smart boundaries"""
    
    def __init__(self, config: Optional[EnhancedChunkConfig] = None):
        """Initialize enhanced chunker"""
        self.config = config or EnhancedChunkConfig()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.metadata_enricher = MetadataEnricher()
    
    def chunk_with_enhancement(self,
                              text: str,
                              doc_id: str,
                              doc_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text with entity enhancement and metadata.
        
        Args:
            text: Document text
            doc_id: Document identifier
            doc_metadata: Document metadata
        
        Returns:
            List of enhanced chunks
        """
        
        if not doc_metadata:
            doc_metadata = {}
        
        # First, identify sections
        sections = self._identify_sections(text)
        
        all_chunks = []
        global_chunk_index = 0
        
        for section in sections:
            # Chunk this section
            section_chunks = self._chunk_section(
                section['text'],
                doc_id,
                section['title']
            )
            
            # Enrich each chunk
            for local_idx, chunk in enumerate(section_chunks):
                enriched = self.metadata_enricher.enrich_chunk(
                    chunk['content'],
                    doc_metadata,
                    global_chunk_index,
                    section['title']
                )
                
                # Add chunk ID
                enriched['id'] = self._generate_chunk_id(
                    doc_id,
                    global_chunk_index,
                    enriched['content']
                )
                
                all_chunks.append(enriched)
                global_chunk_index += 1
        
        return all_chunks
    
    def _identify_sections(self, text: str) -> List[Dict[str, str]]:
        """Identify sections in text"""
        
        sections = []
        
        # Patterns for section headers
        section_patterns = [
            r'^#{1,6}\s+(.+)$',  # Markdown headers
            r'^([A-Z][^.!?]*):$',  # Title case with colon
            r'^\d+\.\s+([A-Z].+)$',  # Numbered sections
            r'^([A-Z\s]+)$',  # All caps headers
        ]
        
        lines = text.split('\n')
        current_section = {'title': 'Introduction', 'text': ''}
        
        for line in lines:
            is_header = False
            
            for pattern in section_patterns:
                match = re.match(pattern, line.strip())
                if match:
                    # Save current section if it has content
                    if current_section['text'].strip():
                        sections.append(current_section)
                    
                    # Start new section
                    current_section = {
                        'title': match.group(1).strip(),
                        'text': ''
                    }
                    is_header = True
                    break
            
            if not is_header:
                current_section['text'] += line + '\n'
        
        # Add last section
        if current_section['text'].strip():
            sections.append(current_section)
        
        # If no sections found, treat entire text as one section
        if not sections:
            sections = [{'title': None, 'text': text}]
        
        return sections
    
    def _chunk_section(self,
                      text: str,
                      doc_id: str,
                      section_title: Optional[str]) -> List[Dict[str, Any]]:
        """Chunk a section of text"""
        
        chunks = []
        sentences = self._split_sentences(text)
        
        if not sentences:
            return []
        
        # Calculate overlap
        overlap_tokens = int(self.config.target_tokens * self.config.overlap_percent)
        
        current_idx = 0
        prev_chunk_text = ""
        
        while current_idx < len(sentences):
            # Build chunk with overlap
            chunk_sentences = []
            
            # Add overlap from previous chunk
            if prev_chunk_text and self.config.overlap_percent > 0:
                overlap_text = self._create_overlap(prev_chunk_text, overlap_tokens)
                if overlap_text:
                    chunk_sentences.append(f"[...{overlap_text[-50:]}]" if len(overlap_text) > 50 else f"[...{overlap_text}]")
            
            # Add sentences until target size
            chunk_text = ' '.join(chunk_sentences)
            remaining_sentences = sentences[current_idx:]
            
            for sent in remaining_sentences:
                test_text = chunk_text + ' ' + sent if chunk_text else sent
                token_count = self._count_tokens(test_text)
                
                if token_count > self.config.max_tokens:
                    break
                
                chunk_sentences.append(sent)
                chunk_text = test_text
                current_idx += 1
                
                if token_count >= self.config.target_tokens:
                    break
            
            # Check minimum size
            if self._count_tokens(chunk_text) < self.config.min_tokens and current_idx < len(sentences):
                # Too small, continue adding
                continue
            
            if chunk_text.strip():
                chunks.append({
                    'content': chunk_text,
                    'section': section_title
                })
                prev_chunk_text = ' '.join(chunk_sentences[1:] if chunk_sentences and chunk_sentences[0].startswith('[...') else chunk_sentences)
        
        return chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        
        # Handle abbreviations
        text = re.sub(r'\s+', ' ', text)
        
        abbreviations = ['Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Sr.', 'Jr.', 'Ph.D.', 'M.D.', 'B.A.', 'M.A.', 'D.D.S.', 'Ph.D', 'Inc.', 'Corp.', 'Co.', 'L.L.C.', 'Ltd.', 'e.g.', 'i.e.', 'etc.', 'vs.']
        for abbr in abbreviations:
            text = text.replace(abbr, abbr.replace('.', '@@@'))
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Restore abbreviations
        sentences = [s.replace('@@@', '.') for s in sentences]
        
        return [s.strip() for s in sentences if s.strip()]
    
    def _create_overlap(self, prev_text: str, overlap_tokens: int) -> str:
        """Create overlap text from previous chunk"""
        
        sentences = self._split_sentences(prev_text)
        overlap_text = ""
        current_tokens = 0
        
        # Build overlap from end of previous chunk
        for sent in reversed(sentences):
            sent_tokens = self._count_tokens(sent)
            if current_tokens + sent_tokens <= overlap_tokens:
                overlap_text = sent + " " + overlap_text
                current_tokens += sent_tokens
            else:
                break
        
        return overlap_text.strip()
    
    def _count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.tokenizer.encode(text))
    
    def _generate_chunk_id(self, doc_id: str, chunk_index: int, content: str) -> str:
        """Generate unique chunk ID"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]  # Use SHA256 instead of MD5
        return f"{doc_id}_chunk_{chunk_index}_{content_hash}"


def create_enhanced_chunker(add_headers: bool = True,
                          overlap: float = 0.15) -> EnhancedChunker:
    """Factory function to create enhanced chunker"""
    
    config = EnhancedChunkConfig(
        add_entity_headers=add_headers,
        overlap_percent=overlap
    )
    
    return EnhancedChunker(config)
#!/usr/bin/env python3
"""
Advanced text chunking with overlap support for RAG pipelines.
Implements smart chunking with configurable overlap and token limits.
"""

import hashlib
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import tiktoken


@dataclass
class ChunkConfig:
    """Configuration for text chunking"""
    min_tokens: int = 300
    max_tokens: int = 700
    target_tokens: int = 500
    overlap_percent: float = 0.15
    preserve_sentences: bool = True
    add_chunk_headers: bool = True


class TextChunker:
    """Advanced text chunker with overlap and smart boundaries"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """Initialize chunker with configuration"""
        self.config = config or ChunkConfig()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        return len(self.tokenizer.encode(text))
    
    def split_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        # Improved sentence splitting with abbreviation handling
        text = re.sub(r'\s+', ' ', text)
        
        # Handle common abbreviations
        abbreviations = ['Dr.', 'Mr.', 'Mrs.', 'Ms.', 'Prof.', 'Sr.', 'Jr.', 'Ph.D.', 'M.D.', 'B.A.', 'M.A.', 'etc.', 'vs.', 'i.e.', 'e.g.']
        for abbr in abbreviations:
            text = text.replace(abbr, abbr.replace('.', '@@@'))
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Restore abbreviations
        sentences = [s.replace('@@@', '.') for s in sentences]
        
        return [s.strip() for s in sentences if s.strip()]
    
    def find_chunk_boundary(self, sentences: List[str], target_tokens: int) -> int:
        """Find optimal chunk boundary near target token count"""
        current_tokens = 0
        best_idx = 0
        best_diff = float('inf')
        
        for i, sentence in enumerate(sentences):
            sentence_tokens = self.count_tokens(sentence)
            current_tokens += sentence_tokens
            
            diff = abs(current_tokens - target_tokens)
            if diff < best_diff:
                best_diff = diff
                best_idx = i + 1
            
            # Stop if we've exceeded max tokens
            if current_tokens > self.config.max_tokens:
                break
        
        return best_idx
    
    def create_overlap(self, prev_chunk: str, overlap_tokens: int) -> str:
        """Create overlap text from previous chunk"""
        if not prev_chunk or overlap_tokens <= 0:
            return ""
        
        sentences = self.split_sentences(prev_chunk)
        overlap_text = ""
        current_tokens = 0
        
        # Build overlap from end of previous chunk
        for sentence in reversed(sentences):
            sentence_tokens = self.count_tokens(sentence)
            if current_tokens + sentence_tokens <= overlap_tokens:
                overlap_text = sentence + " " + overlap_text
                current_tokens += sentence_tokens
            else:
                break
        
        return overlap_text.strip()
    
    def generate_chunk_id(self, doc_id: str, chunk_index: int, content: str) -> str:
        """Generate unique chunk ID"""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]  # Use SHA256 instead of MD5
        return f"{doc_id}_chunk_{chunk_index}_{content_hash}"
    
    def chunk_text(self, 
                   text: str, 
                   doc_id: str,
                   doc_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Chunk text with overlap and metadata.
        
        Args:
            text: Text to chunk
            doc_id: Document identifier
            doc_metadata: Optional metadata to attach to chunks
            
        Returns:
            List of chunk dictionaries with content and metadata
        """
        if not text or not text.strip():
            return []
        
        chunks = []
        sentences = self.split_sentences(text)
        
        if not sentences:
            return []
        
        # Calculate overlap
        overlap_tokens = int(self.config.target_tokens * self.config.overlap_percent)
        
        current_idx = 0
        chunk_index = 0
        prev_chunk_text = ""
        
        while current_idx < len(sentences):
            # Add overlap from previous chunk
            overlap_text = self.create_overlap(prev_chunk_text, overlap_tokens)
            
            # Build current chunk
            chunk_sentences = []
            chunk_text = overlap_text
            
            if overlap_text:
                chunk_sentences.append(f"[...{overlap_text[-50:]}]" if len(overlap_text) > 50 else f"[...{overlap_text}]")
            
            # Add sentences until we reach target tokens
            remaining_sentences = sentences[current_idx:]
            boundary_idx = self.find_chunk_boundary(
                remaining_sentences,
                self.config.target_tokens - self.count_tokens(chunk_text)
            )
            
            if boundary_idx == 0 and current_idx < len(sentences):
                # Force at least one sentence
                boundary_idx = 1
            
            chunk_sentences.extend(remaining_sentences[:boundary_idx])
            chunk_text = " ".join(chunk_sentences)
            
            # Skip if chunk is too small (unless it's the last chunk)
            token_count = self.count_tokens(chunk_text)
            if token_count < self.config.min_tokens and current_idx + boundary_idx < len(sentences):
                # Merge with next chunk
                current_idx += boundary_idx
                continue
            
            # Create chunk metadata
            chunk_id = self.generate_chunk_id(doc_id, chunk_index, chunk_text)
            
            chunk_metadata = {
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "chunk_index": chunk_index,
                "token_count": token_count,
                "has_overlap": bool(overlap_text),
                "start_sentence_idx": current_idx,
                "end_sentence_idx": current_idx + boundary_idx
            }
            
            # Add document metadata if provided
            if doc_metadata:
                chunk_metadata.update({
                    f"doc_{k}": v for k, v in doc_metadata.items()
                    if k not in ["content", "text", "chunks"]
                })
            
            # Add chunk header if configured
            if self.config.add_chunk_headers and doc_metadata and "title" in doc_metadata:
                header = f"[Document: {doc_metadata['title']}] [Chunk {chunk_index + 1}]\n\n"
                chunk_text = header + chunk_text
            
            chunks.append({
                "content": chunk_text,
                "metadata": chunk_metadata
            })
            
            # Update for next iteration
            prev_chunk_text = " ".join(remaining_sentences[:boundary_idx])
            current_idx += boundary_idx
            chunk_index += 1
        
        return chunks
    
    def chunk_documents(self, 
                       documents: List[Dict[str, Any]],
                       content_key: str = "content",
                       id_key: str = "id") -> List[Dict[str, Any]]:
        """
        Chunk multiple documents.
        
        Args:
            documents: List of document dictionaries
            content_key: Key for document content
            id_key: Key for document ID
            
        Returns:
            Flat list of all chunks from all documents
        """
        all_chunks = []
        
        for doc in documents:
            doc_id = doc.get(id_key, f"doc_{hashlib.sha256(str(doc).encode()).hexdigest()[:16]}")
            content = doc.get(content_key, "")
            
            # Extract metadata (everything except content)
            doc_metadata = {k: v for k, v in doc.items() if k != content_key}
            
            chunks = self.chunk_text(content, doc_id, doc_metadata)
            all_chunks.extend(chunks)
        
        return all_chunks


class SemanticChunker(TextChunker):
    """Extended chunker with semantic awareness for better boundaries"""
    
    def __init__(self, config: Optional[ChunkConfig] = None):
        """Initialize semantic chunker"""
        super().__init__(config)
        self.section_markers = [
            r'^#{1,6}\s+',  # Markdown headers
            r'^\d+\.\s+',    # Numbered lists
            r'^[A-Z][^.!?]*:$',  # Section titles
            r'^\s*\n\s*\n',  # Paragraph breaks
        ]
    
    def find_semantic_boundaries(self, text: str) -> List[int]:
        """Find semantic boundaries in text"""
        boundaries = [0]
        
        for pattern in self.section_markers:
            for match in re.finditer(pattern, text, re.MULTILINE):
                boundaries.append(match.start())
        
        boundaries.append(len(text))
        return sorted(set(boundaries))
    
    def chunk_with_sections(self, 
                           text: str,
                           doc_id: str,
                           doc_metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Chunk text respecting section boundaries"""
        boundaries = self.find_semantic_boundaries(text)
        chunks = []
        
        for i in range(len(boundaries) - 1):
            section_text = text[boundaries[i]:boundaries[i + 1]].strip()
            if section_text:
                # Check if section needs further chunking
                token_count = self.count_tokens(section_text)
                
                if token_count <= self.config.max_tokens:
                    # Keep section as single chunk
                    chunk_id = self.generate_chunk_id(doc_id, len(chunks), section_text)
                    chunks.append({
                        "content": section_text,
                        "metadata": {
                            "chunk_id": chunk_id,
                            "doc_id": doc_id,
                            "chunk_index": len(chunks),
                            "token_count": token_count,
                            "is_section": True,
                            **(doc_metadata or {})
                        }
                    })
                else:
                    # Further chunk the section - fix indexing to continue from current count
                    section_chunks = self.chunk_text(section_text, doc_id, doc_metadata)
                    for chunk in section_chunks:
                        chunk["metadata"]["parent_section"] = i
                        # Fix chunk index to continue from current count instead of restarting
                        chunk["metadata"]["chunk_index"] = len(chunks)
                        # Update chunk ID to reflect correct index
                        chunk["metadata"]["chunk_id"] = self.generate_chunk_id(doc_id, len(chunks), chunk["content"])
                        chunks.append(chunk)
        
        return chunks


def create_chunker(chunker_type: str = "basic", config: Optional[ChunkConfig] = None) -> TextChunker:
    """Factory function to create appropriate chunker"""
    if chunker_type == "semantic":
        return SemanticChunker(config)
    else:
        return TextChunker(config)


# Convenience functions for direct use
def chunk_text(text: str, 
               doc_id: str = "default",
               min_tokens: int = 300,
               max_tokens: int = 700,
               overlap_percent: float = 0.15) -> List[Dict[str, Any]]:
    """Convenience function for quick chunking"""
    config = ChunkConfig(
        min_tokens=min_tokens,
        max_tokens=max_tokens,
        overlap_percent=overlap_percent
    )
    chunker = TextChunker(config)
    return chunker.chunk_text(text, doc_id)


def chunk_markdown(markdown_text: str,
                  doc_id: str = "default",
                  preserve_structure: bool = True) -> List[Dict[str, Any]]:
    """Chunk markdown text with structure awareness"""
    if preserve_structure:
        chunker = SemanticChunker()
        return chunker.chunk_with_sections(markdown_text, doc_id)
    else:
        chunker = TextChunker()
        return chunker.chunk_text(markdown_text, doc_id)
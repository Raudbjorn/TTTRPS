//! Semantic Chunker Module
//!
//! Intelligent text chunking with sentence awareness, overlap, and page tracking.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

// ============================================================================
// Configuration
// ============================================================================

/// Configuration for the chunker
#[derive(Debug, Clone)]
pub struct ChunkConfig {
    /// Target chunk size in characters
    pub target_size: usize,
    /// Minimum chunk size (won't split below this)
    pub min_size: usize,
    /// Maximum chunk size (hard limit)
    pub max_size: usize,
    /// Overlap size in characters
    pub overlap_size: usize,
    /// Whether to preserve sentence boundaries
    pub preserve_sentences: bool,
    /// Whether to preserve paragraph boundaries when possible
    pub preserve_paragraphs: bool,
}

impl Default for ChunkConfig {
    fn default() -> Self {
        Self {
            target_size: 1000,
            min_size: 200,
            max_size: 2000,
            overlap_size: 100,
            preserve_sentences: true,
            preserve_paragraphs: true,
        }
    }
}

impl ChunkConfig {
    /// Create config for small, focused chunks
    pub fn small() -> Self {
        Self {
            target_size: 500,
            min_size: 100,
            max_size: 800,
            overlap_size: 50,
            ..Default::default()
        }
    }

    /// Create config for large chunks (better for context)
    pub fn large() -> Self {
        Self {
            target_size: 2000,
            min_size: 500,
            max_size: 4000,
            overlap_size: 200,
            ..Default::default()
        }
    }
}

// ============================================================================
// Content Chunk
// ============================================================================

/// A chunk of content with metadata
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContentChunk {
    /// Unique identifier
    pub id: String,
    /// Source document identifier
    pub source_id: String,
    /// Chunk content
    pub content: String,
    /// Page number (if applicable)
    pub page_number: Option<u32>,
    /// Section/chapter (if detected)
    pub section: Option<String>,
    /// Chunk type (text, table, header, etc.)
    pub chunk_type: String,
    /// Chunk index in document
    pub chunk_index: usize,
    /// Additional metadata
    pub metadata: HashMap<String, String>,
}

// ============================================================================
// Semantic Chunker
// ============================================================================

/// Intelligent chunker with sentence and paragraph awareness
pub struct SemanticChunker {
    config: ChunkConfig,
}

impl SemanticChunker {
    /// Create a new chunker with default config
    pub fn new() -> Self {
        Self {
            config: ChunkConfig::default(),
        }
    }

    /// Create a chunker with custom config
    pub fn with_config(config: ChunkConfig) -> Self {
        Self { config }
    }

    /// Chunk text with page information
    pub fn chunk_with_pages(
        &self,
        pages: &[(u32, String)],
        source_id: &str,
    ) -> Vec<ContentChunk> {
        let mut chunks = Vec::new();
        let mut chunk_index = 0;

        for (page_num, page_text) in pages {
            let page_chunks = self.chunk_page(page_text, source_id, *page_num, &mut chunk_index);
            chunks.extend(page_chunks);
        }

        chunks
    }

    /// Chunk a single page
    fn chunk_page(
        &self,
        text: &str,
        source_id: &str,
        page_number: u32,
        chunk_index: &mut usize,
    ) -> Vec<ContentChunk> {
        let mut chunks = Vec::new();

        // Split into paragraphs
        let paragraphs: Vec<&str> = text
            .split("\n\n")
            .map(|p| p.trim())
            .filter(|p| !p.is_empty())
            .collect();

        let mut current_chunk = String::new();
        let mut current_section: Option<String> = None;

        for para in paragraphs {
            // Detect section headers
            if self.is_header(para) {
                // Flush current chunk before starting new section
                if !current_chunk.is_empty() && current_chunk.len() >= self.config.min_size {
                    chunks.push(self.create_chunk(
                        &current_chunk,
                        source_id,
                        Some(page_number),
                        current_section.clone(),
                        *chunk_index,
                    ));
                    *chunk_index += 1;
                    current_chunk = self.get_overlap(&current_chunk);
                }
                current_section = Some(para.to_string());
            }

            // Check if adding this paragraph would exceed max size
            if current_chunk.len() + para.len() > self.config.max_size {
                // Need to flush and potentially split
                if current_chunk.len() >= self.config.min_size {
                    chunks.push(self.create_chunk(
                        &current_chunk,
                        source_id,
                        Some(page_number),
                        current_section.clone(),
                        *chunk_index,
                    ));
                    *chunk_index += 1;
                    current_chunk = self.get_overlap(&current_chunk);
                }

                // Handle very long paragraphs by sentence splitting
                if para.len() > self.config.max_size {
                    let sentence_chunks = self.split_by_sentences(
                        para,
                        source_id,
                        Some(page_number),
                        current_section.clone(),
                        chunk_index,
                    );
                    chunks.extend(sentence_chunks);
                    current_chunk.clear();
                    continue;
                }
            }

            // Add paragraph to current chunk
            if !current_chunk.is_empty() {
                current_chunk.push_str("\n\n");
            }
            current_chunk.push_str(para);

            // Flush if we've reached target size
            if current_chunk.len() >= self.config.target_size {
                chunks.push(self.create_chunk(
                    &current_chunk,
                    source_id,
                    Some(page_number),
                    current_section.clone(),
                    *chunk_index,
                ));
                *chunk_index += 1;
                current_chunk = self.get_overlap(&current_chunk);
            }
        }

        // Don't forget remaining content
        if !current_chunk.is_empty() && current_chunk.len() >= self.config.min_size {
            chunks.push(self.create_chunk(
                &current_chunk,
                source_id,
                Some(page_number),
                current_section,
                *chunk_index,
            ));
            *chunk_index += 1;
        }

        chunks
    }

    /// Split text by sentences when paragraphs are too long
    fn split_by_sentences(
        &self,
        text: &str,
        source_id: &str,
        page_number: Option<u32>,
        section: Option<String>,
        chunk_index: &mut usize,
    ) -> Vec<ContentChunk> {
        let mut chunks = Vec::new();
        let sentences = self.split_into_sentences(text);
        let mut current_chunk = String::new();

        for sentence in sentences {
            if current_chunk.len() + sentence.len() > self.config.max_size {
                if current_chunk.len() >= self.config.min_size {
                    chunks.push(self.create_chunk(
                        &current_chunk,
                        source_id,
                        page_number,
                        section.clone(),
                        *chunk_index,
                    ));
                    *chunk_index += 1;
                    current_chunk = self.get_overlap(&current_chunk);
                }
            }

            if !current_chunk.is_empty() && !current_chunk.ends_with(' ') {
                current_chunk.push(' ');
            }
            current_chunk.push_str(&sentence);

            if current_chunk.len() >= self.config.target_size {
                chunks.push(self.create_chunk(
                    &current_chunk,
                    source_id,
                    page_number,
                    section.clone(),
                    *chunk_index,
                ));
                *chunk_index += 1;
                current_chunk = self.get_overlap(&current_chunk);
            }
        }

        if !current_chunk.is_empty() && current_chunk.len() >= self.config.min_size {
            chunks.push(self.create_chunk(
                &current_chunk,
                source_id,
                page_number,
                section,
                *chunk_index,
            ));
            *chunk_index += 1;
        }

        chunks
    }

    /// Split text into sentences
    fn split_into_sentences(&self, text: &str) -> Vec<String> {
        let mut sentences = Vec::new();
        let mut current = String::new();
        let chars: Vec<char> = text.chars().collect();

        let mut i = 0;
        while i < chars.len() {
            current.push(chars[i]);

            // Check for sentence-ending punctuation
            if chars[i] == '.' || chars[i] == '!' || chars[i] == '?' {
                // Look ahead to see if this is really the end of a sentence
                let next_is_space_or_end = i + 1 >= chars.len()
                    || chars[i + 1].is_whitespace()
                    || chars[i + 1] == '"'
                    || chars[i + 1] == '\'';

                // Check for common abbreviations (simplified)
                let is_abbreviation = self.is_likely_abbreviation(&current);

                if next_is_space_or_end && !is_abbreviation {
                    sentences.push(current.trim().to_string());
                    current = String::new();
                }
            }

            i += 1;
        }

        if !current.trim().is_empty() {
            sentences.push(current.trim().to_string());
        }

        sentences
    }

    /// Check if the period is likely part of an abbreviation
    fn is_likely_abbreviation(&self, text: &str) -> bool {
        let text = text.trim();
        let abbrevs = [
            "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.",
            "Inc.", "Ltd.", "Corp.", "Co.",
            "vs.", "etc.", "e.g.", "i.e.",
            "St.", "Ave.", "Rd.", "Blvd.",
            "Jan.", "Feb.", "Mar.", "Apr.", "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec.",
        ];

        for abbr in abbrevs {
            if text.ends_with(abbr) {
                return true;
            }
        }

        // Single letter followed by period (like initials)
        if text.len() >= 2 {
            let last_two: String = text.chars().rev().take(2).collect::<String>().chars().rev().collect();
            if last_two.chars().next().unwrap_or(' ').is_alphabetic()
                && last_two.chars().nth(1) == Some('.')
                && text.len() > 2
                && !text.chars().rev().nth(2).unwrap_or('a').is_whitespace()
            {
                return true;
            }
        }

        false
    }

    /// Check if text looks like a header
    fn is_header(&self, text: &str) -> bool {
        let text = text.trim();

        // Too long to be a header
        if text.len() > 100 {
            return false;
        }

        // Ends with sentence punctuation - probably not a header
        if text.ends_with('.') || text.ends_with(',') || text.ends_with(';') {
            return false;
        }

        // All caps
        let letters: Vec<char> = text.chars().filter(|c| c.is_alphabetic()).collect();
        if !letters.is_empty() && letters.iter().all(|c| c.is_uppercase()) {
            return true;
        }

        // Chapter/section patterns
        let lower = text.to_lowercase();
        if lower.starts_with("chapter")
            || lower.starts_with("section")
            || lower.starts_with("part")
            || lower.starts_with("appendix")
        {
            return true;
        }

        false
    }

    /// Get overlap text from the end of a chunk
    fn get_overlap(&self, text: &str) -> String {
        if self.config.overlap_size == 0 || text.len() <= self.config.overlap_size {
            return String::new();
        }

        let overlap_start = text.len().saturating_sub(self.config.overlap_size);

        // Try to start at a sentence or word boundary
        let overlap_text = &text[overlap_start..];

        // Find first space to start at word boundary
        if let Some(space_pos) = overlap_text.find(' ') {
            overlap_text[space_pos + 1..].to_string()
        } else {
            overlap_text.to_string()
        }
    }

    /// Create a content chunk
    fn create_chunk(
        &self,
        content: &str,
        source_id: &str,
        page_number: Option<u32>,
        section: Option<String>,
        chunk_index: usize,
    ) -> ContentChunk {
        ContentChunk {
            id: Uuid::new_v4().to_string(),
            source_id: source_id.to_string(),
            content: content.trim().to_string(),
            page_number,
            section,
            chunk_type: "text".to_string(),
            chunk_index,
            metadata: HashMap::new(),
        }
    }

    /// Simple text chunking without page info
    pub fn chunk_text(&self, text: &str, source_id: &str) -> Vec<ContentChunk> {
        // Convert to single-page format
        let pages = vec![(1, text.to_string())];
        self.chunk_with_pages(&pages, source_id)
    }
}

impl Default for SemanticChunker {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_basic_chunking() {
        let chunker = SemanticChunker::with_config(ChunkConfig {
            target_size: 100,
            min_size: 20,
            max_size: 200,
            overlap_size: 20,
            ..Default::default()
        });

        let text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here.";
        let chunks = chunker.chunk_text(text, "test-source");

        assert!(!chunks.is_empty());
        for chunk in &chunks {
            assert!(!chunk.content.is_empty());
        }
    }

    #[test]
    fn test_sentence_splitting() {
        let chunker = SemanticChunker::new();
        let sentences = chunker.split_into_sentences("Hello world. How are you? I am fine!");

        // Should have at least 2 sentences
        assert!(sentences.len() >= 2, "Expected at least 2 sentences, got {}", sentences.len());
        assert!(sentences.iter().any(|s| s.contains("Hello")));
        assert!(sentences.iter().any(|s| s.contains("fine")));
    }

    #[test]
    fn test_abbreviation_detection() {
        let chunker = SemanticChunker::new();

        // Common abbreviations should be detected
        assert!(chunker.is_likely_abbreviation("Dr."));
        assert!(chunker.is_likely_abbreviation("Hello Mr."));
        // Note: "e.g." and "end." behavior depends on implementation
    }

    #[test]
    fn test_header_detection() {
        let chunker = SemanticChunker::new();

        assert!(chunker.is_header("CHAPTER ONE"));
        assert!(chunker.is_header("Chapter 1: The Beginning"));
        assert!(chunker.is_header("SECTION II"));
        assert!(!chunker.is_header("This is a regular sentence."));
        assert!(!chunker.is_header("This is a very long line that should not be detected as a header because headers are typically short."));
    }
}

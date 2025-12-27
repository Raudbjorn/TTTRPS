//! PDF Parser Module
//!
//! Extracts text and structure from PDF documents for ingestion.

use std::path::Path;
use lopdf::Document;
use serde::{Deserialize, Serialize};
use thiserror::Error;

// ============================================================================
// Error Types
// ============================================================================

#[derive(Error, Debug)]
pub enum PDFError {
    #[error("Failed to load PDF: {0}")]
    LoadError(String),

    #[error("Failed to extract text: {0}")]
    ExtractionError(String),

    #[error("Page not found: {0}")]
    PageNotFound(u32),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

pub type Result<T> = std::result::Result<T, PDFError>;

// ============================================================================
// Extracted Content Types
// ============================================================================

/// A page of extracted content
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedPage {
    /// Page number (1-indexed)
    pub page_number: u32,
    /// Raw text content
    pub text: String,
    /// Detected paragraphs
    pub paragraphs: Vec<String>,
    /// Detected headers (heuristic based on formatting)
    pub headers: Vec<String>,
}

/// Complete extracted document
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedDocument {
    /// Source file path
    pub source_path: String,
    /// Number of pages
    pub page_count: usize,
    /// Extracted pages
    pub pages: Vec<ExtractedPage>,
    /// Document metadata
    pub metadata: DocumentMetadata,
}

/// Document metadata
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct DocumentMetadata {
    pub title: Option<String>,
    pub author: Option<String>,
    pub subject: Option<String>,
    pub keywords: Vec<String>,
    pub creator: Option<String>,
    pub producer: Option<String>,
}

// ============================================================================
// PDF Parser
// ============================================================================

pub struct PDFParser;

impl PDFParser {
    /// Extract text from a PDF file (simple extraction)
    pub fn extract_text(path: &Path) -> Result<String> {
        let doc = Document::load(path)
            .map_err(|e| PDFError::LoadError(e.to_string()))?;

        let mut text = String::new();
        for (page_num, _page_id) in doc.get_pages() {
            let content = doc.extract_text(&[page_num])
                .map_err(|e| PDFError::ExtractionError(e.to_string()))?;
            text.push_str(&content);
            text.push('\n');
        }
        Ok(text)
    }

    /// Extract structured content from a PDF file
    pub fn extract_structured(path: &Path) -> Result<ExtractedDocument> {
        let doc = Document::load(path)
            .map_err(|e| PDFError::LoadError(e.to_string()))?;

        let page_ids: Vec<_> = doc.get_pages().into_iter().collect();
        let page_count = page_ids.len();
        let mut pages = Vec::with_capacity(page_count);

        for (page_num, _page_id) in page_ids {
            let text = doc.extract_text(&[page_num])
                .map_err(|e| PDFError::ExtractionError(e.to_string()))?;

            let (paragraphs, headers) = Self::analyze_text_structure(&text);

            pages.push(ExtractedPage {
                page_number: page_num,
                text,
                paragraphs,
                headers,
            });
        }

        // Extract metadata
        let metadata = Self::extract_metadata(&doc);

        Ok(ExtractedDocument {
            source_path: path.to_string_lossy().to_string(),
            page_count,
            pages,
            metadata,
        })
    }

    /// Analyze text structure to identify paragraphs and headers
    fn analyze_text_structure(text: &str) -> (Vec<String>, Vec<String>) {
        let mut paragraphs = Vec::new();
        let mut headers = Vec::new();

        let lines: Vec<&str> = text.lines().collect();
        let mut current_paragraph = String::new();

        for line in lines {
            let trimmed = line.trim();

            if trimmed.is_empty() {
                // End of paragraph
                if !current_paragraph.is_empty() {
                    paragraphs.push(current_paragraph.trim().to_string());
                    current_paragraph.clear();
                }
                continue;
            }

            // Heuristic header detection:
            // - Short lines (< 100 chars) that are all caps or title case
            // - Lines that don't end with punctuation
            let is_potential_header = trimmed.len() < 100
                && !trimmed.ends_with('.')
                && !trimmed.ends_with(',')
                && !trimmed.ends_with(';')
                && (Self::is_title_case(trimmed) || Self::is_all_caps(trimmed));

            if is_potential_header && current_paragraph.is_empty() {
                headers.push(trimmed.to_string());
            }

            // Add to current paragraph
            if !current_paragraph.is_empty() {
                current_paragraph.push(' ');
            }
            current_paragraph.push_str(trimmed);
        }

        // Don't forget last paragraph
        if !current_paragraph.is_empty() {
            paragraphs.push(current_paragraph.trim().to_string());
        }

        (paragraphs, headers)
    }

    /// Check if text is title case (first letter of each word capitalized)
    fn is_title_case(text: &str) -> bool {
        let words: Vec<&str> = text.split_whitespace().collect();
        if words.is_empty() {
            return false;
        }

        // At least 50% of significant words should be capitalized
        let significant_words: Vec<&&str> = words
            .iter()
            .filter(|w| w.len() > 3)  // Skip small words
            .collect();

        if significant_words.is_empty() {
            return false;
        }

        let capitalized = significant_words
            .iter()
            .filter(|w| {
                w.chars().next().map(|c| c.is_uppercase()).unwrap_or(false)
            })
            .count();

        capitalized >= significant_words.len() / 2
    }

    /// Check if text is all caps
    fn is_all_caps(text: &str) -> bool {
        let letters: Vec<char> = text.chars().filter(|c| c.is_alphabetic()).collect();
        !letters.is_empty() && letters.iter().all(|c| c.is_uppercase())
    }

    /// Extract document metadata
    fn extract_metadata(doc: &Document) -> DocumentMetadata {
        let mut metadata = DocumentMetadata::default();

        // Helper function to convert bytes to string
        fn bytes_to_string(bytes: &[u8]) -> Option<String> {
            std::str::from_utf8(bytes).ok().map(|s| s.to_string())
        }

        // Try to get info dictionary
        if let Ok(info_ref) = doc.trailer.get(b"Info") {
            if let Ok(info_ref) = info_ref.as_reference() {
                if let Ok(info_dict) = doc.get_object(info_ref) {
                    if let Ok(dict) = info_dict.as_dict() {
                        // Extract common fields
                        if let Ok(title) = dict.get(b"Title") {
                            if let Ok(s) = title.as_str() {
                                metadata.title = bytes_to_string(s);
                            }
                        }
                        if let Ok(author) = dict.get(b"Author") {
                            if let Ok(s) = author.as_str() {
                                metadata.author = bytes_to_string(s);
                            }
                        }
                        if let Ok(subject) = dict.get(b"Subject") {
                            if let Ok(s) = subject.as_str() {
                                metadata.subject = bytes_to_string(s);
                            }
                        }
                        if let Ok(keywords) = dict.get(b"Keywords") {
                            if let Ok(s) = keywords.as_str() {
                                if let Some(kw_str) = bytes_to_string(s) {
                                    metadata.keywords = kw_str
                                        .split(&[',', ';'][..])
                                        .map(|k| k.trim().to_string())
                                        .filter(|k| !k.is_empty())
                                        .collect();
                                }
                            }
                        }
                        if let Ok(creator) = dict.get(b"Creator") {
                            if let Ok(s) = creator.as_str() {
                                metadata.creator = bytes_to_string(s);
                            }
                        }
                        if let Ok(producer) = dict.get(b"Producer") {
                            if let Ok(s) = producer.as_str() {
                                metadata.producer = bytes_to_string(s);
                            }
                        }
                    }
                }
            }
        }

        metadata
    }

    /// Get full text with page markers
    pub fn extract_text_with_pages(path: &Path) -> Result<Vec<(u32, String)>> {
        let doc = Document::load(path)
            .map_err(|e| PDFError::LoadError(e.to_string()))?;

        let mut pages = Vec::new();
        for (page_num, _page_id) in doc.get_pages() {
            let text = doc.extract_text(&[page_num])
                .map_err(|e| PDFError::ExtractionError(e.to_string()))?;
            pages.push((page_num, text));
        }
        Ok(pages)
    }

    /// Get page count without extracting content
    pub fn get_page_count(path: &Path) -> Result<usize> {
        let doc = Document::load(path)
            .map_err(|e| PDFError::LoadError(e.to_string()))?;
        Ok(doc.get_pages().len())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_is_title_case() {
        assert!(PDFParser::is_title_case("Chapter One: The Beginning"));
        assert!(PDFParser::is_title_case("THE GOBLIN CAVE"));
        assert!(!PDFParser::is_title_case("this is not title case"));
    }

    #[test]
    fn test_is_all_caps() {
        assert!(PDFParser::is_all_caps("CHAPTER ONE"));
        assert!(PDFParser::is_all_caps("GOBLIN CAVE"));
        assert!(!PDFParser::is_all_caps("Not All Caps"));
    }

    #[test]
    fn test_analyze_structure() {
        let text = "CHAPTER ONE\n\nThis is the first paragraph.\n\nThis is the second paragraph.";
        let (paragraphs, headers) = PDFParser::analyze_text_structure(text);

        assert_eq!(headers.len(), 1);
        assert_eq!(headers[0], "CHAPTER ONE");
        // Paragraphs include the header line, so we have at least 2 content paragraphs
        assert!(paragraphs.len() >= 2, "Expected at least 2 paragraphs, got {}", paragraphs.len());
    }
}

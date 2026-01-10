//! PDF Parser Module
//!
//! Extracts text and structure from PDF documents for ingestion.
//! Supports fallback extraction when primary parser fails or produces garbled output.

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

    #[error("Password required for encrypted PDF")]
    PasswordRequired,

    #[error("Invalid password for PDF")]
    InvalidPassword,

    #[error("Fallback extraction failed: {0}")]
    FallbackFailed(String),
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

    // ========================================================================
    // Enhanced Extraction with Fallback (Task 0.1, 0.2)
    // ========================================================================

    /// Extract with automatic fallback if lopdf fails or produces low-quality output.
    ///
    /// This method tries the primary `lopdf` extraction first, validates the output
    /// quality, and falls back to `pdf-extract` if the result is garbled or empty.
    ///
    /// # Arguments
    /// * `path` - Path to the PDF file
    /// * `password` - Optional password for encrypted PDFs
    ///
    /// # Returns
    /// * `Result<ExtractedDocument>` - The extracted document or an error
    pub fn extract_with_fallback(
        path: &Path,
        password: Option<&str>,
    ) -> Result<ExtractedDocument> {
        // Try lopdf first
        match Self::extract_structured_with_password(path, password) {
            Ok(doc) => {
                // Validate extraction quality
                if Self::is_extraction_quality_acceptable(&doc) {
                    log::info!("lopdf extraction succeeded for {:?}", path);
                    return Ok(doc);
                }
                log::warn!(
                    "lopdf extraction quality low for {:?}, trying fallback",
                    path
                );
            }
            Err(e) => {
                log::warn!("lopdf failed for {:?}: {}, trying fallback", path, e);
            }
        }

        // Fallback to pdf-extract
        Self::extract_with_pdf_extract(path)
    }

    /// Extract structured content with optional password support.
    ///
    /// # Arguments
    /// * `path` - Path to the PDF file
    /// * `password` - Optional password for encrypted PDFs
    pub fn extract_structured_with_password(
        path: &Path,
        password: Option<&str>,
    ) -> Result<ExtractedDocument> {
        // Load the document
        let mut doc = match Document::load(path) {
            Ok(doc) => doc,
            Err(e) => {
                let err_str = e.to_string();
                // lopdf may throw error when loading encrypted PDF without password
                if err_str.contains("encrypted") || err_str.contains("password") {
                    return Err(PDFError::PasswordRequired);
                }
                return Err(PDFError::LoadError(err_str));
            }
        };

        // Check if document is encrypted and handle decryption
        if doc.is_encrypted() {
            match password {
                Some(pwd) => {
                    doc.decrypt(pwd).map_err(|e| {
                        let err_str = e.to_string();
                        if err_str.contains("password") || err_str.contains("decrypt") {
                            PDFError::InvalidPassword
                        } else {
                            PDFError::LoadError(format!("Decryption failed: {}", e))
                        }
                    })?;
                }
                None => {
                    return Err(PDFError::PasswordRequired);
                }
            }
        }

        Self::extract_from_document(doc, path)
    }

    /// Check extraction quality by analyzing the ratio of printable characters.
    ///
    /// Returns `true` if the extraction produced usable text, `false` if the
    /// output appears garbled (high ratio of non-printable characters).
    fn is_extraction_quality_acceptable(doc: &ExtractedDocument) -> bool {
        let total_text: String = doc.pages.iter()
            .map(|p| p.text.as_str())
            .collect();

        if total_text.is_empty() {
            return false;
        }

        // Check for high ratio of non-printable/garbled characters
        let total_chars = total_text.len();
        let printable_count = total_text.chars()
            .filter(|c| {
                c.is_ascii_alphanumeric()
                    || c.is_ascii_punctuation()
                    || c.is_whitespace()
                    // Allow common Unicode characters (accented letters, etc.)
                    || c.is_alphabetic()
            })
            .count();

        let printable_ratio = printable_count as f32 / total_chars as f32;

        // Also check for reasonable word structure
        let word_count = total_text.split_whitespace().count();
        let avg_word_len = if word_count > 0 {
            total_text.split_whitespace()
                .map(|w| w.len())
                .sum::<usize>() as f32 / word_count as f32
        } else {
            0.0
        };

        // Quality criteria:
        // - At least 85% printable characters
        // - Average word length between 2 and 15 (catches garbled output)
        // - At least some words extracted
        printable_ratio > 0.85
            && avg_word_len > 2.0
            && avg_word_len < 15.0
            && word_count > 10
    }

    /// Fallback extraction using the `pdf-extract` crate.
    ///
    /// This is used when `lopdf` fails or produces garbled output. Note that
    /// `pdf-extract` doesn't preserve page boundaries, so the result will be
    /// a single-page document.
    fn extract_with_pdf_extract(path: &Path) -> Result<ExtractedDocument> {
        let bytes = std::fs::read(path)?;
        let text = pdf_extract::extract_text_from_mem(&bytes)
            .map_err(|e| PDFError::FallbackFailed(format!("pdf-extract failed: {}", e)))?;

        if text.trim().is_empty() {
            return Err(PDFError::FallbackFailed(
                "pdf-extract returned empty content".to_string()
            ));
        }

        let (paragraphs, headers) = Self::analyze_text_structure(&text);

        // pdf-extract doesn't preserve page boundaries, create single-page doc
        Ok(ExtractedDocument {
            source_path: path.to_string_lossy().to_string(),
            page_count: 1,
            pages: vec![ExtractedPage {
                page_number: 1,
                text: text.clone(),
                paragraphs,
                headers,
            }],
            metadata: DocumentMetadata::default(),
        })
    }

    /// Internal helper to extract from a loaded Document.
    fn extract_from_document(doc: Document, path: &Path) -> Result<ExtractedDocument> {
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

        let metadata = Self::extract_metadata(&doc);

        Ok(ExtractedDocument {
            source_path: path.to_string_lossy().to_string(),
            page_count,
            pages,
            metadata,
        })
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

    #[test]
    fn test_extraction_quality_acceptable() {
        // Good quality extraction
        let good_doc = ExtractedDocument {
            source_path: "test.pdf".to_string(),
            page_count: 1,
            pages: vec![ExtractedPage {
                page_number: 1,
                text: "This is a good quality extraction with normal English text. It has multiple sentences and proper structure. The words are of reasonable length and everything looks fine.".to_string(),
                paragraphs: vec![],
                headers: vec![],
            }],
            metadata: DocumentMetadata::default(),
        };
        assert!(PDFParser::is_extraction_quality_acceptable(&good_doc));

        // Empty extraction
        let empty_doc = ExtractedDocument {
            source_path: "test.pdf".to_string(),
            page_count: 1,
            pages: vec![ExtractedPage {
                page_number: 1,
                text: "".to_string(),
                paragraphs: vec![],
                headers: vec![],
            }],
            metadata: DocumentMetadata::default(),
        };
        assert!(!PDFParser::is_extraction_quality_acceptable(&empty_doc));

        // Garbled extraction (mostly non-printable characters)
        let garbled_doc = ExtractedDocument {
            source_path: "test.pdf".to_string(),
            page_count: 1,
            pages: vec![ExtractedPage {
                page_number: 1,
                text: "□□□□□□□□□□□□□□□□□□□□".to_string(),
                paragraphs: vec![],
                headers: vec![],
            }],
            metadata: DocumentMetadata::default(),
        };
        assert!(!PDFParser::is_extraction_quality_acceptable(&garbled_doc));
    }
}

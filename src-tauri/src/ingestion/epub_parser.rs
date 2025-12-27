//! EPUB Parser Module
//!
//! Extracts text and structure from EPUB ebook files for ingestion.

use std::path::Path;
use epub::doc::EpubDoc;
use serde::{Deserialize, Serialize};
use thiserror::Error;

// ============================================================================
// Error Types
// ============================================================================

#[derive(Error, Debug)]
pub enum EPUBError {
    #[error("Failed to load EPUB: {0}")]
    LoadError(String),

    #[error("Failed to read chapter: {0}")]
    ChapterError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

pub type Result<T> = std::result::Result<T, EPUBError>;

// ============================================================================
// Extracted Content Types
// ============================================================================

/// A chapter of extracted content
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedChapter {
    /// Chapter index (0-indexed)
    pub index: usize,
    /// Chapter title (if available)
    pub title: Option<String>,
    /// Raw text content (HTML stripped)
    pub text: String,
    /// Detected paragraphs
    pub paragraphs: Vec<String>,
}

/// Complete extracted EPUB
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedEPUB {
    /// Source file path
    pub source_path: String,
    /// Book title
    pub title: Option<String>,
    /// Author(s)
    pub authors: Vec<String>,
    /// Publisher
    pub publisher: Option<String>,
    /// Description
    pub description: Option<String>,
    /// Number of chapters
    pub chapter_count: usize,
    /// Extracted chapters
    pub chapters: Vec<ExtractedChapter>,
}

// ============================================================================
// EPUB Parser
// ============================================================================

pub struct EPUBParser;

impl EPUBParser {
    /// Extract text from an EPUB file (simple extraction)
    pub fn extract_text(path: &Path) -> Result<String> {
        let mut doc = EpubDoc::new(path)
            .map_err(|e| EPUBError::LoadError(e.to_string()))?;

        let mut text = String::new();
        let chapter_count = doc.get_num_chapters();

        for i in 0..chapter_count {
            doc.set_current_chapter(i);
            if let Some((content, _mime)) = doc.get_current_str() {
                let stripped = Self::strip_html(&content);
                text.push_str(&stripped);
                text.push_str("\n\n");
            }
        }

        Ok(text)
    }

    /// Extract structured content from an EPUB file
    pub fn extract_structured(path: &Path) -> Result<ExtractedEPUB> {
        let mut doc = EpubDoc::new(path)
            .map_err(|e| EPUBError::LoadError(e.to_string()))?;

        // Extract metadata
        let title = doc.mdata("title").map(|m| m.value.clone());
        let authors = doc.mdata("creator")
            .map(|m| vec![m.value.clone()])
            .unwrap_or_default();
        let publisher = doc.mdata("publisher").map(|m| m.value.clone());
        let description = doc.mdata("description").map(|m| m.value.clone());

        // Extract chapters
        let chapter_count = doc.get_num_chapters();
        let mut chapters = Vec::with_capacity(chapter_count);

        for i in 0..chapter_count {
            doc.set_current_chapter(i);

            let chapter_title = doc.get_current_id().map(|id| id.to_string());

            if let Some((content, _mime)) = doc.get_current_str() {
                let text = Self::strip_html(&content);
                let paragraphs = Self::extract_paragraphs(&text);

                chapters.push(ExtractedChapter {
                    index: i,
                    title: chapter_title,
                    text,
                    paragraphs,
                });
            }
        }

        Ok(ExtractedEPUB {
            source_path: path.to_string_lossy().to_string(),
            title,
            authors,
            publisher,
            description,
            chapter_count: chapters.len(),
            chapters,
        })
    }

    /// Strip HTML tags from content
    fn strip_html(html: &str) -> String {
        let mut result = String::with_capacity(html.len());
        let mut in_tag = false;
        let mut in_script = false;
        let mut in_style = false;

        let lower = html.to_lowercase();
        let chars: Vec<char> = html.chars().collect();
        let lower_chars: Vec<char> = lower.chars().collect();

        let mut i = 0;
        while i < chars.len() {
            let c = chars[i];

            // Check for script/style start
            if !in_tag && i + 7 < lower_chars.len() {
                let next7: String = lower_chars[i..i + 7].iter().collect();
                if next7 == "<script" {
                    in_script = true;
                } else if next7 == "<style " || (i + 6 < lower_chars.len() && lower_chars[i..i + 6].iter().collect::<String>() == "<style") {
                    in_style = true;
                }
            }

            // Check for script/style end
            if in_script && i + 9 <= lower_chars.len() {
                let next9: String = lower_chars[i..i + 9].iter().collect();
                if next9 == "</script>" {
                    in_script = false;
                    i += 9;
                    continue;
                }
            }
            if in_style && i + 8 <= lower_chars.len() {
                let next8: String = lower_chars[i..i + 8].iter().collect();
                if next8 == "</style>" {
                    in_style = false;
                    i += 8;
                    continue;
                }
            }

            if in_script || in_style {
                i += 1;
                continue;
            }

            if c == '<' {
                in_tag = true;

                // Add space for block elements
                if i + 2 < lower_chars.len() {
                    let tag_start: String = lower_chars[i + 1..std::cmp::min(i + 10, lower_chars.len())].iter().collect();
                    if tag_start.starts_with("p")
                        || tag_start.starts_with("/p")
                        || tag_start.starts_with("br")
                        || tag_start.starts_with("div")
                        || tag_start.starts_with("/div")
                        || tag_start.starts_with("h1")
                        || tag_start.starts_with("h2")
                        || tag_start.starts_with("h3")
                        || tag_start.starts_with("h4")
                        || tag_start.starts_with("h5")
                        || tag_start.starts_with("h6")
                        || tag_start.starts_with("/h")
                        || tag_start.starts_with("li")
                        || tag_start.starts_with("/li")
                    {
                        if !result.ends_with('\n') && !result.ends_with(' ') {
                            result.push('\n');
                        }
                    }
                }
            } else if c == '>' {
                in_tag = false;
            } else if !in_tag {
                result.push(c);
            }

            i += 1;
        }

        // Decode common HTML entities
        result = result
            .replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", "\"")
            .replace("&#39;", "'")
            .replace("&apos;", "'")
            .replace("&mdash;", "—")
            .replace("&ndash;", "–")
            .replace("&hellip;", "…");

        // Clean up whitespace
        let lines: Vec<&str> = result.lines()
            .map(|l| l.trim())
            .filter(|l| !l.is_empty())
            .collect();

        lines.join("\n")
    }

    /// Extract paragraphs from text
    fn extract_paragraphs(text: &str) -> Vec<String> {
        text.split("\n\n")
            .map(|p| p.trim().to_string())
            .filter(|p| !p.is_empty())
            .collect()
    }

    /// Get chapter count without extracting content
    pub fn get_chapter_count(path: &Path) -> Result<usize> {
        let doc = EpubDoc::new(path)
            .map_err(|e| EPUBError::LoadError(e.to_string()))?;
        Ok(doc.get_num_chapters())
    }

    /// Extract text from a specific chapter
    pub fn extract_chapter(path: &Path, chapter_index: usize) -> Result<String> {
        let mut doc = EpubDoc::new(path)
            .map_err(|e| EPUBError::LoadError(e.to_string()))?;

        if chapter_index >= doc.get_num_chapters() {
            return Err(EPUBError::ChapterError(format!(
                "Chapter {} not found (max: {})",
                chapter_index,
                doc.get_num_chapters() - 1
            )));
        }

        doc.set_current_chapter(chapter_index);

        match doc.get_current_str() {
            Some((content, _)) => Ok(Self::strip_html(&content)),
            None => Err(EPUBError::ChapterError(format!(
                "Could not read chapter {}",
                chapter_index
            ))),
        }
    }

    /// Get book metadata without extracting content
    pub fn get_metadata(path: &Path) -> Result<(Option<String>, Vec<String>)> {
        let doc = EpubDoc::new(path)
            .map_err(|e| EPUBError::LoadError(e.to_string()))?;

        let title = doc.mdata("title").map(|m| m.value.clone());
        let authors = doc.mdata("creator")
            .map(|m| vec![m.value.clone()])
            .unwrap_or_default();

        Ok((title, authors))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strip_html() {
        let html = "<p>Hello <b>world</b>!</p><p>Second paragraph.</p>";
        let result = EPUBParser::strip_html(html);
        assert!(result.contains("Hello"));
        assert!(result.contains("world"));
        assert!(!result.contains("<"));
        assert!(!result.contains(">"));
    }

    #[test]
    fn test_strip_html_entities() {
        let html = "Hello&nbsp;world &amp; friends";
        let result = EPUBParser::strip_html(html);
        assert_eq!(result, "Hello world & friends");
    }

    #[test]
    fn test_extract_paragraphs() {
        let text = "First paragraph.\n\nSecond paragraph.\n\nThird.";
        let paragraphs = EPUBParser::extract_paragraphs(text);
        assert_eq!(paragraphs.len(), 3);
    }
}

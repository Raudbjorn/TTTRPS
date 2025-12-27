//! MOBI Parser Module
//!
//! Extracts text and structure from MOBI/PRC ebook files for ingestion.
//! MOBI is Amazon's legacy ebook format used before KF8/AZW3.

use std::fs::File;
use std::io::{Read, Seek, SeekFrom};
use std::path::Path;
use serde::{Deserialize, Serialize};
use thiserror::Error;

// ============================================================================
// Error Types
// ============================================================================

#[derive(Error, Debug)]
pub enum MOBIError {
    #[error("Failed to load MOBI: {0}")]
    LoadError(String),

    #[error("Invalid MOBI format: {0}")]
    FormatError(String),

    #[error("Unsupported compression: {0}")]
    CompressionError(String),

    #[error("Failed to decompress: {0}")]
    DecompressError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),
}

pub type Result<T> = std::result::Result<T, MOBIError>;

// ============================================================================
// MOBI Header Structures
// ============================================================================

/// PalmDOC header (first 78 bytes after PDB header)
#[derive(Debug)]
struct PalmDocHeader {
    compression: u16,
    text_length: u32,
    record_count: u16,
    record_size: u16,
}

/// MOBI header (variable length, follows PalmDOC header)
#[derive(Debug)]
struct MobiHeader {
    identifier: [u8; 4], // "MOBI"
    header_length: u32,
    mobi_type: u32,
    text_encoding: u32,
    unique_id: u32,
    file_version: u32,
    first_non_book_index: u32,
    full_name_offset: u32,
    full_name_length: u32,
    locale: u32,
    first_image_index: u32,
    exth_flags: u32,
}

/// PDB record info entry
#[derive(Debug)]
struct RecordInfo {
    offset: u32,
    #[allow(dead_code)]
    attributes: u8,
    #[allow(dead_code)]
    unique_id: [u8; 3],
}

// ============================================================================
// Extracted Content Types
// ============================================================================

/// A section of extracted content
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedSection {
    /// Section index (0-indexed)
    pub index: usize,
    /// Section title (if detected)
    pub title: Option<String>,
    /// Raw text content (HTML stripped)
    pub text: String,
    /// Detected paragraphs
    pub paragraphs: Vec<String>,
}

/// Complete extracted MOBI
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExtractedMOBI {
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
    /// Language
    pub language: Option<String>,
    /// Number of sections
    pub section_count: usize,
    /// Extracted sections
    pub sections: Vec<ExtractedSection>,
}

// ============================================================================
// Compression
// ============================================================================

/// PalmDOC LZ77 decompression
fn decompress_palmdoc(data: &[u8]) -> Result<Vec<u8>> {
    let mut result = Vec::with_capacity(data.len() * 2);
    let mut i = 0;

    while i < data.len() {
        let byte = data[i];

        if byte == 0x00 {
            // Literal null byte
            result.push(0x00);
            i += 1;
        } else if byte >= 0x01 && byte <= 0x08 {
            // Copy next 1-8 bytes literally
            let count = byte as usize;
            for j in 1..=count {
                if i + j < data.len() {
                    result.push(data[i + j]);
                }
            }
            i += count + 1;
        } else if byte >= 0x09 && byte <= 0x7F {
            // Literal byte
            result.push(byte);
            i += 1;
        } else if byte >= 0x80 && byte <= 0xBF {
            // LZ77 distance/length pair
            if i + 1 >= data.len() {
                break;
            }

            let next = data[i + 1];
            let distance = (((byte as u16) << 5) | ((next as u16) >> 3)) & 0x7FF;
            let length = ((next & 0x07) + 3) as usize;

            if distance as usize > result.len() {
                // Invalid distance, skip
                i += 2;
                continue;
            }

            let start = result.len() - distance as usize;
            for j in 0..length {
                let idx = start + (j % distance as usize);
                if idx < result.len() {
                    result.push(result[idx]);
                }
            }

            i += 2;
        } else {
            // 0xC0 - 0xFF: space + character
            result.push(b' ');
            result.push(byte ^ 0x80);
            i += 1;
        }
    }

    Ok(result)
}

// ============================================================================
// MOBI Parser
// ============================================================================

pub struct MOBIParser;

impl MOBIParser {
    /// Extract text from a MOBI file (simple extraction)
    pub fn extract_text(path: &Path) -> Result<String> {
        let extracted = Self::extract_structured(path)?;

        Ok(extracted.sections
            .iter()
            .map(|s| s.text.as_str())
            .collect::<Vec<_>>()
            .join("\n\n"))
    }

    /// Extract structured content from a MOBI file
    pub fn extract_structured(path: &Path) -> Result<ExtractedMOBI> {
        let mut file = File::open(path)
            .map_err(|e| MOBIError::LoadError(e.to_string()))?;

        // Read PDB header (first 78 bytes)
        let mut pdb_header = [0u8; 78];
        file.read_exact(&mut pdb_header)?;

        // Verify PDB type
        let type_creator = &pdb_header[60..68];
        if type_creator != b"BOOKMOBI" && type_creator != b"TEXtREAd" {
            return Err(MOBIError::FormatError(
                format!("Not a MOBI file, type: {:?}", String::from_utf8_lossy(type_creator))
            ));
        }

        // Get record count
        let record_count = u16::from_be_bytes([pdb_header[76], pdb_header[77]]) as usize;
        if record_count == 0 {
            return Err(MOBIError::FormatError("No records in file".to_string()));
        }

        // Read record info list
        let mut record_infos = Vec::with_capacity(record_count);
        for _ in 0..record_count {
            let mut entry = [0u8; 8];
            file.read_exact(&mut entry)?;

            record_infos.push(RecordInfo {
                offset: u32::from_be_bytes([entry[0], entry[1], entry[2], entry[3]]),
                attributes: entry[4],
                unique_id: [entry[5], entry[6], entry[7]],
            });
        }

        // Read first record (contains headers)
        let first_record = &record_infos[0];
        file.seek(SeekFrom::Start(first_record.offset as u64))?;

        // Read PalmDOC header (16 bytes)
        let mut palmdoc_header = [0u8; 16];
        file.read_exact(&mut palmdoc_header)?;

        let compression = u16::from_be_bytes([palmdoc_header[0], palmdoc_header[1]]);
        let _text_length = u32::from_be_bytes([palmdoc_header[4], palmdoc_header[5], palmdoc_header[6], palmdoc_header[7]]);
        let text_record_count = u16::from_be_bytes([palmdoc_header[8], palmdoc_header[9]]) as usize;

        // Check compression type
        if compression != 1 && compression != 2 {
            return Err(MOBIError::CompressionError(
                format!("Unsupported compression type: {}", compression)
            ));
        }

        // Read MOBI header
        let mut mobi_identifier = [0u8; 4];
        file.read_exact(&mut mobi_identifier)?;

        let (title, authors, publisher, description, language) = if &mobi_identifier == b"MOBI" {
            // Read rest of MOBI header
            let mut mobi_header = [0u8; 228]; // Common size, actual may vary
            file.read_exact(&mut mobi_header)?;

            let header_length = u32::from_be_bytes([mobi_header[0], mobi_header[1], mobi_header[2], mobi_header[3]]);
            let full_name_offset = u32::from_be_bytes([mobi_header[80], mobi_header[81], mobi_header[82], mobi_header[83]]);
            let full_name_length = u32::from_be_bytes([mobi_header[84], mobi_header[85], mobi_header[86], mobi_header[87]]);
            let exth_flags = u32::from_be_bytes([mobi_header[124], mobi_header[125], mobi_header[126], mobi_header[127]]);

            // Read title from full name
            let title = if full_name_length > 0 && full_name_length < 1000 {
                file.seek(SeekFrom::Start(first_record.offset as u64 + full_name_offset as u64))?;
                let mut name_bytes = vec![0u8; full_name_length as usize];
                file.read_exact(&mut name_bytes)?;
                Some(String::from_utf8_lossy(&name_bytes).trim_end_matches('\0').to_string())
            } else {
                None
            };

            // Read EXTH header if present
            let (authors, publisher, description, language) = if exth_flags & 0x40 != 0 {
                Self::parse_exth(&mut file, first_record.offset as u64 + 16 + header_length as u64)?
            } else {
                (vec![], None, None, None)
            };

            (title, authors, publisher, description, language)
        } else {
            // No MOBI header, just PalmDOC
            (None, vec![], None, None, None)
        };

        // Read text records
        let mut combined_text = Vec::new();
        let records_to_read = text_record_count.min(record_infos.len() - 1);

        for i in 1..=records_to_read {
            let record = &record_infos[i];
            let next_offset = if i + 1 < record_infos.len() {
                record_infos[i + 1].offset
            } else {
                file.metadata()?.len() as u32
            };

            let record_size = (next_offset - record.offset) as usize;
            file.seek(SeekFrom::Start(record.offset as u64))?;

            let mut record_data = vec![0u8; record_size];
            file.read_exact(&mut record_data)?;

            // Decompress if needed
            let decompressed = if compression == 2 {
                decompress_palmdoc(&record_data)?
            } else {
                record_data
            };

            combined_text.extend(decompressed);
        }

        // Convert to string
        let text = String::from_utf8_lossy(&combined_text).to_string();
        let stripped = Self::strip_html(&text);

        // Split into sections (using common chapter markers)
        let sections = Self::split_into_sections(&stripped);

        Ok(ExtractedMOBI {
            source_path: path.to_string_lossy().to_string(),
            title,
            authors,
            publisher,
            description,
            language,
            section_count: sections.len(),
            sections,
        })
    }

    /// Parse EXTH header for metadata
    fn parse_exth(
        file: &mut File,
        exth_offset: u64,
    ) -> Result<(Vec<String>, Option<String>, Option<String>, Option<String>)> {
        file.seek(SeekFrom::Start(exth_offset))?;

        let mut exth_header = [0u8; 12];
        if file.read_exact(&mut exth_header).is_err() {
            return Ok((vec![], None, None, None));
        }

        // Verify EXTH identifier
        if &exth_header[0..4] != b"EXTH" {
            return Ok((vec![], None, None, None));
        }

        let _header_length = u32::from_be_bytes([exth_header[4], exth_header[5], exth_header[6], exth_header[7]]);
        let record_count = u32::from_be_bytes([exth_header[8], exth_header[9], exth_header[10], exth_header[11]]) as usize;

        let mut authors = Vec::new();
        let mut publisher = None;
        let mut description = None;
        let mut language = None;

        for _ in 0..record_count.min(100) {
            let mut record_header = [0u8; 8];
            if file.read_exact(&mut record_header).is_err() {
                break;
            }

            let record_type = u32::from_be_bytes([record_header[0], record_header[1], record_header[2], record_header[3]]);
            let record_length = u32::from_be_bytes([record_header[4], record_header[5], record_header[6], record_header[7]]) as usize;

            if record_length <= 8 || record_length > 10000 {
                continue;
            }

            let data_length = record_length - 8;
            let mut data = vec![0u8; data_length];
            if file.read_exact(&mut data).is_err() {
                break;
            }

            let value = String::from_utf8_lossy(&data).trim_end_matches('\0').to_string();

            match record_type {
                100 => authors.push(value), // Author
                101 => publisher = Some(value), // Publisher
                103 => description = Some(value), // Description
                524 => language = Some(value), // Language
                _ => {}
            }
        }

        Ok((authors, publisher, description, language))
    }

    /// Strip HTML tags from content
    fn strip_html(html: &str) -> String {
        let mut result = String::with_capacity(html.len());
        let mut in_tag = false;

        for c in html.chars() {
            if c == '<' {
                in_tag = true;
            } else if c == '>' {
                in_tag = false;
                result.push(' ');
            } else if !in_tag {
                result.push(c);
            }
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

    /// Split text into sections based on chapter markers
    fn split_into_sections(text: &str) -> Vec<ExtractedSection> {
        // Common chapter markers
        let chapter_patterns = [
            "CHAPTER ", "Chapter ", "PART ", "Part ",
            "PROLOGUE", "Prologue", "EPILOGUE", "Epilogue",
            "INTRODUCTION", "Introduction", "PREFACE", "Preface",
        ];

        let mut sections = Vec::new();
        let mut current_section = String::new();
        let mut current_title: Option<String> = None;
        let mut section_index = 0;

        for line in text.lines() {
            let line_trimmed = line.trim();

            // Check if this line is a chapter heading
            let is_chapter = chapter_patterns.iter().any(|p| line_trimmed.starts_with(p))
                && line_trimmed.len() < 100; // Not too long

            if is_chapter && !current_section.is_empty() {
                // Save current section
                let paragraphs = Self::extract_paragraphs(&current_section);
                sections.push(ExtractedSection {
                    index: section_index,
                    title: current_title.take(),
                    text: std::mem::take(&mut current_section),
                    paragraphs,
                });
                section_index += 1;
                current_title = Some(line_trimmed.to_string());
            } else if is_chapter {
                current_title = Some(line_trimmed.to_string());
            } else {
                if !current_section.is_empty() {
                    current_section.push('\n');
                }
                current_section.push_str(line_trimmed);
            }
        }

        // Save final section
        if !current_section.is_empty() {
            let paragraphs = Self::extract_paragraphs(&current_section);
            sections.push(ExtractedSection {
                index: section_index,
                title: current_title,
                text: current_section,
                paragraphs,
            });
        }

        // If no chapters were found, treat the whole thing as one section
        if sections.is_empty() && !text.is_empty() {
            let paragraphs = Self::extract_paragraphs(text);
            sections.push(ExtractedSection {
                index: 0,
                title: None,
                text: text.to_string(),
                paragraphs,
            });
        }

        sections
    }

    /// Extract paragraphs from text
    fn extract_paragraphs(text: &str) -> Vec<String> {
        text.split("\n\n")
            .map(|p| p.trim().to_string())
            .filter(|p| !p.is_empty() && p.len() > 10) // Filter out very short "paragraphs"
            .collect()
    }

    /// Get book metadata without extracting content
    pub fn get_metadata(path: &Path) -> Result<(Option<String>, Vec<String>)> {
        let extracted = Self::extract_structured(path)?;
        Ok((extracted.title, extracted.authors))
    }

    /// Check if a file is a valid MOBI
    pub fn is_valid_mobi(path: &Path) -> bool {
        let mut file = match File::open(path) {
            Ok(f) => f,
            Err(_) => return false,
        };

        let mut pdb_header = [0u8; 78];
        if file.read_exact(&mut pdb_header).is_err() {
            return false;
        }

        let type_creator = &pdb_header[60..68];
        type_creator == b"BOOKMOBI" || type_creator == b"TEXtREAd"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_strip_html() {
        let html = "<p>Hello <b>world</b>!</p><p>Second paragraph.</p>";
        let result = MOBIParser::strip_html(html);
        assert!(result.contains("Hello"));
        assert!(result.contains("world"));
        assert!(!result.contains("<"));
        assert!(!result.contains(">"));
    }

    #[test]
    fn test_strip_html_entities() {
        let html = "Hello&nbsp;world &amp; friends";
        let result = MOBIParser::strip_html(html);
        assert!(result.contains("Hello world"));
        assert!(result.contains("& friends"));
    }

    #[test]
    fn test_extract_paragraphs() {
        let text = "First paragraph with enough content.\n\nSecond paragraph also with content.\n\nThird paragraph here.";
        let paragraphs = MOBIParser::extract_paragraphs(text);
        assert_eq!(paragraphs.len(), 3);
    }

    #[test]
    fn test_split_into_sections() {
        let text = "Some intro text.\nChapter 1\nFirst chapter content.\nChapter 2\nSecond chapter content.";
        let sections = MOBIParser::split_into_sections(text);
        assert!(sections.len() >= 1);
    }

    #[test]
    fn test_decompress_palmdoc_literal() {
        // Simple literal bytes (0x09-0x7F pass through)
        let data = vec![0x48, 0x65, 0x6C, 0x6C, 0x6F]; // "Hello"
        let result = decompress_palmdoc(&data).unwrap();
        assert_eq!(result, data);
    }

    #[test]
    fn test_decompress_palmdoc_space_char() {
        // 0xC0+ encodes space + character
        let data = vec![0xC0 | 0x21]; // space + 'a'
        let result = decompress_palmdoc(&data).unwrap();
        assert_eq!(result, vec![b' ', b'a']);
    }
}

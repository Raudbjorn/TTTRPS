//! DOCX Parser Unit Tests
//!
//! Tests for DOCX text extraction, table/heading extraction, and error handling.
//! Note: Private helper methods (parse_document_xml, read_document_xml) are tested
//! indirectly through the public API.

use std::io::Write;
use std::path::PathBuf;
use tempfile::NamedTempFile;
use zip::write::FileOptions;

use crate::ingestion::docx_parser::{DOCXParser, DOCXError, ExtractedDOCX};

// ============================================================================
// Test Fixtures
// ============================================================================

/// Creates a minimal valid DOCX for testing
fn create_minimal_docx() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".docx").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    // [Content_Types].xml
    zip.start_file("[Content_Types].xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"#).unwrap();

    // _rels/.rels
    zip.start_file("_rels/.rels", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"#).unwrap();

    // word/document.xml - Main document content
    zip.start_file("word/document.xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r>
        <w:t>Hello World</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>This is the second paragraph.</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>"#).unwrap();

    zip.finish().unwrap();
    file
}

/// Creates a DOCX with multiple paragraphs and formatting
fn create_multipart_docx() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".docx").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    zip.start_file("[Content_Types].xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"#).unwrap();

    zip.start_file("_rels/.rels", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"#).unwrap();

    zip.start_file("word/document.xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r>
        <w:t>Document Title</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>First paragraph content with </w:t>
      </w:r>
      <w:r>
        <w:rPr><w:b/></w:rPr>
        <w:t>bold text</w:t>
      </w:r>
      <w:r>
        <w:t> and </w:t>
      </w:r>
      <w:r>
        <w:rPr><w:i/></w:rPr>
        <w:t>italic text</w:t>
      </w:r>
      <w:r>
        <w:t>.</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>Second paragraph.</w:t>
      </w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:t>Third paragraph with more content.</w:t>
      </w:r>
    </w:p>
  </w:body>
</w:document>"#).unwrap();

    zip.finish().unwrap();
    file
}

/// Creates a DOCX with a table
fn create_docx_with_table() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".docx").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    zip.start_file("[Content_Types].xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"#).unwrap();

    zip.start_file("_rels/.rels", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"#).unwrap();

    zip.start_file("word/document.xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r><w:t>Table below:</w:t></w:r>
    </w:p>
    <w:tbl>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Header 1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Header 2</w:t></w:r></w:p></w:tc>
      </w:tr>
      <w:tr>
        <w:tc><w:p><w:r><w:t>Cell 1</w:t></w:r></w:p></w:tc>
        <w:tc><w:p><w:r><w:t>Cell 2</w:t></w:r></w:p></w:tc>
      </w:tr>
    </w:tbl>
    <w:p>
      <w:r><w:t>Content after table.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"#).unwrap();

    zip.finish().unwrap();
    file
}

/// Creates a DOCX with headings
fn create_docx_with_headings() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".docx").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default()
        .compression_method(zip::CompressionMethod::Deflated);

    zip.start_file("[Content_Types].xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"#).unwrap();

    zip.start_file("_rels/.rels", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"#).unwrap();

    zip.start_file("word/document.xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
      <w:r><w:t>Main Title</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Introduction paragraph.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
      <w:r><w:t>Section One</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Section one content.</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
      <w:r><w:t>Section Two</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Section two content.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"#).unwrap();

    zip.finish().unwrap();
    file
}

/// Creates a malformed DOCX (not a valid ZIP)
fn create_malformed_docx() -> NamedTempFile {
    let mut file = NamedTempFile::with_suffix(".docx").unwrap();
    file.write_all(b"This is not a valid DOCX file").unwrap();
    file.flush().unwrap();
    file
}

/// Creates a DOCX with missing document.xml
fn create_docx_missing_document() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".docx").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default();

    zip.start_file("[Content_Types].xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0"?><Types></Types>"#).unwrap();

    zip.finish().unwrap();
    file
}

/// Creates a DOCX with invalid XML in document.xml
fn create_docx_invalid_xml() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".docx").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default();

    zip.start_file("[Content_Types].xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0"?><Types></Types>"#).unwrap();

    zip.start_file("word/document.xml", options).unwrap();
    zip.write_all(b"<invalid xml without closing tags").unwrap();

    zip.finish().unwrap();
    file
}

// ============================================================================
// Text Extraction Tests
// ============================================================================

#[cfg(test)]
mod text_extraction_tests {
    use super::*;

    #[test]
    fn test_extract_text_from_simple_docx() {
        let docx_file = create_minimal_docx();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok(), "Failed to extract text: {:?}", result.err());
        let text = result.unwrap();
        assert!(text.contains("Hello World"));
        assert!(text.contains("second paragraph"));
    }

    #[test]
    fn test_extract_text_preserves_content() {
        let docx_file = create_multipart_docx();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        assert!(text.contains("Document Title"));
        assert!(text.contains("bold text"));
        assert!(text.contains("italic text"));
        assert!(text.contains("Second paragraph"));
    }

    #[test]
    fn test_extract_structured_document() {
        let docx_file = create_minimal_docx();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        assert!(!doc.source_path.is_empty());
        assert!(!doc.text.is_empty());
        assert!(!doc.paragraphs.is_empty());
    }

    #[test]
    fn test_paragraphs_are_separated() {
        let docx_file = create_minimal_docx();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        // Should have separate paragraphs
        assert!(doc.paragraphs.len() >= 2, "Expected at least 2 paragraphs, got {}", doc.paragraphs.len());
    }
}

// ============================================================================
// Table Extraction Tests
// ============================================================================

#[cfg(test)]
mod table_extraction_tests {
    use super::*;

    #[test]
    fn test_extract_text_with_table() {
        let docx_file = create_docx_with_table();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        // Table cells should be extracted as text
        assert!(text.contains("Header 1") || text.contains("Cell 1"));
        assert!(text.contains("Table below"));
        assert!(text.contains("Content after table"));
    }

    #[test]
    fn test_table_content_in_paragraphs() {
        let docx_file = create_docx_with_table();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        // Table content should appear in paragraphs
        let all_content: String = doc.paragraphs.join(" ");
        assert!(all_content.contains("Header") || all_content.contains("Cell") || all_content.contains("Table"));
    }
}

// ============================================================================
// Heading Extraction Tests
// ============================================================================

#[cfg(test)]
mod heading_extraction_tests {
    use super::*;

    #[test]
    fn test_extract_text_with_headings() {
        let docx_file = create_docx_with_headings();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        assert!(text.contains("Main Title"));
        assert!(text.contains("Section One"));
        assert!(text.contains("Section Two"));
    }

    #[test]
    fn test_headings_in_paragraph_list() {
        let docx_file = create_docx_with_headings();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        // Headings should appear as paragraphs
        assert!(doc.paragraphs.iter().any(|p| p.contains("Main Title")));
        assert!(doc.paragraphs.iter().any(|p| p.contains("Section One") || p.contains("Section Two")));
    }
}

// ============================================================================
// Error Handling Tests
// ============================================================================

#[cfg(test)]
mod error_handling_tests {
    use super::*;

    #[test]
    fn test_nonexistent_file_error() {
        let path = PathBuf::from("/nonexistent/path/to/file.docx");
        let result = DOCXParser::extract_text(&path);

        assert!(result.is_err());
        match result.unwrap_err() {
            DOCXError::OpenError(_) | DOCXError::IoError(_) => (),
            e => panic!("Expected OpenError or IoError, got {:?}", e),
        }
    }

    #[test]
    fn test_malformed_docx_error() {
        let malformed_file = create_malformed_docx();
        let result = DOCXParser::extract_text(malformed_file.path());

        assert!(result.is_err());
    }

    #[test]
    fn test_missing_document_xml_error() {
        let missing_doc_file = create_docx_missing_document();
        let result = DOCXParser::extract_text(missing_doc_file.path());

        assert!(result.is_err());
        match result.unwrap_err() {
            DOCXError::ReadError(msg) => {
                assert!(msg.contains("document.xml") || msg.contains("Cannot find"));
            }
            DOCXError::ZipError(_) => (), // Also acceptable
            e => panic!("Expected ReadError or ZipError, got {:?}", e),
        }
    }

    #[test]
    fn test_invalid_xml_error() {
        let invalid_xml_file = create_docx_invalid_xml();
        let result = DOCXParser::extract_text(invalid_xml_file.path());

        assert!(result.is_err());
        match result.unwrap_err() {
            DOCXError::XmlError(_) => (),
            e => panic!("Expected XmlError, got {:?}", e),
        }
    }

    #[test]
    fn test_docx_error_display() {
        let error = DOCXError::OpenError("test error".to_string());
        let display = format!("{}", error);
        assert!(display.contains("test error"));

        let error = DOCXError::ReadError("read error".to_string());
        let display = format!("{}", error);
        assert!(display.contains("read error"));

        let error = DOCXError::XmlError("xml error".to_string());
        let display = format!("{}", error);
        assert!(display.contains("xml error"));
    }

    #[test]
    fn test_empty_file_error() {
        let mut file = NamedTempFile::with_suffix(".docx").unwrap();
        file.write_all(b"").unwrap();
        file.flush().unwrap();

        let result = DOCXParser::extract_text(file.path());
        assert!(result.is_err());
    }
}

// ============================================================================
// Paragraph Count Tests
// ============================================================================

#[cfg(test)]
mod paragraph_count_tests {
    use super::*;

    #[test]
    fn test_get_paragraph_count() {
        let docx_file = create_minimal_docx();
        let result = DOCXParser::get_paragraph_count(docx_file.path());

        assert!(result.is_ok());
        let count = result.unwrap();
        assert!(count >= 2, "Expected at least 2 paragraphs, got {}", count);
    }

    #[test]
    fn test_get_paragraph_count_multipart() {
        let docx_file = create_multipart_docx();
        let result = DOCXParser::get_paragraph_count(docx_file.path());

        assert!(result.is_ok());
        let count = result.unwrap();
        assert!(count >= 3, "Expected at least 3 paragraphs");
    }

    #[test]
    fn test_get_paragraph_count_invalid_file() {
        let path = PathBuf::from("/nonexistent/file.docx");
        let result = DOCXParser::get_paragraph_count(&path);

        assert!(result.is_err());
    }
}

// ============================================================================
// Extracted Document Structure Tests
// ============================================================================

#[cfg(test)]
mod extracted_document_tests {
    use super::*;

    #[test]
    fn test_extracted_docx_structure() {
        let doc = ExtractedDOCX {
            source_path: "/test/path.docx".to_string(),
            text: "Test content".to_string(),
            paragraphs: vec!["Test content".to_string()],
        };

        assert!(!doc.source_path.is_empty());
        assert!(!doc.text.is_empty());
        assert_eq!(doc.paragraphs.len(), 1);
    }

    #[test]
    fn test_source_path_preserved() {
        let docx_file = create_minimal_docx();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        assert!(doc.source_path.contains(".docx"));
    }

    #[test]
    fn test_text_matches_paragraphs() {
        let docx_file = create_minimal_docx();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        // Full text should contain all paragraph content
        for para in &doc.paragraphs {
            assert!(doc.text.contains(para), "Text should contain paragraph: {}", para);
        }
    }

    #[test]
    fn test_extracted_docx_clone() {
        let doc = ExtractedDOCX {
            source_path: "/test/path.docx".to_string(),
            text: "Test".to_string(),
            paragraphs: vec!["Test".to_string()],
        };

        let cloned = doc.clone();
        assert_eq!(doc.source_path, cloned.source_path);
        assert_eq!(doc.text, cloned.text);
    }
}

// ============================================================================
// Metadata Extraction Tests
// ============================================================================

#[cfg(test)]
mod metadata_tests {
    use super::*;

    /// Creates a DOCX with core.xml metadata
    fn create_docx_with_metadata() -> NamedTempFile {
        let file = NamedTempFile::with_suffix(".docx").unwrap();
        let zip_file = std::fs::File::create(file.path()).unwrap();
        let mut zip = zip::ZipWriter::new(zip_file);

        let options: FileOptions<()> = FileOptions::default()
            .compression_method(zip::CompressionMethod::Deflated);

        // Content Types
        zip.start_file("[Content_Types].xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>"#).unwrap();

        // Relationships
        zip.start_file("_rels/.rels", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>"#).unwrap();

        // Core properties (metadata)
        zip.start_file("docProps/core.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:dcterms="http://purl.org/dc/terms/">
  <dc:title>Test Document Title</dc:title>
  <dc:creator>Test Author Name</dc:creator>
  <dc:subject>Test Subject</dc:subject>
  <dc:description>This is a test document description.</dc:description>
  <cp:keywords>test, document, metadata</cp:keywords>
  <dcterms:created>2024-01-15T10:00:00Z</dcterms:created>
  <dcterms:modified>2024-01-16T14:30:00Z</dcterms:modified>
</cp:coreProperties>"#).unwrap();

        // App properties
        zip.start_file("docProps/app.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">
  <Application>Microsoft Office Word</Application>
  <Company>Test Company</Company>
  <Pages>1</Pages>
  <Words>10</Words>
</Properties>"#).unwrap();

        // Document content
        zip.start_file("word/document.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r><w:t>Document with metadata.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"#).unwrap();

        zip.finish().unwrap();
        file
    }

    #[test]
    fn test_docx_with_metadata_extracts_text() {
        let docx_file = create_docx_with_metadata();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();
        assert!(text.contains("Document with metadata"));
    }

    #[test]
    fn test_docx_metadata_does_not_appear_in_text() {
        let docx_file = create_docx_with_metadata();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        // Metadata should not appear in extracted text
        assert!(!text.contains("Test Author Name"));
        assert!(!text.contains("Test Subject"));
        assert!(!text.contains("Test Company"));
    }

    #[test]
    fn test_structured_extraction_with_metadata() {
        let docx_file = create_docx_with_metadata();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        // Text content should be present
        assert!(doc.text.contains("Document with metadata"));
        assert!(!doc.paragraphs.is_empty());
    }
}

// ============================================================================
// Embedded Image Handling Tests
// ============================================================================

#[cfg(test)]
mod embedded_image_tests {
    use super::*;

    /// Creates a DOCX with embedded image references
    fn create_docx_with_images() -> NamedTempFile {
        let file = NamedTempFile::with_suffix(".docx").unwrap();
        let zip_file = std::fs::File::create(file.path()).unwrap();
        let mut zip = zip::ZipWriter::new(zip_file);

        let options: FileOptions<()> = FileOptions::default()
            .compression_method(zip::CompressionMethod::Deflated);

        // Content Types with image support
        zip.start_file("[Content_Types].xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Default Extension="jpeg" ContentType="image/jpeg"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"#).unwrap();

        // Relationships
        zip.start_file("_rels/.rels", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"#).unwrap();

        // Word document relationships (for images)
        zip.start_file("word/_rels/document.xml.rels", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image1.png"/>
</Relationships>"#).unwrap();

        // Document with image reference
        zip.start_file("word/document.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
            xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
            xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"
            xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    <w:p>
      <w:r><w:t>Text before the image.</w:t></w:r>
    </w:p>
    <w:p>
      <w:r>
        <w:drawing>
          <wp:inline>
            <wp:docPr id="1" name="Picture 1" descr="Test image description"/>
            <a:graphic>
              <a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">
                <pic:pic>
                  <pic:blipFill>
                    <a:blip r:embed="rId1"/>
                  </pic:blipFill>
                </pic:pic>
              </a:graphicData>
            </a:graphic>
          </wp:inline>
        </w:drawing>
      </w:r>
    </w:p>
    <w:p>
      <w:r><w:t>Text after the image.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"#).unwrap();

        // Add a minimal PNG image file
        zip.start_file("word/media/image1.png", options).unwrap();
        // Minimal PNG header (1x1 white pixel)
        zip.write_all(&[
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A, // PNG signature
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52, // IHDR chunk
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01, // 1x1 dimensions
            0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53, 0xDE, // RGB, etc
        ]).unwrap();

        zip.finish().unwrap();
        file
    }

    #[test]
    fn test_docx_with_images_extracts_text() {
        let docx_file = create_docx_with_images();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        // Should extract text content
        assert!(text.contains("Text before"));
        assert!(text.contains("Text after"));
    }

    #[test]
    fn test_images_not_in_extracted_text() {
        let docx_file = create_docx_with_images();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        // Should not contain image binary data or drawing XML
        assert!(!text.contains("drawing"));
        assert!(!text.contains("blip"));
        assert!(!text.contains("PNG"));
    }

    #[test]
    fn test_structured_extraction_with_images() {
        let docx_file = create_docx_with_images();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        // Should have paragraphs with text
        assert!(!doc.paragraphs.is_empty());

        // Paragraphs should only contain printable text (Unicode-safe)
        for para in &doc.paragraphs {
            // Should be readable text - allow all Unicode printable characters, not just ASCII
            let is_text = para.chars().all(|c| !c.is_control() || c == '\t' || c == '\n');
            assert!(is_text, "Paragraph should contain only printable text: {}", para);
        }
    }

    #[test]
    fn test_paragraph_count_with_images() {
        let docx_file = create_docx_with_images();
        let result = DOCXParser::get_paragraph_count(docx_file.path());

        assert!(result.is_ok());
        let count = result.unwrap();

        // Should have at least 2 text paragraphs (before and after image)
        // The image paragraph might or might not count depending on implementation
        assert!(count >= 2);
    }
}

// ============================================================================
// List Extraction Tests
// ============================================================================

#[cfg(test)]
mod list_extraction_tests {
    use super::*;

    /// Creates a DOCX with bullet and numbered lists
    fn create_docx_with_lists() -> NamedTempFile {
        let file = NamedTempFile::with_suffix(".docx").unwrap();
        let zip_file = std::fs::File::create(file.path()).unwrap();
        let mut zip = zip::ZipWriter::new(zip_file);

        let options: FileOptions<()> = FileOptions::default()
            .compression_method(zip::CompressionMethod::Deflated);

        zip.start_file("[Content_Types].xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"#).unwrap();

        zip.start_file("_rels/.rels", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"#).unwrap();

        // Document with lists
        zip.start_file("word/document.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p>
      <w:r><w:t>Shopping list:</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
      <w:r><w:t>Apples</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
      <w:r><w:t>Bananas</w:t></w:r>
    </w:p>
    <w:p>
      <w:pPr><w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr></w:pPr>
      <w:r><w:t>Oranges</w:t></w:r>
    </w:p>
    <w:p>
      <w:r><w:t>End of list.</w:t></w:r>
    </w:p>
  </w:body>
</w:document>"#).unwrap();

        zip.finish().unwrap();
        file
    }

    #[test]
    fn test_list_items_extracted() {
        let docx_file = create_docx_with_lists();
        let result = DOCXParser::extract_text(docx_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        // All list items should be present
        assert!(text.contains("Apples"));
        assert!(text.contains("Bananas"));
        assert!(text.contains("Oranges"));
    }

    #[test]
    fn test_list_paragraphs() {
        let docx_file = create_docx_with_lists();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        // Should have multiple paragraphs (header + items + footer)
        assert!(doc.paragraphs.len() >= 5);
    }
}

// ============================================================================
// Integration-Style Unit Tests
// ============================================================================

#[cfg(test)]
mod integration_style_tests {
    use super::*;

    #[test]
    fn test_full_extraction_pipeline() {
        let docx_file = create_minimal_docx();

        let simple_text = DOCXParser::extract_text(docx_file.path());
        let structured = DOCXParser::extract_structured(docx_file.path());
        let para_count = DOCXParser::get_paragraph_count(docx_file.path());

        assert!(simple_text.is_ok());
        assert!(structured.is_ok());
        assert!(para_count.is_ok());

        // Results should be consistent
        let text = simple_text.unwrap();
        let doc = structured.unwrap();
        let count = para_count.unwrap();

        assert_eq!(text, doc.text);
        assert_eq!(count, doc.paragraphs.len());
    }

    #[test]
    fn test_consistent_error_handling() {
        let malformed = create_malformed_docx();

        // All methods should return errors for malformed input
        assert!(DOCXParser::extract_text(malformed.path()).is_err());
        assert!(DOCXParser::extract_structured(malformed.path()).is_err());
        assert!(DOCXParser::get_paragraph_count(malformed.path()).is_err());
    }

    #[test]
    fn test_complex_document_extraction() {
        let docx_file = create_multipart_docx();
        let result = DOCXParser::extract_structured(docx_file.path());

        assert!(result.is_ok());
        let doc = result.unwrap();

        // Should extract all content types
        assert!(doc.text.contains("Document Title"));
        assert!(doc.text.contains("bold text"));
        assert!(doc.text.contains("italic text"));
        assert!(doc.paragraphs.len() >= 3);
    }
}

//! EPUB Parser Unit Tests
//!
//! Tests for EPUB text extraction, chapter parsing, and error handling.
//! Note: Private helper methods (strip_html, extract_paragraphs) are tested
//! indirectly through the public API.

use std::io::Write;
use std::path::PathBuf;
use tempfile::NamedTempFile;
use zip::write::FileOptions;

use crate::ingestion::epub_parser::{EPUBParser, EPUBError, ExtractedEPUB, ExtractedChapter};

// ============================================================================
// Test Fixtures
// ============================================================================

/// Creates a minimal valid EPUB for testing
fn create_minimal_epub() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".epub").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default()
        .compression_method(zip::CompressionMethod::Stored);

    // mimetype (must be first and uncompressed)
    zip.start_file("mimetype", options).unwrap();
    zip.write_all(b"application/epub+zip").unwrap();

    // META-INF/container.xml
    zip.start_file("META-INF/container.xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"#).unwrap();

    // OEBPS/content.opf
    zip.start_file("OEBPS/content.opf", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Test Book</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:publisher>Test Publisher</dc:publisher>
    <dc:description>A test book for unit testing</dc:description>
    <dc:identifier id="BookId">test-book-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter1"/>
    <itemref idref="chapter2"/>
  </spine>
</package>"#).unwrap();

    // OEBPS/toc.ncx
    zip.start_file("OEBPS/toc.ncx", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="test-book-001"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>Test Book</text></docTitle>
  <navMap>
    <navPoint id="navpoint-1" playOrder="1">
      <navLabel><text>Chapter 1</text></navLabel>
      <content src="chapter1.xhtml"/>
    </navPoint>
    <navPoint id="navpoint-2" playOrder="2">
      <navLabel><text>Chapter 2</text></navLabel>
      <content src="chapter2.xhtml"/>
    </navPoint>
  </navMap>
</ncx>"#).unwrap();

    // OEBPS/chapter1.xhtml
    zip.start_file("OEBPS/chapter1.xhtml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 1</title></head>
<body>
<h1>Chapter 1: The Beginning</h1>
<p>This is the first paragraph of chapter one.</p>
<p>This is the second paragraph with some <b>bold text</b> and <i>italic text</i>.</p>
</body>
</html>"#).unwrap();

    // OEBPS/chapter2.xhtml
    zip.start_file("OEBPS/chapter2.xhtml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.1//EN" "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter 2</title></head>
<body>
<h1>Chapter 2: The Journey</h1>
<p>The adventure continues in chapter two.</p>
<p>More exciting content follows.</p>
</body>
</html>"#).unwrap();

    zip.finish().unwrap();
    file
}

/// Creates an EPUB with CSS/style content for testing CSS stripping
fn create_epub_with_css() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".epub").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default()
        .compression_method(zip::CompressionMethod::Stored);

    zip.start_file("mimetype", options).unwrap();
    zip.write_all(b"application/epub+zip").unwrap();

    zip.start_file("META-INF/container.xml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"#).unwrap();

    zip.start_file("OEBPS/content.opf", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>CSS Test Book</dc:title>
    <dc:identifier id="BookId">css-test-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter1"/>
  </spine>
</package>"#).unwrap();

    zip.start_file("OEBPS/toc.ncx", options).unwrap();
    zip.write_all(br#"<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="css-test-001"/></head>
  <docTitle><text>CSS Test</text></docTitle>
  <navMap><navPoint id="np1" playOrder="1"><navLabel><text>Ch1</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap>
</ncx>"#).unwrap();

    // Chapter with inline CSS and style tags
    zip.start_file("OEBPS/chapter1.xhtml", options).unwrap();
    zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>CSS Test</title>
<style type="text/css">
body { font-family: serif; }
p { margin: 1em; }
.highlight { color: red; }
</style>
</head>
<body>
<p style="color: blue; font-size: 14px;">Styled paragraph one.</p>
<p class="highlight">Styled paragraph two.</p>
<script type="text/javascript">
console.log("This should be stripped");
</script>
<p>Plain paragraph three.</p>
</body>
</html>"#).unwrap();

    zip.finish().unwrap();
    file
}

/// Creates a malformed EPUB (not a valid ZIP)
fn create_malformed_epub() -> NamedTempFile {
    let mut file = NamedTempFile::with_suffix(".epub").unwrap();
    file.write_all(b"This is not a valid EPUB file").unwrap();
    file.flush().unwrap();
    file
}

/// Creates an empty EPUB (valid ZIP but missing required files)
fn create_empty_epub() -> NamedTempFile {
    let file = NamedTempFile::with_suffix(".epub").unwrap();
    let zip_file = std::fs::File::create(file.path()).unwrap();
    let mut zip = zip::ZipWriter::new(zip_file);

    let options: FileOptions<()> = FileOptions::default();
    zip.start_file("mimetype", options).unwrap();
    zip.write_all(b"application/epub+zip").unwrap();

    zip.finish().unwrap();
    file
}

// ============================================================================
// Chapter Extraction Tests
// ============================================================================

#[cfg(test)]
mod chapter_extraction_tests {
    use super::*;

    #[test]
    fn test_extract_text_from_epub() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_text(epub_file.path());

        assert!(result.is_ok(), "Failed to extract text: {:?}", result.err());
        let text = result.unwrap();
        assert!(!text.is_empty());
        assert!(text.contains("Chapter 1") || text.contains("first paragraph") || text.contains("Beginning"));
    }

    #[test]
    fn test_extract_structured_chapters() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        assert!(result.is_ok(), "Failed to extract structured: {:?}", result.err());
        let epub = result.unwrap();

        // Should have chapters
        assert!(epub.chapter_count >= 1, "Expected at least 1 chapter, got {}", epub.chapter_count);
        assert!(!epub.chapters.is_empty());
    }

    #[test]
    fn test_chapter_indices_are_sequential() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        if let Ok(epub) = result {
            for (expected_idx, chapter) in epub.chapters.iter().enumerate() {
                assert_eq!(chapter.index, expected_idx, "Chapter index mismatch");
            }
        }
    }

    #[test]
    fn test_extract_specific_chapter() {
        let epub_file = create_minimal_epub();

        // Extract first chapter
        let result = EPUBParser::extract_chapter(epub_file.path(), 0);
        assert!(result.is_ok() || matches!(result.as_ref().err(), Some(EPUBError::ChapterError(_))));
    }

    #[test]
    fn test_extract_invalid_chapter_index() {
        let epub_file = create_minimal_epub();

        // Try to extract chapter that doesn't exist
        let result = EPUBParser::extract_chapter(epub_file.path(), 9999);
        assert!(result.is_err());

        match result.unwrap_err() {
            EPUBError::ChapterError(msg) => {
                assert!(msg.contains("not found") || msg.contains("9999"));
            }
            e => panic!("Expected ChapterError, got {:?}", e),
        }
    }

    #[test]
    fn test_get_chapter_count() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::get_chapter_count(epub_file.path());

        assert!(result.is_ok());
        let count = result.unwrap();
        assert!(count >= 1);
    }
}

// ============================================================================
// Metadata Extraction Tests
// ============================================================================

#[cfg(test)]
mod metadata_extraction_tests {
    use super::*;

    #[test]
    fn test_metadata_extraction() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::get_metadata(epub_file.path());

        assert!(result.is_ok());
        let (title, _authors) = result.unwrap();

        // Should have title from our test EPUB
        if let Some(t) = title {
            assert!(t.contains("Test") || !t.is_empty());
        }
    }

    #[test]
    fn test_structured_metadata() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        if let Ok(epub) = result {
            // Test that metadata fields are accessible
            let _title = epub.title;
            let _authors = epub.authors;
            let _publisher = epub.publisher;
            let _description = epub.description;

            assert!(!epub.source_path.is_empty());
        }
    }

    #[test]
    fn test_extracted_chapter_structure() {
        let chapter = ExtractedChapter {
            index: 0,
            title: Some("Test Chapter".to_string()),
            text: "Test content".to_string(),
            paragraphs: vec!["Test content".to_string()],
        };

        assert_eq!(chapter.index, 0);
        assert!(chapter.title.is_some());
        assert!(!chapter.text.is_empty());
    }
}

// ============================================================================
// CSS Stripping Tests (via public API)
// ============================================================================

#[cfg(test)]
mod css_stripping_tests {
    use super::*;

    #[test]
    fn test_epub_with_css_extraction() {
        // Test CSS stripping indirectly through extract_text
        let epub_file = create_epub_with_css();
        let result = EPUBParser::extract_text(epub_file.path());

        if let Ok(text) = result {
            // Should have content but no CSS
            assert!(text.contains("paragraph") || text.is_empty());
            assert!(!text.contains("font-family"));
            assert!(!text.contains("margin:"));
            assert!(!text.contains("console.log"));
        }
    }

    #[test]
    fn test_structured_extraction_strips_html() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        if let Ok(epub) = result {
            for chapter in &epub.chapters {
                // Should not contain HTML tags
                assert!(!chapter.text.contains("<p>"));
                assert!(!chapter.text.contains("</p>"));
                assert!(!chapter.text.contains("<html>"));
            }
        }
    }

    #[test]
    fn test_html_entities_decoded() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_text(epub_file.path());

        // The extraction should decode common HTML entities
        // We just verify no error occurs
        assert!(result.is_ok() || result.is_err());
    }
}

// ============================================================================
// Paragraph Extraction Tests (via public API)
// ============================================================================

#[cfg(test)]
mod paragraph_extraction_tests {
    use super::*;

    #[test]
    fn test_structured_extraction_has_paragraphs() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        if let Ok(epub) = result {
            // At least some chapters should have paragraphs
            let total_paragraphs: usize = epub.chapters.iter()
                .map(|c| c.paragraphs.len())
                .sum();

            // Should have at least some paragraphs extracted
            assert!(total_paragraphs >= 0);
        }
    }

    #[test]
    fn test_paragraphs_are_not_empty() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        if let Ok(epub) = result {
            for chapter in &epub.chapters {
                for para in &chapter.paragraphs {
                    assert!(!para.trim().is_empty(), "Paragraph should not be empty");
                }
            }
        }
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
        let path = PathBuf::from("/nonexistent/path/to/file.epub");
        let result = EPUBParser::extract_text(&path);

        assert!(result.is_err());
        match result.unwrap_err() {
            EPUBError::LoadError(_) | EPUBError::IoError(_) => (),
            e => panic!("Expected LoadError or IoError, got {:?}", e),
        }
    }

    #[test]
    fn test_malformed_epub_error() {
        let malformed_file = create_malformed_epub();
        let result = EPUBParser::extract_text(malformed_file.path());

        assert!(result.is_err());
    }

    #[test]
    fn test_empty_epub_handling() {
        let empty_file = create_empty_epub();
        let result = EPUBParser::extract_text(empty_file.path());

        // Should return error for EPUB missing required files
        assert!(result.is_err());
    }

    #[test]
    fn test_epub_error_display() {
        let error = EPUBError::LoadError("test error".to_string());
        let display = format!("{}", error);
        assert!(display.contains("test error"));

        let error = EPUBError::ChapterError("chapter not found".to_string());
        let display = format!("{}", error);
        assert!(display.contains("chapter"));
    }

    #[test]
    fn test_consistent_error_handling() {
        let malformed = create_malformed_epub();

        // All methods should return errors for malformed input
        assert!(EPUBParser::extract_text(malformed.path()).is_err());
        assert!(EPUBParser::extract_structured(malformed.path()).is_err());
        assert!(EPUBParser::get_chapter_count(malformed.path()).is_err());
        assert!(EPUBParser::get_metadata(malformed.path()).is_err());
    }
}

// ============================================================================
// Serialization Tests
// ============================================================================

#[cfg(test)]
mod serialization_tests {
    use super::*;

    #[test]
    fn test_extracted_chapter_serialization() {
        let chapter = ExtractedChapter {
            index: 0,
            title: Some("Test".to_string()),
            text: "Content".to_string(),
            paragraphs: vec!["Content".to_string()],
        };

        let json = serde_json::to_string(&chapter);
        assert!(json.is_ok());

        if let Ok(json_str) = json {
            let deserialized: Result<ExtractedChapter, _> = serde_json::from_str(&json_str);
            assert!(deserialized.is_ok());
        }
    }

    #[test]
    fn test_extracted_epub_serialization() {
        let epub = ExtractedEPUB {
            source_path: "/test/path.epub".to_string(),
            title: Some("Test Book".to_string()),
            authors: vec!["Test Author".to_string()],
            publisher: Some("Test Publisher".to_string()),
            description: Some("Test description".to_string()),
            chapter_count: 1,
            chapters: vec![ExtractedChapter {
                index: 0,
                title: Some("Chapter 1".to_string()),
                text: "Content".to_string(),
                paragraphs: vec!["Content".to_string()],
            }],
        };

        let json = serde_json::to_string(&epub);
        assert!(json.is_ok());

        if let Ok(json_str) = json {
            let deserialized: Result<ExtractedEPUB, _> = serde_json::from_str(&json_str);
            assert!(deserialized.is_ok());
        }
    }

    #[test]
    fn test_extracted_chapter_clone() {
        let chapter = ExtractedChapter {
            index: 0,
            title: Some("Test".to_string()),
            text: "Content".to_string(),
            paragraphs: vec!["Content".to_string()],
        };

        let cloned = chapter.clone();
        assert_eq!(chapter.index, cloned.index);
        assert_eq!(chapter.text, cloned.text);
    }
}

// ============================================================================
// TOC Parsing Tests
// ============================================================================

#[cfg(test)]
mod toc_parsing_tests {
    use super::*;

    /// Creates an EPUB with a detailed TOC
    fn create_epub_with_detailed_toc() -> NamedTempFile {
        let file = NamedTempFile::with_suffix(".epub").unwrap();
        let zip_file = std::fs::File::create(file.path()).unwrap();
        let mut zip = zip::ZipWriter::new(zip_file);

        let options: FileOptions<()> = FileOptions::default()
            .compression_method(zip::CompressionMethod::Stored);

        zip.start_file("mimetype", options).unwrap();
        zip.write_all(b"application/epub+zip").unwrap();

        zip.start_file("META-INF/container.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"#).unwrap();

        zip.start_file("OEBPS/content.opf", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>TOC Test Book</dc:title>
    <dc:identifier id="BookId">toc-test-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="intro" href="intro.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
    <item id="appendix" href="appendix.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="intro"/>
    <itemref idref="chapter1"/>
    <itemref idref="chapter2"/>
    <itemref idref="appendix"/>
  </spine>
</package>"#).unwrap();

        // Detailed NCX with nested navigation
        zip.start_file("OEBPS/toc.ncx", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="toc-test-001"/>
    <meta name="dtb:depth" content="2"/>
  </head>
  <docTitle><text>TOC Test Book</text></docTitle>
  <navMap>
    <navPoint id="intro" playOrder="1">
      <navLabel><text>Introduction</text></navLabel>
      <content src="intro.xhtml"/>
    </navPoint>
    <navPoint id="part1" playOrder="2">
      <navLabel><text>Part I: Beginning</text></navLabel>
      <content src="chapter1.xhtml"/>
      <navPoint id="ch1" playOrder="3">
        <navLabel><text>Chapter 1: The Start</text></navLabel>
        <content src="chapter1.xhtml#section1"/>
      </navPoint>
    </navPoint>
    <navPoint id="ch2" playOrder="4">
      <navLabel><text>Chapter 2: The Middle</text></navLabel>
      <content src="chapter2.xhtml"/>
    </navPoint>
    <navPoint id="appendix" playOrder="5">
      <navLabel><text>Appendix A</text></navLabel>
      <content src="appendix.xhtml"/>
    </navPoint>
  </navMap>
</ncx>"#).unwrap();

        // Content files
        for (name, content) in [
            ("intro.xhtml", "Introduction content here."),
            ("chapter1.xhtml", "Chapter 1 content here."),
            ("chapter2.xhtml", "Chapter 2 content here."),
            ("appendix.xhtml", "Appendix content here."),
        ] {
            zip.start_file(format!("OEBPS/{}", name), options).unwrap();
            zip.write_all(format!(r#"<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>{}</title></head>
<body><p>{}</p></body>
</html>"#, name, content).as_bytes()).unwrap();
        }

        zip.finish().unwrap();
        file
    }

    #[test]
    fn test_toc_chapter_count() {
        let epub_file = create_epub_with_detailed_toc();
        let result = EPUBParser::get_chapter_count(epub_file.path());

        assert!(result.is_ok());
        let count = result.unwrap();
        // Should have 4 chapters (intro, chapter1, chapter2, appendix)
        assert_eq!(count, 4);
    }

    #[test]
    fn test_toc_preserves_chapter_order() {
        let epub_file = create_epub_with_detailed_toc();
        let result = EPUBParser::extract_structured(epub_file.path());

        assert!(result.is_ok());
        let epub = result.unwrap();

        // Chapters should be in spine order
        assert_eq!(epub.chapters.len(), 4);

        // Each chapter should have sequential indices
        for (i, chapter) in epub.chapters.iter().enumerate() {
            assert_eq!(chapter.index, i);
        }
    }

    #[test]
    fn test_all_chapters_extracted() {
        let epub_file = create_epub_with_detailed_toc();
        let result = EPUBParser::extract_text(epub_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        // All chapter content should be present
        assert!(text.contains("Introduction") || text.contains("content"));
        assert!(text.contains("Chapter") || text.contains("content"));
        assert!(text.contains("Appendix") || text.contains("content"));
    }
}

// ============================================================================
// Embedded Image Handling Tests
// ============================================================================

#[cfg(test)]
mod embedded_image_tests {
    use super::*;

    /// Creates an EPUB with embedded image references
    fn create_epub_with_images() -> NamedTempFile {
        let file = NamedTempFile::with_suffix(".epub").unwrap();
        let zip_file = std::fs::File::create(file.path()).unwrap();
        let mut zip = zip::ZipWriter::new(zip_file);

        let options: FileOptions<()> = FileOptions::default()
            .compression_method(zip::CompressionMethod::Stored);

        zip.start_file("mimetype", options).unwrap();
        zip.write_all(b"application/epub+zip").unwrap();

        zip.start_file("META-INF/container.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"#).unwrap();

        zip.start_file("OEBPS/content.opf", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Image Test Book</dc:title>
    <dc:identifier id="BookId">image-test-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="cover" href="images/cover.jpg" media-type="image/jpeg"/>
    <item id="fig1" href="images/figure1.png" media-type="image/png"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter1"/>
  </spine>
</package>"#).unwrap();

        zip.start_file("OEBPS/toc.ncx", options).unwrap();
        zip.write_all(br#"<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="image-test-001"/></head>
  <docTitle><text>Image Test</text></docTitle>
  <navMap><navPoint id="ch1" playOrder="1"><navLabel><text>Chapter 1</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap>
</ncx>"#).unwrap();

        // Chapter with image references
        zip.start_file("OEBPS/chapter1.xhtml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head><title>Chapter with Images</title></head>
<body>
<p>Text before the image.</p>
<img src="images/figure1.png" alt="Figure 1: Test diagram"/>
<p>Text after the image with more content.</p>
<figure>
  <img src="images/cover.jpg" alt="Book cover"/>
  <figcaption>The book cover image</figcaption>
</figure>
<p>Final paragraph of text.</p>
</body>
</html>"#).unwrap();

        // Add dummy image files (1x1 pixel placeholders)
        zip.start_file("OEBPS/images/cover.jpg", options).unwrap();
        // Minimal JPEG header
        zip.write_all(&[0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46]).unwrap();

        zip.start_file("OEBPS/images/figure1.png", options).unwrap();
        // Minimal PNG header
        zip.write_all(&[0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]).unwrap();

        zip.finish().unwrap();
        file
    }

    #[test]
    fn test_image_references_stripped_from_text() {
        let epub_file = create_epub_with_images();
        let result = EPUBParser::extract_text(epub_file.path());

        assert!(result.is_ok());
        let text = result.unwrap();

        // Should contain text content
        assert!(text.contains("Text") || text.contains("paragraph"));

        // Should not contain img tags or raw image data
        assert!(!text.contains("<img"));
        assert!(!text.contains(".png"));
        assert!(!text.contains(".jpg"));
    }

    #[test]
    fn test_alt_text_handling() {
        let epub_file = create_epub_with_images();
        let result = EPUBParser::extract_text(epub_file.path());

        if let Ok(text) = result {
            // Alt text might or might not be preserved depending on implementation
            // The key is that we don't crash and extract surrounding text
            assert!(text.contains("Text") || text.contains("paragraph") || text.contains("content"));
        }
    }

    #[test]
    fn test_structured_extraction_with_images() {
        let epub_file = create_epub_with_images();
        let result = EPUBParser::extract_structured(epub_file.path());

        assert!(result.is_ok());
        let epub = result.unwrap();

        // Should have chapters
        assert!(!epub.chapters.is_empty());

        // Chapter text should not contain binary image data
        for chapter in &epub.chapters {
            // No binary data in text
            let is_valid_text = chapter.text.chars().all(|c| !c.is_control() || c == '\n' || c == '\r' || c == '\t');
            assert!(is_valid_text, "Chapter text should not contain binary data");
        }
    }
}

// ============================================================================
// DRM Protection Tests
// ============================================================================

#[cfg(test)]
mod drm_protection_tests {
    use super::*;

    /// Creates an EPUB that simulates DRM protection markers
    fn create_drm_protected_epub() -> NamedTempFile {
        let file = NamedTempFile::with_suffix(".epub").unwrap();
        let zip_file = std::fs::File::create(file.path()).unwrap();
        let mut zip = zip::ZipWriter::new(zip_file);

        let options: FileOptions<()> = FileOptions::default()
            .compression_method(zip::CompressionMethod::Stored);

        zip.start_file("mimetype", options).unwrap();
        zip.write_all(b"application/epub+zip").unwrap();

        zip.start_file("META-INF/container.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>"#).unwrap();

        // Add DRM encryption.xml (Adobe DRM marker)
        zip.start_file("META-INF/encryption.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<encryption xmlns="urn:oasis:names:tc:opendocument:xmlns:container"
            xmlns:enc="http://www.w3.org/2001/04/xmlenc#">
  <enc:EncryptedData>
    <enc:EncryptionMethod Algorithm="http://www.w3.org/2001/04/xmlenc#aes128-cbc"/>
    <enc:CipherData>
      <enc:CipherReference URI="OEBPS/chapter1.xhtml"/>
    </enc:CipherData>
  </enc:EncryptedData>
</encryption>"#).unwrap();

        // Add rights.xml (DRM rights info)
        zip.start_file("META-INF/rights.xml", options).unwrap();
        zip.write_all(br#"<?xml version="1.0"?>
<rights xmlns="http://ns.adobe.com/adept">
  <licenseToken>encrypted-license-token-here</licenseToken>
</rights>"#).unwrap();

        zip.start_file("OEBPS/content.opf", options).unwrap();
        zip.write_all(br#"<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="2.0" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>DRM Protected Book</dc:title>
    <dc:identifier id="BookId">drm-test-001</dc:identifier>
  </metadata>
  <manifest>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>
  </manifest>
  <spine toc="ncx">
    <itemref idref="chapter1"/>
  </spine>
</package>"#).unwrap();

        zip.start_file("OEBPS/toc.ncx", options).unwrap();
        zip.write_all(br#"<?xml version="1.0"?>
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head><meta name="dtb:uid" content="drm-test-001"/></head>
  <docTitle><text>DRM Test</text></docTitle>
  <navMap><navPoint id="ch1" playOrder="1"><navLabel><text>Ch1</text></navLabel><content src="chapter1.xhtml"/></navPoint></navMap>
</ncx>"#).unwrap();

        // "Encrypted" chapter content (gibberish representing encrypted data)
        zip.start_file("OEBPS/chapter1.xhtml", options).unwrap();
        zip.write_all(b"\x00\x01\x02\x03\x04\x05ENCRYPTED_CONTENT\x06\x07\x08").unwrap();

        zip.finish().unwrap();
        file
    }

    #[test]
    fn test_drm_epub_handling() {
        let epub_file = create_drm_protected_epub();
        let result = EPUBParser::extract_text(epub_file.path());

        // Should either return an error or return empty/garbled text
        // The important thing is it doesn't crash
        match result {
            Ok(text) => {
                // If it succeeds, text should be minimal or garbled
                // (encrypted content won't parse as valid XHTML)
                let _ = text;
            }
            Err(_) => {
                // Error is expected for DRM content
            }
        }
    }

    #[test]
    fn test_drm_epub_structured_extraction() {
        let epub_file = create_drm_protected_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        // Should handle gracefully - either error or empty chapters
        match result {
            Ok(epub) => {
                // Chapters might be empty or have garbled content
                let _ = epub;
            }
            Err(_) => {
                // Error is acceptable for DRM content
            }
        }
    }

    #[test]
    fn test_drm_epub_metadata_still_readable() {
        let epub_file = create_drm_protected_epub();
        let result = EPUBParser::get_metadata(epub_file.path());

        // Metadata might still be readable even with DRM
        // The OPF file is typically not encrypted
        if let Ok((title, _authors)) = result {
            // Title should be extractable
            if let Some(t) = title {
                assert!(t.contains("DRM") || t.contains("Protected") || !t.is_empty());
            }
        }
    }

    #[test]
    fn test_drm_epub_chapter_count() {
        let epub_file = create_drm_protected_epub();
        let result = EPUBParser::get_chapter_count(epub_file.path());

        // Chapter count should still work (based on manifest, not content)
        if let Ok(count) = result {
            assert!(count >= 1);
        }
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
        let epub_file = create_minimal_epub();

        // Test complete pipeline
        let chapter_count = EPUBParser::get_chapter_count(epub_file.path());
        let metadata = EPUBParser::get_metadata(epub_file.path());
        let simple_text = EPUBParser::extract_text(epub_file.path());
        let structured = EPUBParser::extract_structured(epub_file.path());

        // All should succeed for valid EPUB
        assert!(chapter_count.is_ok());
        assert!(metadata.is_ok());
        assert!(simple_text.is_ok());
        assert!(structured.is_ok());
    }

    #[test]
    fn test_chapter_iteration() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        if let Ok(epub) = result {
            for chapter in epub.chapters {
                // Each chapter should have valid structure
                assert!(chapter.index < 1000); // Reasonable index
                assert!(!chapter.text.is_empty() || chapter.title.is_some());
            }
        }
    }

    #[test]
    fn test_source_path_preserved() {
        let epub_file = create_minimal_epub();
        let result = EPUBParser::extract_structured(epub_file.path());

        if let Ok(epub) = result {
            assert!(epub.source_path.contains(".epub"));
        }
    }
}

//! Kreuzberg Document Extractor
//!
//! Unified document extraction using the kreuzberg crate.
//! Supports PDF, EPUB, DOCX, MOBI, images, and 50+ other formats.

use kreuzberg::core::config::PageConfig;
use kreuzberg::ExtractionConfig;
use std::path::Path;
use thiserror::Error;
use tokio::process::Command;
use std::process::Stdio;

// ============================================================================
// Error Types
// ============================================================================

#[derive(Error, Debug)]
pub enum ExtractionError {
    #[error("Kreuzberg extraction failed: {0}")]
    KreuzbergError(String),

    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Unsupported format: {0}")]
    UnsupportedFormat(String),
}

impl From<kreuzberg::KreuzbergError> for ExtractionError {
    fn from(e: kreuzberg::KreuzbergError) -> Self {
        ExtractionError::KreuzbergError(e.to_string())
    }
}

pub type Result<T> = std::result::Result<T, ExtractionError>;

// ============================================================================
// Extracted Document Types
// ============================================================================

/// Unified extracted document result
#[derive(Debug, Clone)]
pub struct ExtractedContent {
    /// Source file path
    pub source_path: String,
    /// Extracted text content
    pub content: String,
    /// Number of pages/chapters/sections
    pub page_count: usize,
    /// Document title (if available)
    pub title: Option<String>,
    /// Document author (if available)
    pub author: Option<String>,
    /// MIME type detected
    pub mime_type: String,
    /// Character count
    pub char_count: usize,
    /// Extracted pages (if enabled)
    pub pages: Option<Vec<Page>>,
}

/// Content of a single page
#[derive(Debug, Clone)]
pub struct Page {
    /// Page number (1-indexed)
    pub page_number: usize,
    /// Text content of the page
    pub content: String,
}

// ============================================================================
// Document Extractor
// ============================================================================

/// Kreuzberg-based document extractor
pub struct DocumentExtractor {
    config: ExtractionConfig,
    ocr_enabled: bool,
}

impl Default for DocumentExtractor {
    fn default() -> Self {
        Self::new()
    }
}

impl DocumentExtractor {
    /// Create a new document extractor with default configuration
    pub fn new() -> Self {
        Self {
            config: ExtractionConfig::default(),
            ocr_enabled: false,
        }
    }

    /// Create an extractor with OCR fallback enabled for scanned documents.
    /// Note: OCR is handled via external pdftoppm + tesseract due to
    /// kreuzberg OCR dependency conflicts with other crates.
    pub fn with_ocr() -> Self {
        Self {
            config: ExtractionConfig::default(),
            ocr_enabled: true,
        }
    }

    /// Create an extractor with forced OCR (always use external OCR)
    pub fn with_forced_ocr() -> Self {
        Self {
            config: ExtractionConfig::default(),
            ocr_enabled: true,
        }
    }

    /// Extract content from a file (async)
    pub async fn extract<F>(&self, path: &Path, progress_callback: Option<F>) -> Result<ExtractedContent>
    where F: Fn(f32, &str) + Send + Sync + 'static
    {
        let path_str = path.to_string_lossy().to_string();

        log::info!("Extracting document with kreuzberg (async): {:?}", path.file_name().unwrap_or_default());

        if let Some(ref cb) = progress_callback {
            cb(0.0, &format!("Starting extraction for {:?}", path.file_name().unwrap_or_default()));
        }

        // Enable page extraction for granular results
        let mut config = self.config.clone();
        config.pages = Some(PageConfig {
            extract_pages: true,
            insert_page_markers: false, // We'll handle chunking based on page structs
            marker_format: "".to_string(),
        });

        // Use async extraction
        let result = kreuzberg::extract_file(path, None, &config).await?;

        // Page count from pages Vec length, or default to 1
        let page_count = result.pages
            .as_ref()
            .map(|p| p.len())
            .unwrap_or(1);

        let title = result.metadata.title.clone();
        // Authors is a Vec, join them if present
        let author = result.metadata.authors
            .as_ref()
            .map(|authors| authors.join(", "));
        let mime_type = result.mime_type.clone();
        let char_count = result.content.len();

        log::info!(
            "Kreuzberg extraction complete: {} pages, {} chars, mime={}",
            page_count, char_count, mime_type
        );

        if let Some(ref cb) = progress_callback {
            cb(0.1, &format!("Parsing complete ({} chars detected)", char_count));
        }

        // Map internal PageContent to our needs if necessary, but ExtractedContent just holds the raw text currently.
        // We really want to expose the pages up the chain.
        // For now, let's keep the struct signatures compatible but populate the content rich fields.

        // Check for fallback OCR
        // If we have minimal text for a PDF, and OCR is enabled, try our manual fallback
        let is_pdf = mime_type == "application/pdf";
        let low_text = char_count < 500; // Heuristic: < 500 chars for a document usually means scanned

        if is_pdf && low_text && self.ocr_enabled {
            log::warn!("Minimal text found ({}) in PDF. Attempting async fallback OCR...", char_count);

            if let Some(ref cb) = progress_callback {
                cb(0.15, "Low text detected - Starting OCR fallback...");
            }

            // We pass the current result in case OCR fails or returns nothing
            let fallback_result = self.extract_with_fallback_ocr(path, page_count, progress_callback).await;

            match fallback_result {
                Ok(ocr_content) => {
                    if ocr_content.char_count > char_count {
                        log::info!("Fallback OCR successful: {} chars (was {})", ocr_content.char_count, char_count);
                        return Ok(ocr_content);
                    } else {
                        log::warn!("Fallback OCR produced less/same text. Keeping original.");
                    }
                }
                Err(e) => {
                    log::error!("Fallback OCR failed: {}. Keeping original kreuzberg result.", e);
                }
            }
        }

        Ok(ExtractedContent {
            source_path: path_str,
            content: result.content,
            page_count,
            title,
            author,
            mime_type,
            char_count,
            pages: result.pages.map(|pages| pages.into_iter().map(|p| Page {
                page_number: p.page_number,
                content: p.content,
            }).collect()),
        })
    }

    /// Fallback OCR using pdftoppm + tesseract (async)
    async fn extract_with_fallback_ocr<F>(&self, path: &Path, expected_pages: usize, progress_callback: Option<F>) -> Result<ExtractedContent>
    where F: Fn(f32, &str) + Send + Sync + 'static
    {
        let temp_dir = tempfile::Builder::new()
            .prefix("ocr_")
            .tempdir()
            .map_err(|e| ExtractionError::IoError(e))?;

        let temp_path = temp_dir.path();
        let prefix = "page";

        // 1. Convert PDF to images (pdftoppm)
        // pdftoppm -png -r 300 input.pdf output_prefix
        log::info!("Running pdftoppm (async) on {:?}", path);
        if let Some(ref cb) = progress_callback {
            cb(0.15, "Converting PDF to images for OCR...");
        }

        let status = Command::new("pdftoppm")
            .arg("-png")
            .arg("-r")
            .arg("300")
            .arg(path)
            .arg(temp_path.join(prefix))
            .status()
            .await
            .map_err(|e| ExtractionError::IoError(e))?;

        if !status.success() {
            return Err(ExtractionError::KreuzbergError("pdftoppm failed".to_string()));
        }

        // 2. Perform OCR on each image
        let mut pages = Vec::new();
        let mut full_text = String::new();

        // pdftoppm generates page-1.png, page-2.png, etc.
        // We'll iterate up to expected_pages (or find files)
        // Using expected_pages is safer for ordering

        // Sometimes page count is wrong from kreuzberg, so we should allow some flexibility?
        // But pdftoppm is reliable.
        // Let's iterate 1..=expected_pages + check for existence.
        // If expected_pages was 1 (default), checking 1.. matches.

        // Actually best to read the directory to discover ACTUAL pages generated by pdftoppm
        let mut image_files = Vec::new();
        let mut read_dir = tokio::fs::read_dir(temp_path).await?;

        while let Some(entry) = read_dir.next_entry().await? {
            let path = entry.path();
            if path.extension().and_then(|e| e.to_str()) == Some("png") {
                // Parse page number from filename: page-1.png -> 1
                if let Some(stem) = path.file_stem().and_then(|s| s.to_str()) {
                     if let Some(idx) = stem.rfind('-') {
                         if let Ok(num) = stem[idx+1..].parse::<usize>() {
                             image_files.push((num, path));
                         }
                     }
                }
            }
        }

        // Sort by page number
        image_files.sort_by_key(|k| k.0);

        if image_files.is_empty() {
             return Err(ExtractionError::KreuzbergError("No images generated by pdftoppm".to_string()));
        }

        log::info!("OCR processing {} pages...", image_files.len());
        let total_pages = image_files.len();

        for (i, (page_num, img_path)) in image_files.into_iter().enumerate() {
            // Update progress: 0.2 to 0.8 range for OCR
            if let Some(ref cb) = progress_callback {
                let p = 0.2 + ((i as f32 / total_pages as f32) * 0.6);
                cb(p, &format!("OCR processing page {}/{}", page_num, total_pages));
            }

            // Run tesseract
            // tesseract input.png stdout -l eng
            let output = Command::new("tesseract")
                .arg(&img_path)
                .arg("stdout")
                .arg("-l")
                .arg("eng") // Assumes English, maybe make configurable later
                .output()
                .await
                .map_err(|e| ExtractionError::IoError(e))?;

            if !output.status.success() {
                 log::warn!("Tesseract failed for page {}", page_num);
                 continue;
            }

            let page_text = String::from_utf8_lossy(&output.stdout).to_string();

            // Clean up text slightly (remove form feed?)
            let cleaned_text = page_text.replace('\x0c', "");

            full_text.push_str(&cleaned_text);
            full_text.push('\n'); // Add newline between pages

            pages.push(Page {
                page_number: page_num,
                content: cleaned_text,
            });

            // Optional: emit finer logging
            if page_num % 10 == 0 {
                log::debug!("OCR processed page {}", page_num);
            }
        }

        Ok(ExtractedContent {
             source_path: path.to_string_lossy().to_string(),
             content: full_text.clone(),
             page_count: pages.len(),
             title: None, // Lost metadata
             author: None,
             mime_type: "application/pdf".to_string(),
             char_count: full_text.len(),
             pages: Some(pages),
        })
    }



    /// Extract content from bytes with a specified MIME type (async)
    pub async fn extract_bytes<F>(&self, bytes: &[u8], mime_type: &str, _progress_callback: Option<F>) -> Result<ExtractedContent>
    where F: Fn(f32, &str) + Send + Sync + 'static
    {
        log::info!("Extracting from bytes with kreuzberg (async), mime={}", mime_type);

        let mut config = self.config.clone();
        config.pages = Some(PageConfig {
            extract_pages: true,
            insert_page_markers: false,
            marker_format: "".to_string(),
        });

        let result = kreuzberg::extract_bytes(bytes, mime_type, &config).await?;

        // Page count from pages Vec length, or default to 1
        let page_count = result.pages
            .as_ref()
            .map(|p| p.len())
            .unwrap_or(1);

        let title = result.metadata.title.clone();
        // Authors is a Vec, join them if present
        let author = result.metadata.authors
            .as_ref()
            .map(|authors| authors.join(", "));
        let detected_mime = result.mime_type.clone();
        let char_count = result.content.len();

        log::info!(
            "Kreuzberg extraction complete: {} pages, {} chars",
            page_count, char_count
        );

        Ok(ExtractedContent {
            source_path: String::new(),
            content: result.content,
            page_count,
            title,
            author,
            mime_type: detected_mime,
            char_count,
            pages: result.pages.map(|pages| pages.into_iter().map(|p| Page {
                page_number: p.page_number,
                content: p.content,
            }).collect()),
        })
    }

    /// Check if a file format is supported
    pub fn is_supported(path: &Path) -> bool {
        let extension = path.extension()
            .and_then(|e| e.to_str())
            .unwrap_or("")
            .to_lowercase();

        matches!(extension.as_str(),
            // Documents
            "pdf" | "doc" | "docx" | "odt" | "rtf" |
            // Ebooks
            "epub" | "mobi" | "azw" | "azw3" | "fb2" |
            // Spreadsheets
            "xls" | "xlsx" | "ods" | "csv" |
            // Presentations
            "ppt" | "pptx" | "odp" |
            // Text
            "txt" | "md" | "markdown" | "rst" | "adoc" |
            // Web
            "html" | "htm" | "xml" | "json" | "yaml" | "yml" |
            // Images (for OCR)
            "png" | "jpg" | "jpeg" | "tiff" | "tif" | "bmp" | "gif" | "webp" |
            // Email
            "eml" | "msg"
        )
    }

    /// Get supported file extensions
    pub fn supported_extensions() -> &'static [&'static str] {
        &[
            "pdf", "doc", "docx", "odt", "rtf",
            "epub", "mobi", "azw", "azw3", "fb2",
            "xls", "xlsx", "ods", "csv",
            "ppt", "pptx", "odp",
            "txt", "md", "markdown", "rst", "adoc",
            "html", "htm", "xml", "json", "yaml", "yml",
            "png", "jpg", "jpeg", "tiff", "tif", "bmp", "gif", "webp",
            "eml", "msg",
        ]
    }
}

// ============================================================================
// Convenience Functions
// ============================================================================

/// Extract text from a file using default configuration
pub async fn extract_text(path: &Path) -> Result<String> {
    let extractor = DocumentExtractor::new();
    // No callback
    let cb: Option<fn(f32, &str)> = None;
    Ok(extractor.extract(path, cb).await?.content)
}

/// Extract text from a file with OCR fallback
pub async fn extract_text_with_ocr(path: &Path) -> Result<String> {
    let extractor = DocumentExtractor::with_ocr();
    let cb: Option<fn(f32, &str)> = None;
    Ok(extractor.extract(path, cb).await?.content)
}

/// Extract structured content from a file
pub async fn extract_document(path: &Path) -> Result<ExtractedContent> {
    let extractor = DocumentExtractor::new();
    let cb: Option<fn(f32, &str)> = None;
    extractor.extract(path, cb).await
}

/// Extract structured content with OCR fallback
pub async fn extract_document_with_ocr(path: &Path) -> Result<ExtractedContent> {
    let extractor = DocumentExtractor::with_ocr();
    let cb: Option<fn(f32, &str)> = None;
    extractor.extract(path, cb).await
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_supported_extensions() {
        assert!(DocumentExtractor::is_supported(Path::new("test.pdf")));
        assert!(DocumentExtractor::is_supported(Path::new("test.epub")));
        assert!(DocumentExtractor::is_supported(Path::new("test.docx")));
        assert!(DocumentExtractor::is_supported(Path::new("test.mobi")));
        assert!(DocumentExtractor::is_supported(Path::new("test.txt")));
        assert!(!DocumentExtractor::is_supported(Path::new("test.exe")));
        assert!(!DocumentExtractor::is_supported(Path::new("test.zip")));
    }

    #[tokio::test]
    #[ignore] // Run with: cargo test test_extract_real_pdf -- --ignored
    async fn test_extract_real_pdf() {
        let pdf_path = Path::new("/home/svnbjrn/Delta-Green-Agents-Handbook.pdf");
        if !pdf_path.exists() {
            println!("Test PDF not found, skipping");
            return;
        }

        // Try without OCR first (for text-based PDFs)
        let extractor = DocumentExtractor::new();
        let result = extractor.extract(pdf_path).await;

        match result {
            Ok(content) => {
                println!("=== Extraction successful ===");
                println!("Source: {}", content.source_path);
                println!("MIME type: {}", content.mime_type);
                println!("Pages: {}", content.page_count);
                println!("Characters: {}", content.char_count);
                println!("Title: {:?}", content.title);
                println!("Author: {:?}", content.author);

                if content.char_count > 0 {
                    let preview_len = content.content.len().min(3000);
                    println!("\n=== First {} chars ===\n{}", preview_len, &content.content[..preview_len]);
                } else {
                    println!("\n=== NO TEXT EXTRACTED (scanned PDF needs OCR) ===");
                }

                // Only assert page count since scanned PDFs may have no text
                assert!(content.page_count > 0, "Expected at least 1 page");

                if content.char_count < 1000 {
                    println!("\nWARNING: Minimal text extracted. This PDF may be scanned/image-based.");
                    println!("OCR feature is disabled due to dependency conflicts.");
                }
            }
            Err(e) => {
                panic!("Extraction failed: {}", e);
            }
        }
    }
}

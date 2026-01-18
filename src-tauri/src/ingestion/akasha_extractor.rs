use std::path::Path;
use akasha_core::{Akasha, AkashaConfig};
use super::extraction_settings::ExtractionSettings;
use super::kreuzberg_extractor::{Result, ExtractedContent, Page, ExtractionError};

pub struct AkashaExtractor {
    config: AkashaConfig,
}

impl AkashaExtractor {
    pub fn new(settings: &ExtractionSettings) -> Self {
        let config = AkashaConfig {
            parallel: true, // Always parallelize
            confidence_threshold: 0.6, // Reasonable default
            enable_vision: true,
            enable_ocr: settings.ocr_enabled,
            enable_formulas: true,
            enable_charts: true,
            cache_dir: None,
        };
        Self { config }
    }

    pub fn extract<P: AsRef<Path>>(&self, path: P) -> Result<ExtractedContent> {
        let engine = Akasha::with_config(self.config.clone());

        let doc = engine.extract_file(&path)
            .map_err(|e| ExtractionError::KreuzbergError(format!("Akasha extraction failed: {}", e)))?;

        // Convert Akasha pages to our Page struct and build full content
        let mut full_content_parts: Vec<String> = Vec::new();

        let pages: Vec<Page> = doc.pages.iter().map(|p| {
            // Reconstruct full text from blocks
            let content = p.text_blocks.iter()
                .map(|b| b.text.clone())
                .collect::<Vec<_>>()
                .join("\n");

            // Accumulate for full document content
            full_content_parts.push(content.clone());

            // Serialize layout info (includes text_blocks with bbox, font info, confidence)
            let layout_info = serde_json::to_value(p)
                .ok();

            Page {
                page_number: p.number as usize,
                content,
                layout_info,
            }
        }).collect();

        // Convert full doc structure (NOTE: akasha-core analyze_structure is a stub, returns empty)
        // This will be empty until akasha-core is fully implemented
        let structural_data = serde_json::to_value(&doc.structure).ok();

        // Build full content from extracted text blocks (NOT from to_markdown() which is a stub)
        let full_content = full_content_parts.join("\n\n");

        let char_count = full_content.len();
        let page_count = pages.len();

        Ok(ExtractedContent {
            source_path: path.as_ref().to_string_lossy().to_string(),
            content: full_content,
            page_count,
            title: doc.metadata.title,
            author: doc.metadata.author,
            mime_type: "application/pdf".to_string(), // Akasha focuses on PDFs
            char_count,
            pages: Some(pages),
            detected_language: None, // Akasha 0.1 metadata doesn't explicitly expose language yet? Checked lib.rs, it doesn't.
            structural_data,
        })
    }
}

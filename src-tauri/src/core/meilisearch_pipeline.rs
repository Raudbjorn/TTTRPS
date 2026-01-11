//! Meilisearch Ingestion Pipeline
//!
//! Handles document parsing, chunking, and indexing into Meilisearch.
//! Uses kreuzberg for fast document extraction with OCR fallback.

use crate::core::search_client::{SearchClient, SearchDocument, SearchError};
use crate::ingestion::kreuzberg_extractor::DocumentExtractor;
use chrono::Utc;
use std::collections::HashMap;
use std::path::Path;
use uuid::Uuid;

// ============================================================================
// Configuration
// ============================================================================

/// Chunking configuration
#[derive(Debug, Clone)]
pub struct ChunkConfig {
    /// Target chunk size in characters
    pub chunk_size: usize,
    /// Overlap between chunks in characters
    pub chunk_overlap: usize,
    /// Minimum chunk size (don't create tiny chunks)
    pub min_chunk_size: usize,
}

impl Default for ChunkConfig {
    fn default() -> Self {
        Self {
            chunk_size: 1000,
            chunk_overlap: 200,
            min_chunk_size: 100,
        }
    }
}

/// Pipeline configuration
#[derive(Debug, Clone)]
pub struct PipelineConfig {
    /// Chunking settings
    pub chunk_config: ChunkConfig,
    /// Default source type if not specified
    pub default_source_type: String,
}

impl Default for PipelineConfig {
    fn default() -> Self {
        Self {
            chunk_config: ChunkConfig::default(),
            default_source_type: "document".to_string(),
        }
    }
}

// ============================================================================
// Pipeline Result
// ============================================================================

/// Result of processing a document
#[derive(Debug, Clone)]
pub struct IngestionResult {
    pub source: String,
    pub total_chunks: usize,
    pub stored_chunks: usize,
    pub failed_chunks: usize,
    pub index_used: String,
}

// ============================================================================
// Meilisearch Pipeline
// ============================================================================

pub struct MeilisearchPipeline {
    config: PipelineConfig,
}

impl MeilisearchPipeline {
    pub fn new(config: PipelineConfig) -> Self {
        Self { config }
    }

    pub fn with_defaults() -> Self {
        Self::new(PipelineConfig::default())
    }

    /// Process a file and ingest into Meilisearch
    pub async fn process_file(
        &self,
        search_client: &SearchClient,
        path: &Path,
        source_type: &str,
        campaign_id: Option<&str>,
    ) -> Result<IngestionResult, SearchError> {
        let source_name = path
            .file_name()
            .and_then(|n| n.to_str())
            .unwrap_or("unknown")
            .to_string();

        let chunks = if DocumentExtractor::is_supported(path) {
                // Use kreuzberg for all supported formats
                self.process_with_kreuzberg(path, &source_name).await?
            } else {
             // Fallback for unsupported formats (treat as plain text)
             match std::fs::read_to_string(path) {
                Ok(content) => self.chunk_text(&content, &source_name, None),
                Err(e) => {
                    return Err(SearchError::ConfigError(format!(
                        "Cannot read file or unsupported format: {}", e
                    )));
                }
            }
        };

        // Determine target index
        let index_name = SearchClient::select_index_for_source_type(source_type);

        // Build SearchDocuments
        let now = Utc::now().to_rfc3339();
        let documents: Vec<SearchDocument> = chunks
            .into_iter()
            .enumerate()
            .map(|(i, (content, page))| SearchDocument {
                id: format!("{}-{}", Uuid::new_v4(), i),
                content,
                source: source_name.clone(),
                source_type: source_type.to_string(),
                page_number: page,
                chunk_index: Some(i as u32),
                campaign_id: campaign_id.map(|s| s.to_string()),
                session_id: None,
                created_at: now.clone(),
                metadata: HashMap::new(),
            })
            .collect();

        let total_chunks = documents.len();

        // Ingest into Meilisearch
        search_client.add_documents(index_name, documents).await?;

        log::info!(
            "Ingested {} chunks from '{}' into index '{}'",
            total_chunks, source_name, index_name
        );

        Ok(IngestionResult {
            source: source_name,
            total_chunks,
            stored_chunks: total_chunks,
            failed_chunks: 0,
            index_used: index_name.to_string(),
        })
    }

    /// Process any document using kreuzberg (PDF, DOCX, EPUB, MOBI, images, etc.)
    ///
    /// Uses kreuzberg's async extraction for non-blocking processing.
    async fn process_with_kreuzberg(&self, path: &Path, source_name: &str) -> Result<Vec<(String, Option<u32>)>, SearchError> {
        // Use kreuzberg with OCR fallback for scanned documents
        let extractor = DocumentExtractor::with_ocr();

        // This is now async and uses proper page config
        let cb: Option<fn(f32, &str)> = None;
        let extracted = extractor.extract(path, cb)
            .await
            .map_err(|e| SearchError::ConfigError(format!("Document extraction failed: {}", e)))?;

        let total_text_len = extracted.char_count;
        let page_count = extracted.page_count;

        log::info!(
            "Extracted content from '{}': {} pages, {} chars",
            source_name, page_count, total_text_len
        );

        let mut all_chunks = Vec::new();

        // If we have distinct pages, chunk them individually to preserve page numbers
        if let Some(pages) = extracted.pages {
            for page in pages {
                // Calculate adaptive chunk size per page if needed, but for now global config is fine
                // or we could compute density per page.

                // For simplicity, use standard chunking on page content.
                // We could use the density logic here too if we cared about mixed-density docs.

                let page_len = page.content.len();
                let adaptive_min_chunk_size = if page_len < 100 { 10 } else { self.config.chunk_config.min_chunk_size };

                let page_chunks = self.chunk_text_adaptive(
                    &page.content,
                    source_name,
                    Some(page.page_number as u32),
                    adaptive_min_chunk_size
                );

                all_chunks.extend(page_chunks);
            }
        } else {
            // Fallback for formats without pages or if extraction failed to split pages
             // Calculate adaptive min_chunk_size based on overall extraction quality
            let avg_chars_per_page = if page_count > 0 {
                total_text_len / page_count
            } else {
                0
            };

            let adaptive_min_chunk_size = if avg_chars_per_page >= 2000 {
                self.config.chunk_config.min_chunk_size
            } else if avg_chars_per_page >= 500 {
                50.min(self.config.chunk_config.min_chunk_size)
            } else if avg_chars_per_page >= 100 {
                20.min(self.config.chunk_config.min_chunk_size)
            } else {
                10
            };

            all_chunks = self.chunk_text_adaptive(
                &extracted.content,
                source_name,
                None,
                adaptive_min_chunk_size,
            );
        }

        // Warn if no content extracted
        if all_chunks.is_empty() && total_text_len > 0 {
            log::warn!(
                "Document '{}' extracted {} chars but produced 0 chunks",
                source_name,
                total_text_len
            );
        }

        Ok(all_chunks)
    }

    /// Process a text file
    fn process_text_file(&self, path: &Path, source_name: &str) -> Result<Vec<(String, Option<u32>)>, SearchError> {
        let content = std::fs::read_to_string(path)
            .map_err(|e| SearchError::ConfigError(format!("Failed to read file: {}", e)))?;

        Ok(self.chunk_text(&content, source_name, None))
    }



    /// Chunk text content with overlap
    fn chunk_text(&self, text: &str, _source: &str, page_number: Option<u32>) -> Vec<(String, Option<u32>)> {
        self.chunk_text_adaptive(text, _source, page_number, self.config.chunk_config.min_chunk_size)
    }

    /// Chunk text content with overlap and custom min_chunk_size
    fn chunk_text_adaptive(
        &self,
        text: &str,
        _source: &str,
        page_number: Option<u32>,
        min_chunk_size: usize,
    ) -> Vec<(String, Option<u32>)> {
        let config = &self.config.chunk_config;
        let mut chunks = Vec::new();
        let text = text.trim();

        if text.is_empty() {
            return chunks;
        }

        // If text is smaller than chunk size, return as single chunk (even if below min)
        if text.len() <= config.chunk_size {
            // For adaptive mode, accept smaller chunks
            if text.len() >= min_chunk_size || min_chunk_size <= 10 {
                chunks.push((text.to_string(), page_number));
            }
            return chunks;
        }

        // Split into sentences for smarter chunking
        let sentences: Vec<&str> = text
            .split(|c| c == '.' || c == '!' || c == '?')
            .filter(|s| !s.trim().is_empty())
            .collect();

        let mut current_chunk = String::new();

        for sentence in sentences {
            let sentence = sentence.trim();
            let potential_len = current_chunk.len() + sentence.len() + 2; // +2 for ". "

            if potential_len > config.chunk_size && !current_chunk.is_empty() {
                // Save current chunk
                if current_chunk.len() >= min_chunk_size {
                    chunks.push((current_chunk.clone(), page_number));
                }

                // Start new chunk with overlap
                let overlap_start = current_chunk
                    .char_indices()
                    .rev()
                    .take(config.chunk_overlap)
                    .last()
                    .map(|(i, _)| i)
                    .unwrap_or(0);

                current_chunk = current_chunk[overlap_start..].to_string();
            }

            if !current_chunk.is_empty() {
                current_chunk.push_str(". ");
            }
            current_chunk.push_str(sentence);
        }

        // Don't forget the last chunk
        if current_chunk.len() >= min_chunk_size {
            chunks.push((current_chunk, page_number));
        }

        chunks
    }

    /// Ingest raw text content directly
    pub async fn ingest_text(
        &self,
        search_client: &SearchClient,
        content: &str,
        source: &str,
        source_type: &str,
        campaign_id: Option<&str>,
        metadata: Option<HashMap<String, String>>,
    ) -> Result<IngestionResult, SearchError> {
        let chunks = self.chunk_text(content, source, None);
        let index_name = SearchClient::select_index_for_source_type(source_type);
        let now = Utc::now().to_rfc3339();

        let documents: Vec<SearchDocument> = chunks
            .into_iter()
            .enumerate()
            .map(|(i, (text, _))| SearchDocument {
                id: format!("{}-{}", Uuid::new_v4(), i),
                content: text,
                source: source.to_string(),
                source_type: source_type.to_string(),
                page_number: None,
                chunk_index: Some(i as u32),
                campaign_id: campaign_id.map(|s| s.to_string()),
                session_id: None,
                created_at: now.clone(),
                metadata: metadata.clone().unwrap_or_default(),
            })
            .collect();

        let total_chunks = documents.len();
        search_client.add_documents(index_name, documents).await?;

        Ok(IngestionResult {
            source: source.to_string(),
            total_chunks,
            stored_chunks: total_chunks,
            failed_chunks: 0,
            index_used: index_name.to_string(),
        })
    }

    /// Ingest chat messages into the chat index
    pub async fn ingest_chat_messages(
        &self,
        search_client: &SearchClient,
        messages: Vec<(String, String)>, // (role, content)
        session_id: &str,
        campaign_id: Option<&str>,
    ) -> Result<IngestionResult, SearchError> {
        let now = Utc::now().to_rfc3339();

        let documents: Vec<SearchDocument> = messages
            .into_iter()
            .enumerate()
            .map(|(i, (role, content))| {
                let mut metadata = HashMap::new();
                metadata.insert("role".to_string(), role);

                SearchDocument {
                    id: format!("{}-{}", session_id, i),
                    content,
                    source: format!("session-{}", session_id),
                    source_type: "chat".to_string(),
                    page_number: None,
                    chunk_index: Some(i as u32),
                    campaign_id: campaign_id.map(|s| s.to_string()),
                    session_id: Some(session_id.to_string()),
                    created_at: now.clone(),
                    metadata,
                }
            })
            .collect();

        let total = documents.len();
        search_client.add_documents("chat", documents).await?;

        Ok(IngestionResult {
            source: format!("session-{}", session_id),
            total_chunks: total,
            stored_chunks: total,
            failed_chunks: 0,
            index_used: "chat".to_string(),
        })
    }
}

impl Default for MeilisearchPipeline {
    fn default() -> Self {
        Self::with_defaults()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_chunk_text_small() {
        let pipeline = MeilisearchPipeline::with_defaults();
        let chunks = pipeline.chunk_text("Small text.", "test", None);
        assert_eq!(chunks.len(), 1);
        assert_eq!(chunks[0].0, "Small text.");
    }

    #[test]
    fn test_chunk_text_with_sentences() {
        let pipeline = MeilisearchPipeline::new(PipelineConfig {
            chunk_config: ChunkConfig {
                chunk_size: 50,
                chunk_overlap: 10,
                min_chunk_size: 10,
            },
            ..Default::default()
        });

        let text = "First sentence. Second sentence. Third sentence. Fourth sentence.";
        let chunks = pipeline.chunk_text(text, "test", Some(1));

        assert!(chunks.len() > 1);
        for (_, page) in &chunks {
            assert_eq!(*page, Some(1));
        }
    }
}

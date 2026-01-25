//! Library Management Commands
//!
//! Commands for listing, deleting, updating, and managing library documents.

use tauri::State;

use crate::commands::AppState;
use super::types::{UpdateLibraryDocumentRequest, IngestResult, IngestProgress};

// ============================================================================
// Library Document Management
// ============================================================================

/// List all documents from the library (persisted in Meilisearch)
#[tauri::command]
pub async fn list_library_documents(
    state: State<'_, AppState>,
) -> Result<Vec<crate::core::search_client::LibraryDocumentMetadata>, String> {
    state.search_client
        .list_library_documents()
        .await
        .map_err(|e| format!("Failed to list documents: {}", e))
}

/// Delete a document from the library (removes metadata and content chunks)
#[tauri::command]
pub async fn delete_library_document(
    id: String,
    state: State<'_, AppState>,
) -> Result<(), String> {
    state.search_client
        .delete_library_document_with_content(&id)
        .await
        .map_err(|e| format!("Failed to delete document: {}", e))
}

/// Update a library document's TTRPG metadata
#[tauri::command]
pub async fn update_library_document(
    request: UpdateLibraryDocumentRequest,
    state: State<'_, AppState>,
) -> Result<crate::core::search_client::LibraryDocumentMetadata, String> {
    // Fetch existing document
    let mut doc = state.search_client
        .get_library_document(&request.id)
        .await
        .map_err(|e| format!("Failed to fetch document: {}", e))?
        .ok_or_else(|| format!("Document not found: {}", request.id))?;

    // Update TTRPG metadata fields
    doc.game_system = request.game_system;
    doc.setting = request.setting;
    doc.content_type = request.content_type;
    doc.publisher = request.publisher;

    // Save updated document
    state.search_client
        .save_library_document(&doc)
        .await
        .map_err(|e| format!("Failed to save document: {}", e))?;

    log::info!("Updated library document metadata: {}", request.id);
    Ok(doc)
}

/// Rebuild library metadata from existing content indices.
///
/// Scans all content indices for unique sources and creates metadata entries
/// for sources that don't already have entries. Useful for migrating legacy data.
#[tauri::command]
pub async fn rebuild_library_metadata(
    state: State<'_, AppState>,
) -> Result<usize, String> {
    let created = state.search_client
        .rebuild_library_metadata()
        .await
        .map_err(|e| format!("Failed to rebuild metadata: {}", e))?;

    Ok(created.len())
}

/// Clear a document's content and re-ingest from the original file.
///
/// Useful when ingestion produced garbage content (e.g., failed font decoding)
/// and you want to try again (possibly with OCR this time).
#[tauri::command]
pub async fn clear_and_reingest_document(
    id: String,
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<IngestResult, String> {
    use tauri::Emitter;

    // Get the document metadata to find the file path
    let doc = state.search_client
        .get_library_document(&id)
        .await
        .map_err(|e| format!("Failed to get document: {}", e))?
        .ok_or_else(|| "Document not found".to_string())?;

    let file_path = doc.file_path
        .ok_or_else(|| "Document has no file path - cannot re-ingest".to_string())?;

    // Verify file still exists
    let path = std::path::Path::new(&file_path);
    if !path.exists() {
        return Err(format!("Original file no longer exists: {}", file_path));
    }

    log::info!("Clearing and re-ingesting document: {} ({})", doc.name, id);

    // Delete existing content and metadata
    state.search_client
        .delete_library_document_with_content(&id)
        .await
        .map_err(|e| format!("Failed to delete existing content: {}", e))?;

    // Emit progress for clearing
    let _ = app.emit("ingest-progress", IngestProgress {
        stage: "clearing".to_string(),
        progress: 0.05,
        message: format!("Cleared old content, re-ingesting {}...", doc.name),
        source_name: doc.name.clone(),
    });

    // Re-ingest using the existing ingest logic
    let source_type = Some(doc.source_type.clone());

    // Call the internal ingestion logic
    ingest_document_with_progress_internal(
        file_path,
        source_type,
        app,
        state,
    ).await
}

/// Internal ingestion logic shared by ingest_document_with_progress and clear_and_reingest
pub(crate) async fn ingest_document_with_progress_internal(
    path: String,
    source_type: Option<String>,
    app: tauri::AppHandle,
    state: State<'_, AppState>,
) -> Result<IngestResult, String> {
    use tauri::Emitter;
    use crate::core::meilisearch_pipeline::MeilisearchPipeline;

    let path_buf = std::path::PathBuf::from(&path);
    if !path_buf.exists() {
        return Err(format!("File not found: {}", path));
    }

    let source_name = path_buf
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("unknown")
        .to_string();

    let source_type = source_type.unwrap_or_else(|| "document".to_string());

    // Stage 1: Parsing (0-40%)
    let _ = app.emit("ingest-progress", IngestProgress {
        stage: "parsing".to_string(),
        progress: 0.0,
        message: format!("Loading {}...", source_name),
        source_name: source_name.clone(),
    });

    let extension = path_buf
        .extension()
        .and_then(|e| e.to_str())
        .unwrap_or("")
        .to_lowercase();

    let file_size = std::fs::metadata(&path_buf)
        .map(|m| m.len())
        .unwrap_or(0);
    let estimated_pages = estimate_pdf_pages(&path_buf, file_size);

    let format_name = match extension.as_str() {
        "pdf" => "PDF",
        "epub" => "EPUB",
        "mobi" | "azw" | "azw3" => "MOBI/AZW",
        "docx" => "DOCX",
        "txt" => "text",
        "md" | "markdown" => "Markdown",
        _ => "document",
    };

    let _ = app.emit("ingest-progress", IngestProgress {
        stage: "parsing".to_string(),
        progress: 0.1,
        message: format!("Parsing {} (~{} estimated pages)...", format_name, estimated_pages),
        source_name: source_name.clone(),
    });

    let page_count: usize;
    let text_content: String;

    // Use kreuzberg for supported document formats (PDF, EPUB, DOCX, MOBI, etc.)
    if crate::ingestion::DocumentExtractor::is_supported(&path_buf) {
        use crate::ingestion::DocumentExtractor;

        // Use OCR-enabled extractor for scanned documents
        let extractor = DocumentExtractor::with_ocr();

        let _ = app.emit("ingest-progress", IngestProgress {
            stage: "parsing".to_string(),
            progress: 0.2,
            message: format!("Extracting {} with kreuzberg...", format_name),
            source_name: source_name.clone(),
        });

        // Clone for callback
        let app_handle = app.clone();
        let source_name_cb = source_name.clone();

        let progress_callback = move |p: f32, msg: &str| {
            let scaled_progress = 0.2 + (p * 0.2);

            let _ = app_handle.emit("ingest-progress", IngestProgress {
                stage: "parsing".to_string(),
                progress: scaled_progress,
                message: msg.to_string(),
                source_name: source_name_cb.clone(),
            });
        };

        let extracted = extractor.extract(&path_buf, Some(progress_callback))
            .await
            .map_err(|e| format!("Document extraction failed: {}", e))?;

        page_count = extracted.page_count;
        text_content = extracted.content;

        let _ = app.emit("ingest-progress", IngestProgress {
            stage: "parsing".to_string(),
            progress: 0.4,
            message: format!("Extracted {} pages ({} chars)", page_count, text_content.len()),
            source_name: source_name.clone(),
        });
    } else if extension == "txt" || extension == "md" || extension == "markdown" {
        // Plain text files - read directly
        text_content = std::fs::read_to_string(&path)
            .map_err(|e| format!("Failed to read file: {}", e))?;
        page_count = text_content.lines().count() / 50;

        let _ = app.emit("ingest-progress", IngestProgress {
            stage: "parsing".to_string(),
            progress: 0.4,
            message: format!("Loaded {} characters", text_content.len()),
            source_name: source_name.clone(),
        });
    } else {
        // Try to read as text for other formats
        text_content = std::fs::read_to_string(&path)
            .map_err(|e| format!("Unsupported format or failed to read: {}", e))?;
        page_count = 1;

        let _ = app.emit("ingest-progress", IngestProgress {
            stage: "parsing".to_string(),
            progress: 0.4,
            message: "File loaded".to_string(),
            source_name: source_name.clone(),
        });
    }

    // Stage 2: Chunking (40-60%)
    let _ = app.emit("ingest-progress", IngestProgress {
        stage: "chunking".to_string(),
        progress: 0.5,
        message: format!("Chunking {} characters...", text_content.len()),
        source_name: source_name.clone(),
    });

    // Stage 3: Indexing (60-100%)
    let _ = app.emit("ingest-progress", IngestProgress {
        stage: "indexing".to_string(),
        progress: 0.6,
        message: "Indexing to Meilisearch...".to_string(),
        source_name: source_name.clone(),
    });

    let pipeline = MeilisearchPipeline::default();
    let result = pipeline.ingest_text(
        &state.search_client,
        &text_content,
        &source_name,
        &source_type,
        None,
        None,
    )
    .await
    .map_err(|e| e.to_string())?;

    // Save document metadata
    let library_doc = crate::core::search_client::LibraryDocumentMetadata {
        id: uuid::Uuid::new_v4().to_string(),
        name: source_name.clone(),
        source_type: source_type.clone(),
        file_path: Some(path.clone()),
        page_count: page_count as u32,
        chunk_count: result.total_chunks as u32,
        character_count: text_content.len() as u64,
        content_index: result.index_used.clone(),
        status: "ready".to_string(),
        error_message: None,
        ingested_at: chrono::Utc::now().to_rfc3339(),
        // TTRPG metadata - user-editable, not set during ingestion
        game_system: None,
        setting: None,
        content_type: None,
        publisher: None,
    };

    if let Err(e) = state.search_client.save_library_document(&library_doc).await {
        log::warn!("Failed to save library document metadata: {}. Document indexed but may not persist.", e);
    }

    // Done!
    let _ = app.emit("ingest-progress", IngestProgress {
        stage: "complete".to_string(),
        progress: 1.0,
        message: format!("Indexed {} chunks", result.total_chunks),
        source_name: source_name.clone(),
    });

    Ok(IngestResult {
        page_count,
        character_count: text_content.len(),
        source_name: result.source,
    })
}

/// Estimate PDF page count using pdfinfo (fast) or file size heuristic
fn estimate_pdf_pages(path: &std::path::Path, file_size: u64) -> usize {
    // For PDFs, try to get actual page count from pdfinfo (very fast)
    if path.extension().and_then(|e| e.to_str()) == Some("pdf") {
        if let Ok(output) = std::process::Command::new("pdfinfo")
            .arg(path)
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            for line in stdout.lines() {
                if line.starts_with("Pages:") {
                    if let Some(count_str) = line.split(':').nth(1) {
                        if let Ok(count) = count_str.trim().parse::<usize>() {
                            return count;
                        }
                    }
                }
            }
        }
    }

    // Fallback: estimate based on file size
    // Use 200KB per page as middle ground between text (50KB) and scanned (500KB+)
    (file_size / 200_000).max(1) as usize
}

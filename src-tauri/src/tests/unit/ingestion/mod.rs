//! Ingestion Pipeline Unit Tests
//!
//! This module contains unit tests for the document ingestion pipeline components:
//! - PDF Parser: Text and metadata extraction from PDF files
//! - EPUB Parser: Chapter extraction, TOC parsing, and CSS stripping
//! - DOCX Parser: Text, table, and heading extraction from Word documents
//! - Semantic Chunker: Text chunking with overlap and boundary detection

mod pdf_parser_tests;
mod epub_parser_tests;
mod docx_parser_tests;
mod chunker_tests;

pub mod adaptive_learning;
pub mod pdf_parser;
pub mod epub_parser;
pub mod mobi_parser;
pub mod docx_parser;
pub mod personality;
pub mod flavor;
pub mod character_gen;
pub mod rulebook_linker;
pub mod chunker;
pub mod hash;
pub mod layout;
pub mod ttrpg;

pub use adaptive_learning::AdaptiveLearningSystem;
pub use pdf_parser::{PDFParser, ExtractedDocument, ExtractedPage, DocumentMetadata, PDFError};
pub use epub_parser::{EPUBParser, ExtractedEPUB, ExtractedChapter};
pub use mobi_parser::{MOBIParser, ExtractedMOBI, ExtractedSection};
pub use docx_parser::{DOCXParser, ExtractedDOCX};
pub use chunker::{
    SemanticChunker, ChunkConfig, ContentChunk,
    TTRPGChunker, TTRPGChunkConfig, SectionHierarchy,
};
pub use hash::{hash_file, hash_bytes, hash_file_with_size, get_file_size};
pub use layout::{
    ColumnDetector, ColumnBoundary, TextBlock,
    RegionDetector, DetectedRegion, RegionType, RegionBounds,
    TableExtractor, ExtractedTable,
};
pub use ttrpg::{
    TTRPGClassifier, TTRPGElementType, ClassifiedElement,
    StatBlockParser, StatBlockData, AbilityScores, Feature, Speed,
    RandomTableParser, RandomTableData, TableEntry,
    AttributeExtractor, TTRPGAttributes, AttributeMatch, AttributeSource, FilterableFields,
    GameVocabulary, DnD5eVocabulary, Pf2eVocabulary,
    detect_game_system, detect_game_system_with_confidence, GameSystem, DetectionResult,
};

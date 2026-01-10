//! TTRPG-Specific Content Processing Module
//!
//! This module provides specialized processing for Tabletop Role-Playing Game
//! content, including:
//!
//! - **Element Classification**: Detecting stat blocks, random tables, read-aloud text
//! - **Stat Block Parsing**: Extracting structured creature/NPC data
//! - **Random Table Parsing**: Extracting roll tables with probability distributions
//! - **Attribute Extraction**: Identifying game-specific terms with confidence scores
//! - **Game System Detection**: Auto-detecting D&D 5e, Pathfinder, etc.
//!
//! # Example
//!
//! ```ignore
//! use crate::ingestion::ttrpg::{TTRPGClassifier, AttributeExtractor, detect_game_system};
//!
//! let classifier = TTRPGClassifier::new();
//! let element = classifier.classify(text, page_number);
//!
//! let extractor = AttributeExtractor::new();
//! let attributes = extractor.extract(text);
//!
//! let game_system = detect_game_system(text);
//! ```

pub mod classifier;
pub mod stat_block;
pub mod random_table;
pub mod vocabulary;
pub mod attribute_extractor;
pub mod game_detector;

pub use classifier::{TTRPGClassifier, TTRPGElementType, ClassifiedElement};
pub use stat_block::{StatBlockParser, StatBlockData, AbilityScores, Feature, Speed};
pub use random_table::{RandomTableParser, RandomTableData, TableEntry};
pub use attribute_extractor::{
    AttributeExtractor, TTRPGAttributes, AttributeMatch, AttributeSource,
    FilterableFields,
};
pub use vocabulary::{GameVocabulary, DnD5eVocabulary, Pf2eVocabulary};
pub use game_detector::{detect_game_system, detect_game_system_with_confidence, GameSystem, DetectionResult};

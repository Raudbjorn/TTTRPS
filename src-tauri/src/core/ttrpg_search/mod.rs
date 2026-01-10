//! TTRPG Search Enhancement Module
//!
//! Provides intelligent search capabilities for TTRPG content including:
//! - Query parsing with negation support
//! - Antonym-based penalty scoring
//! - Reciprocal Rank Fusion (RRF) result ranking
//! - Background indexing queue with retry logic
//! - Meilisearch filter string building

pub mod query_parser;
pub mod antonym_mapper;
pub mod result_ranker;
pub mod index_queue;
pub mod attribute_filter;

pub use query_parser::{QueryParser, QueryConstraints, RequiredAttribute};
pub use antonym_mapper::AntonymMapper;
pub use result_ranker::{ResultRanker, RankingConfig, ScoreBreakdown, RankedResult, SearchCandidate};
pub use index_queue::{IndexQueue, PendingDocument};
pub use attribute_filter::AttributeFilter;

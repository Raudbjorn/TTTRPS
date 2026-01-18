//! Campaign Management Module
//!
//! Provides campaign versioning, world state tracking, entity relationship management,
//! and campaign generation features (arcs, phases, milestones, session planning).

pub mod versioning;
pub mod world_state;
pub mod relationships;

// Campaign Generation modules (TASK-CAMP-001 through TASK-CAMP-017)
pub mod meilisearch_indexes;
pub mod meilisearch_client;
pub mod migration;
pub mod arc_types;
pub mod phase_types;
pub mod milestone_types;

// Re-exports for convenience
pub use versioning::{
    CampaignVersion, VersionType, CampaignDiff, DiffEntry, DiffOperation, VersionManager,
};
pub use world_state::{
    WorldState, WorldEvent, WorldEventType, LocationState, NpcRelationshipState,
    InGameDate, WorldStateManager,
};
pub use relationships::{
    EntityRelationship, RelationshipType, EntityType, RelationshipStrength,
    RelationshipManager, EntityGraph, GraphNode, GraphEdge,
};

// Campaign Generation re-exports
pub use meilisearch_indexes::{
    IndexConfig, CampaignArcsIndexConfig, SessionPlansIndexConfig, PlotPointsIndexConfig,
    INDEX_CAMPAIGN_ARCS, INDEX_SESSION_PLANS, INDEX_PLOT_POINTS,
    all_campaign_indexes, get_index_configs,
};
pub use meilisearch_client::{
    MeilisearchCampaignClient, MeilisearchCampaignError, MEILISEARCH_BATCH_SIZE,
};
pub use migration::{
    MigrationReport, MigrationStatus, MigrationOptions, MigrationState,
    MigrationError, defaults as migration_defaults,
};
pub use arc_types::{
    ArcType, ArcStatus, CampaignArc, ArcSummary, ArcProgress,
};
pub use phase_types::{
    PhaseStatus, SessionRange, ArcPhase, PhaseProgress,
};
pub use milestone_types::{
    MilestoneType, MilestoneStatus, Milestone, MilestoneRef,
};

//! Database Migrations
//!
//! Handles schema creation and versioned migrations.

use sqlx::sqlite::SqlitePool;
use sqlx::Row;
use tracing::{info, warn};

/// Current database schema version
const SCHEMA_VERSION: i32 = 1;

/// Run all pending migrations
pub async fn run_migrations(pool: &SqlitePool) -> Result<(), sqlx::Error> {
    // Create migrations table if it doesn't exist
    sqlx::query(
        r#"
        CREATE TABLE IF NOT EXISTS _migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        "#
    )
    .execute(pool)
    .await?;

    // Get current version
    let current_version = get_current_version(pool).await?;

    info!(current_version, target_version = SCHEMA_VERSION, "Checking database migrations");

    if current_version < SCHEMA_VERSION {
        info!("Running database migrations from v{} to v{}", current_version, SCHEMA_VERSION);

        // Run migrations in order
        for version in (current_version + 1)..=SCHEMA_VERSION {
            run_migration(pool, version).await?;
        }

        info!("Database migrations completed successfully");
    }

    Ok(())
}

/// Get the current schema version
async fn get_current_version(pool: &SqlitePool) -> Result<i32, sqlx::Error> {
    let result = sqlx::query("SELECT MAX(version) as version FROM _migrations")
        .fetch_optional(pool)
        .await?;

    Ok(result
        .and_then(|row| row.try_get::<i32, _>("version").ok())
        .unwrap_or(0))
}

/// Run a specific migration version
async fn run_migration(pool: &SqlitePool, version: i32) -> Result<(), sqlx::Error> {
    let (name, sql) = match version {
        1 => ("initial_schema", MIGRATION_V1),
        _ => {
            warn!("Unknown migration version: {}", version);
            return Ok(());
        }
    };

    info!("Applying migration v{}: {}", version, name);

    // Execute migration SQL
    for statement in sql.split(";").filter(|s| !s.trim().is_empty()) {
        sqlx::query(statement.trim())
            .execute(pool)
            .await?;
    }

    // Record migration
    sqlx::query("INSERT INTO _migrations (version, name) VALUES (?, ?)")
        .bind(version)
        .bind(name)
        .execute(pool)
        .await?;

    Ok(())
}

/// Migration v1: Initial schema
const MIGRATION_V1: &str = r#"
-- Campaigns table
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    system TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_campaigns_updated ON campaigns(updated_at DESC);

-- Sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    session_number INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    started_at TEXT NOT NULL,
    ended_at TEXT,
    notes TEXT,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_campaign ON sessions(campaign_id);
CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status);

-- Characters table
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    name TEXT NOT NULL,
    system TEXT NOT NULL,
    character_type TEXT NOT NULL DEFAULT 'player',
    level INTEGER,
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_characters_campaign ON characters(campaign_id);
CREATE INDEX IF NOT EXISTS idx_characters_type ON characters(character_type);

-- NPCs table
CREATE TABLE IF NOT EXISTS npcs (
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    personality_json TEXT NOT NULL,
    stats_json TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_npcs_campaign ON npcs(campaign_id);

-- Combat encounters table
CREATE TABLE IF NOT EXISTS combats (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    round INTEGER NOT NULL DEFAULT 1,
    current_turn INTEGER NOT NULL DEFAULT 0,
    is_active INTEGER NOT NULL DEFAULT 1,
    combatants_json TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_combats_session ON combats(session_id);
CREATE INDEX IF NOT EXISTS idx_combats_active ON combats(is_active);

-- Campaign snapshots for versioning/rollback
CREATE TABLE IF NOT EXISTS campaign_snapshots (
    id TEXT PRIMARY KEY,
    campaign_id TEXT NOT NULL,
    description TEXT NOT NULL,
    snapshot_type TEXT NOT NULL DEFAULT 'manual',
    data_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_snapshots_campaign ON campaign_snapshots(campaign_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_created ON campaign_snapshots(created_at DESC);

-- Documents (ingested sources)
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    source_type TEXT NOT NULL,
    file_path TEXT,
    page_count INTEGER NOT NULL DEFAULT 0,
    chunk_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    ingested_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);

-- Usage tracking
CREATE TABLE IF NOT EXISTS usage_logs (
    id TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    input_tokens INTEGER NOT NULL,
    output_tokens INTEGER NOT NULL,
    estimated_cost_usd REAL NOT NULL DEFAULT 0.0,
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_usage_provider ON usage_logs(provider);
CREATE INDEX IF NOT EXISTS idx_usage_timestamp ON usage_logs(timestamp DESC);

-- Settings key-value store
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Session-specific usage (for tracking current session costs)
CREATE TABLE IF NOT EXISTS session_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_start TEXT NOT NULL,
    input_tokens INTEGER NOT NULL DEFAULT 0,
    output_tokens INTEGER NOT NULL DEFAULT 0,
    requests INTEGER NOT NULL DEFAULT 0,
    cost_usd REAL NOT NULL DEFAULT 0.0
);
"#;

//! Audit Log Commands
//!
//! Commands for querying, exporting, and managing security audit logs.

use std::collections::HashMap;
use tauri::State;

use crate::core::security::{
    SecurityAuditLogger, SecurityAuditEvent, AuditLogQuery, AuditSeverity, ExportFormat,
};

// ============================================================================
// Helper Functions
// ============================================================================

/// Parse a severity string into an AuditSeverity enum
fn parse_severity(severity_str: &str) -> AuditSeverity {
    match severity_str.to_lowercase().as_str() {
        "debug" => AuditSeverity::Debug,
        "info" => AuditSeverity::Info,
        "warning" => AuditSeverity::Warning,
        "security" => AuditSeverity::Security,
        "critical" => AuditSeverity::Critical,
        _ => AuditSeverity::Info,
    }
}

// ============================================================================
// State Types
// ============================================================================

/// State wrapper for audit logging
pub struct AuditLoggerState {
    pub logger: SecurityAuditLogger,
}

impl Default for AuditLoggerState {
    fn default() -> Self {
        // Initialize with file logging to the app data directory
        let log_dir = dirs::data_local_dir()
            .unwrap_or_else(|| std::path::PathBuf::from("."))
            .join("ai-rpg")
            .join("logs");

        Self {
            logger: SecurityAuditLogger::with_file_logging(log_dir),
        }
    }
}

impl AuditLoggerState {
    /// Create with custom log directory
    pub fn with_log_dir(log_dir: std::path::PathBuf) -> Self {
        Self {
            logger: SecurityAuditLogger::with_file_logging(log_dir),
        }
    }
}

// ============================================================================
// Audit Log Commands
// ============================================================================

/// Get recent audit events
#[tauri::command]
pub fn get_audit_logs(
    count: Option<usize>,
    min_severity: Option<String>,
    state: State<'_, AuditLoggerState>,
) -> Vec<SecurityAuditEvent> {
    let count = count.unwrap_or(100);

    if let Some(severity_str) = min_severity {
        let severity = parse_severity(&severity_str);
        state.logger.get_by_severity(severity).into_iter().take(count).collect()
    } else {
        state.logger.get_recent(count)
    }
}

/// Query audit logs with filters
#[tauri::command]
pub fn query_audit_logs(
    from_hours: Option<i64>,
    min_severity: Option<String>,
    event_types: Option<Vec<String>>,
    search_text: Option<String>,
    limit: Option<usize>,
    state: State<'_, AuditLoggerState>,
) -> Vec<SecurityAuditEvent> {
    let from = from_hours.map(|h| chrono::Utc::now() - chrono::Duration::hours(h));
    let min_sev = min_severity.map(|s| parse_severity(&s));

    state.logger.query(AuditLogQuery {
        from,
        to: None,
        min_severity: min_sev,
        event_types,
        search_text,
        limit,
        offset: None,
    })
}

/// Export audit logs
#[tauri::command]
pub fn export_audit_logs(
    format: String,
    from_hours: Option<i64>,
    state: State<'_, AuditLoggerState>,
) -> Result<String, String> {
    let export_format = match format.to_lowercase().as_str() {
        "json" => ExportFormat::Json,
        "csv" => ExportFormat::Csv,
        "jsonl" => ExportFormat::Jsonl,
        _ => return Err(format!("Unsupported format: {}", format)),
    };

    let query = AuditLogQuery {
        from: from_hours.map(|h| chrono::Utc::now() - chrono::Duration::hours(h)),
        ..Default::default()
    };

    state.logger.export(query, export_format)
}

/// Clear old audit logs (older than specified days)
///
/// # Arguments
/// * `days` - Number of days to keep. Must be positive. Logs older than this will be deleted.
#[tauri::command]
pub fn clear_old_logs(days: i64, state: State<'_, AuditLoggerState>) -> Result<usize, String> {
    if days <= 0 {
        return Err("Days must be a positive number".to_string());
    }
    Ok(state.logger.cleanup(days))
}

/// Get security event counts by severity
#[tauri::command]
pub fn get_audit_summary(state: State<'_, AuditLoggerState>) -> HashMap<String, usize> {
    state.logger.count_by_severity()
}

/// Get recent security-level events (last 24 hours)
#[tauri::command]
pub fn get_security_events(state: State<'_, AuditLoggerState>) -> Vec<SecurityAuditEvent> {
    state.logger.get_security_events()
}

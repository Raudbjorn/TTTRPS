//! Helper Macros for Command State Access
//!
//! Reduces boilerplate for common state access patterns in Tauri commands.

/// Access read-locked state manager
#[macro_export]
macro_rules! read_state {
    ($state:expr, $field:ident) => {
        $state.$field.read().await
    };
}

/// Access write-locked state manager
#[macro_export]
macro_rules! write_state {
    ($state:expr, $field:ident) => {
        $state.$field.write().await
    };
}

/// Helper macro to reduce boilerplate for database access in Tauri commands.
///
/// Usage:
/// ```ignore
/// with_db!(db, |db| db.some_method(&arg1, &arg2))
/// ```
#[macro_export]
macro_rules! with_db {
    ($db_state:expr, |$db:ident| $body:expr) => {{
        let db_guard = $db_state.read().await;
        let $db = db_guard.as_ref().ok_or("Database not initialized")?;
        $body.await.map_err(|e| e.to_string())
    }};
}

pub use read_state;
pub use write_state;
pub use with_db;

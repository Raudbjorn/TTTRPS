pub mod manager;
pub mod metadata;

// Re-export key types
pub use manager::{SettingsManager, UnifiedSettings};
pub use metadata::UnifiedSettingsMetadata;

#[cfg(test)]
mod tests;

#[cfg(test)]
mod tests {
    use crate::core::settings::{UnifiedSettings, metadata::UnifiedSettingsMetadata};

    #[test]
    fn test_default_settings() {
        let settings = UnifiedSettings::default();
        assert!(settings.llm.is_none());
        // Voice config has defaults?
        // Extraction starts with default?
        // Just smoke test that it constructs
    }

    #[test]
    fn test_metadata_generation() {
        let metadata = UnifiedSettingsMetadata::generate();
        assert!(!metadata.llm.is_empty());
        assert!(!metadata.extraction.is_empty());
        assert!(!metadata.voice.is_empty());

        // specific check
        let llm_provider = metadata.llm.iter().find(|f| f.key == "provider").expect("Provider field missing");
        assert_eq!(llm_provider.options.as_ref().map(|v| v.len()).unwrap_or(0), 12); // approx count of providers
    }

    #[test]
    fn test_serialization() {
        let settings = UnifiedSettings::default();
        let json = serde_json::to_string(&settings).unwrap();
        let loaded: UnifiedSettings = serde_json::from_str(&json).unwrap();
        assert_eq!(settings.id, loaded.id);
    }
}

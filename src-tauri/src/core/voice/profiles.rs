//! Voice Profile System
//!
//! Manages voice profiles for NPCs and DM narration, with preset personas
//! and customizable settings.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::RwLock;
use uuid::Uuid;
use chrono::{DateTime, Utc};

use super::types::{VoiceSettings, VoiceProviderType};

// ============================================================================
// Voice Profile Types
// ============================================================================

/// A voice profile that can be linked to NPCs or used for narration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VoiceProfile {
    /// Unique profile ID
    pub id: String,
    /// Display name for the profile
    pub name: String,
    /// Description of the voice/character
    pub description: Option<String>,
    /// Voice provider to use
    pub provider: VoiceProviderType,
    /// Provider-specific voice ID
    pub voice_id: String,
    /// Voice synthesis settings
    pub settings: VoiceSettings,
    /// Profile metadata
    pub metadata: VoiceProfileMetadata,
    /// Whether this is a preset (non-deletable)
    pub is_preset: bool,
    /// Creation timestamp
    pub created_at: DateTime<Utc>,
    /// Last updated timestamp
    pub updated_at: DateTime<Utc>,
}

/// Metadata for voice profiles
#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct VoiceProfileMetadata {
    /// Age category (child, young, adult, middle-aged, elderly)
    pub age: Option<VoiceAge>,
    /// Gender presentation
    pub gender: Option<VoiceGender>,
    /// Personality traits
    pub personality: Vec<String>,
    /// Accent or dialect
    pub accent: Option<String>,
    /// Speaking style (formal, casual, dramatic, etc.)
    pub style: Option<String>,
    /// Character archetype (wizard, warrior, merchant, etc.)
    pub archetype: Option<String>,
    /// Tags for categorization
    pub tags: Vec<String>,
}

/// Voice age category
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum VoiceAge {
    Child,
    Young,
    Adult,
    MiddleAged,
    Elderly,
}

/// Voice gender presentation
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum VoiceGender {
    Masculine,
    Feminine,
    Neutral,
    Androgynous,
}

impl VoiceProfile {
    /// Create a new voice profile
    pub fn new(name: impl Into<String>, provider: VoiceProviderType, voice_id: impl Into<String>) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            name: name.into(),
            description: None,
            provider,
            voice_id: voice_id.into(),
            settings: VoiceSettings::default(),
            metadata: VoiceProfileMetadata::default(),
            is_preset: false,
            created_at: now,
            updated_at: now,
        }
    }

    /// Create a preset profile (non-deletable)
    pub fn preset(
        id: impl Into<String>,
        name: impl Into<String>,
        description: impl Into<String>,
        provider: VoiceProviderType,
        voice_id: impl Into<String>,
        metadata: VoiceProfileMetadata,
    ) -> Self {
        let now = Utc::now();
        Self {
            id: id.into(),
            name: name.into(),
            description: Some(description.into()),
            provider,
            voice_id: voice_id.into(),
            settings: VoiceSettings::default(),
            metadata,
            is_preset: true,
            created_at: now,
            updated_at: now,
        }
    }

    /// Update the profile
    pub fn update(&mut self) {
        self.updated_at = Utc::now();
    }

    /// Set description
    pub fn with_description(mut self, desc: impl Into<String>) -> Self {
        self.description = Some(desc.into());
        self
    }

    /// Set settings
    pub fn with_settings(mut self, settings: VoiceSettings) -> Self {
        self.settings = settings;
        self
    }

    /// Set metadata
    pub fn with_metadata(mut self, metadata: VoiceProfileMetadata) -> Self {
        self.metadata = metadata;
        self
    }
}

// ============================================================================
// Voice Profile Store
// ============================================================================

/// Manages voice profiles with CRUD operations
pub struct VoiceProfileStore {
    /// All profiles indexed by ID
    profiles: RwLock<HashMap<String, VoiceProfile>>,
    /// NPC to profile mappings (npc_id -> profile_id)
    npc_mappings: RwLock<HashMap<String, String>>,
    /// Default profile ID for narration
    default_narration_id: RwLock<Option<String>>,
}

impl VoiceProfileStore {
    /// Create a new profile store with presets loaded
    pub fn new() -> Self {
        let store = Self {
            profiles: RwLock::new(HashMap::new()),
            npc_mappings: RwLock::new(HashMap::new()),
            default_narration_id: RwLock::new(None),
        };

        // Load preset profiles
        store.load_presets();

        store
    }

    /// Load preset DM personas
    fn load_presets(&self) {
        let presets = get_preset_profiles();
        let mut profiles = self.profiles.write().unwrap();

        for preset in presets {
            profiles.insert(preset.id.clone(), preset);
        }

        // Set default narration to first preset
        if let Some(first) = profiles.values().find(|p| p.is_preset && p.metadata.tags.contains(&"narration".to_string())) {
            let mut default = self.default_narration_id.write().unwrap();
            *default = Some(first.id.clone());
        }
    }

    // ========================================================================
    // CRUD Operations
    // ========================================================================

    /// Create a new profile
    pub fn create(&self, profile: VoiceProfile) -> VoiceProfile {
        let mut profiles = self.profiles.write().unwrap();
        let id = profile.id.clone();
        profiles.insert(id, profile.clone());
        profile
    }

    /// Get a profile by ID
    pub fn get(&self, id: &str) -> Option<VoiceProfile> {
        let profiles = self.profiles.read().unwrap();
        profiles.get(id).cloned()
    }

    /// Update a profile
    pub fn update(&self, id: &str, mut profile: VoiceProfile) -> Option<VoiceProfile> {
        let mut profiles = self.profiles.write().unwrap();

        // Don't allow updating presets' core properties
        if let Some(existing) = profiles.get(id) {
            if existing.is_preset {
                // Only allow updating settings for presets
                profile.id = existing.id.clone();
                profile.name = existing.name.clone();
                profile.is_preset = true;
            }
        }

        profile.update();
        profiles.insert(id.to_string(), profile.clone());
        Some(profile)
    }

    /// Delete a profile
    pub fn delete(&self, id: &str) -> bool {
        let mut profiles = self.profiles.write().unwrap();

        // Don't allow deleting presets
        if let Some(profile) = profiles.get(id) {
            if profile.is_preset {
                return false;
            }
        }

        profiles.remove(id).is_some()
    }

    /// List all profiles
    pub fn list(&self) -> Vec<VoiceProfile> {
        let profiles = self.profiles.read().unwrap();
        profiles.values().cloned().collect()
    }

    /// List preset profiles only
    pub fn list_presets(&self) -> Vec<VoiceProfile> {
        let profiles = self.profiles.read().unwrap();
        profiles.values().filter(|p| p.is_preset).cloned().collect()
    }

    /// List custom (non-preset) profiles only
    pub fn list_custom(&self) -> Vec<VoiceProfile> {
        let profiles = self.profiles.read().unwrap();
        profiles.values().filter(|p| !p.is_preset).cloned().collect()
    }

    /// Search profiles by name or tags
    pub fn search(&self, query: &str) -> Vec<VoiceProfile> {
        let profiles = self.profiles.read().unwrap();
        let query_lower = query.to_lowercase();

        profiles.values()
            .filter(|p| {
                p.name.to_lowercase().contains(&query_lower)
                    || p.metadata.tags.iter().any(|t| t.to_lowercase().contains(&query_lower))
                    || p.metadata.archetype.as_ref().map(|a| a.to_lowercase().contains(&query_lower)).unwrap_or(false)
                    || p.description.as_ref().map(|d| d.to_lowercase().contains(&query_lower)).unwrap_or(false)
            })
            .cloned()
            .collect()
    }

    // ========================================================================
    // NPC Mapping
    // ========================================================================

    /// Link an NPC to a voice profile
    pub fn link_npc(&self, npc_id: &str, profile_id: &str) -> bool {
        // Verify profile exists
        let profiles = self.profiles.read().unwrap();
        if !profiles.contains_key(profile_id) {
            return false;
        }
        drop(profiles);

        let mut mappings = self.npc_mappings.write().unwrap();
        mappings.insert(npc_id.to_string(), profile_id.to_string());
        true
    }

    /// Unlink an NPC from its voice profile
    pub fn unlink_npc(&self, npc_id: &str) -> bool {
        let mut mappings = self.npc_mappings.write().unwrap();
        mappings.remove(npc_id).is_some()
    }

    /// Get the profile linked to an NPC
    pub fn get_npc_profile(&self, npc_id: &str) -> Option<VoiceProfile> {
        let mappings = self.npc_mappings.read().unwrap();
        let profile_id = mappings.get(npc_id)?;

        let profiles = self.profiles.read().unwrap();
        profiles.get(profile_id).cloned()
    }

    /// List all NPC mappings
    pub fn list_npc_mappings(&self) -> HashMap<String, String> {
        let mappings = self.npc_mappings.read().unwrap();
        mappings.clone()
    }

    // ========================================================================
    // Default Profile
    // ========================================================================

    /// Set the default narration profile
    pub fn set_default_narration(&self, profile_id: &str) -> bool {
        // Verify profile exists
        let profiles = self.profiles.read().unwrap();
        if !profiles.contains_key(profile_id) {
            return false;
        }
        drop(profiles);

        let mut default = self.default_narration_id.write().unwrap();
        *default = Some(profile_id.to_string());
        true
    }

    /// Get the default narration profile
    pub fn get_default_narration(&self) -> Option<VoiceProfile> {
        let default = self.default_narration_id.read().unwrap();
        let profile_id = default.as_ref()?;

        self.get(profile_id)
    }
}

impl Default for VoiceProfileStore {
    fn default() -> Self {
        Self::new()
    }
}

// ============================================================================
// Preset Profiles
// ============================================================================

/// Get all preset DM/narrator voice profiles
pub fn get_preset_profiles() -> Vec<VoiceProfile> {
    vec![
        // Classic DM Narrators
        VoiceProfile::preset(
            "preset-dm-classic",
            "Classic Dungeon Master",
            "The quintessential DM voice - dramatic, authoritative, and immersive",
            VoiceProviderType::ElevenLabs,
            "pNInz6obpgDQGcFmaJgB", // Adam
            VoiceProfileMetadata {
                age: Some(VoiceAge::MiddleAged),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["dramatic".into(), "authoritative".into(), "theatrical".into()],
                style: Some("dramatic narration".into()),
                archetype: Some("dungeon master".into()),
                tags: vec!["narration".into(), "dm".into(), "classic".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-dm-storyteller",
            "Wise Storyteller",
            "Warm and engaging narrator with a gift for building suspense",
            VoiceProviderType::ElevenLabs,
            "EXAVITQu4vr4xnSDxMaL", // Bella
            VoiceProfileMetadata {
                age: Some(VoiceAge::Elderly),
                gender: Some(VoiceGender::Feminine),
                personality: vec!["warm".into(), "wise".into(), "patient".into()],
                style: Some("storytelling".into()),
                archetype: Some("storyteller".into()),
                tags: vec!["narration".into(), "storyteller".into(), "wise".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-dm-dark",
            "Dark Chronicles",
            "Ominous and foreboding voice for horror and dark fantasy",
            VoiceProviderType::ElevenLabs,
            "VR6AewLTigWG4xSOukaG", // Arnold
            VoiceProfileMetadata {
                age: Some(VoiceAge::Adult),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["ominous".into(), "mysterious".into(), "intense".into()],
                style: Some("dark narration".into()),
                archetype: Some("dark narrator".into()),
                tags: vec!["narration".into(), "horror".into(), "dark".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-dm-epic",
            "Epic Herald",
            "Grand and sweeping voice for epic fantasy adventures",
            VoiceProviderType::ElevenLabs,
            "TxGEqnHWrfWFTfGW9XjX", // Josh
            VoiceProfileMetadata {
                age: Some(VoiceAge::Adult),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["heroic".into(), "grandiose".into(), "inspiring".into()],
                style: Some("epic narration".into()),
                archetype: Some("herald".into()),
                tags: vec!["narration".into(), "epic".into(), "heroic".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-dm-whimsical",
            "Whimsical Narrator",
            "Playful and lighthearted voice for comedic or fairy tale adventures",
            VoiceProviderType::ElevenLabs,
            "jsCqWAovK2LkecY7zXl4", // Freya
            VoiceProfileMetadata {
                age: Some(VoiceAge::Young),
                gender: Some(VoiceGender::Feminine),
                personality: vec!["playful".into(), "whimsical".into(), "cheerful".into()],
                style: Some("lighthearted".into()),
                archetype: Some("fairy tale narrator".into()),
                tags: vec!["narration".into(), "comedy".into(), "whimsical".into()],
                ..Default::default()
            },
        ),

        // Character Archetypes
        VoiceProfile::preset(
            "preset-char-wizard",
            "Ancient Wizard",
            "Wise and mysterious voice befitting a powerful arcane caster",
            VoiceProviderType::ElevenLabs,
            "onwK4e9ZLuTAKqWW03F9", // Daniel
            VoiceProfileMetadata {
                age: Some(VoiceAge::Elderly),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["wise".into(), "mysterious".into(), "scholarly".into()],
                accent: Some("arcane".into()),
                archetype: Some("wizard".into()),
                tags: vec!["character".into(), "wizard".into(), "magic".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-char-warrior",
            "Battle-Hardened Warrior",
            "Gruff and commanding voice of a seasoned fighter",
            VoiceProviderType::ElevenLabs,
            "yoZ06aMxZJJ28mfd3POQ", // Sam
            VoiceProfileMetadata {
                age: Some(VoiceAge::MiddleAged),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["gruff".into(), "commanding".into(), "battle-worn".into()],
                archetype: Some("warrior".into()),
                tags: vec!["character".into(), "warrior".into(), "fighter".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-char-rogue",
            "Sly Rogue",
            "Quick-witted and charming voice with a hint of mischief",
            VoiceProviderType::ElevenLabs,
            "SOYHLrjzK2X1ezoPC6cr", // Harry
            VoiceProfileMetadata {
                age: Some(VoiceAge::Young),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["witty".into(), "charming".into(), "sly".into()],
                archetype: Some("rogue".into()),
                tags: vec!["character".into(), "rogue".into(), "thief".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-char-noble",
            "Aristocratic Noble",
            "Refined and haughty voice befitting royalty or nobility",
            VoiceProviderType::ElevenLabs,
            "GBv7mTt0atIp3Br8iCZE", // Thomas
            VoiceProfileMetadata {
                age: Some(VoiceAge::Adult),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["refined".into(), "proud".into(), "aristocratic".into()],
                accent: Some("aristocratic".into()),
                style: Some("formal".into()),
                archetype: Some("noble".into()),
                tags: vec!["character".into(), "noble".into(), "royalty".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-char-merchant",
            "Friendly Merchant",
            "Jovial and persuasive voice of a traveling trader",
            VoiceProviderType::ElevenLabs,
            "g5CIjZEefAph4nQFvHAz", // Ethan
            VoiceProfileMetadata {
                age: Some(VoiceAge::MiddleAged),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["friendly".into(), "persuasive".into(), "jovial".into()],
                archetype: Some("merchant".into()),
                tags: vec!["character".into(), "merchant".into(), "trader".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-char-tavern",
            "Tavern Keeper",
            "Warm and welcoming voice of a friendly innkeeper",
            VoiceProviderType::ElevenLabs,
            "N2lVS1w4EtoT3dr4eOWO", // Callum
            VoiceProfileMetadata {
                age: Some(VoiceAge::MiddleAged),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["warm".into(), "welcoming".into(), "hearty".into()],
                archetype: Some("innkeeper".into()),
                tags: vec!["character".into(), "tavern".into(), "innkeeper".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-char-villain",
            "Sinister Villain",
            "Dark and menacing voice for antagonists and evil-doers",
            VoiceProviderType::ElevenLabs,
            "JBFqnCBsd6RMkjVDRZzb", // George
            VoiceProfileMetadata {
                age: Some(VoiceAge::Adult),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["sinister".into(), "menacing".into(), "calculating".into()],
                archetype: Some("villain".into()),
                tags: vec!["character".into(), "villain".into(), "antagonist".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-char-cleric",
            "Devout Cleric",
            "Calm and reassuring voice of a faithful healer",
            VoiceProviderType::ElevenLabs,
            "flq6f7yk4E4fJM5XTYuZ", // Michael
            VoiceProfileMetadata {
                age: Some(VoiceAge::Adult),
                gender: Some(VoiceGender::Masculine),
                personality: vec!["calm".into(), "reassuring".into(), "devout".into()],
                archetype: Some("cleric".into()),
                tags: vec!["character".into(), "cleric".into(), "healer".into()],
                ..Default::default()
            },
        ),

        // OpenAI presets (for users who prefer OpenAI TTS)
        VoiceProfile::preset(
            "preset-openai-alloy",
            "Balanced Narrator (Alloy)",
            "Neutral and balanced voice for general narration",
            VoiceProviderType::OpenAI,
            "alloy",
            VoiceProfileMetadata {
                gender: Some(VoiceGender::Neutral),
                personality: vec!["balanced".into(), "neutral".into(), "clear".into()],
                style: Some("narration".into()),
                tags: vec!["narration".into(), "openai".into(), "neutral".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-openai-onyx",
            "Deep Narrator (Onyx)",
            "Deep and authoritative voice for dramatic moments",
            VoiceProviderType::OpenAI,
            "onyx",
            VoiceProfileMetadata {
                gender: Some(VoiceGender::Masculine),
                personality: vec!["deep".into(), "authoritative".into(), "resonant".into()],
                style: Some("dramatic".into()),
                tags: vec!["narration".into(), "openai".into(), "dramatic".into()],
                ..Default::default()
            },
        ),
        VoiceProfile::preset(
            "preset-openai-nova",
            "Warm Narrator (Nova)",
            "Warm and engaging voice for storytelling",
            VoiceProviderType::OpenAI,
            "nova",
            VoiceProfileMetadata {
                gender: Some(VoiceGender::Feminine),
                personality: vec!["warm".into(), "engaging".into(), "friendly".into()],
                style: Some("storytelling".into()),
                tags: vec!["narration".into(), "openai".into(), "warm".into()],
                ..Default::default()
            },
        ),
    ]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_profile_creation() {
        let profile = VoiceProfile::new("Test Voice", VoiceProviderType::ElevenLabs, "test-id");
        assert_eq!(profile.name, "Test Voice");
        assert!(!profile.is_preset);
    }

    #[test]
    fn test_store_crud() {
        let store = VoiceProfileStore::new();

        // Create
        let profile = VoiceProfile::new("Custom Voice", VoiceProviderType::OpenAI, "alloy");
        let created = store.create(profile);
        assert_eq!(created.name, "Custom Voice");

        // Read
        let fetched = store.get(&created.id).unwrap();
        assert_eq!(fetched.name, "Custom Voice");

        // Update
        let mut updated = fetched.clone();
        updated.name = "Updated Voice".to_string();
        store.update(&created.id, updated);
        let refetched = store.get(&created.id).unwrap();
        assert_eq!(refetched.name, "Updated Voice");

        // Delete
        assert!(store.delete(&created.id));
        assert!(store.get(&created.id).is_none());
    }

    #[test]
    fn test_preset_protection() {
        let store = VoiceProfileStore::new();

        // Presets should be loaded
        let presets = store.list_presets();
        assert!(!presets.is_empty());

        // Cannot delete presets
        let preset_id = &presets[0].id;
        assert!(!store.delete(preset_id));
        assert!(store.get(preset_id).is_some());
    }

    #[test]
    fn test_npc_mapping() {
        let store = VoiceProfileStore::new();
        let presets = store.list_presets();
        let profile_id = &presets[0].id;

        // Link NPC
        assert!(store.link_npc("npc-1", profile_id));

        // Get linked profile
        let linked = store.get_npc_profile("npc-1").unwrap();
        assert_eq!(&linked.id, profile_id);

        // Unlink
        assert!(store.unlink_npc("npc-1"));
        assert!(store.get_npc_profile("npc-1").is_none());
    }

    #[test]
    fn test_preset_count() {
        let presets = get_preset_profiles();
        // Should have at least 13 presets as per requirements
        assert!(presets.len() >= 13, "Expected at least 13 presets, got {}", presets.len());
    }
}

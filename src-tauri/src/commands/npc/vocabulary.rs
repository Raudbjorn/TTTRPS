//! NPC Vocabulary Commands
//!
//! Commands for loading and using NPC vocabulary banks.

use crate::core::npc_gen::{
    VocabularyBank as NpcVocabularyBank, Formality, PhraseEntry,
    load_yaml_file, get_vocabulary_dir,
};

// ============================================================================
// NPC Vocabulary Commands
// ============================================================================

/// Load a vocabulary bank from YAML file (legacy NPC format)
#[tauri::command]
pub async fn load_vocabulary_bank(path: String) -> Result<NpcVocabularyBank, String> {
    load_yaml_file(&std::path::PathBuf::from(path))
        .await
        .map_err(|e| e.to_string())
}

/// Get the vocabulary directory path
#[tauri::command]
pub fn get_vocabulary_directory() -> String {
    get_vocabulary_dir().to_string_lossy().to_string()
}

/// Get a random phrase from a vocabulary bank (legacy NPC format)
#[tauri::command]
pub fn get_vocabulary_phrase(
    bank: NpcVocabularyBank,
    category: String,
    formality: String,
) -> Result<Option<PhraseEntry>, String> {
    let formality = Formality::from_str(&formality);
    let mut rng = rand::thread_rng();

    let phrase = match category.as_str() {
        "greeting" | "greetings" => bank.get_greeting(formality, &mut rng),
        "farewell" | "farewells" => bank.get_farewell(formality, &mut rng),
        "exclamation" | "exclamations" => bank.get_exclamation(&mut rng),
        "negotiation" => bank.get_negotiation_phrase(&mut rng),
        "combat" => bank.get_combat_phrase(&mut rng),
        _ => None,
    };

    Ok(phrase.cloned())
}

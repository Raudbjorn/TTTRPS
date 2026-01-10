//! Game System Detection Module
//!
//! Auto-detects the TTRPG game system from document content using
//! pattern matching on system-specific terminology.

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

// ============================================================================
// Types
// ============================================================================

/// Supported TTRPG game systems.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
pub enum GameSystem {
    /// Dungeons & Dragons 5th Edition
    DnD5e,
    /// Pathfinder 2nd Edition
    Pathfinder2e,
    /// Call of Cthulhu
    CallOfCthulhu,
    /// World of Darkness / Chronicles of Darkness
    WorldOfDarkness,
    /// Shadowrun
    Shadowrun,
    /// FATE
    Fate,
    /// Powered by the Apocalypse games
    PbtA,
    /// Unknown or unsupported system
    Other,
}

impl GameSystem {
    /// Get a human-readable name for this game system.
    pub fn as_str(&self) -> &'static str {
        match self {
            Self::DnD5e => "dnd5e",
            Self::Pathfinder2e => "pf2e",
            Self::CallOfCthulhu => "coc",
            Self::WorldOfDarkness => "wod",
            Self::Shadowrun => "shadowrun",
            Self::Fate => "fate",
            Self::PbtA => "pbta",
            Self::Other => "other",
        }
    }

    /// Get a display name for this game system.
    pub fn display_name(&self) -> &'static str {
        match self {
            Self::DnD5e => "D&D 5th Edition",
            Self::Pathfinder2e => "Pathfinder 2e",
            Self::CallOfCthulhu => "Call of Cthulhu",
            Self::WorldOfDarkness => "World of Darkness",
            Self::Shadowrun => "Shadowrun",
            Self::Fate => "FATE",
            Self::PbtA => "Powered by the Apocalypse",
            Self::Other => "Unknown System",
        }
    }
}

// ============================================================================
// Detection
// ============================================================================

/// Detection result with confidence.
#[derive(Debug, Clone)]
pub struct DetectionResult {
    /// The detected game system
    pub system: GameSystem,
    /// Confidence score (0.0 to 1.0)
    pub confidence: f32,
    /// Indicators that matched
    pub matched_indicators: Vec<String>,
}

/// Indicator patterns for each game system.
struct SystemIndicators {
    /// Patterns that strongly indicate this system
    strong: Vec<&'static str>,
    /// Patterns that weakly indicate this system
    weak: Vec<&'static str>,
}

/// Detect the game system from document content.
///
/// # Arguments
/// * `text` - The document text to analyze
///
/// # Returns
/// * `Option<GameSystem>` - The detected system, or None if confidence is too low
pub fn detect_game_system(text: &str) -> Option<GameSystem> {
    let result = detect_game_system_with_confidence(text);
    if result.confidence >= 0.5 {
        Some(result.system)
    } else {
        None
    }
}

/// Detect the game system with detailed confidence information.
pub fn detect_game_system_with_confidence(text: &str) -> DetectionResult {
    let text_lower = text.to_lowercase();
    let indicators = get_system_indicators();

    let mut scores: HashMap<GameSystem, (f32, Vec<String>)> = HashMap::new();

    for (system, patterns) in &indicators {
        let mut score = 0.0_f32;
        let mut matched = Vec::new();

        // Strong indicators (1.0 each)
        for pattern in &patterns.strong {
            if text_lower.contains(pattern) {
                score += 1.0;
                matched.push(pattern.to_string());
            }
        }

        // Weak indicators (0.3 each)
        for pattern in &patterns.weak {
            if text_lower.contains(pattern) {
                score += 0.3;
                matched.push(pattern.to_string());
            }
        }

        scores.insert(*system, (score, matched));
    }

    // Find the system with the highest score
    let (best_system, (best_score, matched)) = scores
        .into_iter()
        .max_by(|(_, (a, _)), (_, (b, _))| a.partial_cmp(b).unwrap())
        .unwrap_or((GameSystem::Other, (0.0, vec![])));

    // Calculate confidence (normalized against threshold)
    let threshold = 3.0_f32; // Need at least 3 strong indicators for full confidence
    let confidence = (best_score / threshold).min(1.0);

    DetectionResult {
        system: if confidence >= 0.3 { best_system } else { GameSystem::Other },
        confidence,
        matched_indicators: matched,
    }
}

/// Get indicator patterns for all supported game systems.
fn get_system_indicators() -> HashMap<GameSystem, SystemIndicators> {
    let mut indicators = HashMap::new();

    // D&D 5e indicators
    indicators.insert(GameSystem::DnD5e, SystemIndicators {
        strong: vec![
            "armor class",
            "hit dice",
            "spell slots",
            "proficiency bonus",
            "5th edition",
            "5e",
            "dungeon master",
            "saving throw",
            "advantage",
            "disadvantage",
            "death saving throw",
            "cantrip",
            "wizard's handbook",
            "monster manual",
        ],
        weak: vec![
            "d20",
            "hit points",
            "ability score",
            "attack roll",
            "damage roll",
            "short rest",
            "long rest",
            "spellcasting",
        ],
    });

    // Pathfinder 2e indicators
    indicators.insert(GameSystem::Pathfinder2e, SystemIndicators {
        strong: vec![
            "three actions",
            "ancestry",
            "heritage",
            "proficiency rank",
            "pathfinder",
            "2nd edition",
            "paizo",
            "golarion",
            "archetypes",
            "trained",
            "expert",
            "master",
            "legendary",
        ],
        weak: vec![
            "feat",
            "skill check",
            "ability modifier",
            "reaction",
            "free action",
        ],
    });

    // Call of Cthulhu indicators
    indicators.insert(GameSystem::CallOfCthulhu, SystemIndicators {
        strong: vec![
            "sanity",
            "sanity check",
            "sanity points",
            "mythos",
            "investigator",
            "keeper",
            "cthulhu",
            "call of cthulhu",
            "chaosium",
            "luck points",
            "credit rating",
        ],
        weak: vec![
            "horror",
            "madness",
            "cosmic",
            "eldritch",
            "1920s",
        ],
    });

    // World of Darkness indicators
    indicators.insert(GameSystem::WorldOfDarkness, SystemIndicators {
        strong: vec![
            "storyteller",
            "dice pool",
            "vampire",
            "werewolf",
            "mage",
            "changeling",
            "world of darkness",
            "chronicles of darkness",
            "white wolf",
            "blood potency",
            "humanity",
        ],
        weak: vec![
            "willpower",
            "disciplines",
            "clan",
            "covenant",
        ],
    });

    // Shadowrun indicators
    indicators.insert(GameSystem::Shadowrun, SystemIndicators {
        strong: vec![
            "shadowrun",
            "nuyen",
            "decker",
            "rigger",
            "street samurai",
            "awakened",
            "technomancer",
            "matrix",
            "astral",
            "sixth world",
            "karma",
        ],
        weak: vec![
            "cyberware",
            "megacorp",
            "corp",
            "seattle",
            "essence",
        ],
    });

    // FATE indicators
    indicators.insert(GameSystem::Fate, SystemIndicators {
        strong: vec![
            "fate",
            "fate core",
            "fate points",
            "aspects",
            "invoke",
            "compel",
            "stunts",
            "fate dice",
            "fudge dice",
        ],
        weak: vec![
            "approach",
            "high concept",
            "trouble",
        ],
    });

    // PbtA indicators
    indicators.insert(GameSystem::PbtA, SystemIndicators {
        strong: vec![
            "powered by the apocalypse",
            "pbta",
            "moves",
            "playbook",
            "hard move",
            "soft move",
            "2d6",
            "7-9",
            "10+",
            "miss",
            "partial success",
        ],
        weak: vec![
            "mc",
            "basic moves",
            "advance",
        ],
    });

    indicators
}

// ============================================================================
// Tests
// ============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_detect_dnd5e() {
        let text = r#"
            The goblin has Armor Class 15 and Hit Points 7 (2d6).
            It has proficiency bonus +2 and can make a saving throw.
            The DM may grant advantage on the roll.
        "#;

        let result = detect_game_system_with_confidence(text);
        assert_eq!(result.system, GameSystem::DnD5e);
        assert!(result.confidence >= 0.5);
    }

    #[test]
    fn test_detect_pathfinder2e() {
        let text = r#"
            The elf has a heritage of woodland ancestry.
            Using three actions, they can achieve a legendary proficiency rank.
            This is a Pathfinder 2nd Edition character.
        "#;

        let result = detect_game_system_with_confidence(text);
        assert_eq!(result.system, GameSystem::Pathfinder2e);
        assert!(result.confidence >= 0.5);
    }

    #[test]
    fn test_detect_coc() {
        let text = r#"
            The investigator must make a sanity check after witnessing
            the eldritch horror. The Keeper describes the mythos creature.
            Roll against your sanity points.
        "#;

        let result = detect_game_system_with_confidence(text);
        assert_eq!(result.system, GameSystem::CallOfCthulhu);
        assert!(result.confidence >= 0.5);
    }

    #[test]
    fn test_detect_unknown() {
        let text = "This is just regular text without any game system indicators.";

        let result = detect_game_system_with_confidence(text);
        assert!(result.confidence < 0.5);
    }

    #[test]
    fn test_game_system_as_str() {
        assert_eq!(GameSystem::DnD5e.as_str(), "dnd5e");
        assert_eq!(GameSystem::Pathfinder2e.as_str(), "pf2e");
        assert_eq!(GameSystem::CallOfCthulhu.as_str(), "coc");
    }
}

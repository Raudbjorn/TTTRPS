//! Spell Correction Module
//!
//! Provides spelling suggestions for TTRPG-related search queries.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

// ============================================================================
// Types
// ============================================================================

/// Spelling suggestion
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SpellingSuggestion {
    /// Original word
    pub original: String,
    /// Suggested correction
    pub suggestion: String,
    /// Edit distance
    pub distance: usize,
    /// Confidence (0.0 - 1.0)
    pub confidence: f64,
}

/// Correction result for a query
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CorrectionResult {
    /// Original query
    pub original_query: String,
    /// Corrected query
    pub corrected_query: String,
    /// Individual word corrections
    pub corrections: Vec<SpellingSuggestion>,
    /// Whether any corrections were made
    pub has_corrections: bool,
}

// ============================================================================
// Spell Corrector
// ============================================================================

/// TTRPG-aware spell corrector
pub struct SpellCorrector {
    /// Dictionary of known words
    dictionary: HashSet<String>,
    /// Word frequency map (for ranking suggestions)
    word_frequencies: std::collections::HashMap<String, u32>,
}

impl SpellCorrector {
    pub fn new() -> Self {
        let mut corrector = Self {
            dictionary: HashSet::new(),
            word_frequencies: std::collections::HashMap::new(),
        };
        corrector.load_default_dictionary();
        corrector
    }

    /// Load default TTRPG dictionary
    fn load_default_dictionary(&mut self) {
        // Common TTRPG terms
        let terms = vec![
            // Core mechanics
            "ability", "action", "armor", "attack", "bonus", "cantrip", "character",
            "class", "combat", "concentration", "condition", "constitution", "critical",
            "damage", "dexterity", "difficulty", "dungeon", "encounter", "equipment",
            "experience", "feat", "feature", "grapple", "health", "hit", "initiative",
            "intelligence", "level", "modifier", "monster", "multiclass", "perception",
            "points", "proficiency", "race", "range", "reaction", "resistance", "rest",
            "ritual", "roll", "save", "saving", "skill", "speed", "spell", "spellcasting",
            "stealth", "strength", "target", "terrain", "throw", "trait", "turn",
            "vulnerability", "weapon", "wisdom",

            // Classes
            "artificer", "barbarian", "bard", "cleric", "druid", "fighter", "monk",
            "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard",

            // Races
            "aasimar", "dragonborn", "dwarf", "elf", "gnome", "goliath", "halfling",
            "half-elf", "half-orc", "human", "tiefling", "orc", "goblin", "kobold",

            // Monsters
            "aboleth", "beholder", "bugbear", "demon", "devil", "dragon", "elemental",
            "fiend", "giant", "hobgoblin", "hydra", "lich", "mimic", "mind flayer",
            "ogre", "owlbear", "skeleton", "troll", "undead", "vampire", "werewolf",
            "wyvern", "zombie",

            // Spells (common)
            "fireball", "lightning", "bolt", "magic", "missile", "shield", "healing",
            "word", "cure", "wounds", "dispel", "detect", "identify", "invisibility",
            "polymorph", "teleport", "resurrection", "dimension", "door",

            // Equipment
            "sword", "axe", "bow", "crossbow", "dagger", "mace", "staff", "wand",
            "shield", "armor", "plate", "chain", "leather", "potion", "scroll",
            "ring", "amulet", "cloak", "boots", "gauntlets", "helm", "helmet",

            // Conditions
            "blinded", "charmed", "deafened", "exhausted", "frightened", "grappled",
            "incapacitated", "invisible", "paralyzed", "petrified", "poisoned",
            "prone", "restrained", "stunned", "unconscious",

            // Game terms
            "campaign", "adventure", "quest", "dungeon", "master", "player", "session",
            "backstory", "alignment", "lawful", "chaotic", "neutral", "good", "evil",
            "background", "inspiration", "advantage", "disadvantage", "legendary",
        ];

        for term in terms {
            self.dictionary.insert(term.to_lowercase());
            self.word_frequencies.insert(term.to_lowercase(), 100);
        }

        // Add common English words with lower frequency
        let common_words = vec![
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through", "during",
            "before", "after", "above", "below", "between", "under", "again", "further",
            "then", "once", "here", "there", "when", "where", "why", "how", "all",
            "each", "few", "more", "most", "other", "some", "such", "no", "nor",
            "not", "only", "own", "same", "so", "than", "too", "very", "can", "will",
            "just", "should", "now", "does", "what", "which", "who", "this", "that",
            "these", "those", "am", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "having", "do", "did", "doing", "would", "could",
            "might", "must", "shall",
        ];

        for word in common_words {
            self.dictionary.insert(word.to_lowercase());
            self.word_frequencies.insert(word.to_lowercase(), 50);
        }
    }

    /// Correct a query
    pub fn correct(&self, query: &str) -> CorrectionResult {
        let words: Vec<&str> = query.split_whitespace().collect();
        let mut corrections = Vec::new();
        let mut corrected_words = Vec::new();

        for word in &words {
            let word_lower = word.to_lowercase();

            // Skip if word is in dictionary or too short
            if self.dictionary.contains(&word_lower) || word.len() < 3 {
                corrected_words.push(word.to_string());
                continue;
            }

            // Find suggestions
            if let Some(suggestion) = self.find_best_suggestion(&word_lower) {
                corrections.push(SpellingSuggestion {
                    original: word.to_string(),
                    suggestion: suggestion.clone(),
                    distance: self.levenshtein(&word_lower, &suggestion),
                    confidence: self.calculate_confidence(&word_lower, &suggestion),
                });
                corrected_words.push(suggestion);
            } else {
                corrected_words.push(word.to_string());
            }
        }

        let corrected_query = corrected_words.join(" ");
        let has_corrections = !corrections.is_empty();

        CorrectionResult {
            original_query: query.to_string(),
            corrected_query,
            corrections,
            has_corrections,
        }
    }

    /// Find the best suggestion for a word
    fn find_best_suggestion(&self, word: &str) -> Option<String> {
        let max_distance = match word.len() {
            0..=3 => 1,
            4..=5 => 2,
            _ => 3,
        };

        let mut best: Option<(String, usize, u32)> = None;

        for dict_word in &self.dictionary {
            let distance = self.levenshtein(word, dict_word);

            if distance <= max_distance {
                let freq = *self.word_frequencies.get(dict_word).unwrap_or(&1);

                match &best {
                    None => best = Some((dict_word.clone(), distance, freq)),
                    Some((_, best_dist, best_freq)) => {
                        // Prefer lower distance, then higher frequency
                        if distance < *best_dist
                            || (distance == *best_dist && freq > *best_freq)
                        {
                            best = Some((dict_word.clone(), distance, freq));
                        }
                    }
                }
            }
        }

        best.map(|(word, _, _)| word)
    }

    /// Calculate Levenshtein distance between two strings
    fn levenshtein(&self, s1: &str, s2: &str) -> usize {
        let s1_chars: Vec<char> = s1.chars().collect();
        let s2_chars: Vec<char> = s2.chars().collect();

        let len1 = s1_chars.len();
        let len2 = s2_chars.len();

        if len1 == 0 {
            return len2;
        }
        if len2 == 0 {
            return len1;
        }

        let mut matrix = vec![vec![0usize; len2 + 1]; len1 + 1];

        for i in 0..=len1 {
            matrix[i][0] = i;
        }
        for j in 0..=len2 {
            matrix[0][j] = j;
        }

        for i in 1..=len1 {
            for j in 1..=len2 {
                let cost = if s1_chars[i - 1] == s2_chars[j - 1] {
                    0
                } else {
                    1
                };

                matrix[i][j] = (matrix[i - 1][j] + 1)
                    .min(matrix[i][j - 1] + 1)
                    .min(matrix[i - 1][j - 1] + cost);
            }
        }

        matrix[len1][len2]
    }

    /// Calculate confidence for a suggestion
    fn calculate_confidence(&self, original: &str, suggestion: &str) -> f64 {
        let distance = self.levenshtein(original, suggestion);
        let max_len = original.len().max(suggestion.len()) as f64;

        // Higher confidence for smaller relative distance
        let relative_distance = distance as f64 / max_len;
        let base_confidence = 1.0 - relative_distance;

        // Boost for common words
        let freq_boost = if let Some(&freq) = self.word_frequencies.get(suggestion) {
            (freq as f64 / 100.0).min(0.2)
        } else {
            0.0
        };

        (base_confidence + freq_boost).min(1.0)
    }

    /// Get "did you mean" suggestions
    pub fn did_you_mean(&self, word: &str) -> Vec<String> {
        let word_lower = word.to_lowercase();
        let mut suggestions: Vec<(String, usize, u32)> = Vec::new();

        for dict_word in &self.dictionary {
            let distance = self.levenshtein(&word_lower, dict_word);

            if distance <= 3 && distance > 0 {
                let freq = *self.word_frequencies.get(dict_word).unwrap_or(&1);
                suggestions.push((dict_word.clone(), distance, freq));
            }
        }

        // Sort by distance, then frequency
        suggestions.sort_by(|a, b| {
            a.1.cmp(&b.1).then_with(|| b.2.cmp(&a.2))
        });

        suggestions.into_iter().take(5).map(|(w, _, _)| w).collect()
    }

    /// Add a word to the dictionary
    pub fn add_word(&mut self, word: &str, frequency: u32) {
        let word_lower = word.to_lowercase();
        self.dictionary.insert(word_lower.clone());
        self.word_frequencies.insert(word_lower, frequency);
    }

    /// Check if a word is in the dictionary
    pub fn is_known(&self, word: &str) -> bool {
        self.dictionary.contains(&word.to_lowercase())
    }
}

impl Default for SpellCorrector {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_levenshtein() {
        let corrector = SpellCorrector::new();

        assert_eq!(corrector.levenshtein("kitten", "sitting"), 3);
        assert_eq!(corrector.levenshtein("spell", "spell"), 0);
        assert_eq!(corrector.levenshtein("", "test"), 4);
    }

    #[test]
    fn test_correction() {
        let corrector = SpellCorrector::new();

        let result = corrector.correct("fiorball damage");
        assert!(result.has_corrections);
        assert!(result.corrected_query.contains("fireball"));
    }

    #[test]
    fn test_did_you_mean() {
        let corrector = SpellCorrector::new();

        let suggestions = corrector.did_you_mean("fiorball");
        assert!(!suggestions.is_empty());
        assert!(suggestions.contains(&"fireball".to_string()));
    }

    #[test]
    fn test_known_words() {
        let corrector = SpellCorrector::new();

        assert!(corrector.is_known("fireball"));
        assert!(corrector.is_known("dragon"));
        assert!(!corrector.is_known("xyzabc123"));
    }
}

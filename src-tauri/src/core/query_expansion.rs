//! Query Expansion Module
//!
//! Expands search queries with TTRPG-specific synonyms and related terms.

use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};

// ============================================================================
// Types
// ============================================================================

/// Expanded query result
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExpandedQuery {
    /// Original query
    pub original: String,
    /// Expanded terms
    pub expanded_terms: Vec<String>,
    /// Full expanded query string
    pub expanded_query: String,
    /// Synonyms that were applied
    pub applied_synonyms: Vec<(String, Vec<String>)>,
}

// ============================================================================
// Query Expander
// ============================================================================

/// Expands queries with TTRPG-specific terms
pub struct QueryExpander {
    /// Synonym map: term -> list of synonyms
    synonyms: HashMap<String, Vec<String>>,
    /// Abbreviation expansions
    abbreviations: HashMap<String, String>,
    /// Related terms (broader relationships)
    related_terms: HashMap<String, Vec<String>>,
}

impl QueryExpander {
    pub fn new() -> Self {
        let mut expander = Self {
            synonyms: HashMap::new(),
            abbreviations: HashMap::new(),
            related_terms: HashMap::new(),
        };
        expander.load_default_synonyms();
        expander
    }

    /// Load default TTRPG synonyms
    fn load_default_synonyms(&mut self) {
        // Common abbreviations
        self.abbreviations.insert("hp".to_string(), "hit points".to_string());
        self.abbreviations.insert("ac".to_string(), "armor class".to_string());
        self.abbreviations.insert("dc".to_string(), "difficulty class".to_string());
        self.abbreviations.insert("atk".to_string(), "attack".to_string());
        self.abbreviations.insert("dmg".to_string(), "damage".to_string());
        self.abbreviations.insert("str".to_string(), "strength".to_string());
        self.abbreviations.insert("dex".to_string(), "dexterity".to_string());
        self.abbreviations.insert("con".to_string(), "constitution".to_string());
        self.abbreviations.insert("int".to_string(), "intelligence".to_string());
        self.abbreviations.insert("wis".to_string(), "wisdom".to_string());
        self.abbreviations.insert("cha".to_string(), "charisma".to_string());
        self.abbreviations.insert("xp".to_string(), "experience points".to_string());
        self.abbreviations.insert("gp".to_string(), "gold pieces".to_string());
        self.abbreviations.insert("sp".to_string(), "silver pieces".to_string());
        self.abbreviations.insert("cp".to_string(), "copper pieces".to_string());
        self.abbreviations.insert("pp".to_string(), "platinum pieces".to_string());
        self.abbreviations.insert("cr".to_string(), "challenge rating".to_string());
        self.abbreviations.insert("npc".to_string(), "non-player character".to_string());
        self.abbreviations.insert("pc".to_string(), "player character".to_string());
        self.abbreviations.insert("dm".to_string(), "dungeon master".to_string());
        self.abbreviations.insert("gm".to_string(), "game master".to_string());
        self.abbreviations.insert("aoe".to_string(), "area of effect".to_string());
        self.abbreviations.insert("bab".to_string(), "base attack bonus".to_string());
        self.abbreviations.insert("thac0".to_string(), "to hit armor class zero".to_string());

        // Synonyms for common terms
        self.synonyms.insert(
            "hit points".to_string(),
            vec!["hp".to_string(), "health".to_string(), "life".to_string()],
        );
        self.synonyms.insert(
            "armor class".to_string(),
            vec!["ac".to_string(), "defense".to_string(), "protection".to_string()],
        );
        self.synonyms.insert(
            "difficulty class".to_string(),
            vec!["dc".to_string(), "target number".to_string(), "check".to_string()],
        );
        self.synonyms.insert(
            "attack".to_string(),
            vec!["strike".to_string(), "hit".to_string(), "assault".to_string()],
        );
        self.synonyms.insert(
            "damage".to_string(),
            vec!["harm".to_string(), "injury".to_string(), "dmg".to_string()],
        );
        self.synonyms.insert(
            "spell".to_string(),
            vec!["magic".to_string(), "incantation".to_string(), "cantrip".to_string()],
        );
        self.synonyms.insert(
            "monster".to_string(),
            vec!["creature".to_string(), "beast".to_string(), "enemy".to_string(), "foe".to_string()],
        );
        self.synonyms.insert(
            "weapon".to_string(),
            vec!["arm".to_string(), "armament".to_string(), "blade".to_string()],
        );
        self.synonyms.insert(
            "save".to_string(),
            vec!["saving throw".to_string(), "saving".to_string()],
        );
        self.synonyms.insert(
            "ability".to_string(),
            vec!["stat".to_string(), "attribute".to_string(), "score".to_string()],
        );
        self.synonyms.insert(
            "skill".to_string(),
            vec!["proficiency".to_string(), "talent".to_string()],
        );
        self.synonyms.insert(
            "feat".to_string(),
            vec!["talent".to_string(), "ability".to_string(), "feature".to_string()],
        );
        self.synonyms.insert(
            "race".to_string(),
            vec!["species".to_string(), "ancestry".to_string(), "lineage".to_string()],
        );
        self.synonyms.insert(
            "class".to_string(),
            vec!["profession".to_string(), "archetype".to_string(), "role".to_string()],
        );
        self.synonyms.insert(
            "level".to_string(),
            vec!["tier".to_string(), "rank".to_string()],
        );
        self.synonyms.insert(
            "gold".to_string(),
            vec!["gp".to_string(), "coins".to_string(), "money".to_string(), "currency".to_string()],
        );

        // Related terms
        self.related_terms.insert(
            "combat".to_string(),
            vec![
                "attack".to_string(),
                "damage".to_string(),
                "initiative".to_string(),
                "action".to_string(),
            ],
        );
        self.related_terms.insert(
            "magic".to_string(),
            vec![
                "spell".to_string(),
                "cantrip".to_string(),
                "ritual".to_string(),
                "arcane".to_string(),
            ],
        );
        self.related_terms.insert(
            "character".to_string(),
            vec![
                "class".to_string(),
                "race".to_string(),
                "level".to_string(),
                "background".to_string(),
            ],
        );
    }

    /// Expand a query with synonyms and related terms
    pub fn expand(&self, query: &str) -> ExpandedQuery {
        let query_lower = query.to_lowercase();
        let words: Vec<&str> = query_lower.split_whitespace().collect();
        let mut expanded_terms: HashSet<String> = HashSet::new();
        let mut applied_synonyms: Vec<(String, Vec<String>)> = Vec::new();

        // Add original terms
        for word in &words {
            expanded_terms.insert(word.to_string());
        }

        // Expand abbreviations
        for word in &words {
            if let Some(expansion) = self.abbreviations.get(*word) {
                expanded_terms.insert(expansion.clone());
                applied_synonyms.push((word.to_string(), vec![expansion.clone()]));
            }
        }

        // Look for multi-word phrases and expand them
        let query_string = words.join(" ");
        for (term, synonyms) in &self.synonyms {
            if query_string.contains(term) {
                for syn in synonyms {
                    expanded_terms.insert(syn.clone());
                }
                applied_synonyms.push((term.clone(), synonyms.clone()));
            }
        }

        // Also check if query words match synonym keys
        for word in &words {
            if let Some(synonyms) = self.synonyms.get(*word) {
                for syn in synonyms {
                    expanded_terms.insert(syn.clone());
                }
                if !applied_synonyms.iter().any(|(t, _)| t == *word) {
                    applied_synonyms.push((word.to_string(), synonyms.clone()));
                }
            }
        }

        // Add related terms (less weight)
        for word in &words {
            if let Some(related) = self.related_terms.get(*word) {
                for rel in related {
                    expanded_terms.insert(rel.clone());
                }
            }
        }

        // Build expanded query
        let expanded_list: Vec<String> = expanded_terms.into_iter().collect();
        let expanded_query = if expanded_list.len() > words.len() {
            format!("{} OR ({})", query, expanded_list.join(" OR "))
        } else {
            query.to_string()
        };

        ExpandedQuery {
            original: query.to_string(),
            expanded_terms: expanded_list,
            expanded_query,
            applied_synonyms,
        }
    }

    /// Add a custom synonym
    pub fn add_synonym(&mut self, term: &str, synonyms: Vec<String>) {
        self.synonyms.insert(term.to_lowercase(), synonyms);
    }

    /// Add a custom abbreviation
    pub fn add_abbreviation(&mut self, abbrev: &str, expansion: &str) {
        self.abbreviations
            .insert(abbrev.to_lowercase(), expansion.to_string());
    }

    /// Get suggestions for a partial query
    pub fn suggest(&self, partial: &str) -> Vec<String> {
        let partial_lower = partial.to_lowercase();
        let mut suggestions: Vec<String> = Vec::new();

        // Suggest from abbreviations
        for (abbrev, expansion) in &self.abbreviations {
            if abbrev.starts_with(&partial_lower) {
                suggestions.push(format!("{} ({})", abbrev, expansion));
            }
        }

        // Suggest from synonym keys
        for term in self.synonyms.keys() {
            if term.starts_with(&partial_lower) {
                suggestions.push(term.clone());
            }
        }

        suggestions.sort();
        suggestions.truncate(10);
        suggestions
    }

    /// Stem a word (simple suffix removal)
    pub fn stem(&self, word: &str) -> String {
        let word = word.to_lowercase();

        // Simple English stemming rules
        if word.ends_with("ing") && word.len() > 5 {
            return word[..word.len() - 3].to_string();
        }
        if word.ends_with("ed") && word.len() > 4 {
            return word[..word.len() - 2].to_string();
        }
        if word.ends_with("s") && !word.ends_with("ss") && word.len() > 3 {
            return word[..word.len() - 1].to_string();
        }
        if word.ends_with("ly") && word.len() > 4 {
            return word[..word.len() - 2].to_string();
        }

        word
    }

    /// Expand with stemming
    pub fn expand_with_stemming(&self, query: &str) -> ExpandedQuery {
        let mut base_expansion = self.expand(query);

        // Add stemmed versions
        let words: Vec<&str> = query.split_whitespace().collect();
        for word in words {
            let stemmed = self.stem(word);
            if stemmed != word.to_lowercase() {
                base_expansion.expanded_terms.push(stemmed);
            }
        }

        base_expansion
    }
}

impl Default for QueryExpander {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_abbreviation_expansion() {
        let expander = QueryExpander::new();
        let result = expander.expand("How much HP does a goblin have?");

        assert!(result.expanded_terms.contains(&"hit points".to_string()));
    }

    #[test]
    fn test_synonym_expansion() {
        let expander = QueryExpander::new();
        let result = expander.expand("attack damage");

        assert!(result.expanded_terms.len() > 2);
    }

    #[test]
    fn test_stemming() {
        let expander = QueryExpander::new();

        assert_eq!(expander.stem("attacking"), "attack");
        assert_eq!(expander.stem("damaged"), "damag");
        assert_eq!(expander.stem("spells"), "spell");
    }

    #[test]
    fn test_suggestions() {
        let expander = QueryExpander::new();
        let suggestions = expander.suggest("hp");

        assert!(!suggestions.is_empty());
        assert!(suggestions[0].contains("hit points"));
    }
}

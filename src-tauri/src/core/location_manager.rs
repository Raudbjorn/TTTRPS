//! Location Manager Module
//!
//! Manages campaign locations with hierarchical relationships.

use chrono::{DateTime, Utc};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::sync::RwLock;
use uuid::Uuid;

// ============================================================================
// Types
// ============================================================================

/// Location type
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum LocationType {
    City,
    Town,
    Village,
    Dungeon,
    Wilderness,
    Building,
    Room,
    Region,
    Continent,
    Plane,
    Other(String),
}

/// A campaign location
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Location {
    /// Unique identifier
    pub id: String,
    /// Campaign this location belongs to
    pub campaign_id: String,
    /// Location name
    pub name: String,
    /// Location type
    pub location_type: LocationType,
    /// Description
    pub description: String,
    /// Parent location ID (for hierarchy)
    pub parent_id: Option<String>,
    /// Connected location IDs
    pub connections: Vec<String>,
    /// NPCs present at this location
    pub npcs_present: Vec<String>,
    /// Notable features
    pub features: Vec<String>,
    /// Secrets (hidden from players)
    pub secrets: Vec<String>,
    /// Custom attributes
    pub attributes: HashMap<String, String>,
    /// Tags for categorization
    pub tags: Vec<String>,
    /// Created timestamp
    pub created_at: DateTime<Utc>,
    /// Updated timestamp
    pub updated_at: DateTime<Utc>,
}

impl Location {
    pub fn new(campaign_id: &str, name: &str, location_type: LocationType) -> Self {
        let now = Utc::now();
        Self {
            id: Uuid::new_v4().to_string(),
            campaign_id: campaign_id.to_string(),
            name: name.to_string(),
            location_type,
            description: String::new(),
            parent_id: None,
            connections: Vec::new(),
            npcs_present: Vec::new(),
            features: Vec::new(),
            secrets: Vec::new(),
            attributes: HashMap::new(),
            tags: Vec::new(),
            created_at: now,
            updated_at: now,
        }
    }
}

// ============================================================================
// Location Manager
// ============================================================================

/// Manages locations for campaigns
pub struct LocationManager {
    /// Locations by ID
    locations: RwLock<HashMap<String, Location>>,
}

impl LocationManager {
    pub fn new() -> Self {
        Self {
            locations: RwLock::new(HashMap::new()),
        }
    }

    /// Create a new location
    pub fn create(&self, location: Location) -> String {
        let id = location.id.clone();
        let mut locations = self.locations.write().unwrap();
        locations.insert(id.clone(), location);
        id
    }

    /// Get a location by ID
    pub fn get(&self, id: &str) -> Option<Location> {
        let locations = self.locations.read().unwrap();
        locations.get(id).cloned()
    }

    /// Update a location
    pub fn update(&self, location: Location) -> bool {
        let mut locations = self.locations.write().unwrap();
        if locations.contains_key(&location.id) {
            let mut updated = location;
            updated.updated_at = Utc::now();
            locations.insert(updated.id.clone(), updated);
            true
        } else {
            false
        }
    }

    /// Delete a location
    pub fn delete(&self, id: &str) -> bool {
        let mut locations = self.locations.write().unwrap();

        // Remove from parent's children (not tracked explicitly, but clear connections)
        if let Some(location) = locations.get(id) {
            // Remove this location from connections of other locations
            let location_id = location.id.clone();
            for other in locations.values_mut() {
                other.connections.retain(|c| c != &location_id);
            }
        }

        locations.remove(id).is_some()
    }

    /// List all locations for a campaign
    pub fn list_by_campaign(&self, campaign_id: &str) -> Vec<Location> {
        let locations = self.locations.read().unwrap();
        locations
            .values()
            .filter(|l| l.campaign_id == campaign_id)
            .cloned()
            .collect()
    }

    /// Get child locations (locations with this as parent)
    pub fn get_children(&self, parent_id: &str) -> Vec<Location> {
        let locations = self.locations.read().unwrap();
        locations
            .values()
            .filter(|l| l.parent_id.as_deref() == Some(parent_id))
            .cloned()
            .collect()
    }

    /// Get the location hierarchy (ancestors)
    pub fn get_hierarchy(&self, location_id: &str) -> Vec<Location> {
        let locations = self.locations.read().unwrap();
        let mut hierarchy = Vec::new();
        let mut current_id = Some(location_id.to_string());

        while let Some(id) = current_id {
            if let Some(location) = locations.get(&id) {
                hierarchy.push(location.clone());
                current_id = location.parent_id.clone();
            } else {
                break;
            }
        }

        hierarchy.reverse();
        hierarchy
    }

    /// Get connected locations
    pub fn get_connected(&self, location_id: &str) -> Vec<Location> {
        let locations = self.locations.read().unwrap();

        if let Some(location) = locations.get(location_id) {
            location
                .connections
                .iter()
                .filter_map(|id| locations.get(id).cloned())
                .collect()
        } else {
            Vec::new()
        }
    }

    /// Add a connection between two locations
    pub fn add_connection(&self, from_id: &str, to_id: &str) -> bool {
        let mut locations = self.locations.write().unwrap();

        // Verify both locations exist
        if !locations.contains_key(from_id) || !locations.contains_key(to_id) {
            return false;
        }

        // Add bidirectional connection
        if let Some(from_loc) = locations.get_mut(from_id) {
            if !from_loc.connections.contains(&to_id.to_string()) {
                from_loc.connections.push(to_id.to_string());
                from_loc.updated_at = Utc::now();
            }
        }

        if let Some(to_loc) = locations.get_mut(to_id) {
            if !to_loc.connections.contains(&from_id.to_string()) {
                to_loc.connections.push(from_id.to_string());
                to_loc.updated_at = Utc::now();
            }
        }

        true
    }

    /// Remove a connection between two locations
    pub fn remove_connection(&self, from_id: &str, to_id: &str) -> bool {
        let mut locations = self.locations.write().unwrap();

        let mut removed = false;

        if let Some(from_loc) = locations.get_mut(from_id) {
            let initial_len = from_loc.connections.len();
            from_loc.connections.retain(|c| c != to_id);
            if from_loc.connections.len() < initial_len {
                from_loc.updated_at = Utc::now();
                removed = true;
            }
        }

        if let Some(to_loc) = locations.get_mut(to_id) {
            let initial_len = to_loc.connections.len();
            to_loc.connections.retain(|c| c != from_id);
            if to_loc.connections.len() < initial_len {
                to_loc.updated_at = Utc::now();
                removed = true;
            }
        }

        removed
    }

    /// Add an NPC to a location
    pub fn add_npc(&self, location_id: &str, npc_id: &str) -> bool {
        let mut locations = self.locations.write().unwrap();

        if let Some(location) = locations.get_mut(location_id) {
            if !location.npcs_present.contains(&npc_id.to_string()) {
                location.npcs_present.push(npc_id.to_string());
                location.updated_at = Utc::now();
                return true;
            }
        }

        false
    }

    /// Remove an NPC from a location
    pub fn remove_npc(&self, location_id: &str, npc_id: &str) -> bool {
        let mut locations = self.locations.write().unwrap();

        if let Some(location) = locations.get_mut(location_id) {
            let initial_len = location.npcs_present.len();
            location.npcs_present.retain(|n| n != npc_id);
            if location.npcs_present.len() < initial_len {
                location.updated_at = Utc::now();
                return true;
            }
        }

        false
    }

    /// Search locations by name or description
    pub fn search(&self, campaign_id: &str, query: &str) -> Vec<Location> {
        let locations = self.locations.read().unwrap();
        let query_lower = query.to_lowercase();

        locations
            .values()
            .filter(|l| {
                l.campaign_id == campaign_id
                    && (l.name.to_lowercase().contains(&query_lower)
                        || l.description.to_lowercase().contains(&query_lower)
                        || l.tags.iter().any(|t| t.to_lowercase().contains(&query_lower)))
            })
            .cloned()
            .collect()
    }

    /// Get locations by type
    pub fn get_by_type(&self, campaign_id: &str, location_type: &LocationType) -> Vec<Location> {
        let locations = self.locations.read().unwrap();
        locations
            .values()
            .filter(|l| l.campaign_id == campaign_id && &l.location_type == location_type)
            .cloned()
            .collect()
    }

    /// Get all root locations (no parent)
    pub fn get_root_locations(&self, campaign_id: &str) -> Vec<Location> {
        let locations = self.locations.read().unwrap();
        locations
            .values()
            .filter(|l| l.campaign_id == campaign_id && l.parent_id.is_none())
            .cloned()
            .collect()
    }
}

impl Default for LocationManager {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create_location() {
        let manager = LocationManager::new();

        let location = Location::new("campaign-1", "Waterdeep", LocationType::City);
        let id = manager.create(location);

        assert!(!id.is_empty());

        let retrieved = manager.get(&id).unwrap();
        assert_eq!(retrieved.name, "Waterdeep");
    }

    #[test]
    fn test_hierarchy() {
        let manager = LocationManager::new();

        let mut region = Location::new("campaign-1", "Sword Coast", LocationType::Region);
        let region_id = manager.create(region.clone());

        let mut city = Location::new("campaign-1", "Neverwinter", LocationType::City);
        city.parent_id = Some(region_id.clone());
        let city_id = manager.create(city);

        let hierarchy = manager.get_hierarchy(&city_id);
        assert_eq!(hierarchy.len(), 2);
        assert_eq!(hierarchy[0].name, "Sword Coast");
        assert_eq!(hierarchy[1].name, "Neverwinter");
    }

    #[test]
    fn test_connections() {
        let manager = LocationManager::new();

        let loc1 = Location::new("campaign-1", "Town A", LocationType::Town);
        let loc2 = Location::new("campaign-1", "Town B", LocationType::Town);

        let id1 = manager.create(loc1);
        let id2 = manager.create(loc2);

        manager.add_connection(&id1, &id2);

        let connected = manager.get_connected(&id1);
        assert_eq!(connected.len(), 1);
        assert_eq!(connected[0].name, "Town B");
    }
}

//! Location Types Commands
//!
//! Commands for listing available location types.

use serde::{Deserialize, Serialize};

/// Location type information for UI display
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LocationTypeInfo {
    pub id: String,
    pub name: String,
    pub category: String,
    pub description: String,
}

/// Get all available location types with detailed information
#[tauri::command]
pub fn get_location_types() -> Vec<LocationTypeInfo> {
    vec![
        LocationTypeInfo { id: "city".to_string(), name: "City".to_string(), category: "Urban".to_string(), description: "A large settlement with walls, markets, and political intrigue".to_string() },
        LocationTypeInfo { id: "town".to_string(), name: "Town".to_string(), category: "Urban".to_string(), description: "A medium-sized settlement with basic amenities".to_string() },
        LocationTypeInfo { id: "village".to_string(), name: "Village".to_string(), category: "Urban".to_string(), description: "A small rural community".to_string() },
        LocationTypeInfo { id: "tavern".to_string(), name: "Tavern".to_string(), category: "Buildings".to_string(), description: "A place for drinking, dining, and gathering information".to_string() },
        LocationTypeInfo { id: "inn".to_string(), name: "Inn".to_string(), category: "Buildings".to_string(), description: "Lodging for weary travelers".to_string() },
        LocationTypeInfo { id: "shop".to_string(), name: "Shop".to_string(), category: "Buildings".to_string(), description: "A merchant's establishment".to_string() },
        LocationTypeInfo { id: "market".to_string(), name: "Market".to_string(), category: "Buildings".to_string(), description: "An open marketplace with many vendors".to_string() },
        LocationTypeInfo { id: "temple".to_string(), name: "Temple".to_string(), category: "Buildings".to_string(), description: "A place of worship and divine power".to_string() },
        LocationTypeInfo { id: "shrine".to_string(), name: "Shrine".to_string(), category: "Buildings".to_string(), description: "A small sacred site".to_string() },
        LocationTypeInfo { id: "guild".to_string(), name: "Guild Hall".to_string(), category: "Buildings".to_string(), description: "Headquarters of a professional organization".to_string() },
        LocationTypeInfo { id: "castle".to_string(), name: "Castle".to_string(), category: "Fortifications".to_string(), description: "A noble's fortified residence".to_string() },
        LocationTypeInfo { id: "stronghold".to_string(), name: "Stronghold".to_string(), category: "Fortifications".to_string(), description: "A military fortress".to_string() },
        LocationTypeInfo { id: "manor".to_string(), name: "Manor".to_string(), category: "Fortifications".to_string(), description: "A wealthy estate".to_string() },
        LocationTypeInfo { id: "tower".to_string(), name: "Tower".to_string(), category: "Fortifications".to_string(), description: "A wizard's tower or watchtower".to_string() },
        LocationTypeInfo { id: "dungeon".to_string(), name: "Dungeon".to_string(), category: "Adventure Sites".to_string(), description: "An underground complex of danger and treasure".to_string() },
        LocationTypeInfo { id: "cave".to_string(), name: "Cave".to_string(), category: "Adventure Sites".to_string(), description: "A natural underground cavern".to_string() },
        LocationTypeInfo { id: "ruins".to_string(), name: "Ruins".to_string(), category: "Adventure Sites".to_string(), description: "The remains of an ancient civilization".to_string() },
        LocationTypeInfo { id: "tomb".to_string(), name: "Tomb".to_string(), category: "Adventure Sites".to_string(), description: "A burial place for the dead".to_string() },
        LocationTypeInfo { id: "mine".to_string(), name: "Mine".to_string(), category: "Adventure Sites".to_string(), description: "An excavation for precious resources".to_string() },
        LocationTypeInfo { id: "lair".to_string(), name: "Monster Lair".to_string(), category: "Adventure Sites".to_string(), description: "The den of a dangerous creature".to_string() },
        LocationTypeInfo { id: "forest".to_string(), name: "Forest".to_string(), category: "Wilderness".to_string(), description: "A vast woodland area".to_string() },
        LocationTypeInfo { id: "mountain".to_string(), name: "Mountain".to_string(), category: "Wilderness".to_string(), description: "A towering peak or mountain range".to_string() },
        LocationTypeInfo { id: "swamp".to_string(), name: "Swamp".to_string(), category: "Wilderness".to_string(), description: "A treacherous wetland".to_string() },
        LocationTypeInfo { id: "desert".to_string(), name: "Desert".to_string(), category: "Wilderness".to_string(), description: "An arid wasteland".to_string() },
        LocationTypeInfo { id: "plains".to_string(), name: "Plains".to_string(), category: "Wilderness".to_string(), description: "Open grassland terrain".to_string() },
        LocationTypeInfo { id: "coast".to_string(), name: "Coast".to_string(), category: "Wilderness".to_string(), description: "Shoreline and coastal waters".to_string() },
        LocationTypeInfo { id: "island".to_string(), name: "Island".to_string(), category: "Wilderness".to_string(), description: "An isolated landmass surrounded by water".to_string() },
        LocationTypeInfo { id: "river".to_string(), name: "River".to_string(), category: "Wilderness".to_string(), description: "A major waterway".to_string() },
        LocationTypeInfo { id: "lake".to_string(), name: "Lake".to_string(), category: "Wilderness".to_string(), description: "A body of fresh water".to_string() },
        LocationTypeInfo { id: "portal".to_string(), name: "Portal".to_string(), category: "Magical".to_string(), description: "A gateway to another place or plane".to_string() },
        LocationTypeInfo { id: "planar".to_string(), name: "Planar Location".to_string(), category: "Magical".to_string(), description: "A location on another plane of existence".to_string() },
        LocationTypeInfo { id: "custom".to_string(), name: "Custom".to_string(), category: "Other".to_string(), description: "A unique location type".to_string() },
    ]
}

/// List available location types (simple string list)
#[tauri::command]
pub fn list_location_types() -> Vec<String> {
    vec![
        "Tavern", "Inn", "Shop", "Guild", "Temple", "Castle", "Manor", "Prison", "Slum", "Market", "City", "Town", "Village",
        "Forest", "Mountain", "Swamp", "Desert", "Plains", "Coast", "Island", "River", "Lake", "Cave",
        "Dungeon", "Ruins", "Tower", "Tomb", "Mine", "Stronghold", "Lair", "Camp", "Shrine", "Portal",
        "Planar", "Underwater", "Aerial"
    ].into_iter().map(String::from).collect()
}

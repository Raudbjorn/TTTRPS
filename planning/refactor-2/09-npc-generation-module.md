# NPC and Generation Commands Analysis

## Executive Summary

The NPC/generation domain contains ~72 commands spanning NPC CRUD, conversations, personality assignment, NPC extensions (vocabulary, names, dialects), indexing, character generation, location generation, and location management.

---

## 1. NPC Commands (~33 commands)

### 1.1 CRUD Operations (7 commands)

| Command | Purpose |
|---------|---------|
| `generate_npc` | Generates NPC, saves to store + database |
| `get_npc` | Retrieves from store or database fallback |
| `list_npcs` | Lists all NPCs for campaign |
| `list_npc_summaries` | Builds summaries with metadata |
| `update_npc` | Updates store and database |
| `delete_npc` | Removes from store and database |
| `search_npcs` | Full-text search via store |

### 1.2 Conversations (5 commands)

| Command | Purpose |
|---------|---------|
| `list_npc_conversations` | Lists all NPC conversations |
| `get_npc_conversation` | Retrieves specific conversation |
| `add_npc_message` | Adds message, updates unread |
| `mark_npc_read` | Clears unread count |
| `reply_as_npc` | LLM-generated response |

### 1.3 Personality Assignment (2 commands)

| Command | Purpose |
|---------|---------|
| `assign_npc_personality` | Links personality to NPC |
| `unassign_npc_personality` | Removes personality link |

### 1.4 NPC Extensions - Vocabulary (3 commands)

| Command | Purpose |
|---------|---------|
| `load_vocabulary_bank` | Loads YAML vocabulary |
| `get_vocabulary_directory` | Returns directory path |
| `get_vocabulary_phrase` | Gets phrase by category |

### 1.5 NPC Extensions - Names (4 commands)

| Command | Purpose |
|---------|---------|
| `load_naming_rules` | Loads YAML naming rules |
| `get_names_directory` | Returns directory path |
| `validate_naming_rules` | Validates schema |
| `get_random_name_structure` | Generates random name |

### 1.6 NPC Extensions - Dialects (3 commands)

| Command | Purpose |
|---------|---------|
| `load_dialect` | Loads YAML dialect |
| `get_dialects_directory` | Returns directory path |
| `apply_dialect` | Transforms text with rules |

### 1.7 Indexing (3 commands)

| Command | Purpose |
|---------|---------|
| `initialize_npc_indexes` | Creates Meilisearch indexes |
| `get_npc_indexes_stats` | Retrieves index statistics |
| `clear_npc_indexes` | Clears all indexes |

---

## 2. Character Generation (4 commands)

| Command | Purpose |
|---------|---------|
| `generate_character` | Basic character generation |
| `generate_character_advanced` | Full-featured generation |
| `list_system_info` | Returns supported systems |
| `get_system_info` | Returns system info |

---

## 3. Location Commands (~35 commands)

### 3.1 Generation (2 commands)

| Command | Purpose |
|---------|---------|
| `generate_location` | AI-enhanced or procedural |
| `generate_location_quick` | Pure procedural |

### 3.2 CRUD (7 commands)

| Command | Purpose |
|---------|---------|
| `save_location` | Persists location |
| `get_location` | Retrieves by ID |
| `list_campaign_locations` | Lists for campaign |
| `delete_location` | Removes location |
| `update_location` | Updates existing |
| `search_locations` | Multi-criteria search |
| `get_connected_locations` | Returns connected locations |

### 3.3 Connections (2 commands)

| Command | Purpose |
|---------|---------|
| `add_location_connection` | Creates connection |
| `remove_location_connection` | Removes connection |

**Connection Types**: door, path, road, stairs, ladder, portal, secret, water, climb, flight

### 3.4 Details (5 commands)

| Command | Purpose |
|---------|---------|
| `add_location_inhabitant` | Adds NPC/creature |
| `remove_location_inhabitant` | Removes inhabitant |
| `add_location_secret` | Adds hidden secret |
| `add_location_encounter` | Adds encounter |
| `set_location_map_reference` | Associates map coordinates |

### 3.5 Metadata (2 commands)

| Command | Purpose |
|---------|---------|
| `get_location_types` | Returns all types with metadata |
| `list_location_types` | Returns type names |

---

## 4. AppState Dependencies

```rust
pub npc_store: NPCStore,
pub personality_store: Arc<PersonalityStore>,
pub personality_manager: Arc<PersonalityApplicationManager>,
pub location_manager: LocationManager,
pub search_client: Arc<SearchClient>,
pub llm_config: RwLock<Option<LLMConfig>>,
pub database: Database,
```

---

## 5. Proposed Module Structure

```
commands/
├── generation/
│   ├── mod.rs
│   ├── character.rs      # Character generation (4 commands)
│   └── location.rs       # Location generation (2 commands)
│
├── npc/
│   ├── mod.rs
│   ├── crud.rs           # NPC CRUD (7 commands)
│   ├── conversations.rs  # NPC conversations (5 commands)
│   ├── personality.rs    # Personality assignment (2 commands)
│   ├── indexing.rs       # Search indexes (3 commands)
│   └── extensions/
│       ├── mod.rs
│       ├── vocabulary.rs # Vocabulary (3 commands)
│       ├── names.rs      # Names (4 commands)
│       └── dialects.rs   # Dialects (3 commands)
│
└── location/
    ├── mod.rs
    ├── crud.rs           # Location CRUD (7 commands)
    ├── connections.rs    # Connections (2 commands)
    ├── details.rs        # Details (5 commands)
    └── types.rs          # Metadata (2 commands)
```

---

## 6. Key Patterns

### Dual Storage Pattern
```rust
// Typical NPC CRUD pattern
- In-memory store (npc_store) for fast access
- Database (SQLite) for persistence
- Fallback chain: memory → database → error
```

### JSON Serialization Pattern
```rust
// Store complex types as JSON blobs
let personality_json = serde_json::to_string(&npc.personality)?;
let data_json = serde_json::to_string(&npc)?;
```

### LLM Conditional Pattern
```rust
// Location generation with AI fallback
if gen_options.use_ai {
    if let Some(config) = llm_config {
        // AI-enhanced generation
    } else {
        // Fall back to quick generation
    }
}
```

---

## 7. Command Distribution

| Module | Count | Async | Sync |
|--------|-------|-------|------|
| Character Generation | 4 | 0 | 4 |
| Location Generation | 2 | 1 | 1 |
| NPC CRUD | 7 | 5 | 2 |
| NPC Conversations | 5 | 4 | 0 |
| NPC Personality | 2 | 0 | 2 |
| NPC Extensions | 10 | 3 | 7 |
| NPC Indexing | 3 | 3 | 0 |
| Location CRUD | 7 | 1 | 6 |
| Location Connections | 2 | 0 | 2 |
| Location Details | 5 | 0 | 5 |
| Location Metadata | 2 | 0 | 2 |

---

## 8. Migration Priority

1. Character generation - Simple, isolated
2. NPC CRUD - Core functionality
3. NPC extensions - File I/O
4. Location CRUD - Similar to NPC pattern
5. Location connections/details - Manager delegation
6. NPC conversations - Database + LLM
7. NPC indexing - Meilisearch integration

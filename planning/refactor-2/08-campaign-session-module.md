# Campaign and Session Commands Analysis

## Executive Summary

The campaign/session domain contains ~72 commands spanning campaign CRUD, session management, combat tracking, conditions, global chat, versioning, and notes. This is one of the largest command groups.

---

## 1. Campaign Commands (~25 commands)

### 1.1 CRUD Operations (5 commands)

| Command | Purpose |
|---------|---------|
| `list_campaigns` | Returns all campaigns |
| `create_campaign` | Creates new campaign |
| `get_campaign` | Retrieves single campaign |
| `update_campaign` | Updates campaign (with optional auto-snapshot) |
| `delete_campaign` | Deletes campaign |

### 1.2 Theme Management (3 commands)

| Command | Purpose |
|---------|---------|
| `get_campaign_theme` | Retrieves theme weights |
| `set_campaign_theme` | Sets theme weights |
| `get_theme_preset` | Gets preset theme for system |

### 1.3 Snapshots (3 commands)

| Command | Purpose |
|---------|---------|
| `create_snapshot` | Creates manual snapshot |
| `list_snapshots` | Lists all snapshots |
| `restore_snapshot` | Restores to snapshot |

### 1.4 Import/Export (2 commands)

| Command | Purpose |
|---------|---------|
| `export_campaign` | Exports to JSON |
| `import_campaign` | Imports from JSON |

### 1.5 Utilities (2 commands)

| Command | Purpose |
|---------|---------|
| `get_campaign_stats` | Returns session count, playtime, etc. |
| `generate_campaign_cover` | Generates SVG cover image |

### 1.6 Campaign Notes (4 commands)

| Command | Purpose |
|---------|---------|
| `add_campaign_note` | Creates note |
| `get_campaign_notes` | Lists all notes |
| `search_campaign_notes` | Searches with tag filter |
| `delete_campaign_note` | Deletes note |

### 1.7 Versioning (6 commands)

| Command | Purpose |
|---------|---------|
| `create_campaign_version` | Creates versioned snapshot |
| `list_campaign_versions` | Lists all versions |
| `get_campaign_version` | Retrieves specific version |
| `compare_campaign_versions` | Shows diff between versions |
| `rollback_campaign` | Restores to version |
| `delete_campaign_version` | Deletes version |

---

## 2. Session Commands (~35 commands)

### 2.1 CRUD Operations (8 commands)

| Command | Purpose |
|---------|---------|
| `start_session` | Creates active session |
| `get_session` | Retrieves session |
| `get_active_session` | Gets current active session |
| `list_sessions` | Lists all sessions |
| `end_session` | Ends session, returns summary |
| `create_planned_session` | Creates planned session |
| `start_planned_session` | Transitions planned → active |
| `reorder_session` | Reorders session in list |

### 2.2 Global Chat (8 commands)

| Command | Purpose |
|---------|---------|
| `get_or_create_chat_session` | Creates/retrieves global chat |
| `get_active_chat_session` | Gets current chat session |
| `list_chat_sessions` | Lists all chat sessions |
| `get_chat_messages` | Retrieves messages |
| `add_chat_message` | Adds message |
| `update_chat_message` | Updates after streaming |
| `clear_chat_messages` | Clears all messages |
| `end_chat_session_and_spawn_new` | Ends and creates new |

### 2.3 Session Notes (8 commands)

| Command | Purpose |
|---------|---------|
| `create_session_note` | Full-featured note creation |
| `get_session_note` | Retrieves note |
| `update_session_note` | Updates note |
| `delete_session_note` | Deletes note |
| `list_session_notes` | Lists notes for session |
| `search_session_notes` | Full-text search |
| `get_notes_by_category` | Filter by category |
| `get_notes_by_tag` | Filter by tag |

### 2.4 AI-Assisted (1 command)

| Command | Purpose |
|---------|---------|
| `categorize_note_ai` | LLM suggests category |

---

## 3. Combat Commands (~20 commands)

### 3.1 Combat State (3 commands)

| Command | Purpose |
|---------|---------|
| `start_combat` | Initializes combat |
| `end_combat` | Ends combat |
| `get_combat` | Returns CombatState |

### 3.2 Combatants (5 commands)

| Command | Purpose |
|---------|---------|
| `add_combatant` | Adds to combat |
| `remove_combatant` | Removes from combat |
| `get_current_combatant` | Gets whose turn it is |
| `damage_combatant` | Reduces HP |
| `heal_combatant` | Increases HP |

### 3.3 Initiative (1 command)

| Command | Purpose |
|---------|---------|
| `next_turn` | Advances initiative order |

### 3.4 Conditions (7 commands)

| Command | Purpose |
|---------|---------|
| `add_condition` | Uses pre-defined conditions |
| `add_condition_advanced` | Full control over duration/save |
| `remove_condition` | Removes by name |
| `remove_condition_by_id` | Removes by ID |
| `get_combatant_conditions` | Lists all conditions |
| `tick_conditions_end_of_turn` | Decrements durations |
| `tick_conditions_start_of_turn` | Processes start effects |
| `list_condition_templates` | Lists templates |

---

## 4. AppState Dependencies

```rust
pub campaign_manager: CampaignManager,
pub session_manager: SessionManager,
pub version_manager: VersionManager,
pub database: Database,
```

---

## 5. Proposed Module Structure

### Option A: Nested (Recommended)

```
commands/
├── campaign/
│   ├── mod.rs
│   ├── crud.rs           # CRUD operations
│   ├── notes.rs          # Campaign notes
│   ├── theme.rs          # Theme management
│   ├── import_export.rs  # Export/import
│   ├── cover.rs          # Cover generation
│   ├── versioning.rs     # Versioning + rollback
│   └── snapshots.rs      # Legacy snapshots
├── session/
│   ├── mod.rs
│   ├── crud.rs           # Session CRUD
│   ├── planned.rs        # Planned sessions
│   ├── chat.rs           # Global chat
│   └── notes.rs          # Session notes + AI
└── combat/
    ├── mod.rs
    ├── state.rs          # Start/end/get combat
    ├── combatants.rs     # Add/remove/damage/heal
    └── conditions.rs     # Condition management
```

### Option B: Flat

```
commands/
├── campaign/
│   ├── mod.rs
│   ├── crud.rs
│   ├── notes.rs
│   ├── theme.rs
│   └── import_export.rs
├── session/
│   ├── mod.rs
│   ├── crud.rs
│   ├── chat.rs
│   ├── notes.rs
│   ├── combat.rs
│   └── conditions.rs
```

---

## 6. Note Categories

```rust
enum NoteCategory {
    General, Combat, Character, Location, Plot, Quest,
    Loot, Rules, Meta, Worldbuilding, Dialogue, Secret, Custom
}
```

---

## 7. Condition Duration Types

```rust
enum ConditionDuration {
    Turns(u32), Rounds(u32), Minutes(u32), Hours(u32),
    EndOfNextTurn, StartOfNextTurn, EndOfSourceTurn,
    UntilSave { save_type, dc, timing },
    UntilRemoved, Permanent,
}
```

---

## 8. Migration Priority

1. Campaign CRUD - Core, simple
2. Campaign theme/snapshots - Independent
3. Session CRUD - Core
4. Combat state - Independent
5. Combat conditions - Complex
6. Session notes - LLM integration
7. Campaign versioning - Complex diff logic
8. Global chat - Database-backed

# World State and Utilities Commands Analysis

## Executive Summary

This module covers world state, relationships, timeline, usage tracking, credentials, audit logs, and system utilities. Total ~46 commands spanning multiple smaller domains.

---

## 1. World State Commands (13 commands)

### 1.1 State Management (5 commands)

| Command | Purpose |
|---------|---------|
| `get_world_state` | Retrieve campaign world state |
| `update_world_state` | Update entire world state |
| `set_world_custom_field` | Set custom field |
| `get_world_custom_field` | Get custom field |
| `list_world_custom_fields` | List all custom fields |

### 1.2 In-Game Calendar (3 commands)

| Command | Purpose |
|---------|---------|
| `set_in_game_date` | Set current date |
| `get_in_game_date` | Get current date |
| `advance_in_game_date` | Advance calendar |

### 1.3 Location State (4 commands)

| Command | Purpose |
|---------|---------|
| `set_location_state` | Store location state |
| `get_location_state` | Retrieve location |
| `list_locations` | List all locations |
| `update_location_condition` | Update location status |

### 1.4 World Events (3 commands)

| Command | Purpose |
|---------|---------|
| `add_world_event` | Create event |
| `list_world_events` | Query events |
| `delete_world_event` | Remove event |

---

## 2. Relationship Commands (8 commands)

### 2.1 CRUD Operations (4 commands)

| Command | Purpose |
|---------|---------|
| `create_entity_relationship` | Create relationship |
| `get_entity_relationship` | Retrieve by ID |
| `update_entity_relationship` | Update relationship |
| `delete_entity_relationship` | Delete relationship |

### 2.2 Queries (2 commands)

| Command | Purpose |
|---------|---------|
| `list_entity_relationships` | All relationships in campaign |
| `get_relationships_for_entity` | All connections to entity |
| `get_relationships_between_entities` | Direct connections |

### 2.3 Graph Operations (2 commands)

| Command | Purpose |
|---------|---------|
| `get_entity_graph` | Full graph for visualization |
| `get_ego_graph` | Ego-centric subgraph (depth=2) |

**Entity Types**: PC, NPC, Location, Faction, Item, Event, Quest, Deity, Creature, Custom

**Relationship Types**: 28+ including Ally, Enemy, Romantic, Family, Mentor, Patron, MemberOf, LeaderOf, LocatedAt, Worships, etc.

---

## 3. Timeline Commands (4 commands)

| Command | Purpose |
|---------|---------|
| `add_timeline_event` | Create timeline entry |
| `get_session_timeline` | Retrieve events for session |
| `get_timeline_summary` | Get aggregate stats |
| `get_timeline_events_by_type` | Filter by type |

**Event Types**: SessionStart, SessionEnd, CombatStart, CombatEnd, CombatDamage, CombatHealing, CombatDeath, NoteAdded, NPCInteraction, LocationChange, ConditionApplied, etc.

---

## 4. Usage Tracking Commands (7 commands)

### 4.1 Statistics (4 commands)

| Command | Purpose |
|---------|---------|
| `get_usage_stats` | Total usage across providers |
| `get_usage_by_period` | Usage in past N hours |
| `get_cost_breakdown` | Cost by provider and model |
| `get_provider_usage` | Provider-specific stats |

### 4.2 Budget Management (3 commands)

| Command | Purpose |
|---------|---------|
| `get_budget_status` | Check budget limits |
| `set_budget_limit` | Set/update budget |
| `reset_usage_session` | Clear session metrics |

**State**: `UsageTrackerState { tracker: UsageTracker }`

---

## 5. Credential Commands (4 commands)

| Command | Purpose |
|---------|---------|
| `save_api_key` | Store API key in keyring |
| `get_api_key` | Retrieve API key |
| `delete_api_key` | Remove from keyring |
| `list_stored_providers` | List configured providers |

**Storage**: System keyring via `CredentialManager`

---

## 6. Audit Log Commands (6 commands)

### 6.1 Queries (4 commands)

| Command | Purpose |
|---------|---------|
| `get_audit_logs` | Recent events |
| `query_audit_logs` | Advanced query |
| `get_security_events` | Critical events (24h) |
| `get_audit_summary` | Count by severity |

### 6.2 Export & Maintenance (2 commands)

| Command | Purpose |
|---------|---------|
| `export_audit_logs` | Export as JSON/CSV/JSONL |
| `clear_old_logs` | Delete old logs |

**Severity Levels**: Debug, Info, Warning, Security, Critical

**State**: `AuditLoggerState { logger: SecurityAuditLogger }`

---

## 7. System Utility Commands (4 commands)

| Command | Purpose |
|---------|---------|
| `get_app_version` | Returns CARGO_PKG_VERSION |
| `get_app_system_info` | Returns OS, arch, version |
| `get_audio_volumes` | Returns AudioVolumes |
| `get_sfx_categories` | Lists SFX categories |
| `open_url_in_browser` | Shell to system browser |

---

## 8. AppState Dependencies

```rust
pub world_state_manager: WorldStateManager,
pub relationship_manager: RelationshipManager,
pub session_manager: SessionManager,  // For timeline
pub credentials: CredentialManager,
pub database: Database,
```

Additional state types:
- `UsageTrackerState`
- `AuditLoggerState`

---

## 9. Proposed Module Structure

```
commands/
├── world/
│   ├── mod.rs
│   ├── state.rs          # get/update state, custom fields
│   ├── calendar.rs       # In-game date management
│   ├── locations.rs      # Location state management
│   └── events.rs         # World event CRUD
│
├── relationships/
│   ├── mod.rs
│   ├── crud.rs           # Create/read/update/delete
│   ├── queries.rs        # List/get relationships
│   └── graph.rs          # Entity graph operations
│
├── timeline/
│   ├── mod.rs
│   └── events.rs         # Add/get/query timeline events
│
├── usage/
│   ├── mod.rs
│   ├── stats.rs          # Usage statistics
│   └── budget.rs         # Budget management
│
├── credentials/
│   ├── mod.rs
│   └── keys.rs           # API key storage
│
├── audit/
│   ├── mod.rs
│   ├── logs.rs           # Query and retrieval
│   └── export.rs         # Export operations
│
└── system/
    ├── mod.rs
    ├── info.rs           # App version, system info
    └── audio.rs          # Audio volume, SFX
```

---

## 10. Command Count by Module

| Module | Count | Est. LOC |
|--------|-------|----------|
| world/ | 13 | 250 |
| relationships/ | 8 | 200 |
| timeline/ | 4 | 120 |
| usage/ | 7 | 150 |
| credentials/ | 4 | 80 |
| audit/ | 6 | 180 |
| system/ | 4 | 80 |
| **Total** | **46** | **1,060** |

---

## 11. Migration Priority

1. System utilities - Simple, isolated
2. Credentials - Simple keyring operations
3. World state - Independent manager
4. Relationships - Graph operations
5. Timeline - Session manager dependency
6. Usage tracking - Separate state type
7. Audit logs - Separate state type

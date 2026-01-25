# Personality System Commands Analysis

## Executive Summary

The personality system is one of the largest command groups (~35 commands, ~550 lines). It spans personality profiles, setting templates, blend rules, contextual personality management, NPC dialogue styling, and narration.

**Recommended structure**: 6 focused modules (`profiles`, `templates`, `blending`, `context`, `styling`, `types`)

---

## 1. Identified Commands

### 1.1 Personality Profile Commands (14 commands)

| Command | Purpose |
|---------|---------|
| `set_active_personality` | Set active personality for session |
| `get_active_personality` | Get active personality ID |
| `get_personality_prompt` | Get system prompt for personality |
| `apply_personality_to_text` | Apply LLM transformation (async) |
| `get_personality_context` | Get campaign personality context |
| `get_session_personality_context` | Get session-specific context |
| `set_personality_context` | Update personality context |
| `set_narrator_personality` | Set narrator personality |
| `assign_npc_personality` | Assign personality to NPC |
| `unassign_npc_personality` | Remove personality from NPC |
| `set_personality_settings` | Update settings |
| `set_personality_active` | Toggle on/off |
| `list_personalities` | List all with previews |
| `clear_session_personality_context` | Clear session context |

### 1.2 Preview Commands (4 commands)

| Command | Purpose |
|---------|---------|
| `preview_personality` | Get personality preview |
| `preview_personality_extended` | Get full preview |
| `generate_personality_preview` | LLM-generated preview (async) |
| `test_personality` | Test with prompt (async) |

### 1.3 Template Commands (9 commands)

| Command | Purpose |
|---------|---------|
| `list_personality_templates` | List all templates |
| `filter_templates_by_game_system` | Filter by system |
| `filter_templates_by_setting` | Filter by setting |
| `search_personality_templates` | Keyword search |
| `get_template_preview` | Get by ID |
| `apply_template_to_campaign` | Apply template |
| `create_template_from_personality` | Create from profile |
| `export_personality_template` | Export to YAML |
| `import_personality_template` | Import from YAML |

### 1.4 Blend Rule Commands (6 commands)

| Command | Purpose |
|---------|---------|
| `set_blend_rule` | Create/update blend rule |
| `get_blend_rule` | Get rule for context |
| `list_blend_rules` | List campaign rules |
| `delete_blend_rule` | Delete rule |
| `get_blender_cache_stats` | Get cache stats |
| `get_blend_rule_cache_stats` | Get rule cache stats |

### 1.5 Context Commands (7 commands)

| Command | Purpose |
|---------|---------|
| `detect_gameplay_context` | Detect from input |
| `get_contextual_personality` | Get blended for context |
| `get_current_context` | Get smoothed context |
| `clear_context_history` | Reset detection |
| `get_contextual_personality_config` | Get config |
| `set_contextual_personality_config` | Update config |
| `list_gameplay_contexts` | List all context types |

### 1.6 Styling Commands (4 commands)

| Command | Purpose |
|---------|---------|
| `style_npc_dialogue` | Apply styling to dialogue |
| `build_npc_system_prompt` | Build NPC prompt |
| `get_session_system_prompt` | Get session prompt |
| `build_narration_prompt` | Build narration prompt |

---

## 2. AppState Dependencies

```rust
pub personality_store: Arc<PersonalityStore>,
pub personality_manager: Arc<PersonalityApplicationManager>,
pub template_store: Arc<SettingTemplateStore>,
pub blend_rule_store: Arc<BlendRuleStore>,
pub personality_blender: Arc<PersonalityBlender>,
pub contextual_personality_manager: Arc<ContextualPersonalityManager>,
pub llm_config: RwLock<Option<LLMConfig>>,  // For async commands
```

---

## 3. Proposed Module Structure

```
commands/personality/
├── mod.rs              # Re-exports (~20 lines)
├── types.rs            # Request/Response types (~100 lines)
├── profiles.rs         # Profile CRUD + preview (~170 lines)
├── templates.rs        # Template operations (~155 lines)
├── blending.rs         # Blend rules (~85 lines)
├── context.rs          # Context detection (~145 lines)
└── styling.rs          # Dialogue styling (~60 lines)
```

**Total**: ~735 lines across 7 files

---

## 4. Key Types to Extract

### Request Types
- `SetActivePersonalityRequest`
- `PersonalitySettingsRequest`
- `ApplyTemplateRequest`
- `CreateTemplateFromPersonalityRequest`
- `SetBlendRuleRequest`
- `BlendComponentInput`
- `DetectContextRequest`
- `GetContextualPersonalityRequest`

### Response Types
- `TemplatePreviewResponse` + `From<SettingTemplate>`
- `BlendRuleResponse` + `From<BlendRule>`
- `GameplayContextInfo`

---

## 5. Migration Priority

1. `types.rs` - No dependencies
2. `profiles.rs` - Depends on types
3. `blending.rs` - Depends on types
4. `templates.rs` - Depends on types, profiles
5. `context.rs` - Depends on types, blending
6. `styling.rs` - Depends on types, profiles
7. `mod.rs` - Aggregates all

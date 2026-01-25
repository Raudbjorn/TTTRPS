# Command Inventory

Total commands in `commands_legacy.rs`: **310**

## Categorized Commands by Domain

### LLM / Intelligence (~25 commands)
**Configuration & Health**
- `configure_llm` - Configure LLM provider
- `get_llm_config` - Get current LLM config
- `check_llm_health` - Check provider health

**Router**
- `get_router_stats` - Get router statistics
- `get_router_health` - Check router health
- `get_router_costs` - Get cost tracking
- `run_provider_health_checks` - Run health checks
- `set_routing_strategy` - Set routing strategy
- `get_healthy_providers` - List healthy providers

**Chat**
- `chat` - Send chat message
- `stream_chat` - Stream chat response
- `cancel_stream` - Cancel active stream
- `get_active_streams` - List active streams

**Model Listing**
- `list_ollama_models` - List Ollama models
- `list_openai_models` - List OpenAI models
- `list_claude_models` - List Claude models
- `list_gemini_models` - List Gemini models
- `list_openrouter_models` - List OpenRouter models
- `list_provider_models` - List models for provider
- `list_chat_providers` - List chat providers

**Model Selection**
- `get_model_selection` - Get model selection
- `get_model_selection_for_prompt` - Get model for prompt
- `set_model_override` - Override model selection
- `estimate_request_cost` - Estimate request cost

**Embeddings**
- `configure_meilisearch_embedder` - Configure embedder
- `list_local_embedding_models` - List local models
- `list_ollama_embedding_models` - List Ollama embeddings
- `setup_local_embeddings` - Setup local embeddings
- `setup_ollama_embeddings` - Setup Ollama embeddings
- `get_embedder_status` - Get embedder status
- `get_vector_store_status` - Get vector store status

---

### Campaign (~20 commands)
**CRUD**
- `create_campaign` - Create campaign
- `get_campaign` - Get campaign
- `list_campaigns` - List campaigns
- `update_campaign` - Update campaign
- `delete_campaign` - Delete campaign
- `get_campaign_stats` - Get campaign statistics

**Notes**
- `add_campaign_note` - Add note
- `get_campaign_notes` - Get notes
- `search_campaign_notes` - Search notes
- `delete_campaign_note` - Delete note

**Theme**
- `get_campaign_theme` - Get theme
- `set_campaign_theme` - Set theme
- `get_theme_preset` - Get theme preset

**Import/Export**
- `export_campaign` - Export campaign
- `import_campaign` - Import campaign
- `generate_campaign_cover` - Generate cover image

**Versioning**
- `create_campaign_version` - Create version
- `list_campaign_versions` - List versions
- `get_campaign_version` - Get version
- `compare_campaign_versions` - Compare versions
- `delete_campaign_version` - Delete version
- `rollback_campaign` - Rollback to version
- `add_version_tag` - Add version tag
- `mark_version_milestone` - Mark milestone

**Snapshots**
- `create_snapshot` - Create snapshot
- `list_snapshots` - List snapshots
- `restore_snapshot` - Restore snapshot

---

### Session (~25 commands)
**CRUD**
- `start_session` - Start session
- `get_session` - Get session
- `get_active_session` - Get active session
- `list_sessions` - List sessions
- `end_session` - End session
- `create_planned_session` - Create planned
- `start_planned_session` - Start planned
- `reorder_session` - Reorder session

**Notes**
- `create_session_note` - Create note
- `get_session_note` - Get note
- `list_session_notes` - List notes
- `update_session_note` - Update note
- `delete_session_note` - Delete note
- `search_session_notes` - Search notes
- `get_notes_by_category` - Get by category
- `get_notes_by_tag` - Get by tag
- `link_entity_to_note` - Link entity
- `unlink_entity_from_note` - Unlink entity
- `categorize_note_ai` - AI categorization

**Timeline**
- `get_session_timeline` - Get timeline

**System Prompt**
- `get_session_system_prompt` - Get system prompt

---

### Combat (~20 commands)
**State**
- `start_combat` - Start combat
- `end_combat` - End combat
- `get_combat` - Get combat state

**Combatants**
- `add_combatant` - Add combatant
- `remove_combatant` - Remove combatant
- `damage_combatant` - Apply damage
- `heal_combatant` - Apply healing
- `next_turn` - Next turn
- `get_current_combatant` - Get current

**Conditions**
- `add_condition` - Add condition
- `add_condition_advanced` - Add advanced
- `remove_condition` - Remove condition
- `remove_condition_by_id` - Remove by ID
- `remove_advanced_condition` - Remove advanced
- `apply_advanced_condition` - Apply advanced
- `get_combatant_conditions` - Get conditions
- `list_condition_templates` - List templates
- `tick_conditions_start_of_turn` - Tick start
- `tick_conditions_end_of_turn` - Tick end

---

### Global Chat Sessions (~10 commands)
- `get_or_create_chat_session` - Get or create
- `get_active_chat_session` - Get active
- `list_chat_sessions` - List sessions
- `get_chat_sessions_for_game` - Get for game
- `get_chat_messages` - Get messages
- `add_chat_message` - Add message
- `update_chat_message` - Update message
- `clear_chat_messages` - Clear messages
- `link_chat_to_game_session` - Link to game
- `end_chat_session_and_spawn_new` - End and spawn

---

### NPC (~20 commands)
**CRUD**
- `generate_npc` - Generate NPC
- `get_npc` - Get NPC
- `list_npcs` - List NPCs
- `list_npc_summaries` - List summaries
- `update_npc` - Update NPC
- `delete_npc` - Delete NPC
- `search_npcs` - Search NPCs

**Conversations**
- `get_npc_conversation` - Get conversation
- `list_npc_conversations` - List conversations
- `add_npc_message` - Add message
- `reply_as_npc` - Reply as NPC
- `mark_npc_read` - Mark as read

**Personality**
- `assign_npc_personality` - Assign personality
- `unassign_npc_personality` - Unassign
- `build_npc_system_prompt` - Build prompt
- `build_npc_system_prompt_stub` - Build stub

**Indexing**
- `initialize_npc_indexes` - Init indexes
- `get_npc_indexes_stats` - Get stats
- `clear_npc_indexes` - Clear indexes

---

### NPC Extensions (~10 commands)
**Vocabulary**
- `load_vocabulary_bank` - Load vocabulary
- `get_vocabulary_phrase` - Get phrase
- `get_vocabulary_directory` - Get directory

**Names**
- `load_naming_rules` - Load rules
- `validate_naming_rules` - Validate rules
- `get_random_name_structure` - Get random
- `get_names_directory` - Get directory

**Dialects**
- `load_dialect` - Load dialect
- `apply_dialect` - Apply dialect
- `get_dialects_directory` - Get directory

---

### Personality (~30 commands)
**CRUD**
- `list_personalities` - List all
- `get_active_personality` - Get active
- `set_active_personality` - Set active
- `set_personality_active` - Set active (variant)
- `preview_personality` - Preview
- `preview_personality_extended` - Extended preview
- `generate_personality_preview` - Generate preview
- `test_personality` - Test personality

**Templates**
- `list_personality_templates` - List templates
- `search_personality_templates` - Search templates
- `filter_templates_by_setting` - Filter by setting
- `filter_templates_by_game_system` - Filter by system
- `import_personality_template` - Import template
- `export_personality_template` - Export template
- `create_template_from_personality` - Create from profile
- `get_template_preview` - Get preview
- `apply_template_to_campaign` - Apply to campaign

**Blending**
- `list_blend_rules` - List rules
- `get_blend_rule` - Get rule
- `set_blend_rule` - Set rule
- `delete_blend_rule` - Delete rule
- `get_blender_cache_stats` - Get cache stats
- `get_blend_rule_cache_stats` - Get rule cache

**Context**
- `get_contextual_personality` - Get contextual
- `get_contextual_personality_config` - Get config
- `set_contextual_personality_config` - Set config
- `detect_gameplay_context` - Detect context
- `list_gameplay_contexts` - List contexts
- `get_personality_context` - Get context
- `set_personality_context` - Set context
- `get_session_personality_context` - Get session context
- `clear_session_personality_context` - Clear context
- `clear_context_history` - Clear history
- `get_current_context` - Get current

**Settings**
- `set_personality_settings` - Set settings
- `get_personality_prompt` - Get prompt

**Styling**
- `style_npc_dialogue` - Style dialogue
- `apply_personality_to_text` - Apply to text
- `build_narration_prompt` - Build prompt
- `set_narrator_personality` - Set narrator
- `set_scene_mood` - Set mood

---

### Search & Library (~40 commands)
**Search**
- `search` - Basic search
- `hybrid_search` - Hybrid search
- `expand_query` - Expand query
- `correct_query` - Correct query
- `get_search_hints` - Get hints
- `get_search_suggestions` - Get suggestions

**Meilisearch**
- `check_meilisearch_health` - Check health
- `configure_meilisearch_chat` - Configure chat

**Documents**
- `ingest_document` - Ingest document
- `ingest_document_two_phase` - Two-phase ingest
- `ingest_pdf` - Ingest PDF
- `get_ttrpg_document` - Get document
- `get_ttrpg_document_attributes` - Get attributes
- `get_ttrpg_document_stats` - Get stats
- `delete_ttrpg_document` - Delete document
- `search_ttrpg_documents_by_name` - Search by name
- `find_ttrpg_documents_by_attribute` - Find by attribute
- `list_ttrpg_documents_by_type` - List by type
- `list_ttrpg_documents_by_system` - List by system
- `list_ttrpg_documents_by_source` - List by source
- `list_ttrpg_documents_by_cr` - List by CR
- `count_ttrpg_documents_by_type` - Count by type
- `clear_and_reingest_document` - Clear and reingest

**Ingestion Jobs**
- `get_ttrpg_ingestion_job` - Get job
- `get_ttrpg_ingestion_job_by_document` - Get by doc
- `list_active_ttrpg_ingestion_jobs` - List active
- `list_pending_ttrpg_ingestion_jobs` - List pending

**Library**
- `list_library_documents` - List documents
- `delete_library_document` - Delete document
- `update_library_document` - Update document
- `rebuild_library_metadata` - Rebuild metadata
- `reindex_library` - Reindex library

**Analytics (In-Memory)**
- `get_search_analytics` - Get analytics
- `get_popular_queries` - Popular queries
- `get_cache_stats` - Cache stats
- `get_trending_queries` - Trending queries
- `get_zero_result_queries` - Zero results
- `get_click_distribution` - Click distribution
- `record_search_selection` - Record selection
- `record_search_event` - Record event
- `cleanup_search_analytics` - Cleanup

**Analytics (Database)**
- `get_search_analytics_db` - Get from DB
- `get_popular_queries_db` - Popular from DB
- `get_cache_stats_db` - Cache from DB
- `get_trending_queries_db` - Trending from DB
- `get_zero_result_queries_db` - Zero from DB
- `get_click_distribution_db` - Clicks from DB
- `record_search_selection_db` - Record to DB

---

### Extraction (~5 commands)
- `get_extraction_settings` - Get settings
- `save_extraction_settings` - Save settings
- `get_extraction_presets` - Get presets
- `check_ocr_availability` - Check OCR
- `get_supported_formats` - Get formats

---

### World State (~15 commands)
**State**
- `get_world_state` - Get state
- `update_world_state` - Update state

**Locations**
- `set_location_state` - Set location
- `get_location_state` - Get location
- `list_locations` - List locations
- `update_location_condition` - Update condition

**Custom Fields**
- `set_world_custom_field` - Set field
- `get_world_custom_field` - Get field
- `list_world_custom_fields` - List fields

**Calendar**
- `set_calendar_config` - Set config
- `get_calendar_config` - Get config
- `get_in_game_date` - Get date
- `set_in_game_date` - Set date
- `advance_in_game_date` - Advance date

---

### Relationships (~10 commands)
- `create_entity_relationship` - Create
- `get_entity_relationship` - Get
- `update_entity_relationship` - Update
- `delete_entity_relationship` - Delete
- `list_entity_relationships` - List all
- `get_relationships_for_entity` - For entity
- `get_relationships_between_entities` - Between entities
- `get_entity_graph` - Get graph
- `get_ego_graph` - Get ego graph

---

### Timeline (~10 commands)
- `add_timeline_event` - Add event
- `add_world_event` - Add world event
- `delete_world_event` - Delete event
- `list_world_events` - List events
- `get_timeline_events_by_type` - By type
- `get_timeline_summary` - Get summary

---

### Location Generation (~15 commands)
**Generation**
- `generate_location` - Generate full
- `generate_location_quick` - Generate quick

**CRUD**
- `save_location` - Save location
- `get_location` - Get location
- `list_campaign_locations` - List for campaign
- `delete_location` - Delete location
- `search_locations` - Search locations
- `update_location` - Update location

**Details**
- `add_location_connection` - Add connection
- `remove_location_connection` - Remove connection
- `get_connected_locations` - Get connected
- `add_location_inhabitant` - Add inhabitant
- `remove_location_inhabitant` - Remove inhabitant
- `add_location_encounter` - Add encounter
- `add_location_secret` - Add secret
- `set_location_map_reference` - Set map ref

**Types**
- `list_location_types` - List types
- `get_location_types` - Get types

---

### Character Generation (~5 commands)
- `generate_character` - Generate character
- `generate_character_advanced` - Advanced generation
- `get_system_info` - Get system info
- `list_system_info` - List systems
- `get_supported_systems` - Get supported

---

### Usage Tracking (~7 commands)
- `get_usage_stats` - Get stats
- `get_usage_by_period` - By period
- `get_cost_breakdown` - Cost breakdown
- `get_budget_status` - Budget status
- `set_budget_limit` - Set limit
- `get_provider_usage` - Provider usage
- `reset_usage_session` - Reset session

---

### Credentials (~4 commands)
- `save_api_key` - Save key
- `get_api_key` - Get key
- `delete_api_key` - Delete key
- `list_stored_providers` - List providers

---

### Audit (~7 commands)
- `get_audit_logs` - Get logs
- `query_audit_logs` - Query logs
- `export_audit_logs` - Export logs
- `get_audit_summary` - Get summary
- `get_security_events` - Get security events
- `clear_old_logs` - Clear old logs

---

### System Utilities (~10 commands)
- `get_app_version` - Get version
- `get_app_system_info` - Get system info
- `get_audio_volumes` - Get volumes
- `get_sfx_categories` - Get SFX categories
- `open_url_in_browser` - Open URL
- `speak` - TTS speak
- `transcribe_audio` - Transcribe audio
- `import_layout_json` - Import layout
- `configure_chat_workspace` - Configure workspace
- `get_chat_workspace_settings` - Get workspace settings

---

## Summary by Module

| Module | Command Count | Est. Lines |
|--------|--------------|------------|
| `llm/` | ~25 | ~600 |
| `campaign/` | ~20 | ~400 |
| `session/` | ~25 | ~400 |
| `combat/` | ~20 | ~400 |
| `chat/` | ~10 | ~200 |
| `npc/` | ~30 | ~600 |
| `personality/` | ~30 | ~800 |
| `search/` | ~40 | ~800 |
| `world/` | ~15 | ~300 |
| `relationships/` | ~10 | ~300 |
| `timeline/` | ~10 | ~200 |
| `location/` | ~15 | ~400 |
| `generation/` | ~5 | ~200 |
| `usage/` | ~7 | ~100 |
| `credentials/` | ~4 | ~100 |
| `audit/` | ~7 | ~200 |
| `system/` | ~10 | ~200 |
| **TOTAL** | **~310** | **~6200** |

Note: ~2000 lines are types, helpers, and AppState struct which should be extracted to shared modules.

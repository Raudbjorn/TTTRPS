# Commands Refactoring Project - Planning Index

## Overview

This planning directory contains the spec-driven development artifacts for refactoring
`src-tauri/src/commands_legacy.rs` (8303 lines, 310 Tauri commands) into domain-specific modules.

## Branch

- Feature branch: `refactor/commands-modularization`
- Base: `main`

## Planning Phase Status

**Status: ✅ COMPLETE** (2026-01-25)

All planning documents have been generated. The project is ready to proceed to implementation following the task sequence in `12-tasks.md`.

| Metric | Value |
|--------|-------|
| Commands to Extract | ~310 |
| Legacy File Lines | 8,303 |
| Target Modules | 16 |
| Implementation Tasks | 29 |
| Estimated Effort | ~66 hours |
| Phases | 6 |

---

## Current State

### Already Extracted Modules
- `commands/voice/` - Voice synthesis, providers, presets, profiles, queue, cache
- `commands/oauth/` - Claude, Gemini, Copilot OAuth flows
- `commands/archetype/` - CRUD, vocabulary, setting packs, resolution

### Remaining in commands_legacy.rs
- ~310 commands across multiple domains
- ~8303 lines to be organized

## Planning Documents

### Analysis Phase
| Document | Description | Status |
|----------|-------------|--------|
| `01-codebase-analysis.md` | Full codebase structure map | ✅ Complete |
| `02-module-architecture.md` | Target module design | ✅ Complete |
| `03-tauri-patterns.md` | Tauri command patterns analysis | ✅ Complete |

### Requirements Phase
| Document | Description | Status |
|----------|-------------|--------|
| `04-requirements.md` | EARS-format requirements | ✅ Complete |

### Domain Analysis
| Document | Description | Status |
|----------|-------------|--------|
| `05-personality-module.md` | Personality system commands | ✅ Complete |
| `06-search-library-module.md` | Search and library commands | ✅ Complete |
| `07-llm-module.md` | LLM and streaming commands | ✅ Complete |
| `08-campaign-session-module.md` | Campaign and session commands | ✅ Complete |
| `09-npc-generation-module.md` | NPC and generation commands | ✅ Complete |
| `10-world-utilities-module.md` | World state and utilities | ✅ Complete |

### Design Phase
| Document | Description | Status |
|----------|-------------|--------|
| `11-design.md` | Comprehensive design document | ✅ Complete |

### Implementation Phase
| Document | Description | Status |
|----------|-------------|--------|
| `12-tasks.md` | Sequenced implementation tasks | ✅ Complete |

## Proposed Module Structure

```
src-tauri/src/commands/
├── mod.rs              # Re-exports all modules
├── error.rs            # CommandError, CommandResult (existing)
├── macros.rs           # Helper macros (existing)
├── state.rs            # State access traits (new)
├── types.rs            # Shared request/response types (new)
│
├── voice/              # [DONE] Voice synthesis
├── oauth/              # [DONE] OAuth flows
├── archetype/          # [DONE] Archetype system
│
├── llm/                # LLM config, chat, streaming, models
├── campaign/           # Campaign CRUD, notes, theme, versioning
├── session/            # Sessions, combat, combatants
├── npc/                # NPC CRUD, conversations, extensions
├── personality/        # Profiles, templates, blending
├── search/             # Search, analytics, ingestion
├── world/              # World state, calendar, locations
├── relationships/      # Entity relationships, graphs
├── generation/         # Character, location generation
├── credentials/        # API key management
├── usage/              # Usage tracking, budgets
├── timeline/           # Timeline events
├── audit/              # Audit logs, security
└── system/             # App info, utilities
```

## Settings Tab Alignment

| Settings Tab | Command Modules |
|--------------|-----------------|
| General | `system/` |
| Intelligence | `llm/`, `oauth/` |
| Voice | `voice/` |
| Data & Library | `search/`, `credentials/` |
| Extraction | `search/extraction.rs` |

## Key Design Decisions

1. **Module Grouping**: Commands grouped by domain for cohesion
2. **Re-export Pattern**: Glob re-exports (`pub use module::*`) for Tauri registration
3. **Error Handling**: Unified `CommandError` with domain-specific variants
4. **Testability**: Trait-based state access for mock injection
5. **File Size**: Target <500 lines per file, split into submodules if larger

## Non-Goals

- No frontend changes required
- No command signature changes
- No new features (pure refactoring)

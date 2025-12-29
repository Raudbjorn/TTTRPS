# UX Overhaul & Feature Tasks

## Phase 1: Backend Implementation (Rust/Tauri)
These tasks must be completed to support the new UX requirements.

### NPC & Character Management
- [ ] **[BE] Task B1**: Implement `save_character` and `list_characters(campaign_id)` commands.
    - *Context*: Currently `generate_character` exists but no persistence linked to campaigns.
    - *Requirement*: NPC Sidebar.
- [ ] **[BE] Task B2**: Update `Character` struct to include `campaign_id` and `is_npc` boolean.

### Session Management Needs
- [ ] **[BE] Task B3**: Update `list_sessions` to return `status` (Past, Active, Planned) in `SessionSummary`.
    - *Context*: Currently `SessionSummary` lacks status info.
- [ ] **[BE] Task B4**: Implement "Planned" session state support (create session without starting it?).

### Personality & Voice
- [ ] **[BE] Task B5**: Create `Personality` storage/struct (Voice ID + Source Document path).
- [ ] **[BE] Task B6**: Implement `list_personalities` and `save_personality`.
- [ ] **[BE] Task B7**: Implement Real-time STT (Speech-to-Text) backend or expose web-based STT capability if local not feasible yet.
    - *Requirement*: Live Transcription.

---

## Phase 2: Frontend Implementation (Dioxus/Rust)
These tasks implement the UX/UI changes using the backend capabilities.

### Campaign & Layout
- [ ] **[FE] Task F1**: Refactor `Campaigns` page to new 3-column layout (Nav | Sessions | Active View | NPC Sidebar).
    - *Mockup Data*: Use placeholder signals until BE Task B1/B3 are ready.
- [ ] **[FE] Task F2**: Implement `SessionList` component.
    - Groups sessions by Status (Past/Current/Planned).
- [ ] **[FE] Task F3**: Implement `NPCList` Sidebar component.
    - Displays NPCs for current campaign.

### Personality Manager
- [ ] **[FE] Task F4**: Create `PersonalityManager` view.
    - Grid view of personalities.
    - Link Voice -> Document.

### Chat & Audio Interaction
- [ ] **[FE] Task F5**: Create `MediaBar` component (Persistent Bottom Bar).
    - Features: Play/Pause, Volume, Active Voice visualization.
- [ ] **[FE] Task F6**: Update `ChatMessage` to queue audio to `MediaBar` instead of playing inline.
- [ ] **[FE] Task F7**: Add `TranscriptionToggle` to `MediaBar` or Chat.
    - *Blocked by*: BE Task B7.

### Visual Polish
- [ ] **[FE] Task F8**: Global Theme Update (Tailwind).
    - Glassmorphism effects.
    - Typography updates.

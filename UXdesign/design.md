# UX Design Specification

## Overview
The goal is to modernize the TTRPG Assistant interface, switching to a more dense, information-rich, yet clean layout suitable for Dungeon Masters. We will leverage a "Glassmorphism" aesthetic with dark modes to fit the "Fantasy" theme.

## Design Metaphor: "Spotify meets Slack"
- **Spotify**:
    - **Campaigns = Albums**: Detailed cover art, list of tracks (Sessions).
    - **Sessions = Songs**: The unit of content. Playlist view in sidebar.
    - **Settings = Genres/Moods**: Visual theming.
- **Slack**:
    - **NPC Interactions = DMs**: Sidebar list of NPCs mimics a DM list.
    - **Game Log = Thread**: The main chat view follows Slack's reliable message threading and input style.
- **Obsidian**: Dense, text-centric knowledge management for the Library. File trees, preview panes, and markdown-first editing.

## Layout Structure
### Global Layout
- **App Rail (Leftmost)**: Icons only (Slack-style). [Chat, Campaigns, Library, Settings, Personalities].
- **Context Sidebar (Secondary Left)**:
    - **In Campaign Mode**: "Channels" = Sessions. Grouped by Status.
    - **In Library Mode**: File tree (Obsidian-style).
- **Main Content Area (Center)**:
    - The active workspace.
- **Info Sidebar (Right / Toggleable)**:
    - **Details/Thread**: NPC Details, Dice Roller, extensive properties.
- **Media Bar (Bottom)**:
    - Persistent audio controls for Voice/TTS playback.


## Component Designs

### 1. NPC Sidebar
- **Visual**: Vertical list of avatar + name cards.
- **Interaction**: Click to open details modal/panel. Hover for quick stats.
- **Location**: Right side of the Campaign View.

### 2. Session Manager
- **Visual**: Accordion or Tabbed list in the Secondary Left Sidebar.
- **Groups**:
    - *History* (Past) - greyed out / archived look.
    - *Active* (Current) - Highlighted, pulsing indicator.
    - *Planning* (Planned) - Dashed border or distinct "draft" styling.

### 3. Personality Manager
- **Interface**: Grid view of available "Voices/Personalities".
- **Configuration**: Dropdown to link a personality to a Source Document (e.g., "Gladiator.pdf").
- **Edit Mode**: Slider/Form for adjusting parameters (Speed, Pitch if available).

### Visual Polish & Dynamic Immersion
- [ ] **[FE] Task F8**: Implement `ThemeManager` service.
    -   Detects Campaign System -> Sets Global Theme Class (`fantasy`, `cosmic`, `terminal`).
- [ ] **[FE] Task F9**: Create CSS/Tailwind definitions for the 3 Dynamic Themes.
    -   *Fantasy*: Glassmorphism.
    -   *Cosmic*: Grain/Horror.
    -   *Terminal*: CRT/Scanlines.
- [ ] **[FE] Task F10**: Global Theme Update (Refactor components to use CSS variables/Theme tokens).

### 4. Chat/Output Interface
- **Message Bubble**:
    - **Header**: Speaker Name (DM/NPC).
    - **Body**: Text content.
    - **Footer**:
        - **Play Action**: Queue to Bottom Media Bar.
- **Media Bar (New)**:
    - **Location**: Fixed at bottom of screen.
    - **Controls**: Play/Pause, Volume, Visualization of active voice.
- **Transcription Control**:
    - **Location**: Top of Chat Input or Media Bar.


## Dynamic Immersion (Theming)
The UI must visually adapt to the active campaign's game system.
**Core Themes**:
1.  **Fantasy (Default / D&D)**:
    -   *Aesthetic*: Clean Glassmorphism + "Arcane" accents.
    -   *Colors*: Deep purple/slate, Gold borders.
    -   *Font*: Sans-serif body, Serif headers (Cinzel/Merriweather).
2.  **Cosmic Horror (Cthulhu)**:
    -   *Aesthetic*: Grime, "Old" paper feel, Unsettling geometry.
    -   *Colors*: Sickly green, deep black, void purple.
    -   *Effects*: Subtle film grain, slow pulsating shadows.
3.  **Retro Sci-Fi (Mothership/Alien)**:
    -   *Aesthetic*: "Nostromo" Mainframe, CRUD, Terminal.
    -   *Colors*: High contrast Amber/Green on Black.
    -   *Font*: Monospace (Fira Code/VT323).
    -   *Effects*: Scanlines, CRT curved corners, text glow, "glitch" transitions.

## Aesthetics (Tailwind)
- **Colors**: Defined via CSS variables tailored to the active theme class (`.theme-fantasy`, `.theme-cosmic`, `.theme-terminal`).


# ERP AI TUI Design Specification

> **Date:** 2026-04-29
> **Status:** Approved
> **Author:** Sisyphus

## Overview

Terminal User Interface (TUI) for ERP AI Assistant with split-panel layout, command palette, and ANSI color theming.

## UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│  ERP AI Assistant                            [Ctrl+K: Command] │
├───────────────────────────────────────────────────────│───┤
│                                                       │ D │
│  CHAT PANEL (left 70%)                  │ATA PANEL│     │ O │
│                                          │right 30%│     │   │
│  > You: Add customer Acme Corp            │         │     │ R │
│    AI: Customer created! ID: 1             │ Context │     │   │
│                                          │         │     │   │
│  > You: Show inventory                   │ History │     │   │
│    AI: Items: Widget A ($10)...          │         │     │   │
│                                          │         │     │   │
│  ─────────────────────────────────────   │         │     │   │
│  > Type message...                      │         │     │   │
└─────────────────────────────────────────────────────────────┘
```

**Dimensions:**
- Chat panel: 70% width (left)
- Data panel: 30% width (right)
- Min terminal width: 80 cols
- Header: 1 row
- Input area: 1 row

## Visual Design

### Color Scheme

| Element | Color Code | Hex |
|---------|----------|-----|
| Background | Default | `#1e1e2e` |
| Primary text | Light gray | `#cdd6f4` |
| User messages | Blue | `#89b4fa` |
| AI responses | Green | `#a6e3a1` |
| Borders | Gray | `#45475a` |
| Accent | Yellow | `#f9e2af` |
| Error | Red | `#f38ba8` |
| Input prompt | Purple | `#cba6f7` |

### Typography

- Font: Terminal default (monospace)
- Size: Terminal default
- Line height: 1

### ASCII/Unicode Elements

- Vertical divider: `│` (U+2502)
- Horizontal divider: `─` (U+2500)
- Top-left corner: `┌` (U+250C)
- Top-right corner: `┐` (U+2510)
- Bottom-left corner: `└` (U+2514)
- Bottom-right corner: `┘` (U+2518)
- T intersections: `├` (U+251C)
- T intersections: `┤` (U+2524)

## Components

### 1. Header Bar
- Left: App title "ERP AI Assistant"
- Right: Command hint "[Ctrl+K: Command]"
- Style: Bold, accent color

### 2. Chat Panel (Left)
- Scrollable message history
- Each message shows: role (You/AI), content, timestamp
- User messages: blue prefix `> You:`
- AI messages: green prefix `AI:`
- Input prompt: `> ` with purple color

### 3. Data Panel (Right)
- Tabs at top: "Context" | "History"
- Context tab: Current session data
- History tab: Conversation history

### 4. Input Area
- Fixed at bottom of chat panel
- Multiline support (Enter for new line, Esc+Enter to send)
- Autocomplete for commands with Tab

## Command Palette (Ctrl+K)

Trigger: `Ctrl+K` opens overlay input

| Command | Action |
|---------|--------|
| `/customers` | List customers |
| `/items` | List inventory |
| `/invoice` | Generate invoice |
| `/switch` | Toggle LLM provider |
| `/clear` | Clear chat |
| `/quit` or `/exit` | Exit TUI |
| `/help` | Show commands |
| `/model` | Show current model |

## Keybindings

| Key | Action |
|-----|--------|
| `Ctrl+K` | Open command palette |
| `Up/Down` | Navigate history |
| `Ctrl+C` | Cancel input |
| `Ctrl+L` | Clear screen |
| `Ctrl+Q` | Quit |

## Implementation

### Files
- **New:** `tui.py` - Main TUI module
- **Modified:** `run.sh` - Add TUI mode

### Dependencies
- Standard library only (ansi codes)
- No external TUI library (styled text only)

### Integration
- Entry: `tui.py` as alternative to `main.py`
- Mode selection in `run.sh`

## Acceptance Criteria

1. [ ] Split panels render correctly (70/30)
2. [ ] Colors display properly
3. [ ] Messages scroll in chat panel
4. [ ] Ctrl+K opens command input
5. [ ] All commands work
6. [ ] Provider switching works
7. [ ] Exit returns to menu
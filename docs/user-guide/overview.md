# User Guide Overview

Welcome to the VimAbl user guide! This section covers everything you need to know to use VimAbl effectively.

## What You'll Learn

### 🎯 Core Concepts

- **Vim-style Navigation** - How `gg`, `G`, and other motions work in Ableton Live
- **Context-Aware Commands** - Different behavior in Session vs Arrangement view
- **Real-Time Updates** - Understanding the observer system and web visualization

### 📚 Guide Sections

#### [Navigation](navigation.md)
Learn all the navigation commands for moving around in Ableton Live efficiently:

- Jump to first/last scene or track (`gg`, `G`)
- Context switching between views
- Scrolling and focus management

#### [Editing](editing.md)
Master the editing commands for manipulating your project:

- Delete operations (`dd`)
- Undo/redo (`za`)
- Browser and device controls

#### [Session vs Arrangement](session-vs-arrangement.md)
Understand how commands behave differently in each view:

- Session View specifics
- Arrangement View specifics
- View switching and context awareness

#### [Keybindings Reference](keybindings.md)
Complete reference of all available keybindings:

- Organized by category
- Includes default mappings
- Quick reference table

#### [UDP/OSC Observers](udp-observers.md)
Learn about the real-time observer system:

- What observers do
- Event types and debouncing
- Performance characteristics

#### [Web TreeViewer](web-treeviewer.md)
Using the real-time project visualization:

- Starting the TreeViewer
- Navigation and exploration
- Real-time updates

## Getting Help

!!! tip "Quick Reference"
    For a complete list of all keybindings, see the [Keybindings Reference](keybindings.md).

!!! question "Troubleshooting"
    Having issues? Check the [Troubleshooting Guide](../troubleshooting.md).

## Vim Philosophy in VimAbl

VimAbl brings Vim's efficient keyboard-driven workflow to Ableton Live:

### Motions
- **`gg`** - Go to beginning (first scene/track)
- **`G`** - Go to end (last scene/track)

### Operators
- **`d`** - Delete operator (requires double-tap: `dd`)
- **`z`** - Fold/undo operator (requires `a`: `za`)

### Context Awareness
Unlike traditional Vim, VimAbl is context-aware based on which Ableton view is active:

- **Session View** - Commands operate on scenes and clips
- **Arrangement View** - Commands operate on tracks and timeline

This ensures the right command is executed for your current workflow.

## Command Categories

### Navigation Commands
Commands for moving around in your project quickly and efficiently.

**Key commands:** `gg`, `G`

**Learn more:** [Navigation Guide](navigation.md)

### Editing Commands
Commands for manipulating and modifying your project.

**Key commands:** `dd`, `za`, `Ctrl + -`

**Learn more:** [Editing Guide](editing.md)

### View Commands
Commands for switching between and controlling different Ableton views.

**Key commands:** `Tab` (built-in), browser toggles

**Learn more:** [Session vs Arrangement](session-vs-arrangement.md)

## Tips for Effective Use

### 1. Start with the Basics
Master `gg` and `G` first - these are your primary navigation tools.

### 2. Learn the Context
Understanding when you're in Session vs Arrangement view is crucial for predictable behavior.

### 3. Use the Web TreeViewer
The TreeViewer helps you visualize your project structure and see real-time changes.

### 4. Check Observer Status
Monitor observer events to understand what's happening under the hood:

```bash
echo "GET_OBSERVER_STATUS" | nc localhost 9001
```

### 5. Customize as Needed
VimAbl is designed to be extended. See the [Development Guide](../development/extending.md) for customization options.

## Next Steps

- **New to VimAbl?** → Start with [Navigation](navigation.md)
- **Vim user?** → Jump to [Keybindings Reference](keybindings.md)
- **Developer?** → Check out [Architecture](../architecture/overview.md)

---

Ready to dive in? Let's start with [Navigation](navigation.md)!

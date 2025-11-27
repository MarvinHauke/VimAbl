# Frontend State Management & Diffing

This document details the frontend state management architecture in VimAbl's Svelte web client, specifically focusing on how diffs are applied and how component state is preserved during real-time updates.

## Overview

The frontend uses a reactive store (`src/web/frontend/src/lib/stores/ast.svelte.ts`) to maintain the Abstract Syntax Tree (AST) of the Ableton Live project. Instead of replacing the entire tree on every update, it incrementally patches the existing AST. This is critical for:

1.  **Performance**: Minimizing DOM updates.
2.  **UX**: Preserving UI state (expanded/collapsed nodes, scroll position).
3.  **Visual Feedback**: Enabling granular animations for specific changes.

## Core Concepts

### Incremental Patching

```typescript
// ❌ OLD APPROACH (destroys state):
astState.root = newAST;  // Replaces entire tree → loses expand/collapse state

// ✅ NEW APPROACH (preserves state):
node.attributes = { ...node.attributes, ...new_value };  // Mutates in place
astState.root = astState.root;  // Triggers reactivity → preserves component instances
```

### Component Preservation

The `TreeNode` component uses a keyed `{#each}` loop to ensure Svelte reuses existing component instances when the data changes.

```svelte
<!-- TreeNode.svelte -->
{#each node.children as child (child.id)}
  <TreeNode node={child} depth={depth + 1} />
{/each}
```

*   **Keying by `id`**: Svelte tracks components by their unique node ID (e.g., `track_1`, `device_0_2`).
*   **State Preservation**: Local component state (like `let expanded = $state(...)`) survives as long as the node ID remains in the tree.

## Change Types

The system supports four types of changes, broadcast by the backend via `DIFF_UPDATE` messages.

### 1. `added` - Node Creation

**Supported Types**: `track`, `device`, `scene`

**Behavior**:
*   Creates a new `ASTNode` with the provided attributes.
*   Inserts it into the parent's `children` array at the correct index.
*   **Visual Indicator**: 🟢 Green flash (5 seconds).

**Example**:
```json
{
  "type": "added",
  "node_type": "track",
  "node_id": "track_5",
  "path": "tracks[5]",
  "new_value": { "name": "New Audio Track", "index": 5, "type": "audio" }
}
```

### 2. `removed` - Node Deletion

**Supported Types**: Generic fallback for any node type.

**Behavior**:
*   Marks the node with `_changeType = 'removed'`.
*   **Visual Indicator**: 🔴 Red flash / fade-out (1 second).
*   Removes the node from the parent's `children` array after the animation completes.

**Example**:
```json
{
  "type": "removed",
  "node_type": "device",
  "node_id": "device_3_2",
  "path": "tracks[3].devices[2]"
}
```

### 3. `modified` - Attribute Updates

**Supported Attributes**: `name`, `color`, `is_enabled`, etc.

**Behavior**:
*   Merges new attributes with existing ones: `{ ...node.attributes, ...new_value }`.
*   **Visual Indicator**: 🟡 Yellow flash (5 seconds).
*   **State Preserved**: The node remains expanded if it was before.

**Example**:
```json
{
  "type": "modified",
  "node_type": "track",
  "node_id": "track_3",
  "path": "tracks[3]",
  "old_value": { "name": "Audio" },
  "new_value": { "name": "Lead Synth" }
}
```

### 4. `state_changed` - Lightweight Updates

**Supported Attributes**: `is_muted`, `is_armed`, `volume`

**Behavior**:
*   Updates the attribute directly.
*   **No Visual Indicator**: These updates happen too frequently (e.g., fader moves) to flash the UI.
*   Designed for high-frequency updates.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  User saves .als file in Ableton                        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  XMLFileWatcher detects change                          │
│  → Triggers ast_server.load_project()                   │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  AST Server computes diff                               │
│  → diff_visitor.diff(old_ast, new_ast)                  │
│  → Returns list of changes:                             │
│     - added: [track_5]                                  │
│     - removed: []                                       │
│     - modified: [track_3]                               │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  WebSocket Server broadcasts DIFF_UPDATE                │
│  → Message type: "DIFF_UPDATE"                          │
│  → Payload: { changes: [...] }                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Svelte UI receives message (+page.svelte)              │
│  → astStore.applyDiff(payload)                          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  applyDiff() patches AST in place                       │
│  → Mutates existing nodes                               │
│  → Adds/removes nodes from children arrays              │
│  → Sets _changeType markers                             │
│  → astState.root = astState.root  ← Triggers reactivity │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Svelte reactivity propagates changes                   │
│  → TreeView re-renders (only changed subtrees)          │
│  → TreeNode components preserved (keyed {#each})        │
│  → expanded state survives ✅                            │
│  → Visual indicators flash (5 sec)                      │
└─────────────────────────────────────────────────────────┘
```

## Implementation Details

### `applyDiff()` Logic

The `applyDiff` function in `src/web/frontend/src/lib/stores/ast.svelte.ts` is the core of the patching logic.

1.  **Traversal**: It recursively finds the target node using `findNodeById` or `findTrackByIndex`.
2.  **Mutation**: It modifies the node in-place.
3.  **Reactivity**: It triggers Svelte's reactivity system by re-assigning the root state.

### Visual Indicators

Visual feedback is handled by temporary markers on the AST nodes:
*   `(node as any)._changeType = 'added' | 'removed' | 'modified'`
*   These markers are automatically cleared after a timeout (1-5 seconds).
*   The `TreeNode` component reads these markers to apply CSS classes (`.node-added`, `.node-modified`).

## Known Limitations

1.  **Track Index Shifts**: When a track is inserted or deleted, the indices of subsequent tracks change. This changes their IDs (e.g., `track_5` → `track_6`), causing Svelte to recreate those components and lose their expanded state.
    *   *Mitigation*: Future backend updates should send index updates as separate events.
2.  **No Undo/Redo**: Diffs are applied immediately. There is no local history stack to revert changes in the UI.
3.  **Race Conditions**: Rapid file saves could theoretically cause diffs to be applied out of order, though the debouncer in `XMLFileWatcher` mitigates this.

## Testing

Testing this logic involves simulating file changes while the UI is running.

1.  Start the WebSocket server with an example project.
2.  Open the Web UI.
3.  Use a script to modify the `.xml` file (simulating an Ableton save).
4.  Verify that:
    *   The UI updates correctly.
    *   The modified node flashes yellow/green.
    *   **Sibling nodes remain expanded.**

See `tools/test_diff_preservation.md` for detailed test procedures.

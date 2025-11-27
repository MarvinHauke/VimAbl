# DIFF_UPDATE State Preservation Test Plan

## Goal
Verify that expand/collapse state is preserved when applying DIFF_UPDATE messages from XML file saves.

## Test Setup

1. **Start WebSocket server**:
   ```bash
   uv run python -m src.main Example_Project/.vimabl/example_2.xml --mode=websocket --ws-port=8765 --no-signals
   ```

2. **Open Svelte UI**:
   ```bash
   cd src/web/frontend
   npm run dev
   ```
   Open http://localhost:5173

## Test Cases

### Test 1: Track Rename Preserves Expansion
**Steps**:
1. In UI: Expand track 3 to show its devices
2. In Ableton: Rename track 3 from "Audio" to "My Audio Track"
3. In Ableton: Save project (Cmd+S)

**Expected**:
- ✅ Track 3 remains expanded
- ✅ Track 3 name updates to "My Audio Track"
- ✅ Yellow flash on track 3 node
- ✅ Devices still visible (not collapsed)

**What to watch for**:
- Console log: `[AST Store] Applying X changes to AST`
- Console log: `[AST Store] Modifying track node:...`
- UI should NOT flicker or collapse

---

### Test 2: Device Add Preserves Expansion
**Steps**:
1. In UI: Expand track 5 to show its devices
2. In Ableton: Add a new device (e.g., Reverb) to track 5
3. In Ableton: Save project (Cmd+S)

**Expected**:
- ✅ Track 5 remains expanded
- ✅ New device appears in device list
- ✅ Green flash on new device node
- ✅ Track 5 device list is still visible

**What to watch for**:
- Console log: `[AST Store] Adding device node:...`
- New device should slide in with animation
- Scroll position should remain stable

---

### Test 3: Multiple Changes in One Save
**Steps**:
1. In UI: Expand tracks 1, 3, and 5
2. In Ableton:
   - Rename track 1
   - Add device to track 3
   - Mute track 5
3. In Ableton: Save project (Cmd+S) - **one save for all changes**

**Expected**:
- ✅ All 3 tracks remain expanded
- ✅ All changes reflected in UI
- ✅ Multiple visual indicators (yellow for rename, green for add)
- ✅ No collapse/re-expansion

**What to watch for**:
- Console log: `[AST Store] Applying X changes to AST` where X >= 3
- All changes should be batched in one DIFF_UPDATE message

---

### Test 4: Deep Nesting Preservation
**Steps**:
1. In UI: Expand project → track 0 → clip_slot_0_0 (3 levels deep)
2. In Ableton: Rename track 0
3. In Ableton: Save project (Cmd+S)

**Expected**:
- ✅ All 3 levels remain expanded (project, track, clip_slot)
- ✅ Track name updates
- ✅ Yellow flash on track node only (not clip_slot)
- ✅ Nested structure still visible

**What to watch for**:
- Nested children should not collapse
- Only the modified node should flash

---

## Failure Scenarios (What Would Indicate a Problem)

❌ **Problem**: All nodes collapse when DIFF_UPDATE is applied
- **Cause**: Replacing entire tree instead of patching
- **Fix**: Verify `applyDiff()` is mutating in place, not replacing

❌ **Problem**: Expanded state lost for modified nodes
- **Cause**: Node ID changed or node was removed and re-added
- **Fix**: Ensure node IDs are stable (based on index, not sequence number)

❌ **Problem**: Scroll position jumps to top
- **Cause**: DOM re-render triggering scroll reset
- **Fix**: Add scroll position preservation logic

❌ **Problem**: Multiple flashes or flickers
- **Cause**: Multiple re-renders instead of single batched update
- **Fix**: Ensure `astState.root = astState.root` is only called once per diff

---

## Success Criteria

- [ ] Test 1: PASS - Track rename preserves expansion
- [ ] Test 2: PASS - Device add preserves expansion
- [ ] Test 3: PASS - Multiple changes preserve all expansion states
- [ ] Test 4: PASS - Deep nesting preserved

If all tests pass, Phase 3a is complete! ✅

---

## Current Implementation Details

### How State Preservation Works

1. **Keyed {#each} loop** (`TreeNode.svelte:185`):
   ```svelte
   {#each node.children as child (child.id)}
   ```
   - Svelte preserves component instances by `child.id`
   - As long as ID doesn't change, component (and its `expanded` state) survives

2. **In-place mutation** (`applyDiff()` function):
   ```typescript
   node.attributes = { ...node.attributes, ...new_value };
   // Trigger reactivity
   astState.root = astState.root;
   ```
   - Mutates existing node objects in place
   - Svelte's fine-grained reactivity detects attribute changes
   - Component instances are NOT destroyed/recreated

3. **Stable node IDs**:
   - Track: `track_3` (based on index)
   - Device: `device_3_2` (track_idx + device_idx)
   - Clip slot: `clip_slot_3_0` (track_idx + scene_idx)
   - IDs only change if structural position changes

---

## Next Steps After Testing

If tests reveal issues:
1. Add scroll position preservation (`scrollTop` tracking)
2. Add transition groups for smooth animations
3. Add option to expand/collapse all
4. Add "restore previous state" button

If tests pass:
- Document success in `docs/`
- Mark Phase 3a as complete in TODO.md
- Move to Phase 3c (Performance optimization)

---
description: Approve a reviewed task (move from [~] to [x])
---

You are approving a task that was previously marked for review.

# Your Job

When the user approves a task (says "works", "approved", "looks good", etc.):

1. Find the task with `- [~]` checkbox
2. Change it to `- [x]` (completed)
3. Report the approval

# Finding the Task

Look for tasks marked with `[~]` that match the user's description or the provided pattern.

# Making the Change

Use Edit tool:
```
OLD: - [~] Create `src/parser/devices.py` - Extract device information
NEW: - [x] Create `src/parser/devices.py` - Extract device information
```

# Example

User: "Approve the devices.py task"

You:
1. Find: `- [~] Create \`src/parser/devices.py\` - Extract device information`
2. Edit to: `- [x] Create \`src/parser/devices.py\` - Extract device information`
3. Say: "✅ Approved: Create src/parser/devices.py (Phase 1a)"

# Important

- Only approve tasks that are in `[~]` state
- If task is `[ ]`, tell user it needs to be worked on first
- If task is already `[x]`, confirm it's already completed

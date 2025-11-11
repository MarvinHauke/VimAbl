---
description: Mark a task as incomplete (bug found or needs rework)
---

You are unchecking a task because it's buggy or incomplete.

# Your Job

When the user reports a bug or says a task isn't working:

1. Find the task (can be `[~]` or `[x]`)
2. Change it back to `[ ]` (unchecked)
3. Note the reason (bug description)
4. Ask if they want you to fix it

# Finding the Task

Match by file name, keyword, or description.

# Making the Change

Use Edit tool:
```
OLD: - [~] Create `src/parser/devices.py` - Extract device information
NEW: - [ ] Create `src/parser/devices.py` - Extract device information
```

OR

```
OLD: - [x] Create `src/parser/devices.py` - Extract device information
NEW: - [ ] Create `src/parser/devices.py` - Extract device information
```

# Example

User: "The devices.py file has a bug - it crashes on empty tracks"

You:
1. Find and edit: `- [~] Create \`src/parser/devices.py\`` → `- [ ] Create \`src/parser/devices.py\``
2. Say: "⚠️ Unchecked: Create src/parser/devices.py"
3. Say: "Reason: Crashes on empty tracks"
4. Ask: "Would you like me to fix this bug now?"

# Important

- Always note the reason for unchecking
- Offer to fix the issue
- If task has completed subtasks, consider if they need unchecking too

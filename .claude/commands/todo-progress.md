---
description: Show TODO.md progress statistics
---

You are reporting progress on the TODO.md file.

# Your Job

Read TODO.md and calculate statistics:

1. Count tasks by state:
   - `[ ]` Unchecked (pending)
   - `[~]` In Review (waiting approval)
   - `[x]` Completed (approved)

2. Calculate percentages

3. Break down by phase (Phase 1a, Phase 1b, etc.)

# Output Format

```
📊 TODO PROGRESS REPORT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall Status:
  Total Tasks:    X
  Completed:      X (XX%)
  In Review:      X (XX%)
  Pending:        X (XX%)

Phase Breakdown:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 1a: Devices & Clips
  ████████░░░░░░░░░░░░  8/20 (40%)
  In Review: 3, Pending: 9

Phase 1b: Scenes & Mixer
  ░░░░░░░░░░░░░░░░░░░░  0/15 (0%)
  In Review: 0, Pending: 15

...

Current Focus:
  Next task: Create `src/parser/devices.py`
  Phase: Phase 1a: Devices & Clips
```

# Tips

- Use Read tool to get TODO.md content
- Use regex to match `- \[([ ~x])\]` patterns
- Group tasks by their parent headers
- Show a progress bar for each phase (use █ for complete, ░ for incomplete)
- Highlight tasks in review state `[~]`

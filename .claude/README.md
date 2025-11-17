# Claude Code Configuration

This directory contains Claude Code agents, commands, and configuration for VimAbl.

## Directory Structure

```
.claude/
├── agents/
│   └── docs-agent.md              # Documentation agent specification
├── commands/
│   ├── doc-feature.md             # /doc-feature slash command
│   ├── todo-approve.md            # /todo-approve (existing)
│   ├── todo-progress.md           # /todo-progress (existing)
│   ├── todo-review.md             # /todo-review (existing)
│   └── todo-uncheck.md            # /todo-uncheck (existing)
├── config/
│   └── feature-tracking.json      # Feature documentation tracking
├── settings.local.json            # Local settings
└── README.md                      # This file
```

## Documentation Agent

The documentation agent helps maintain comprehensive documentation for VimAbl features.

### Usage

**Slash Command:**
```
/doc-feature Session View Cursor Tracking
```

**What it does:**
1. Searches codebase for the feature
2. Analyzes implementation (Python/Lua/Web UI)
3. Generates/updates documentation
4. Updates changelog and feature tracking
5. Reports summary

### Agent Workflow

The agent follows this process:

1. **Analyze** - Search for code related to the feature
2. **Check** - Scan existing docs for gaps
3. **Generate** - Create/update documentation files
4. **Validate** - Ensure quality standards
5. **Report** - Provide summary of changes

### Feature Tracking

The agent maintains `.claude/config/feature-tracking.json` to track:

- Feature name and description
- Implementation date
- Documentation date
- Components affected (Python/Lua/Web/Server)
- Documentation files
- Status (documented/partially_documented/undocumented)

### Auto-Generation Scripts

Located in `tools/`:

**Extract Commands:**
```bash
python tools/extract_commands.py > docs/_auto-generated/commands-table.md
```

**Extract Keybindings:**
```bash
python tools/extract_keybindings.py > docs/_auto-generated/keybindings-table.md
```

**Extract Observers:**
```bash
python tools/extract_observers.py > docs/_auto-generated/observers-table.md
```

## Documentation Standards

### Writing Style
- Clear, concise, active voice
- Address reader as "you"
- Start with "what" and "why" before "how"

### Code Examples
- Always include working examples
- Add comments for clarity
- Include expected output

### Structure
- Use hierarchical headings (H1 → H2 → H3)
- Include tables for reference info
- Use admonitions (tip, warning, note)
- Add diagrams for complex concepts

## Feature Documentation Checklist

When documenting a feature:

- [ ] User guide with examples (if user-facing)
- [ ] API reference with request/response (if API)
- [ ] Architecture docs (if architecture change)
- [ ] Code examples that work
- [ ] Troubleshooting section
- [ ] Changelog entry
- [ ] Feature tracking updated
- [ ] Cross-references added

## Quick Reference

**Check feature tracking status:**
```bash
cat .claude/config/feature-tracking.json | jq '.documentation_coverage'
```

**List undocumented features:**
```bash
cat .claude/config/feature-tracking.json | jq '.features[] | select(.status != "documented")'
```

**Generate all auto-docs:**
```bash
python tools/extract_commands.py > docs/_auto-generated/commands-table.md
python tools/extract_keybindings.py > docs/_auto-generated/keybindings-table.md
python tools/extract_observers.py > docs/_auto-generated/observers-table.md
```

## Contributing

When adding a new feature:

1. Implement the feature
2. Test thoroughly
3. Run `/doc-feature <feature-name>`
4. Review generated documentation
5. Add screenshots if applicable
6. Test `mkdocs serve`
7. Commit changes

## Support

- Documentation: `docs/`
- Agents: `.claude/agents/`
- Commands: `.claude/commands/`
- Tracking: `.claude/config/feature-tracking.json`

---

**Last Updated:** 2025-11-17
**Phase:** 2 - Agent Development Complete

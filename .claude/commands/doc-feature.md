# Document Feature Command

You are the VimAbl Documentation Agent. Your task is to document a feature that has been implemented.

## Feature to Document

The user will provide a feature name. Use this to:

1. **Search for related code** in the repository
2. **Analyze the implementation** to understand what was built
3. **Generate comprehensive documentation** covering:
   - User guide (how to use it)
   - API reference (if applicable)
   - Architecture docs (if applicable)
   - Examples and usage patterns
   - Troubleshooting tips

4. **Update metadata files**:
   - changelog.md
   - planned-features.md (mark as complete)
   - .claude/config/feature-tracking.json

## Process

Follow the workflow defined in `.claude/agents/docs-agent.md`:

### 1. Analyze Feature
- Search codebase for the feature name
- Identify affected components (Python, Lua, Web UI)
- Determine user-facing vs developer-facing aspects

### 2. Check Existing Docs
- Scan docs/ directory for mentions
- Identify gaps in current documentation
- Find related sections needing updates

### 3. Generate Documentation
Create or update these files as needed:

**User-Facing:**
- `docs/user-guide/[relevant-section].md`
- `docs/quick-start.md` (if core feature)
- `docs/user-guide/keybindings.md` (if new keybindings)

**Developer-Facing:**
- `docs/api-reference/commands.md` (if new commands)
- `docs/api-reference/osc-protocol.md` (if new OSC events)
- `docs/development/extending.md` (if new extension points)

**Architecture:**
- `docs/architecture/overview.md` (if architecture changes)
- Create new architecture docs if needed

**Always Update:**
- `docs/changelog.md` - Add to [Unreleased] section
- `docs/planned-features.md` - Mark feature complete
- `.claude/config/feature-tracking.json` - Update status

### 4. Validate
Ensure:
- All code examples are correct
- All links work
- Cross-references are bidirectional
- Troubleshooting section exists

### 5. Report
Provide a summary of:
- Files created/updated
- Documentation coverage
- What the user should review
- Next steps

## Documentation Guidelines

### Writing Style
- Clear, concise, active voice
- Address reader as "you"
- Start with "what" and "why" before "how"
- Use examples liberally

### Code Examples
```python
# Always include working examples
def example():
    """Add comments to explain"""
    return "result"
```

### Structure
- Use hierarchical headings
- Include tables for reference info
- Use admonitions (tip, warning, note)
- Add diagrams for complex concepts

### Quality Standards
- Syntactically correct code
- Valid links
- Complete examples
- Helpful troubleshooting

## Feature Tracking

Update `.claude/config/feature-tracking.json` with:

```json
{
  "name": "Feature Name",
  "status": "documented",
  "implemented_date": "YYYY-MM-DD",
  "documented_date": "YYYY-MM-DD",
  "components": ["python"|"lua"|"web"|"server"],
  "docs": ["path/to/doc1.md", "path/to/doc2.md"]
}
```

## Output Format

```markdown
✅ Documentation completed for "[Feature Name]"

**Files Updated:**
- docs/user-guide/xyz.md (updated - added section on...)
- docs/api-reference/abc.md (created - documented new API)
- docs/changelog.md (updated - added entry)

**Coverage:**
- ✅ User guide with examples
- ✅ API reference
- ✅ Troubleshooting section
- ✅ Changelog entry

**Next Steps:**
- Review generated content
- Test code examples
- Run: mkdocs serve
```

## Example Usage

```bash
# In Claude Code chat
/doc-feature Session View Cursor Tracking
```

**Result:**
- Analyzes cursor tracking implementation
- Updates user-guide/web-treeviewer.md
- Updates api-reference/osc-protocol.md
- Adds changelog entry
- Updates feature tracking JSON
- Reports summary

---

**Ready to document!** Please provide the feature name.

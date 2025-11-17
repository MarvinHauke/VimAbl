# GitHub Workflows

This directory contains GitHub Actions workflows for VimAbl.

## Workflows

### Documentation (`docs.yaml`)

Automatically builds and deploys MkDocs documentation.

**Triggers:**
- Push to `main` or `feature/docs` branches
- Pull requests to `main`
- Manual workflow dispatch

**Jobs:**
1. **build** - Build documentation with auto-generation
2. **deploy** - Deploy to GitHub Pages (main branch only)
3. **pr-comment** - Comment on PR with preview info
4. **validate** - Validate links and check for warnings

**Auto-Generation:**
- Commands table from `src/remote_script/commands.py`
- Keybindings table from `src/hammerspoon/keys/*.lua`
- Observers table from `src/remote_script/observers.py`

**Output:**
- Deployed to: `https://<username>.github.io/VimAbl/`
- PR preview artifact available for download

## Setup

See [SETUP_GITHUB_PAGES.md](./SETUP_GITHUB_PAGES.md) for detailed setup instructions.

**Quick setup:**
1. Enable GitHub Pages in repository settings
2. Set source to "GitHub Actions"
3. Push this workflow to `main` branch
4. Documentation will auto-deploy

## Workflow Features

### ✅ Automatic Documentation Generation

The workflow extracts documentation from source code:

```bash
# Generated files (not committed)
docs/_auto-generated/
├── commands-table.md       # All TCP commands
├── keybindings-table.md    # All keybindings
└── observers-table.md      # All OSC events
```

### ✅ Link Validation

Checks for:
- Broken internal links
- Missing files
- Build warnings

### ✅ PR Preview

On pull requests:
- Builds documentation
- Posts comment with status
- Uploads preview artifact

### ✅ Deployment Protection

- Only deploys on push to `main`
- Requires successful build
- Single concurrent deployment

## Local Testing

Test the workflow locally before pushing:

```bash
# Install dependencies
uv pip install mkdocs-material mkdocs-git-revision-date-localized-plugin

# Generate auto-docs
mkdir -p docs/_auto-generated
python tools/extract_commands.py > docs/_auto-generated/commands-table.md
python tools/extract_keybindings.py > docs/_auto-generated/keybindings-table.md
python tools/extract_observers.py > docs/_auto-generated/observers-table.md

# Build documentation
mkdocs build --strict

# Serve locally
mkdocs serve
```

## Customization

### Add New Auto-Generation

1. Create extraction script in `tools/`
2. Add step to workflow:
```yaml
- name: Generate new docs
  run: python tools/extract_new.py > docs/_auto-generated/new.md
```

### Change Deployment Branch

Edit workflow:
```yaml
on:
  push:
    branches: [production]  # Change from 'main'
```

### Add Deployment Approval

1. Settings → Environments → New environment
2. Name: `github-pages`
3. Add required reviewers
4. Workflow will wait for approval before deploy

## Monitoring

### View Workflow Runs

**GitHub UI:**
1. Go to **Actions** tab
2. Select **Documentation** workflow
3. View run history and logs

### Build Badge

Add to README.md:
```markdown
[![Docs](https://github.com/<user>/VimAbl/actions/workflows/docs.yaml/badge.svg)](https://github.com/<user>/VimAbl/actions/workflows/docs.yaml)
```

### Notifications

**Enable email:**
1. Profile → Settings → Notifications
2. Actions → Send notifications for failed workflows

## Troubleshooting

### Build Fails

**Check logs:**
```bash
# GitHub Actions tab → Failed run → build job → Expand failed step
```

**Common issues:**
- Missing dependencies → Update `Install dependencies` step
- Broken links → Fix links in markdown files
- Invalid YAML → Check `mkdocs.yml` syntax

### Deployment Fails

**Check permissions:**
- Settings → Actions → General
- Workflow permissions: "Read and write"
- Allow PR creation: Enabled

**Check Pages settings:**
- Settings → Pages
- Source: "GitHub Actions" (not "Deploy from a branch")

### Auto-Generation Fails

**Verify scripts exist:**
```bash
ls -la tools/extract_*.py
```

**Test locally:**
```bash
python tools/extract_commands.py
# Should output markdown table
```

## Security

### Workflow Permissions

The workflow has minimal permissions:
- `contents: read` - Read repository files
- `pages: write` - Deploy to GitHub Pages
- `id-token: write` - OIDC token for deployment
- `pull-requests: write` - Comment on PRs

### Secrets

No secrets required for basic operation.

If needed:
1. Settings → Secrets and variables → Actions
2. New repository secret
3. Use: `${{ secrets.SECRET_NAME }}`

## Performance

**Typical build time:**
- Build job: ~2 minutes
- Deploy job: ~30 seconds
- Total: ~2.5 minutes

**Optimization tips:**
- Cache Python dependencies (already configured)
- Use `--strict` mode to catch errors early
- Minimize file changes to reduce build time

## Future Enhancements

Planned improvements:
- [ ] Deploy preview sites for PRs (Netlify/Vercel)
- [ ] Link checking with external validator
- [ ] Documentation coverage metrics
- [ ] Auto-update changelog from commits
- [ ] Accessibility testing

## Support

- **GitHub Actions**: https://docs.github.com/en/actions
- **MkDocs**: https://www.mkdocs.org/
- **Material Theme**: https://squidfunk.github.io/mkdocs-material/

---

**Last Updated:** 2025-11-17

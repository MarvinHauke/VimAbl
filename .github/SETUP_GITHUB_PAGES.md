# GitHub Pages Setup Guide

This guide explains how to set up GitHub Pages for VimAbl documentation.

## Prerequisites

- Repository is on GitHub
- You have admin access to the repository
- The `docs.yaml` workflow is committed

## Setup Steps

### 1. Enable GitHub Pages

1. Go to your repository on GitHub
2. Click **Settings** → **Pages** (left sidebar)
3. Under **Source**, select:
   - Source: **GitHub Actions**
   - (Do NOT select "Deploy from a branch")

### 2. Configure Repository Permissions

1. Go to **Settings** → **Actions** → **General**
2. Scroll to **Workflow permissions**
3. Select: **Read and write permissions**
4. Check: **Allow GitHub Actions to create and approve pull requests**
5. Click **Save**

### 3. Trigger First Build

**Option A: Push to main**
```bash
git add .github/workflows/docs.yaml mkdocs.yml docs/
git commit -m "feat: add documentation CI/CD"
git push origin main
```

**Option B: Manual trigger**
1. Go to **Actions** tab
2. Select **Documentation** workflow
3. Click **Run workflow** → **Run workflow**

### 4. Monitor Build

1. Go to **Actions** tab
2. Click on the running workflow
3. Watch the **build** and **deploy** jobs
4. Should complete in 2-3 minutes

### 5. Access Documentation

Once deployed, your documentation will be available at:

```
https://<username>.github.io/<repository>/
```

For example:
```
https://yourusername.github.io/VimAbl/
```

## Workflow Behavior

### On Push to Main
- ✅ Builds documentation
- ✅ Generates auto-docs from source code
- ✅ Deploys to GitHub Pages
- ✅ Validates links

### On Pull Request
- ✅ Builds documentation
- ✅ Generates auto-docs
- ✅ Validates links
- ✅ Posts comment with status
- ❌ Does NOT deploy (preview only)

### On Push to `feature/docs`
- ✅ Builds documentation
- ✅ Generates auto-docs
- ✅ Deploys to GitHub Pages (for testing)
- ✅ Validates links

## Auto-Generated Documentation

The workflow automatically generates documentation from source code:

| File | Generated From | Description |
|------|----------------|-------------|
| `docs/_auto-generated/commands-table.md` | `src/remote_script/commands.py` | TCP commands reference |
| `docs/_auto-generated/keybindings-table.md` | `src/hammerspoon/keys/*.lua` | Keybindings reference |
| `docs/_auto-generated/observers-table.md` | `src/remote_script/observers.py` | OSC observers reference |

These files are:
- ✅ Generated on every build
- ✅ Not committed to git (in `.gitignore`)
- ✅ Always up-to-date with source code

## Troubleshooting

### Build Fails

**Check the workflow logs:**
1. Go to **Actions** tab
2. Click on failed workflow run
3. Click on **build** job
4. Expand failed step to see error

**Common issues:**
- Missing dependencies → Check `Install dependencies` step
- Broken links → Check `Build documentation` step warnings
- Invalid mkdocs.yml → Check YAML syntax

### Deployment Fails

**Check permissions:**
1. **Settings** → **Actions** → **General**
2. Ensure **Read and write permissions** is selected
3. Ensure **Allow GitHub Actions to create and approve pull requests** is checked

**Check GitHub Pages settings:**
1. **Settings** → **Pages**
2. Source should be **GitHub Actions** (not "Deploy from a branch")

### Documentation Not Updating

**Clear browser cache:**
- Hard refresh: `Ctrl+Shift+R` (Windows/Linux) or `Cmd+Shift+R` (Mac)

**Check deployment status:**
1. **Actions** tab → Latest workflow run
2. Verify **deploy** job succeeded
3. Check deployment URL in job output

### Auto-Generated Files Missing

**Verify extraction scripts exist:**
```bash
ls -la tools/extract_*.py
```

**Check workflow logs:**
- Look for "Generate commands documentation" step
- Check for errors in extraction scripts

## Custom Domain (Optional)

### 1. Add Custom Domain

1. **Settings** → **Pages**
2. Under **Custom domain**, enter your domain (e.g., `docs.vimabl.dev`)
3. Click **Save**

### 2. Configure DNS

Add a CNAME record pointing to:
```
<username>.github.io
```

### 3. Enable HTTPS

1. Wait for DNS to propagate (can take 24 hours)
2. **Settings** → **Pages**
3. Check **Enforce HTTPS**

## Monitoring

### Build Notifications

**Enable email notifications:**
1. Click your profile → **Settings**
2. **Notifications** → **Actions**
3. Check **Send notifications for failed workflows only**

### Build Badge

Add to README.md:
```markdown
[![Documentation](https://github.com/<username>/<repo>/actions/workflows/docs.yaml/badge.svg)](https://github.com/<username>/<repo>/actions/workflows/docs.yaml)
```

## Maintenance

### Update Dependencies

Update Python packages in workflow:
```yaml
- name: Install dependencies
  run: |
    uv pip install --system mkdocs-material==<version>
    uv pip install --system mkdocs-git-revision-date-localized-plugin==<version>
```

### Add New Auto-Generation Scripts

1. Create script in `tools/`
2. Add generation step to workflow:
```yaml
- name: Generate new docs
  run: |
    python tools/extract_new.py > docs/_auto-generated/new-table.md
```

## Security

### Secrets

If you need secrets (e.g., for API keys):

1. **Settings** → **Secrets and variables** → **Actions**
2. Click **New repository secret**
3. Add secret name and value
4. Use in workflow:
```yaml
- name: Step with secret
  env:
    API_KEY: ${{ secrets.API_KEY }}
  run: ./script.sh
```

## Advanced Configuration

### Deploy to Multiple Environments

Add environment-specific configs:

```yaml
environment:
  name: production
  url: https://docs.vimabl.dev
```

### Add Deployment Approval

1. **Settings** → **Environments**
2. Click **New environment**
3. Name: `production`
4. Check **Required reviewers**
5. Add reviewers

## Support

- **GitHub Pages Docs**: https://docs.github.com/en/pages
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **MkDocs Material**: https://squidfunk.github.io/mkdocs-material/

---

**Last Updated:** 2025-11-17

---
description: Push local changes to GitHub repository. This workflow stages all modified files, creates a commit with automatic timestamp-based message, and pushes to the 'main' branch of the configured remote.
---

# GitHub Push Update Workflow

This workflow automatically pushes all your changes to GitHub with timestamp-based commit messages.

## 1. Stage all changes
// turbo
```bash
git add .
```

## 2. Create commit with timestamp
// turbo
```bash
git commit -m "Update $(date +%Y-%m-%d_%H:%M:%S)"
```

## 3. Push to GitHub
// turbo
```bash
git push origin main
```

## Notes
- All files will be automatically staged, committed, and pushed
- Commit messages are automatically generated with current timestamp
- No user input required - just run the workflow
- For more complex scenarios, use Git commands directly

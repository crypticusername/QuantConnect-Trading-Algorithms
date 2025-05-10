---
description: Update all QuantConnect documentation repositories
---

# WARNING: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER PERMISSION
# Update QuantConnect Documentation Repositories

This workflow updates all QuantConnect documentation repositories that have been set up as Git submodules in the `.windsurf/QC-Doc-Repos` directory.

## Steps

1. Navigate to the project root directory
```bash
cd /Users/overton/CascadeProjects/QuantConnect Trading Algorithms
```

2. Update all submodules to their latest versions
```bash
git submodule update --remote --merge
```

3. Commit the updated submodule references
```bash
git add .
git commit -m "Update QuantConnect documentation repositories"
```

## Notes

- This workflow only pulls updates from the original QuantConnect repositories. It does not push any of your code to those repositories.
- The submodules are set up to track the main branch of each repository.
- This is a safe operation that will not expose your code to others.
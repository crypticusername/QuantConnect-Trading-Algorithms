---
description: Create a new QuantConnect algorithm project with proper Lean CLI structure for cloud synchronization, complete with algorithm code and strategy documentation.
---

# WARNING: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER PERMISSION
# New Trading Algo Project

This workflow creates a new algorithm project using the official Lean CLI structure, enhanced with our custom templates and documentation. Projects are immediately ready for cloud synchronization and backtesting.

## 1. Enter project name
- id: project_name
- type: input
- prompt: Enter a name for your new trading algorithm project:

## 2. Create project with Lean CLI
```bash
# Creates a properly structured project recognized by Lean CLI
lean create-project "{{ project_name }}" --language python
```
```

## Next Steps
After the project is created, you can:
1. Define your strategy in the `{{ project_name }}-strategy.md` file or other file if provided by user. 
2. Implement your algorithm logic in `main.py`
   ```
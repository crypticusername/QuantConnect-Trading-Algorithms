---
description: Push local algorithm changes to QuantConnect Cloud. This workflow synchronizes your local algorithm files with your QuantConnect Cloud account.
---

# QuantConnect Cloud Push

This workflow synchronizes your local algorithm changes with QuantConnect Cloud, making them available for backtesting and live trading.

## 1. Enter project name
- id: project_name
- type: input
- prompt: Enter the name of the algorithm project to push to QuantConnect Cloud:

## 2. Push to QuantConnect Cloud
// turbo
```bash
# Push local changes to QuantConnect Cloud
lean cloud push --project "{{ project_name }}"
```

## Notes
- This workflow only pushes your local changes to the cloud
- It does not run a backtest (use the QC-Cloud-Backtest workflow for that)
- Your algorithm must already exist locally (created via the New Trading Algo Project workflow)
- Changes will be immediately available in your QuantConnect account
- Any cloud files not in your local project will be deleted
- Windsurf Casacade should attempt to detect the algorithm name based on chat context and the main.py file recently edited
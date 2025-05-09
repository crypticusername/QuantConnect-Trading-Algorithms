---
description: Push local algorithm changes to QuantConnect Cloud and immediately run a backtest. This workflow synchronizes your code and executes a backtest in one step.
---

# QuantConnect Cloud Push & Backtest

This workflow synchronizes your local algorithm changes with QuantConnect Cloud and immediately runs a backtest with the updated code.

## 1. Enter project name
- id: project_name
- type: input
- prompt: Enter the name of the algorithm project to push and backtest:

## 2. Push to QuantConnect Cloud and run backtest
// turbo
```bash
# Push local changes to QuantConnect Cloud
lean cloud push --project "{{ project_name }}" && \
# Run backtest with the updated code
lean cloud backtest "{{ project_name }}" --open
```

## Notes
- This workflow combines pushing local changes and running a backtest in one step
- Your local algorithm changes will be synchronized to QuantConnect Cloud first
- The backtest will run using the newly pushed code
- The `--open` flag automatically opens the backtest results in your browser
- Backtest results will be available in your QuantConnect account
- This is ideal for iterative development and testing cycles
- Windsurf Casacade should attempt to detect the algorithm name based on chat context and the main.py file recently edited
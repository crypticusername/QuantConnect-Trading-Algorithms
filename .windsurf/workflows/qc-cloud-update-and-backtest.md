---
description: Push local algorithm changes to QuantConnect Cloud and immediately run a backtest. This workflow synchronizes your code and executes a backtest in one step.
---

# WARNING: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER PERMISSION
# QuantConnect Cloud Push & Backtest

This workflow synchronizes your local algorithm changes with QuantConnect Cloud and immediately runs a backtest with the updated code.

## 1. Enter project name
- id: project_name
- type: input
- prompt: Enter the name of the algorithm project to push and backtest:

## 2. Push to QuantConnect Cloud and run backtest
// turbo
```bash
# Push local changes and run backtest in a single command
lean cloud backtest "{{ project_name }}" --open --push
```

## Notes
- This workflow combines pushing local changes and running a backtest in one step using the `--push` flag
- The `--push` flag ensures your local algorithm changes are synchronized to QuantConnect Cloud before running the backtest
- The `--open` flag automatically opens the backtest results in your browser
- Backtest results will be available in your QuantConnect account
- This is ideal for iterative development and testing cycles
- This approach is more efficient than running separate push and backtest commands
- Windsurf Casacade should attempt to detect the algorithm name based on chat context and the main.py file recently edited
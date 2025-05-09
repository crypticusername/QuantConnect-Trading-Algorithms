---
description: Run a backtest of your algorithm on QuantConnect Cloud. This workflow executes a backtest using your algorithm's current code.
---

# QuantConnect Cloud Backtest

This workflow runs a backtest of your algorithm on QuantConnect Cloud using the current code version.

## 1. Enter project name
- id: project_name
- type: input
- prompt: Enter the name of the algorithm project to backtest:

## 2. Run backtest on QuantConnect Cloud
// turbo
```bash
# Run backtest and extract URL in one step
lean cloud backtest "{{ project_name }}" | tee /tmp/qc_backtest_output.txt && \
BACKTEST_URL=$(grep -o 'https://www.quantconnect.com/project/[^[:space:]]*' /tmp/qc_backtest_output.txt | tail -1) && \
open -a Safari "$BACKTEST_URL"
```

## Notes
- This workflow runs a backtest using the algorithm version currently on QuantConnect Cloud
- It does not push local changes first (use QC-Cloud-Push workflow before this one if needed)
- The `--open` flag automatically opens the backtest results in your browser
- Backtest results will be available in your QuantConnect account
- For custom parameters, use the Lean CLI directly with additional flags
- Windsurf Casacade should attempt to detect the algorithm name based on chat context and the main.py file recently edited

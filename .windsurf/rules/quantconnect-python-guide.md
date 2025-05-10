---
trigger: always_on
---

# WARNING: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER PERMISSION

# QuantConnect Python Workspace Rules

> **Scope:** This guide defines conventions for creating Python option-trading algorithms for QuantConnect Cloud via Lean CLI (cloud mode).

---
## 1  Authoritative References
| Topic                          | Source                                                                                  |
|--------------------------------|-----------------------------------------------------------------------------------------|
| Local Documentation            | `.windsurf/QC-Doc-Repos/Documentation`                                                  |
| Local Lean CLI                 | `.windsurf/QC-Doc-Repos/lean-cli`                                                       |
| Local Lean Engine              | `.windsurf/QC-Doc-Repos/Lean`                                                           |
| Local IB Brokerage             | `.windsurf/QC-Doc-Repos/Lean.Brokerages.InteractiveBrokers`                             |
| Code Examples                  | `.windsurf/qc-code-examples.md`                                                         |
| QuantConnect Docs (v2)         | https://www.quantconnect.com/docs/v2                                                     |
| Python PEP 8 Style Guide       | https://peps.python.org/pep-0008/                                                       |

---
## 2  Project & Folder Conventions
1. Use the `/new-trading-algo-project` workflow to create new algorithm projects with proper structure.
2. Each algorithm lives in its own folder at workspace root.
3. Main algorithm code is in `main.py` (created by the workflow).
4. Strategy documentation is in `[project-name]-strategy.md` (created by the workflow).
5. Use `/qc-cloud-push-update` to sync changes to QuantConnect Cloud.
6. Use `/qc-cloud-run-backtest` to run backtests on the cloud.
7. Use `/qc-cloud-update-and-backtest` to push changes and immediately run a backtest.

---
## 3  Algorithm Syntax Requirements
- Always use `from AlgorithmImports import *`
- **CRITICAL:** Python algorithms for QuantConnect MUST use snake_case for method names (`initialize` not `Initialize`, `set_start_date` not `SetStartDate`). Using camelCase will cause compilation errors.
- Use UPPERCASE for TimeZones and Resolution values (`TimeZones.NEW_YORK`, `Resolution.MINUTE`).
- Use `self.schedule.on` with `self.date_rules` and `self.time_rules`.
- Include docstrings for all methods.
- Follow PEP 8 for code style (4-space indentation, 79-char line limit).
- See `.windsurf/qc-code-examples.md` for complete code examples.

---
## 4  Data Subscriptions & Universes
- Use `self.add_equity()`, `self.add_option()`, `self.add_index_option()`, etc. to subscribe to data.
- For options, always use `set_filter()` to narrow down the universe.
- Include weeklys with `include_weeklys()` when needed.
- Limit strikes and expirations to reasonable ranges.
- Store symbols as instance variables for later reference.
- See `.windsurf/qc-code-examples.md` for detailed examples.

---
## 5  Option Strategy Construction
- Use the `OptionStrategies` class for predefined strategies.
- Always check if option chain exists before accessing it.
- Use modern Python-friendly syntax for accessing option chains.
- Sort strikes and expiries to ensure consistent selection.
- See `.windsurf/qc-code-examples.md` for implementation examples.

---
## 6  Risk & Position Sizing
1. Define max drawdown tolerance (e.g., 5%).
2. Implement position sizing based on volatility.
3. Use `self.portfolio.margin_remaining` for buying power awareness.
4. Set stop-loss and take-profit levels for each trade.
5. Monitor and adjust leverage ratios.

---
## 7  Documentation-First Principle
1. **ALWAYS check local documentation repositories** in this order before writing code:
   - `.windsurf/QC-Doc-Repos/Documentation` (primary reference)
   - `.windsurf/QC-Doc-Repos/lean-cli` (deployment interface)
   - `.windsurf/QC-Doc-Repos/Lean` (engine implementation)
   - `.windsurf/QC-Doc-Repos/Lean.Brokerages.InteractiveBrokers` (IB-specific)
2. **Use the `/trading-strategy-to-implementation-plan` workflow** to research documentation for new strategies.
3. **Never guess syntax** - always verify in local documentation.
4. **Validate all implementations** against documentation examples.
5. **Document version discrepancies** if found between local docs and current platform.

This workspace is configured for Lean CLI cloud synchronization mode exclusively. When implementing algorithm features, always check the proper syntax in documentation rather than guessing.

---
## 8  Code Quality & Style
1. Always follow the Documentation-First principle 
2. Follow PEP 8 for Python style.
3. Include docstrings for all methods.
4. Add comments for complex logic.
5. Use type hints where possible.
6. Keep methods small and focused.
7. Implement proper error handling.
8. See `.windsurf/qc-code-examples.md` for examples.

---
## 9  Consultation Triggers
Consult before:
1. Changing core algorithm structure.
2. Adding new asset classes.
3. Modifying risk parameters.
4. Implementing complex option strategies.
5. When documentation appears inconsistent or outdated.
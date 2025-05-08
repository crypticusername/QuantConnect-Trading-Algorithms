---
trigger: always_on
---

# WARNING: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER PERMISSION
# QuantConnect Python Workspace Rules

> **Scope:** This guide defines conventions for creating Python option-trading algorithms for QuantConnect Cloud via Lean CLI (cloud mode). Follow these alongside global rules.

---
## 1  Authoritative References
| Topic                          | Source                                                                                  |
|--------------------------------|-----------------------------------------------------------------------------------------|
| QuantConnect Docs (v2)         | https://www.quantconnect.com/docs/v2                                                     |
| LEAN Engine GitHub             | https://github.com/QuantConnect/Lean                                                     |
| Documentation GitHub           | https://github.com/QuantConnect/Documentation                                           |
| Option Strategies              | https://www.quantconnect.com/docs/v2/writing-algorithms/trading-and-orders/option-strategies |
| Equity Options Universe        | https://www.quantconnect.com/docs/v2/writing-algorithms/universes/equity-options        |
| Index Options Universe         | https://www.quantconnect.com/docs/v2/writing-algorithms/universes/index-options         |
| Future Options Universe        | https://www.quantconnect.com/docs/v2/writing-algorithms/universes/future-options        |
| Lean CLI API Reference         | https://www.quantconnect.com/docs/v2/lean-cli/api-reference                              |

---
## 2  Project & Folder Conventions
1. Place each strategy in its own folder under `./projects/`.
2. Name the main file `strategy_name.py`, config `lean.json` or `config.yaml`.
3. Helpers in `./lib/`; avoid circular imports.
4. Don’t commit backtest outputs; store in `.results/` (git-ignored).

---
## 3  Algorithm Boilerplate
```python
from AlgorithmImports import *

class MyAlgorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        self.SetTimeZone(TimeZones.NEW_YORK)
        self.SetWarmUp(10, Resolution.Daily)

        equity = self.AddEquity("SPY", Resolution.Minute).Symbol
        opt = self.AddOption("SPY", Resolution.Minute)
        opt.SetFilter(lambda u: u.IncludeWeeklys().Strikes(-5, 5).Expiration(0, 7))
        self.option_symbol = opt.Symbol

        self.Schedule.On(DateRules.EveryDay(), TimeRules.AfterMarketOpen("SPY", 5), self.OpenTrades)
```
- Always `from AlgorithmImports import *` ([docs](https://www.quantconnect.com/docs/v2/writing-algorithms/key-concepts/algorithm-imports)).
- Use `Schedule.On` for timed entry/exit. 

---
## 4  Data Subscriptions & Universes
```python
# Equity options
opt = self.AddOption("SPY", Resolution.Minute)
opt.SetFilter(lambda u: u.IncludeWeeklys().Strikes(-5, 5).Expiration(0, 7))

# Index options
idx = self.AddIndexOption("SPX", Resolution.Minute)
idx.SetFilter(lambda u: u.IncludeWeeklys().Strikes(-10, 10).Expiration(0, 7))

# Future options
fut = self.AddFuture(Futures.Indices.SP500EMini, Resolution.Minute)
opt = self.AddFutureOption(fut.Symbol, Resolution.Minute)
```
[Equity Options Universe](https://www.quantconnect.com/docs/v2/writing-algorithms/universes/equity-options).

---
## 5  Option Strategy Construction
```python
# Bull Put Spread
strat = OptionStrategies.BullPutSpread(self.option_symbol.Canonical, shortStrike, longStrike, expiry)
self.Sell(strat, qty)
```
Guard empty chains:
```python
chain = self.CurrentSlice.OptionChains.get(self.option_symbol)
if chain is None:
    return
```
[Option Strategies](https://www.quantconnect.com/docs/v2/writing-algorithms/trading-and-orders/option-strategies).

---
## 6  Risk & Position Sizing
```python
risk_pct = 0.02
risk_budget = self.Portfolio.TotalPortfolioValue * risk_pct
max_loss = (width * 100 - credit * 100)
qty = int(risk_budget / max_loss)
```
- Flat all positions 30 min before close.
- Use stop-loss triggers in scheduled callbacks.

---
## 7  Spread / Condor Rules
| Spread               | Guidelines                                                |
|----------------------|-----------------------------------------------------------|
| BullPut/BearCall     | Short leg Δ≈0.30; width 1–2 strikes; credit≥`creditPct×width` |
| (Short) IronCondor   | Use `OptionStrategies.ShortIronCondor`; balance wings symmetrically |

---
## 8  Lean CLI Cloud Workflow
| Action             | Command                                                                     |
|--------------------|-----------------------------------------------------------------------------|
| Create project     | `lean cloud create-project "<Name>" --language python`                     |
| Pull project       | `lean cloud pull "<Name>"`                                                |
| Push & backtest    | `lean cloud backtest "<Name>" --push --open false --output results.json`  |
| Deploy live        | `lean cloud live deploy "<Name>" --brokerage PaperTrading`                |
[Lean CLI API](https://www.quantconnect.com/docs/v2/lean-cli/api-reference).

---
## 9  Code Quality & Style
- **PEP 8** (4-space indents, ≤120 cols).  
- Type hints and docstrings for public methods.  
- Atomic commits: `feat:`, `fix:`, `docs:`.

---
## 10  Consultation Triggers
Consult before: architecture changes, core dependency swaps, >20% refactor, or fundamental risk logic edits.

*Last updated: 2025-05-08*

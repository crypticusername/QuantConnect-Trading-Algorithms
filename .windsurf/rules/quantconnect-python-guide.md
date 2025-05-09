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
| QuantConnect Docs (v2)         | https://www.quantconnect.com/docs/v2                                                     |
| Option Strategies              | https://www.quantconnect.com/docs/v2/writing-algorithms/trading-and-orders/option-strategies |
| Equity Options Universe        | https://www.quantconnect.com/docs/v2/writing-algorithms/universes/equity-options        |
| Index Options Universe         | https://www.quantconnect.com/docs/v2/writing-algorithms/universes/index-options         |
| Future Options Universe        | https://www.quantconnect.com/docs/v2/writing-algorithms/universes/future-options        |
| Lean CLI API Reference         | https://www.quantconnect.com/docs/v2/lean-cli/api-reference                              |
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
## 3  Algorithm Boilerplate
```python
from AlgorithmImports import *

class MyAlgorithm(QCAlgorithm):
    def Initialize(self):
        """Initialize algorithm parameters, data subscriptions, and scheduling."""
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(100000)
        self.set_time_zone(TimeZones.EASTERN_STANDARD)
        self.set_warm_up(10, Resolution.DAILY)

        # Add equity and options
        equity = self.add_equity("SPY", Resolution.MINUTE).Symbol
        opt = self.add_option("SPY", Resolution.MINUTE)
        opt.set_filter(lambda u: u.include_weeklys().strikes(-5, 5).expiration(0, 7))
        self.option_symbol = opt.Symbol

        # Schedule algorithm entry points
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.after_market_open("SPY", 5), 
                         self.open_trades)
```

### Algorithm Syntax Requirements
- Always use `from AlgorithmImports import *`
- Use snake_case for method names (`set_start_date` not `SetStartDate`).
- Use UPPERCASE for Resolution values (`Resolution.MINUTE` not `Resolution.Minute`).
- Use `self.schedule.on` with `self.date_rules` and `self.time_rules`.
- Include docstrings for all methods.
- Follow PEP 8 for code style (4-space indentation, 79-char line limit).

---
## 4  Data Subscriptions & Universes
```python
# Equity options
opt = self.add_option("SPY", Resolution.MINUTE)
opt.set_filter(lambda u: u.include_weeklys().strikes(-5, 5).expiration(0, 7))

# Index options
idx = self.add_index_option("SPX", Resolution.MINUTE)
idx.set_filter(lambda u: u.include_weeklys().strikes(-10, 10).expiration(0, 7))

# Future options
fut = self.add_future(Futures.Indices.SP500EMini, Resolution.MINUTE)
opt = self.add_future_option(fut.Symbol, Resolution.MINUTE)
```

---
## 5  Option Strategy Construction
```python
# Create a put credit spread
symbol = self.option_symbol
expiry = sorted(self.option_chain.GetExpiryFunctions().Select(x => x.Date))[0]
strikes = sorted([x.Strike for x in self.option_chain.GetStrikesByExpiration(expiry)])
spread = OptionStrategies.BearPutSpread(symbol, strikes[1], strikes[0], expiry)
self.buy(spread, 1)
```

---
## 6  Risk & Position Sizing
1. Define max drawdown tolerance (e.g., 5%).
2. Implement position sizing based on volatility.
3. Use `self.portfolio.margin_remaining` for buying power awareness.
4. Set stop-loss and take-profit levels for each trade.
5. Monitor and adjust leverage ratios.

---
## 7  Documentation-First Principle
1. **Always consult official documentation** before writing algorithm code.
2. **Use Lean CLI cloud documentation** specifically - not Docker-based approaches.
3. **Never ad-lib or guess syntax** for QuantConnect-specific methods.
4. **When researching, prioritize**:
   - Official QuantConnect Docs (v2)
   - QuantConnect Options Strategies documentation
   - QuantConnect Algorithm Writing guides
   - LEAN GitHub repository examples
   - QuantConnect Forum verified answers

This workspace is configured for Lean CLI cloud synchronization mode exclusively. When implementing algorithm features, always check the proper syntax in documentation rather than guessing.

---
## 8  Code Quality & Style
1. Follow PEP 8 for Python style.
2. Include docstrings for all methods.
3. Add comments for complex logic.
4. Use type hints where possible.
5. Keep methods small and focused.
6. Implement proper error handling.

```python
def open_trades(self):
    """
    Execute opening trades based on market conditions.
    """
    try:
        # Implementation logic
        pass
    except Exception as e:
        self.log(f"Error in open_trades: {e}")
```

---
## 9  Consultation Triggers
Consult before:
1. Changing core algorithm structure.
2. Adding new asset classes.
3. Modifying risk parameters.
4. Implementing complex option strategies.
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

## 3. Enhance main.py with our custom algorithm boilerplate
```bash
cat > "{{ project_name }}/main.py" << 'EOF'
from AlgorithmImports import *

class {{ project_name | replace('-', '_') | title }}Algorithm(QCAlgorithm):
    def Initialize(self):
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
        self.schedule.on(self.date_rules.every_day(), self.time_rules.after_market_open("SPY", 5), self.OpenTrades)
        self.schedule.on(self.date_rules.every_day(), self.time_rules.before_market_close("SPY", 30), self.ClosePositions)

    def OpenTrades(self):
        """Logic for opening positions goes here"""
        pass

    def ClosePositions(self):
        """Logic for closing positions goes here"""
        pass

    def OnData(self, slice):
        """Event-driven trading logic goes here (optional)"""
        pass
EOF
```

## 4. Add strategy documentation template
```bash
cat > "{{ project_name }}/{{ project_name }}-strategy.md" << 'EOF'
# {{ project_name | replace('-', ' ') | title }} Strategy

## Overview
*[Brief description of the strategy and its goals]*

## Market Hypothesis
*[What market inefficiency or pattern does this strategy exploit?]*

## Key Components
- **Assets**: 
- **Time Frame**: 
- **Entry Criteria**: 
- **Exit Criteria**: 
- **Position Sizing**: 
- **Risk Management**: 

## Expected Performance
*[Performance expectations, drawdowns, Sharpe ratio targets, etc.]*

## Limitations
*[Known limitations or scenarios where the strategy may underperform]*

## Implementation Notes
*[Technical considerations for implementing this strategy in QC]*
EOF
```

## 5. Push to QuantConnect Cloud (Optional)
```bash
# Uncomment this line to automatically push to QC Cloud
# lean cloud push --project "{{ project_name }}"
```

## Next Steps
After the project is created, you can:
1. Define your strategy in the `{{ project_name }}-strategy.md` file
2. Implement your algorithm logic in `main.py`
3. Push to the cloud with:
   ```
   lean cloud push --project "{{ project_name }}"
   ```
4. Run a backtest with:
   ```
   lean cloud backtest "{{ project_name }}" --open
   ```
---
description: Create a new QuantConnect algorithm project with appropriate folder structure, main.py for algorithm code, and documentation template for strategy explanation.
---


# New QuantConnect Algorithm Project

This workflow creates a new algorithm project at the root of the "QuantConnect Trading Algorithms" workspace, following QuantConnect python standards and workspace rules. Each algorithm will be in its own dedicated folder.

## 1. Enter project name
- id: project_name
- type: input
- prompt: Enter a name for your new trading algorithm project:

## 2. Create project directory structure
```bash
# Creates the project folder at workspace root
mkdir -p "{{ project_name }}"
```

## 3. Create main.py with algorithm boilerplate
```bash
cat > "{{ project_name }}/main.py" << 'EOF'
from AlgorithmImports import *

class {{ project_name | replace('-', '_') | title }}Algorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        self.SetTimeZone(TimeZones.NEW_YORK)
        self.SetWarmUp(10, Resolution.Daily)

        # Add equity and options
        equity = self.AddEquity("SPY", Resolution.Minute).Symbol
        opt = self.AddOption("SPY", Resolution.Minute)
        opt.SetFilter(lambda u: u.IncludeWeeklys().Strikes(-5, 5).Expiration(0, 7))
        self.option_symbol = opt.Symbol

        # Schedule algorithm entry points
        self.Schedule.On(DateRules.EveryDay(), TimeRules.AfterMarketOpen("SPY", 5), self.OpenTrades)
        self.Schedule.On(DateRules.EveryDay(), TimeRules.BeforeMarketClose("SPY", 30), self.ClosePositions)

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

## 4. Create strategy documentation template
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

## Limitations
*[Known limitations or scenarios where the strategy may underperform]*

## Implementation Notes
*[Technical considerations for implementing this strategy in QC]*
EOF
```

## Next Steps
After the project is created, you can:
1. Define your strategy by describing it to Windsurf and editing the `{{ project_name }}-strategy.md` file
2. Work with Windsruf to code and implement your algorithm logic in `main.py`
3. Test and backtest using Lean CLI to QC Cloud 
# Credit Spread Strategy: Future Iterations

This document outlines potential modifications and enhancements to the current 0DTE SPY credit spread strategy.

## Asset Class Variations

### 1. Futures Options Implementation
**Difficulty**: Moderate  
**Changes Required**:
- Replace `add_equity` with `add_future` and `add_future_option` in main.py
- Modify option chain filters to use futures options syntax
- Update symbol handling in SpreadSelector for futures option symbols
- Adjust delta targeting for futures options (which may have different greeks behavior)
- Consider different margin and settlement requirements

```python
# Example of Futures Option setup
self.es_future = self.add_future("ES", Resolution.MINUTE)
self.es_future.set_filter(0, 180)  # Front month futures
self.es_option = self.add_future_option(self.es_future.symbol, Resolution.MINUTE)
self.es_option.set_filter(lambda universe: universe.Expiration(0, 5))
```

### 2. Index Options Implementation
**Difficulty**: Easy-to-Moderate  
**Changes Required**:
- Replace `add_equity`/`add_option` with `add_index_option` in main.py
- Modify symbol references to match index option syntax
- Update spread creation to use appropriate index option strategies
- Adjust for European-style vs American-style exercise

```python
# Example of Index Option setup
self.spx = self.add_index("SPX")
self.option_symbol = self.add_index_option(self.spx.symbol, Resolution.MINUTE)
self.option_symbol.set_filter(lambda universe: universe.Expiration(0, 5))
```

## DTE (Days to Expiration) Modifications

### 3. Extending DTE Range
**Difficulty**: Easy  
**Changes Required**:
- Adjust option filter in main.py to include longer-dated options
- Consider adapting delta targets for longer-dated options

```python
# Example of extended DTE filters
# For 0-5 DTE
self.option_symbol.set_filter(lambda universe: universe
    .IncludeWeeklys()
    .Expiration(0, 5)  # 0-5 DTE
    .Strikes(-15, +15)
)
```

### 4. Specific DTE Targeting
**Difficulty**: Easy  
**Changes Required**:
- Change option filter to target specific DTE values
- Potentially add logic to select highest premium opportunity among different DTEs

```python
# Example of specific DTE targeting
# For exactly 2 DTE
self.option_symbol.set_filter(lambda universe: universe
    .IncludeWeeklys()
    .Expiration(2, 2)  # Exactly 2 DTE
    .Strikes(-15, +15)
)
```

## Weekly Trading Strategy Modifications

### 5. Monday Entry for Friday Expiry
**Difficulty**: Easy  
**Changes Required**:
- Modify scheduling to only run entry on Mondays
- Adjust option filter to select contracts expiring on the upcoming Friday
- Update position management logic to handle weekly timeframe

```python
# Monday scheduling example
self.schedule.on(self.date_rules.week_start(), self.time_rules.at(10, 0), self.open_trades)

# Friday expiry filtering
self.option_symbol.set_filter(lambda universe: universe
    .IncludeWeeklys()
    .Expiration(4, 4)  # Expiring in 4 days (Friday if today is Monday)
    .Strikes(-15, +15)
)
```

### 6. One Position Per Week (Any Day Entry)
**Difficulty**: Moderate  
**Changes Required**:
- Modify option filter to only consider Friday expiries
- Add tracking logic to monitor if a position was opened in the current week
- Implement reset of the weekly position flag at the beginning of each week

```python
# In initialize
self.position_opened_this_week = False
self.schedule.on(self.date_rules.week_start(), self.time_rules.at(9, 30), self.reset_weekly_position_flag)

# Reset method
def reset_weekly_position_flag(self):
    self.position_opened_this_week = False
    self.log("Reset weekly position flag")
    
# In open_trades
def open_trades(self):
    if self.position_opened_this_week:
        self.log("Already opened a position this week, skipping trade entry")
        return
        
    # Find and place trade...
    if trade_placed:
        self.position_opened_this_week = True
```

## Possible Combinations

The modifications above can be combined in various ways to create different trading strategies:

1. **Weekly ES Future Options Strategy**: Combining #1 and #5 to trade ES options on Mondays for Friday expiry
2. **Weekly SPX 2DTE Strategy**: Combining #2, #4, and #6 to trade SPX options once per week with exactly 2 DTE
3. **Dynamic DTE Equity Options**: Combining #3 and #6 to select the best opportunity across multiple DTEs once per week

## Implementation Considerations

- **Data Availability**: Ensure the required data for different asset classes is available in your QuantConnect subscription
- **Margin Requirements**: Different asset classes have different margin requirements
- **Liquidity**: Consider the liquidity profiles of different option chains
- **Backtesting Accuracy**: Longer DTE strategies require longer backtests to evaluate properly
- **Exercise Risk**: Be aware of different exercise rules (American vs European) and dividend risk

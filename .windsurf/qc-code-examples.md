# WARNING: DO NOT MODIFY THIS FILE WITHOUT EXPLICIT USER PERMISSION
# QuantConnect Python Code Examples

This file contains code examples for QuantConnect algorithms that follow the official naming conventions and best practices, verified against the QuantConnect documentation repositories.

## Algorithm Boilerplate

```python
from AlgorithmImports import *

class MyAlgorithm(QCAlgorithm):
    def initialize(self) -> None:
        """Initialize algorithm parameters, data subscriptions, and scheduling."""
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.set_warm_up(10, Resolution.DAILY)

        # Add equity and options
        equity = self.add_equity("SPY", Resolution.MINUTE)
        self.equity_symbol = equity.Symbol
        
        option = self.add_option("SPY", Resolution.MINUTE)
        # Set our strike/expiry filter for this option chain
        option.set_filter(lambda u: u.include_weeklys()
                                     .strikes(-5, 5)
                                     .expiration(0, 7))
        self.option_symbol = option.Symbol
        
        # Set benchmark
        self.set_benchmark(self.equity_symbol)

        # Schedule algorithm entry points
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.after_market_open("SPY", 5), 
                         self.open_trades)

## Data Subscriptions & Universes

```python
# Equity options
option = self.add_option("SPY", Resolution.MINUTE)

# Method 1: Using lambda expression (recommended)
option.set_filter(lambda u: u.include_weeklys()
                           .strikes(-5, 5)
                           .expiration(0, 7))

# Method 2: Using direct parameters
# option.set_filter(-5, 5, 0, 7, includeWeeklys=True)

# Method 3: Using TimeSpan
# option.set_filter(lambda u: u.include_weeklys()
#                           .strikes(-5, 5)
#                           .expiration(TimeSpan.zero, TimeSpan.from_days(7)))

# Index options
idx = self.add_index_option("SPX", Resolution.MINUTE)
idx.set_filter(lambda u: u.include_weeklys()
                         .strikes(-10, 10)
                         .expiration(0, 7))

# Future options
fut = self.add_future(Futures.Indices.SP500EMini, Resolution.MINUTE)
opt = self.add_future_option(fut.Symbol, Resolution.MINUTE)
```

## Option Strategy Construction

```python
# Method 1: Using OptionChains from slice in on_data
def on_data(self, slice):
    if self.portfolio.invested: return
    if not self.is_market_open(self.option_symbol): return
    
    # Get the option chain from the slice
    chain = slice.option_chains.get_value(self.option_symbol)
    if chain is None: return
    
    # Find at-the-money (ATM) contracts with nearest expiration
    contracts = sorted(chain, key=lambda x: abs(chain.underlying.price - x.strike))
    if len(contracts) == 0: return
    
    # Create option strategy
    nearest_expiry = min(contract.expiry for contract in contracts)
    atm_strike = contracts[0].strike
    bear_put_spread = OptionStrategies.bear_put_spread(
        self.option_symbol, 
        atm_strike + 5, 
        atm_strike,
        nearest_expiry)
    
    # Execute the strategy
    self.buy(bear_put_spread, 1)

# Method 2: Using stored option chain data
def open_trades(self):
    if self.portfolio.invested: return
    
    # Check if we have option chains available
    if not slice.option_chains.contains_key(self.option_symbol): return
    chain = slice.option_chains[self.option_symbol]
    
    # Sort by expiration, then by strike
    expirations = sorted(chain.expiry_dates)
    if len(expirations) == 0: return
    
    nearest_expiry = expirations[0]
    strikes = sorted(chain.strikes)
    
    # Create and execute a straddle strategy
    straddle = OptionStrategies.straddle(
        self.option_symbol,
        strikes[len(strikes)//2],  # Middle strike
        nearest_expiry)
    
    self.buy(straddle, 1)
```

## Error Handling and Logging Examples

```python
def open_trades(self) -> None:
    """
    Execute opening trades based on market conditions.
    
    This method is called after market open and implements the core trading logic.
    """
    try:
        # Implementation logic
        if not self.portfolio.invested and self.is_market_open(self.option_symbol):
            # Check for trading signals
            self.debug(f"Looking for trading signals at {self.time}")
            
            # Example of different log levels
            self.log(f"Portfolio value: ${self.portfolio.total_portfolio_value}")
            self.debug(f"Current cash: ${self.portfolio.cash}")
            
            # Only place trades during market hours
            if not self.is_market_open(self.option_symbol):
                self.debug("Market closed for options, skipping trade")
                return
    except Exception as e:
        self.error(f"Error in open_trades: {e}")
        # You can also include stack trace for debugging
        import traceback
        self.error(traceback.format_exc())
```

## Complete Algorithm Example

```python
from AlgorithmImports import *

class OptionTradingAlgorithm(QCAlgorithm):
    def initialize(self) -> None:
        """Initialize algorithm parameters and data subscriptions."""
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)
        
        # Add equity as underlying
        equity = self.add_equity("SPY", Resolution.MINUTE)
        self.equity_symbol = equity.Symbol
        
        # Add and filter option chain
        option = self.add_option("SPY", Resolution.MINUTE)
        option.set_filter(lambda u: u.include_weeklys()
                                    .strikes(-5, 5)
                                    .expiration(0, 30))
        self.option_symbol = option.Symbol
        
        # Set benchmark and schedule events
        self.set_benchmark(self.equity_symbol)
        self.schedule.on(self.date_rules.every_day(),
                        self.time_rules.after_market_open("SPY", 30),
                        self.open_positions)
        self.schedule.on(self.date_rules.every_day(),
                        self.time_rules.before_market_close("SPY", 10),
                        self.close_positions)
    
    def open_positions(self) -> None:
        """Strategy logic for opening positions."""
        if self.portfolio.invested: return
        
        self.log(f"Looking for trading opportunities at {self.time}")
    
    def close_positions(self) -> None:
        """Strategy logic for closing positions."""
        if self.portfolio.invested:
            self.liquidate()
            self.log("Closed all positions")
    
    def on_data(self, slice) -> None:
        """Event-driven trading logic based on data updates."""
        pass
    
    def on_order_event(self, order_event) -> None:
        """Handle order status updates."""
        if order_event.status == OrderStatus.FILLED:
            self.debug(f"Order filled: {order_event.order_id}, Quantity: {order_event.fill_quantity}, Price: {order_event.fill_price}")
```

## Reference to Official QuantConnect Example Algorithms

The following are paths to key example algorithms in the QuantConnect repositories that demonstrate important concepts and strategies. You can find these in the `.windsurf/QC-Doc-Repos/Lean/Algorithm.Python/` directory:

### Basic Algorithm Templates

- **Basic Equity Algorithm**: `BasicTemplateAlgorithm.py`
- **Basic Options Algorithm**: `BasicTemplateOptionsAlgorithm.py`
- **Basic Options Strategy Algorithm**: `BasicTemplateOptionStrategyAlgorithm.py`
- **Basic Index Options Algorithm**: `BasicTemplateIndexOptionsAlgorithm.py`
- **Basic Future Options Algorithm**: `BasicTemplateFutureOptionAlgorithm.py`

### Option Strategies

#### Index Options
- **Bear Call Spread**: `IndexOptionBearCallSpreadAlgorithm.py`
- **Bear Put Spread**: `IndexOptionBearPutSpreadAlgorithm.py`
- **Bull Call Spread**: `IndexOptionBullCallSpreadAlgorithm.py`
- **Bull Put Spread**: `IndexOptionBullPutSpreadAlgorithm.py`
- **Call Butterfly**: `IndexOptionCallButterflyAlgorithm.py`
- **Put Butterfly**: `IndexOptionPutButterflyAlgorithm.py`
- **Call Calendar Spread**: `IndexOptionCallCalendarSpreadAlgorithm.py`
- **Put Calendar Spread**: `IndexOptionPutCalendarSpreadAlgorithm.py`
- **Iron Condor**: `IndexOptionIronCondorAlgorithm.py`

#### Equity Options
- **Basic Option Strategy**: `BasicTemplateOptionStrategyAlgorithm.py`
- **Option Equity Strategy**: `BasicTemplateOptionEquityStrategyAlgorithm.py`
- **Straddle & Short Straddle**: `LongAndShortStraddleStrategiesAlgorithm.py`
- **Strangle & Short Strangle**: `LongAndShortStrangleStrategiesAlgorithm.py`
- **Call Butterfly & Short Call Butterfly**: `LongAndShortButterflyCallStrategiesAlgorithm.py`
- **Put Butterfly & Short Put Butterfly**: `LongAndShortButterflyPutStrategiesAlgorithm.py`
- **Call Calendar Spread & Short Call Calendar Spread**: `LongAndShortCallCalendarSpreadStrategiesAlgorithm.py`
- **Put Calendar Spread & Short Put Calendar Spread**: `LongAndShortPutCalendarSpreadStrategiesAlgorithm.py`
- **Covered Call & Protective Call**: `CoveredAndProtectiveCallStrategiesAlgorithm.py`
- **Covered Put & Protective Put**: `CoveredAndProtectivePutStrategiesAlgorithm.py`
- **Naked Call**: `NakedCallStrategyAlgorithm.py`
- **Naked Put**: `NakedPutStrategyAlgorithm.py`
- **Iron Condor**: `IronCondorStrategyAlgorithm.py`

#### Future Options
- **Basic Future Option Algorithm**: `BasicTemplateFutureOptionAlgorithm.py`
- **Future Option Buy/Sell Call**: `FutureOptionBuySellCallIntradayRegressionAlgorithm.py`
- **Future Option Call ITM Expiry**: `FutureOptionCallITMExpiryRegressionAlgorithm.py`
- **Future Option Call OTM Expiry**: `FutureOptionCallOTMExpiryRegressionAlgorithm.py`
- **Future Option Put ITM Expiry**: `FutureOptionPutITMExpiryRegressionAlgorithm.py`
- **Future Option Put OTM Expiry**: `FutureOptionPutOTMExpiryRegressionAlgorithm.py`
- **Future Option Short Call ITM Expiry**: `FutureOptionShortCallITMExpiryRegressionAlgorithm.py`
- **Future Option Short Put ITM Expiry**: `FutureOptionShortPutITMExpiryRegressionAlgorithm.py`

### Advanced Concepts

- **Option Chain Filtering**: `BasicTemplateOptionsFilterUniverseAlgorithm.py`
- **Option Chain Consolidation**: `BasicTemplateOptionsConsolidationAlgorithm.py`
- **Option History**: `BasicTemplateOptionsHistoryAlgorithm.py`
- **Option Price Models**: `BasicTemplateOptionsPriceModel.py`
- **Framework-based Options**: `BasicTemplateOptionsFrameworkAlgorithm.py`

### Documentation References

For more detailed documentation on options trading in QuantConnect, refer to these files in the Documentation repository:

- **Option Universe Selection**: `.windsurf/QC-Doc-Repos/Documentation/02 Algorithm Reference/04 Universe Selection/03 Option Universe Selection.html`
- **Option Strategies**: `.windsurf/QC-Doc-Repos/Documentation/02 Algorithm Reference/08 Trading and Orders/03 Option Strategies.html`
- **Option Exercise and Assignment**: `.windsurf/QC-Doc-Repos/Documentation/02 Algorithm Reference/08 Trading and Orders/04 Option Exercise and Assignment.html`

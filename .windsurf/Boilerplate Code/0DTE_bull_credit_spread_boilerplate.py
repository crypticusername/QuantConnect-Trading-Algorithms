from AlgorithmImports import *

class OptionStrategyBoilerplateAlgorithm(QCAlgorithm):
    """
    BOILERPLATE ALGORITHM for 0-DTE (Zero Days to Expiration) Option Spreads.
    This algorithm demonstrates a common structure for trading daily option spreads,
    specifically a Bull Put Credit Spread on SPY as an example.

    Key Features & Customization Points:
    - Equity and Option Data Subscription
    - Option Filtering (strikes, expiration)
    - Scheduled Trade Entry and Exit
    - Robust Exit Timing (handles early market closures)
    - Option Chain Processing
    - Strike Selection Logic (example for Bull Put)
    - Spread Definition using OptionStrategies
    - Order Management (basic tracking)

    How to Use as Boilerplate:
    1. Rename the class `OptionStrategyBoilerplateAlgorithm`.
    2. Adjust `initialize()` parameters (dates, cash, symbols).
    3. Modify `option.set_filter()` for your desired contract characteristics.
    4. Change scheduling in `initialize()` if different entry/exit times are needed.
    5. Adapt `try_open_spread_strategy()` for your specific strategy:
        - Modify strike selection logic (e.g., for Bear Call, Iron Condor, etc.).
        - Change `OptionStrategies` call (e.g., `OptionStrategies.bear_call_spread`).
    6. Customize `try_close_spread_strategy()` if more complex closing logic is required.
    7. Add risk management, position sizing, and indicator logic as needed.
    """

    def initialize(self) -> None:
        """Initialize algorithm parameters, data subscriptions, and scheduling."""
        # --- Algorithm Settings (Customize) ---
        self.set_start_date(2024, 1, 1)  # Example: Start date for backtest
        self.set_end_date(2024, 12, 31)    # Example: End date for backtest
        self.set_cash(10000)             # Example: Initial portfolio cash
        self.set_time_zone(TimeZones.NEW_YORK) # Crucial for aligning with US market times

        # --- Underlying Asset (Customize) ---
        underlying_ticker = "SPY"  # Example: SPDR S&P 500 ETF

        # --- Data Subscriptions (Typically keep Resolution.MINUTE for options) ---
        equity = self.add_equity(underlying_ticker, Resolution.MINUTE)
        self.equity_symbol = equity.Symbol
        
        option = self.add_option(underlying_ticker, Resolution.MINUTE)
        self.option_symbol = option.Symbol # Store the generic option symbol (e.g., SPY)

        # --- Option Filter (CRITICAL: Customize for your strategy) ---
        # This filter determines which option contracts are loaded into the option chain.
        # It's a preliminary filter; more precise selection happens in `on_data` or `try_open_spread_strategy`.
        option.set_filter(lambda u: u.include_weeklys()  # Include weekly options
                                     .strikes(-20, +20)   # Load strikes within +/- 20 from ATM (adjust as needed)
                                     .expiration(0, 35)) # Load expirations from 0 to 35 days out (adjust for DTE needs)
                                                        # For 0-DTE, (0,1) or (0,2) might be sufficient if running daily.

        # --- Benchmarking (Optional but good practice) ---
        self.set_benchmark(self.equity_symbol)

        # --- Position Tracking (Basic example) ---
        self.spread_is_open = False      # Flag to indicate if a spread position is currently active
        # self.active_spread_details = None # Could store details of the open spread (e.g., strikes, expiry)

        # --- Flags for Scheduled Actions (Decouples scheduling from data handling) ---
        self.pending_open_trade_flag = False
        self.pending_close_trade_flag = False

        # --- Event Scheduling (CRITICAL: Customize for your strategy's timing) ---
        # Example: Schedule trade entry attempt (e.g., at 10:00 AM New York Time)
        # The `equity_symbol` is often used for `date_rules` to align with its trading calendar.
        self.schedule.on(self.date_rules.every_day(self.equity_symbol), 
                         self.time_rules.at(10, 0),  # 10:00 AM NY time
                         self.schedule_open_trades_event)

        # Example: Schedule trade exit attempt (e.g., 15 mins before market close)
        # Using `option_symbol` for `before_market_close` is key for early closure handling.
        self.schedule.on(self.date_rules.every_day(self.equity_symbol), 
                         self.time_rules.before_market_close(self.option_symbol, 15), # 15 mins before option market close
                         self.schedule_close_trades_event)

    def schedule_open_trades_event(self):
        """Scheduled event to set a flag, indicating the desire to open a trade.
           Actual trade logic will occur in `on_data` to ensure data is available."""
        if self.spread_is_open:
            self.debug(f"{self.time}: Spread already open, skipping open schedule.")
            return
        self.debug(f"{self.time}: Setting flag to attempt opening trades on next data slice.")
        self.pending_open_trade_flag = True

    def schedule_close_trades_event(self):
        """Scheduled event to set a flag, indicating the desire to close a trade.
           Actual trade logic will occur in `on_data` or a dedicated closing method."""
        if not self.spread_is_open:
            self.debug(f"{self.time}: No spread position open to schedule for closure.")
            return
        self.debug(f"{self.time}: Setting flag to attempt closing positions on next data slice.")
        self.pending_close_trade_flag = True

    def on_data(self, slice: Slice):
        """Main data handler. Processes flags set by scheduled events.
           This ensures that option chain data is available when attempting trades."""
        # Check if we were flagged to open a new position
        if self.pending_open_trade_flag:
            self.debug(f"{self.time}: `on_data` triggered for pending_open_trade_flag.")
            self.try_open_spread_strategy(slice)
            self.pending_open_trade_flag = False # Reset flag after attempt
            
        # Check if we were flagged to close existing positions
        if self.pending_close_trade_flag:
            self.debug(f"{self.time}: `on_data` triggered for pending_close_trade_flag.")
            self.try_close_spread_strategy(slice) # Pass slice if needed for new orders/checks
            self.pending_close_trade_flag = False # Reset flag after attempt
    
    def try_open_spread_strategy(self, slice: Slice):
        """Attempts to open a specific option spread strategy (e.g., Bull Put Credit Spread).
           CRITICAL: This method needs significant customization for different strategies."""
        if self.portfolio.invested and self.spread_is_open: # Basic check to avoid multiple concurrent spreads
            self.debug(f"{self.time}: Already invested in a spread, not opening another.")
            return

        # --- Option Chain Retrieval ---
        if not self.option_symbol in slice.option_chains:
            self.debug(f"{self.time}: No option chain data for {self.option_symbol} in current slice.")
            return
            
        chain = slice.option_chains[self.option_symbol]
        if not chain:
            self.debug(f"{self.time}: Option chain for {self.option_symbol} is present but empty.")
            return
        
        # --- Strategy-Specific Parameters & Logic (EXAMPLE: 0-DTE Bull Put) ---
        target_dte = 0 # For 0-DTE strategies
        # For other DTEs, adjust: target_dte = 7, etc.

        underlying_price = self.securities[self.equity_symbol].price
        if underlying_price == 0:
            self.debug(f"{self.time}: Underlying price for {self.equity_symbol} is 0, cannot proceed.")
            return
        self.debug(f"{self.time}: Current {self.equity_symbol} price: {underlying_price:.2f}")
        
        # --- Contract Filtering & Selection (HIGHLY CUSTOMIZABLE) ---
        # Example: Find Put options expiring at target_dte
        target_expiry_date = self.time.date() + timedelta(days=target_dte)
        
        candidate_contracts = [c for c in chain 
                               if c.right == OptionRight.PUT and \  # PUTs for Bull Put Spread
                               c.expiry.date() == target_expiry_date]

        if not candidate_contracts or len(candidate_contracts) < 2:
            self.debug(f"{self.time}: Not enough suitable contracts for {target_expiry_date.strftime('%Y-%m-%d')} (found {len(candidate_contracts)}).")
            return

        # Example: Select strikes for Bull Put Spread (Short Put OTM, Long Put further OTM)
        # This is a simplified example. Robust selection might use delta, width, premium, etc.
        otm_puts = sorted([c for c in candidate_contracts if c.strike < underlying_price],
                          key=lambda c: c.strike, reverse=True) # Closest to ATM first

        if len(otm_puts) < 2:
            self.debug(f"{self.time}: Not enough OTM Puts for {target_expiry_date.strftime('%Y-%m-%d')} to form spread (found {len(otm_puts)}).")
            return
        
        short_put_contract = otm_puts[0] # Higher strike (closer to money)
        long_put_contract = otm_puts[1]  # Lower strike (further from money)

        # --- Sanity Checks (Important!) ---
        if short_put_contract.strike <= long_put_contract.strike:
            self.debug(f"{self.time}: Invalid strike selection: Short strike {short_put_contract.strike} not > Long strike {long_put_contract.strike}.")
            return

        self.debug(f"{self.time}: Selected for Bull Put Spread (Exp: {target_expiry_date.strftime('%Y-%m-%d')}):")
        self.debug(f"  Short Put: {short_put_contract.symbol.value} (Strike: {short_put_contract.strike})")
        self.debug(f"  Long Put:  {long_put_contract.symbol.value} (Strike: {long_put_contract.strike})")
        
        # --- Define and Execute Strategy using OptionStrategies ---
        try:
            # For Bull Put Spread: Short Put Strike > Long Put Strike
            bull_put_spread_strategy = OptionStrategies.bull_put_spread(
                self.option_symbol,      # Generic option symbol (e.g., SPY)
                short_put_contract.strike, # Higher strike (short put)
                long_put_contract.strike,  # Lower strike (long put)
                target_expiry_date         # Expiration date
            )
            
            # --- Order Sizing (Customize) ---
            quantity = 1 # Example: 1 contract of the spread
            
            # Submit the order for the spread (BUY for credit spreads, SELL for debit spreads)
            # For a Bull Put (credit spread), we are selling the spread, so we receive premium.
            # QuantConnect's `OptionStrategies` handles this; `self.buy` is used for credit spreads.
            orders = self.buy(bull_put_spread_strategy, quantity) # Returns a list of order tickets
            # For debit spreads like Bull Call, use `self.sell(...)`

            self.spread_is_open = True
            # self.active_spread_details = ... # Store details if needed for complex management
            self.log(f"{self.time}: Submitted Bull Put Spread. Short: {short_put_contract.symbol.value}, Long: {long_put_contract.symbol.value}. Orders: {[o.id for o in orders]}")

        except Exception as e:
            self.error(f"{self.time}: Error opening spread: {e}")

    def try_close_spread_strategy(self, slice: Slice):
        """Attempts to close any open option spread positions.
           This example liquidates any position that looks like the one it opened.
           More sophisticated logic may be needed if managing multiple/different spreads."""
        if not self.spread_is_open or not self.portfolio.invested:
            self.debug(f"{self.time}: No open spread or not invested, skipping close attempt.")
            return

        # --- Identify Open Spread Legs (Customize if complex) ---
        # This basic version assumes we only have one type of spread open at a time.
        # It finds the first option position and assumes it's part of our spread.
        # For robust closing of a specific known spread, you'd use `self.active_spread_details`
        # or iterate through portfolio to find specific short/long legs matching expected strikes/expiry.

        open_option_positions = [pos for pos in self.portfolio.values 
                                 if pos.invested and pos.type == SecurityType.OPTION and pos.symbol.canonical == self.option_symbol]
        
        if not open_option_positions:
            self.debug(f"{self.time}: No open option positions found in portfolio for {self.option_symbol}.")
            self.spread_is_open = False # Reset flag if no positions found
            return

        self.log(f"{self.time}: Attempting to liquidate {len(open_option_positions)} option position(s) for {self.option_symbol}.")
        
        # --- Liquidate Positions ---
        # The simplest way to close is to liquidate all positions for the canonical option symbol.
        # If a specific strategy was opened with OptionStrategies, liquidating the canonical symbol
        # might not always work as intended if the strategy object itself isn't used.
        # A more robust way for strategies opened with OptionStrategies is to re-define the strategy
        # using the known strikes and expiry and then liquidate that strategy object.
        # However, for a simple 0-DTE, liquidating all legs of the option symbol is often sufficient.

        # Example of liquidating all positions for the option symbol (simplest)
        for position in open_option_positions:
             self.liquidate(position.symbol) # Liquidate each leg individually
             self.log(f"{self.time}: Submitted liquidation for {position.symbol.value}.")
        
        # Reset flags after attempting liquidation
        self.spread_is_open = False
        # self.active_spread_details = None
        self.log(f"{self.time}: Spread closure process initiated.")

    def on_order_event(self, order_event: OrderEvent):
        """Handles order events. Can be used for logging, error handling, or updating state."""
        if order_event.status == OrderStatus.FILLED:
            self.log(f"{self.time}: Order FILLED: {self.securities[order_event.symbol].symbol.value} - Quantity: {order_event.filled_quantity} @ {order_event.fill_price:.2f}")
        elif order_event.status == OrderStatus.CANCELED:
            self.log(f"{self.time}: Order CANCELED: {order_event.symbol}")
        elif order_event.status == OrderStatus.INVALID:
            self.log(f"{self.time}: Order INVALID: {order_event.symbol} - Message: {order_event.message}")
        # Add more status checks as needed (Submitted, PartialFill, Error, etc.)

# --- Potential Enhancements (Add as separate methods or logic blocks) ---
# - Risk Management (e.g., stop loss on spread value, max loss per day)
# - Position Sizing (e.g., based on account equity, volatility)
# - Indicator-based Entry/Exit Signals (e.g., RSI, MACD, VWAP)
# - Dynamic Strike Selection (e.g., based on Delta, probability OTM)
# - Handling Multiple Concurrent Spreads
# - Adjusting for different market conditions (e.g., VIX levels)
# - More sophisticated error handling and retry logic for orders


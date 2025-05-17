from AlgorithmImports import *
from datetime import datetime # Ensure datetime is imported

# ===== COMPONENT: IMPORTS =====
# All imports should be placed above this line
# ===== END COMPONENT =====

# ===== COMPONENT: CONFIGURATION =====
# Strategy parameters and configuration should be defined below
# ===== END COMPONENT =====

# ===== COMPONENT: STATE_MANAGEMENT =====
# State tracking variables should be defined below
# ===== END COMPONENT =====

class Basic_Credit_SpreadAlgorithm(QCAlgorithm):
    # ===== COMPONENT: INITIALIZATION =====
    # Algorithm initialization code goes here
    def initialize(self) -> None:
        self.set_start_date(2023, 10, 1)
        self.set_end_date(2023, 12, 31) 
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)

        self.equity_symbol = self.add_equity("SPY", Resolution.MINUTE).symbol
        option = self.add_option("SPY", resolution=Resolution.MINUTE)
        option.set_filter(lambda u: u.include_weeklys().expiration(0, 30)) # Filter for options expiring within 0 to 30 days
        self.option_symbol = option.symbol
        self.set_benchmark(self.equity_symbol)

        # Algorithm parameters - Core risk/reward settings
        self.min_credit_threshold = 0.10  # Minimum credit to receive for opening a spread
        self.enable_stop_loss = True  # Set to False to disable stop loss
        self.stop_loss_multiplier = 2.0  # Stop loss at 2x credit received (set to 0 to disable)
        self.profit_target_percentage = 0.50 # Target 50% of max profit (initial credit)
        
        # Option selection parameters - Configurable strategy settings
        self.short_put_delta_mode = "MAX"  # Options: "EXACT", "RANGE", "MAX"
        self.short_put_delta_exact = 0.30  # Used when mode is "EXACT"
        self.short_put_delta_min = 0.25    # Used when mode is "RANGE"
        self.short_put_delta_max = 0.30    # Used when mode is "RANGE" or "MAX"

        # Spread width parameters
        self.spread_width_mode = "FIXED"   # Options: "FIXED", "RANGE", "DYNAMIC"
        self.spread_width_fixed = 5.0      # Used when mode is "FIXED"
        self.spread_width_min = 1.0        # Used when mode is "RANGE"
        self.spread_width_max = 15.0       # Used when mode is "RANGE"

        # Long put parameters
        self.long_put_selection_mode = "WIDTH"  # Options: "WIDTH", "DELTA", "BOTH"
        self.long_put_delta_min = 0.10     # Used when mode includes "DELTA"
        self.long_put_delta_max = 0.20     # Used when mode includes "DELTA"

        # State variables - simplified for clearer flow control
        self.spread_is_open = False
        self.pending_open = False
        self.pending_close = False
        
        self.opened_short_put_symbol = None
        self.opened_long_put_symbol = None
        self.initial_credit = None
        self.stop_loss_target_debit = None
        self.profit_target_value_debit = None
        
        self.opening_order_tickets = []
        self.closing_order_tickets = []

        # Scheduled actions
        self.schedule.on(
            self.date_rules.every_day(self.option_symbol),
            self.time_rules.at(10, 0),
            self.open_trades
        )
        # Regular close positions
        self.schedule.on(
            self.date_rules.every_day(self.option_symbol),
            self.time_rules.before_market_close(self.option_symbol, 30),
            self.close_positions
        )
        # Failsafe: force close all legs 15 min before market close
        self.schedule.on(
            self.date_rules.every_day(self.option_symbol),
            self.time_rules.before_market_close(self.option_symbol, 15),
            self.close_all_option_positions_force
        ) 

    # ===== COMPONENT: TRADE_ENTRY =====
    # Trade entry logic goes here
    def open_trades(self) -> None:
        if self.spread_is_open:
            self.log("Spread already open, skipping")
            return
        self.log("Setting flag to open trades on next data slice")
        self.pending_open = True

    # ===== COMPONENT: TRADE_EXIT =====
    # Trade exit logic goes here
    def close_positions(self) -> None:
        if not self.spread_is_open:
            self.log("No spread position open to close")
            return
        self.log("Setting flag to close positions on next data slice")
        self.pending_close = True
        
    # ===== COMPONENT: RISK_MANAGEMENT =====
    # Risk management and emergency close logic goes here
    def close_all_option_positions_force(self) -> None:
        """
        Scheduled failsafe to close ALL open option contracts for this symbol before expiry/market close.
        """
        self.log("FAILSAFE: Executing forced liquidation of all option positions before market close")
        holding_count = 0
        
        for kvp in self.portfolio:
            holding = kvp.value
            if (holding.type == SecurityType.OPTION and
                    holding.symbol.canonical == self.option_symbol and
                    holding.invested):
                self.log(f"FAILSAFE: Liquidating {holding.symbol.value}, Quantity: {holding.quantity}")
                quantity_to_close = -holding.quantity
                ticket = self.market_order(holding.symbol, quantity_to_close)
                self.log(f"FAILSAFE: Order created. ID: {ticket.order_id} for {holding.symbol.value}")
                holding_count += 1

        if holding_count > 0:
            self.log(f"FAILSAFE: Submitted liquidation orders for {holding_count} open option leg(s) before market close")
        else:
            self.log("FAILSAFE: No open option legs to liquidate before close")

        # Reset spread state regardless of whether positions were found
        self.spread_is_open = False
        self.opening_order_tickets.clear()
        self.closing_order_tickets.clear()
        self.opened_short_put_symbol = None
        self.opened_long_put_symbol = None
        self.pending_close = False
        self.log("FAILSAFE: Spread position marked as closed")


    # ===== COMPONENT: DATA_HANDLING =====
    # Main data processing and event handling
    def on_data(self, slice: Slice) -> None:
        """Main event handler for market data updates."""
        # First, handle pending open if no spread is open yet
        if self.pending_open and not self.spread_is_open:
            self.log("ON_DATA: Opening trade initiated")
            self.try_open_spread(slice)
            self.pending_open = False  # Reset flag regardless of success
            return  # Exit to avoid checking other conditions in the same bar
            
        # Then, handle pending close if spread is open
        if self.pending_close and self.spread_is_open:
            self.log("ON_DATA: Close initiated")
            self.try_close_spread("PendingClose")
            return  # Exit to avoid checking other conditions in the same bar
            
        # If we have an open spread, check for stop loss or profit target
        if self.spread_is_open:
            self.log("ON_DATA: Checking stop loss")
            stop_loss_hit = self.check_stop_loss(slice)
            
            # If stop loss triggered a close, don't check profit target
            if stop_loss_hit or self.pending_close:
                return
                
            self.log("ON_DATA: Checking profit target")
            self.monitor_profit_target(slice)
            
    # ===== COMPONENT: STOP_LOSS =====
    # Stop loss calculation and triggering
    def check_stop_loss(self, slice: Slice) -> bool:
        """Checks if the current position has hit the stop loss threshold.
        
        The stop loss is triggered when the current debit to close the spread
        reaches (initial_credit * stop_loss_multiplier).
        
        Returns:
            bool: True if stop loss was triggered, False otherwise
        """
        # Skip if stop loss is disabled
        if not self.enable_stop_loss or self.stop_loss_multiplier <= 0:
            return False
            
        if not self.spread_is_open or not self.opened_short_put_symbol or not self.opened_long_put_symbol:
            self.log("CHECK_STOP_LOSS: No spread is open, skipping stop loss check")
            return False
        
        if not self.initial_credit or self.initial_credit <= 0:
            self.log("CHECK_STOP_LOSS: Initial credit not set or invalid, skipping stop loss check")
            return False
            
        try:    
            # Calculate current debit to close the spread
            current_debit = self.calculate_current_debit_to_close(slice)
            
            if current_debit is None:
                self.log("CHECK_STOP_LOSS: Could not calculate current debit, skipping stop loss check")
                return False
                
            # Calculate stop loss price (2x initial credit)
            stop_loss_price = self.initial_credit * self.stop_loss_multiplier
            
            self.log(f"CHECK_STOP_LOSS: Current debit: ${current_debit:.2f}, Stop loss at: ${stop_loss_price:.2f} ({self.stop_loss_multiplier}x initial credit ${self.initial_credit:.2f})")
            
            # Check if we've hit stop loss
            if current_debit >= stop_loss_price:
                self.log(f"CHECK_STOP_LOSS: STOP LOSS HIT! Current debit: ${current_debit:.2f}, Target: ${stop_loss_price:.2f} ({self.stop_loss_multiplier}x initial credit)")
                self.pending_close = True
                self.try_close_spread("StopLoss")
                return True
                
            return False
            
        except Exception as e:
            self.error(f"CHECK_STOP_LOSS: Error in stop loss check: {str(e)}")
            return False
            
    # ===== COMPONENT: PROFIT_TARGET =====
    # Profit target monitoring and triggering
    def monitor_profit_target(self, slice: Slice) -> None:
        """Monitors an open spread for profit target"""
        if not self.spread_is_open or not self.initial_credit:
            return
            
        try:
            # Get current market data for our options
            option_chain = slice.option_chains.get(self.option_symbol)
            if not option_chain:
                self.log("PROFIT_TARGET: No option chain data available. Cannot check profit target.")
                return
                
            short_put_data = option_chain.get(self.opened_short_put_symbol)
            long_put_data = option_chain.get(self.opened_long_put_symbol)
            
            if not short_put_data or not long_put_data:
                self.log("PROFIT_TARGET: Missing market data for one or both options. Cannot check profit target.")
                return
                
            # Calculate current debit to close with fallbacks for zero prices
            short_put_ask = short_put_data.ask_price
            long_put_bid = long_put_data.bid_price
            
            # If ask is zero, try to use last price or mid price as fallback
            if short_put_ask == 0:
                if short_put_data.last_price > 0:
                    short_put_ask = short_put_data.last_price
                    self.log(f"PROFIT_TARGET: Using last price {short_put_ask} as fallback for zero ask on short put")
                elif short_put_data.bid_price > 0:
                    # Use mid price if available
                    short_put_ask = short_put_data.bid_price * 1.1  # Add 10% to bid as estimate
                    self.log(f"PROFIT_TARGET: Using adjusted bid {short_put_ask} as fallback for zero ask on short put")
            
            # If bid is zero, try to use last price or mid price as fallback
            if long_put_bid == 0:
                if long_put_data.last_price > 0:
                    long_put_bid = long_put_data.last_price
                    self.log(f"PROFIT_TARGET: Using last price {long_put_bid} as fallback for zero bid on long put")
                elif long_put_data.ask_price > 0:
                    # Use mid price if available
                    long_put_bid = long_put_data.ask_price * 0.9  # Subtract 10% from ask as estimate
                    self.log(f"PROFIT_TARGET: Using adjusted ask {long_put_bid} as fallback for zero bid on long put")
            
            # Calculate current debit to close
            current_debit = short_put_ask - long_put_bid
            
            # Sanity check - debit should not be negative
            if current_debit < 0:
                self.log(f"PROFIT_TARGET: Warning - calculated negative debit to close: ${current_debit:.2f}. Using absolute value.")
                current_debit = abs(current_debit)
            
            # Calculate profit target
            profit_target_debit = self.initial_credit * (1 - self.profit_target_percentage)
            
            # Calculate current profit percentage
            current_profit = self.initial_credit - current_debit
            profit_percentage = (current_profit / self.initial_credit) * 100 if self.initial_credit > 0 else 0
            
            # Check if we've hit profit target
            if current_debit <= profit_target_debit:
                self.log(f"PROFIT_TARGET: Target hit! Current debit: ${current_debit:.2f}, Target: ${profit_target_debit:.2f}, Profit: {profit_percentage:.1f}%")
                self.pending_close = True
                self.try_close_spread("ProfitTarget")
                return
                
            # Log current position status with more details
            self.log(f"PROFIT_TARGET: Current debit: ${current_debit:.2f}, Target: ${profit_target_debit:.2f}, Initial credit: ${self.initial_credit:.2f}, Profit: {profit_percentage:.1f}%")
            
        except Exception as e:
            self.error(f"PROFIT_TARGET: Error calculating profit target: {str(e)}")

    # ===== COMPONENT: SPREAD_SELECTION =====
    # Spread selection and entry logic
    def try_open_spread(self, slice: Slice) -> None:
        """Attempts to open a bull put spread if conditions are met."""
        self.log(f"TRY_OPEN_SPREAD: Attempting to open spread. Current Time: {self.time}")
        
        chain = slice.option_chains.get(self.option_symbol)
        if not chain:
            self.log("TRY_OPEN_SPREAD: No option chain found for SPY.")
            return

        # Organize contracts by expiry date (from Alert Apricot Duck)
        current_date = self.time.date()
        puts = [x for x in chain if x.right == OptionRight.PUT and x.strike < chain.underlying.price]
        if not puts:
            self.log("TRY_OPEN_SPREAD: No OTM puts found.")
            return
            
        # Organize contracts by expiry date
        contracts_by_expiry = {}
        for put in puts:
            expiry_date = put.expiry.date()
            if expiry_date not in contracts_by_expiry:
                contracts_by_expiry[expiry_date] = []
            contracts_by_expiry[expiry_date].append(put)
            
        # Prioritize same-day expiry (0DTE) if available
        target_expiry_date = None
        if current_date in contracts_by_expiry and len(contracts_by_expiry[current_date]) >= 2:
            target_expiry_date = current_date
            self.log(f"TRY_OPEN_SPREAD: Found same-day expiry options (0DTE)")
        else:
            available_expiries = sorted(contracts_by_expiry.keys())
            if not available_expiries:
                self.log("TRY_OPEN_SPREAD: No put options available with any expiry.")
                return
            for expiry in available_expiries:
                if len(contracts_by_expiry[expiry]) >= 2:
                    target_expiry_date = expiry
                    self.log(f"TRY_OPEN_SPREAD: Using nearest expiry date: {expiry}")
                    break
                    
        if target_expiry_date is None:
            self.log("TRY_OPEN_SPREAD: No expiration date has at least 2 put contracts.")
            return
            
        target_contracts = contracts_by_expiry[target_expiry_date]
        target_expiry_dt = datetime(target_expiry_date.year, target_expiry_date.month, target_expiry_date.day)
        
        # Select short put candidates based on configured mode
        short_put_candidates = []
        if self.short_put_delta_mode == "EXACT":
            self.log(f"TRY_OPEN_SPREAD: Using EXACT delta targeting mode with target {self.short_put_delta_exact}")
            short_put_candidates = [c for c in target_contracts if c.greeks and c.greeks.delta is not None 
                                   and abs(abs(c.greeks.delta) - self.short_put_delta_exact) < 0.05]
        elif self.short_put_delta_mode == "RANGE":
            self.log(f"TRY_OPEN_SPREAD: Using RANGE delta targeting mode with range {self.short_put_delta_min}-{self.short_put_delta_max}")
            short_put_candidates = [c for c in target_contracts if c.greeks and c.greeks.delta is not None 
                                   and self.short_put_delta_min <= abs(c.greeks.delta) <= self.short_put_delta_max]
        else:  # "MAX" mode (default)
            self.log(f"TRY_OPEN_SPREAD: Using MAX delta targeting mode with max {self.short_put_delta_max}")
            short_put_candidates = [c for c in target_contracts if c.greeks and c.greeks.delta is not None 
                                   and abs(c.greeks.delta) <= self.short_put_delta_max]
        
        if not short_put_candidates:
            self.log(f"TRY_OPEN_SPREAD: No suitable short put candidates found with delta criteria.")
            return
            
        # Sort by strike and select highest (from Alert Apricot Duck)
        short_put_candidates.sort(key=lambda x: x.strike, reverse=True)
        short_put = short_put_candidates[0]
        short_put_strike = short_put.strike
        
        self.log(f"TRY_OPEN_SPREAD: Selected short put at strike {short_put_strike} with delta {short_put.greeks.delta:.2f}")
        
        # Calculate target long put strike based on spread width mode
        long_put_strike_target = None
        if self.spread_width_mode == "FIXED":
            long_put_strike_target = short_put_strike - self.spread_width_fixed
            self.log(f"TRY_OPEN_SPREAD: Using FIXED spread width of {self.spread_width_fixed} points")
        elif self.spread_width_mode == "RANGE":
            # Find all available strikes within the acceptable range
            available_strikes = sorted([c.strike for c in target_contracts])
            valid_strikes = [s for s in available_strikes if 
                            (short_put_strike - s) >= self.spread_width_min and 
                            (short_put_strike - s) <= self.spread_width_max]
            if valid_strikes:
                long_put_strike_target = valid_strikes[0]  # Choose the widest valid spread
                self.log(f"TRY_OPEN_SPREAD: Using RANGE spread width between {self.spread_width_min}-{self.spread_width_max} points")
            else:
                self.log(f"TRY_OPEN_SPREAD: No strikes available within spread width range {self.spread_width_min}-{self.spread_width_max}")
                return
        else:  # "DYNAMIC" mode - implement custom logic if needed
            self.log("TRY_OPEN_SPREAD: DYNAMIC spread width mode not implemented yet, using FIXED as fallback")
            long_put_strike_target = short_put_strike - self.spread_width_fixed
            
        # Find contracts with strike closest to target
        contracts_by_strike = {contract.strike: contract for contract in target_contracts}
        
        # Select long put based on configured mode
        long_put = None
        if self.long_put_selection_mode in ["WIDTH", "BOTH"]:
            # Try to find exact strike match first
            if long_put_strike_target in contracts_by_strike:
                long_put = contracts_by_strike[long_put_strike_target]
                self.log(f"TRY_OPEN_SPREAD: Found exact strike match for long put at {long_put_strike_target}")
            else:
                # Find closest available strike
                available_strikes = sorted([s for s in contracts_by_strike.keys() if s < short_put_strike])
                if available_strikes:
                    closest_strike = min(available_strikes, key=lambda s: abs(s - long_put_strike_target))
                    long_put = contracts_by_strike[closest_strike]
                    self.log(f"TRY_OPEN_SPREAD: Using closest available strike {closest_strike} for long put (target was {long_put_strike_target})")
        
        if self.long_put_selection_mode in ["DELTA", "BOTH"] and (long_put is None or self.long_put_selection_mode == "BOTH"):
            # Filter by delta if no exact strike match or if using BOTH mode
            delta_candidates = [c for c in target_contracts if 
                              c.strike < short_put_strike and
                              c.greeks and c.greeks.delta is not None and
                              self.long_put_delta_min <= abs(c.greeks.delta) <= self.long_put_delta_max]
            
            if delta_candidates:
                # If in BOTH mode and we already have a strike-based candidate, choose the one closer to target strike
                if long_put is not None and self.long_put_selection_mode == "BOTH":
                    delta_candidates.append(long_put)
                    delta_candidates.sort(key=lambda c: abs(c.strike - long_put_strike_target))
                    long_put = delta_candidates[0]
                    self.log(f"TRY_OPEN_SPREAD: Selected long put using BOTH criteria, strike: {long_put.strike}, delta: {long_put.greeks.delta:.2f}")
                else:
                    # Sort by delta proximity to midpoint of range
                    delta_target = (self.long_put_delta_min + self.long_put_delta_max) / 2
                    delta_candidates.sort(key=lambda c: abs(abs(c.greeks.delta) - delta_target))
                    long_put = delta_candidates[0]
                    self.log(f"TRY_OPEN_SPREAD: Selected long put using DELTA criteria, strike: {long_put.strike}, delta: {long_put.greeks.delta:.2f}")
        
        if not long_put:
            self.log("TRY_OPEN_SPREAD: No suitable long put found with current selection criteria.")
            return

        # Ensure strikes are different
        if short_put.strike == long_put.strike:
            self.log("TRY_OPEN_SPREAD: Short and long put strikes are the same. Cannot create spread.")
            return

        # Calculate spread width and expected credit
        spread_width = short_put.strike - long_put.strike
        expected_credit = (short_put.bid_price - long_put.ask_price) * 100  # Convert to dollars
        
        self.log(f"TRY_OPEN_SPREAD: Selected short put at strike {short_put.strike}, delta {abs(short_put.greeks.delta):.2f}")
        self.log(f"TRY_OPEN_SPREAD: Selected long put at strike {long_put.strike}, delta {abs(long_put.greeks.delta):.2f}")
        self.log(f"TRY_OPEN_SPREAD: Spread width: {spread_width} points, Expected credit: ${expected_credit:.2f}")
        
        # Check if credit is sufficient
        if expected_credit < self.min_credit_threshold * 100:  # Convert threshold to dollars
            self.log(f"TRY_OPEN_SPREAD: Expected credit ${expected_credit:.2f} below threshold ${self.min_credit_threshold * 100:.2f}. Not opening spread.")
            return

        # Calculate max loss (width - credit) and set stop loss target
        max_loss = (spread_width * 100) - expected_credit
        stop_loss_target = expected_credit * self.stop_loss_multiplier
        self.log(f"TRY_OPEN_SPREAD: Max loss: ${max_loss:.2f}, Stop loss target: ${stop_loss_target:.2f}")

        try:
            # Create the bull put spread strategy (from Alert Apricot Duck)
            bull_put_spread = OptionStrategies.bull_put_spread(
                self.option_symbol,  # Underlying
                short_put.strike,     # Short put strike
                long_put.strike,      # Long put strike
                short_put.expiry      # Expiry date
            )
            
            # Buy the spread (for a bull put spread, buying the strategy means selling the spread)
            self.log("TRY_OPEN_SPREAD: Placing order using OptionStrategies")
            spread_order_tickets = self.buy(bull_put_spread, 1)
            
            if not spread_order_tickets:
                self.log("TRY_OPEN_SPREAD: Failed to place spread order using strategy approach.")
                return
                
            # Track the orders
            if isinstance(spread_order_tickets, list):
                self.opening_order_tickets = spread_order_tickets
            else:
                self.opening_order_tickets = [spread_order_tickets]
                
            self.pending_open = True
            
            # Store the symbols and other trade information
            self.opened_short_put_symbol = short_put.symbol
            self.opened_long_put_symbol = long_put.symbol
            self.spread_width = spread_width
            self.expected_credit = expected_credit / 100  # Store in decimal form
            self.stop_loss_target_debit = stop_loss_target / 100  # Store in decimal form
            self.max_loss = max_loss / 100  # Store in decimal form
            
            self.log(f"TRY_OPEN_SPREAD: Orders placed successfully. Short put: {short_put.symbol.value}, Long put: {long_put.symbol.value}")
            
        except Exception as e:
            self.error(f"TRY_OPEN_SPREAD: Error placing orders: {str(e)}")
            # Attempt to use individual orders as fallback
            try:
                self.log("TRY_OPEN_SPREAD: Strategy approach failed, falling back to individual orders")
                
                # Sell short put (sell to open)
                short_put_order = self.sell(short_put.symbol, 1)
                if not short_put_order:
                    self.log("TRY_OPEN_SPREAD: Failed to place short put order.")
                    return
                    
                # Buy long put (buy to open)
                long_put_order = self.buy(long_put.symbol, 1)
                if not long_put_order:
                    self.log("TRY_OPEN_SPREAD: Failed to place long put order. Attempting to close short put.")
                    self.liquidate(short_put.symbol)  # Clean up the short put if long put order fails
                    return
                    
                # Track the orders
                self.opening_order_tickets = [short_put_order, long_put_order]
                self.pending_open = True
                
                # Store the symbols and other trade information
                self.opened_short_put_symbol = short_put.symbol
                self.opened_long_put_symbol = long_put.symbol
                self.spread_width = spread_width
                self.expected_credit = expected_credit / 100  # Store in decimal form
                self.stop_loss_target_debit = stop_loss_target / 100  # Store in decimal form
                self.max_loss = max_loss / 100  # Store in decimal form
                
                self.log(f"TRY_OPEN_SPREAD: Individual orders placed successfully. Short put: {short_put.symbol.value}, Long put: {long_put.symbol.value}")
                
            except Exception as fallback_error:
                self.error(f"TRY_OPEN_SPREAD: Error placing individual orders: {str(fallback_error)}")
                # Clean up any partial orders
                if short_put.symbol in self.portfolio and self.portfolio[short_put.symbol].invested:
                    self.liquidate(short_put.symbol)
                if long_put.symbol in self.portfolio and self.portfolio[long_put.symbol].invested:
                    self.liquidate(long_put.symbol)

    # ===== COMPONENT: POSITION_MANAGEMENT =====
    # Position management and order execution
    def try_close_spread(self, reason: str = "Unknown") -> None:
        """Attempts to close the current spread position."""
        if not self.spread_is_open:
            self.log(f"TRY_CLOSE_SPREAD ({reason}): No spread is currently open.")
            return
            
        self.log(f"TRY_CLOSE_SPREAD ({reason}): Attempting to close spread...")
        order_ticket = None  # Initialize order_ticket to prevent UnboundLocalError
        if not self.spread_is_open or not self.opened_short_put_symbol or not self.opened_long_put_symbol:
            self.log(f"TRY_CLOSE_SPREAD ({reason}): No open spread with defined legs to close.")
            self.pending_close = False
            return

        self.log(f"TRY_CLOSE_SPREAD ({reason}): Attempting to close spread. Short: {self.opened_short_put_symbol}, Long: {self.opened_long_put_symbol}")
        try:
            # First, try to use the strategy-based approach (from Alert Apricot Duck)
            # This is the preferred method as it ensures proper margin handling
            try:
                # Get strike and expiry from the stored symbols
                short_leg_symbol = self.opened_short_put_symbol
                long_leg_symbol = self.opened_long_put_symbol
                
                # Get strike prices
                short_strike = short_leg_symbol.id.strike_price
                long_strike = long_leg_symbol.id.strike_price
                
                # Get expiry (assuming both legs have the same expiry, which they should for a spread)
                expiry_dt = short_leg_symbol.id.date
                
                # Create the closing spread strategy
                closing_spread_strategy = OptionStrategies.bull_put_spread(
                    self.option_symbol,  # Underlying
                    short_strike,
                    long_strike,
                    expiry_dt  # datetime object
                )
                
                # Submit closing combo order by SELLING the spread
                # (We BUY to open, SELL to close for bull put spread)
                self.log(f"TRY_CLOSE_SPREAD ({reason}): Using strategy-based closure with OptionStrategies")
                closing_orders = self.sell(closing_spread_strategy, 1)
                
                # Track the closing orders
                if closing_orders:
                    if isinstance(closing_orders, list):
                        self.closing_order_tickets.extend(closing_orders)
                    else:
                        self.closing_order_tickets.append(closing_orders)
                    self.log(f"TRY_CLOSE_SPREAD ({reason}): Submitted strategy-based closing order")
                    return
                else:
                    self.log(f"TRY_CLOSE_SPREAD ({reason}): Strategy-based closure failed, falling back to individual leg liquidation")
            except Exception as strategy_error:
                self.error(f"TRY_CLOSE_SPREAD ({reason}): Error during strategy-based closure: {str(strategy_error)}. Falling back to individual leg liquidation.")
            
            # Fallback to individual leg liquidation if strategy-based approach fails
            closed_count = 0
            
            # Liquidate both options positions - check for our specific option symbols
            if self.opened_short_put_symbol in self.portfolio and self.portfolio[self.opened_short_put_symbol].invested:
                security = self.securities[self.opened_short_put_symbol]
                current_ask = security.ask_price
                current_bid = security.bid_price
                
                if current_ask <= 0 or current_bid <= 0:
                    self.log(f"TRY_CLOSE_SPREAD ({reason}): Illiquid quote detected for {self.opened_short_put_symbol.value}. Attempting forced close via MarketOrder.")
                    quantity_to_close = -self.portfolio[self.opened_short_put_symbol].quantity
                    order_ticket = self.market_order(self.opened_short_put_symbol, quantity_to_close)
                else:
                    self.log(f"TRY_CLOSE_SPREAD ({reason}): Liquidating short put: {self.opened_short_put_symbol.value}, Quantity: {self.portfolio[self.opened_short_put_symbol].quantity}")
                    order_ticket = self.liquidate(self.opened_short_put_symbol)
                
                if order_ticket:
                    # Handle both single ticket and list of tickets
                    if isinstance(order_ticket, list):
                        self.closing_order_tickets.extend(order_ticket)
                    else:
                        self.closing_order_tickets.append(order_ticket)
                    closed_count += 1
                    
            if self.opened_long_put_symbol in self.portfolio and self.portfolio[self.opened_long_put_symbol].invested:
                security = self.securities[self.opened_long_put_symbol]
                current_ask = security.ask_price
                current_bid = security.bid_price
                
                if current_ask <= 0 or current_bid <= 0:
                    self.log(f"TRY_CLOSE_SPREAD ({reason}): Illiquid quote detected for {self.opened_long_put_symbol.value}. Attempting forced close via MarketOrder.")
                    quantity_to_close = -self.portfolio[self.opened_long_put_symbol].quantity
                    order_ticket = self.market_order(self.opened_long_put_symbol, quantity_to_close)
                else:
                    self.log(f"TRY_CLOSE_SPREAD ({reason}): Liquidating long put: {self.opened_long_put_symbol.value}, Quantity: {self.portfolio[self.opened_long_put_symbol].quantity}")
                    order_ticket = self.liquidate(self.opened_long_put_symbol)
                
                if order_ticket:
                    # Handle both single ticket and list of tickets
                    if isinstance(order_ticket, list):
                        self.closing_order_tickets.extend(order_ticket)
                    else:
                        self.closing_order_tickets.append(order_ticket)
                    closed_count += 1
            
            if closed_count > 0:
                self.log(f"TRY_CLOSE_SPREAD ({reason}): Submitted liquidation orders for {closed_count} option legs.")
            else:
                self.log(f"TRY_CLOSE_SPREAD ({reason}): No option holdings found to liquidate.")
                self.pending_close = False
                self.reset_spread_state(f"NoOptionsToClose_{reason}")
                return

        except Exception as e:
            self.error(f"TRY_CLOSE_SPREAD ({reason}): Error during spread closure: {str(e)}")
            self.reset_spread_state(f"CloseOrderFail_{reason}")

    # ===== COMPONENT: STATE_MANAGEMENT =====
    # State management and cleanup
    def reset_spread_state(self, reason: str = "Unknown"):
        self.log(f"RESET_SPREAD_STATE ({reason}): Resetting all spread-related state variables.")
        self.spread_is_open = False 
        self.pending_open = False
        self.pending_close = False
        self.initial_credit = None
        self.stop_loss_target_debit = None
        self.profit_target_value_debit = None
        self.opened_short_put_symbol = None
        self.opened_long_put_symbol = None
        
        self.opening_order_tickets.clear()
        self.closing_order_tickets.clear()

    # ===== COMPONENT: PRICING =====
    # Pricing and valuation calculations
    def calculate_current_debit_to_close(self, slice: Slice) -> float:
        """Calculates the current debit required to close the spread."""
        if not self.spread_is_open or not self.opened_short_put_symbol or not self.opened_long_put_symbol:
            self.log("CALC_DEBIT: Spread not open or legs not defined.")
            return None

        try:
            short_put_leg = self.securities[self.opened_short_put_symbol]
            long_put_leg = self.securities[self.opened_long_put_symbol]

            # Get ask/bid prices
            short_put_ask = short_put_leg.ask_price
            long_put_bid = long_put_leg.bid_price
            
            # If ask/bid is zero, try to use the last price as a fallback
            if short_put_ask == 0 and short_put_leg.price != 0:
                short_put_ask = short_put_leg.price
                self.log(f"CALC_DEBIT: Using last price {short_put_ask} for {self.opened_short_put_symbol} as ask is zero")
                
            if long_put_bid == 0 and long_put_leg.price != 0:
                long_put_bid = long_put_leg.price
                self.log(f"CALC_DEBIT: Using last price {long_put_bid} for {self.opened_long_put_symbol} as bid is zero")

            if short_put_ask == 0 or long_put_bid == 0:
                self.log(f"CALC_DEBIT: Market data not ready for {self.opened_short_put_symbol} (Ask: {short_put_ask}) or {self.opened_long_put_symbol} (Bid: {long_put_bid}).") 
                return None
            
            # To close: Buy back short put (pay Ask), Sell long put (receive Bid)
            debit = short_put_ask - long_put_bid
            self.log(f"CALC_DEBIT: Short Put {self.opened_short_put_symbol} Ask: {short_put_ask}, Long Put {self.opened_long_put_symbol} Bid: {long_put_bid}, Debit: {debit:.2f}")
            return debit
        except Exception as e:
            self.error(f"CALC_DEBIT: Error calculating debit to close: {str(e)}")
            return None



    # ===== COMPONENT: ORDER_HANDLING =====
    # Order event processing and tracking
    def on_order_event(self, order_event: OrderEvent) -> None:
        """Handles order events for tracking fill prices and status."""
        self.log(f"ON_ORDER_EVENT: Received event for OrderID {order_event.order_id}. Status: {order_event.status}, Symbol: {order_event.symbol.value}")
        
        # Check if this is an opening order event
        is_opening_order = False
        for ticket in self.opening_order_tickets:
            if hasattr(ticket, 'order_id') and ticket.order_id == order_event.order_id:
                is_opening_order = True
                break
                
        # Check if this is a closing order event
        is_closing_order = False
        for ticket in self.closing_order_tickets:
            if hasattr(ticket, 'order_id') and ticket.order_id == order_event.order_id:
                is_closing_order = True
                break
                
        # If not directly matched but matches our tracked symbols, consider it part of our spread
        if not is_opening_order and not is_closing_order:
            if self.pending_open and not self.spread_is_open and order_event.symbol in [self.opened_short_put_symbol, self.opened_long_put_symbol]:
                is_opening_order = True
            elif self.pending_close and self.spread_is_open and order_event.symbol in [self.opened_short_put_symbol, self.opened_long_put_symbol]:
                is_closing_order = True
                
        # Handle opening orders
        if is_opening_order:
            self.log(f"ON_ORDER_EVENT: Event for opening order. Status: {order_event.status}, Symbol: {order_event.symbol.value}")
            
            if order_event.status == OrderStatus.FILLED:
                # Track fill prices to calculate actual credit received
                if order_event.symbol == self.opened_short_put_symbol:
                    self.short_put_fill_price = order_event.fill_price
                    self.log(f"ON_ORDER_EVENT: Short put filled at {self.short_put_fill_price}")
                elif order_event.symbol == self.opened_long_put_symbol:
                    self.long_put_fill_price = order_event.fill_price
                    self.log(f"ON_ORDER_EVENT: Long put filled at {self.long_put_fill_price}")
                elif hasattr(order_event.symbol, 'underlying_symbol') and order_event.symbol.underlying_symbol == self.equity_symbol:
                    # This might be a combo/strategy order
                    self.log(f"ON_ORDER_EVENT: Strategy order filled for {order_event.symbol.value} at {order_event.fill_price}")
                    
                    # For strategy orders, we'll use the expected credit initially
                    if not hasattr(self, 'initial_credit') or self.initial_credit == 0:
                        self.initial_credit = self.expected_credit
                        self.log(f"ON_ORDER_EVENT: Using expected credit as initial value: ${self.initial_credit:.2f}")
                        
                        # Calculate stop loss target based on initial credit
                        self.stop_loss_target_debit = self.initial_credit * self.stop_loss_multiplier
                        self.log(f"ON_ORDER_EVENT: Stop loss target set to ${self.stop_loss_target_debit:.2f}")
                        
                        # Mark spread as open
                        self.spread_is_open = True
                        self.pending_open = False
                
                # Check if both legs are filled or we have a strategy fill
                if (hasattr(self, 'short_put_fill_price') and hasattr(self, 'long_put_fill_price')) or \
                   (self.spread_is_open and hasattr(self, 'initial_credit')):
                    
                    # If we have individual leg fills, calculate actual credit
                    if hasattr(self, 'short_put_fill_price') and hasattr(self, 'long_put_fill_price'):
                        actual_credit = self.short_put_fill_price - self.long_put_fill_price
                        self.log(f"ON_ORDER_EVENT: Both legs filled. Actual credit received: ${actual_credit:.2f}")
                        
                        # Only update if different from expected
                        if abs(actual_credit - self.initial_credit) > 0.01:
                            self.initial_credit = actual_credit
                            self.log(f"ON_ORDER_EVENT: Updating credit to actual value: ${self.initial_credit:.2f}")
                            
                            # Recalculate targets based on actual credit
                            self.stop_loss_target_debit = self.initial_credit * self.stop_loss_multiplier
                            self.log(f"ON_ORDER_EVENT: Updated stop loss target to ${self.stop_loss_target_debit:.2f}")
                    
                    # Calculate profit target based on initial credit
                    self.profit_target_value_debit = self.initial_credit * (1 - self.profit_target_percentage)
                    self.log(f"ON_ORDER_EVENT: Profit target set to ${self.profit_target_value_debit:.2f}")
                    
                    # Mark spread as open and reset tracking
                    self.spread_is_open = True
                    self.pending_open = False
                    self.opening_order_tickets = []
                    
            elif order_event.status in [OrderStatus.CANCELED, OrderStatus.INVALID]:
                self.log(f"ON_ORDER_EVENT: Opening order failed or canceled: {order_event.status}. Message: {order_event.message}")
                self.pending_open = False
                self.reset_spread_state("OpenOrderFailed")
                
        # Handle closing orders
        elif is_closing_order:
            self.log(f"ON_ORDER_EVENT: Event for closing order. Status: {order_event.status}, Symbol: {order_event.symbol.value}")
            
            if order_event.status == OrderStatus.FILLED:
                self.log(f"ON_ORDER_EVENT: Closing order filled for {order_event.symbol.value} at {order_event.fill_price}")
                
                # For strategy-based orders, track the fill price
                if hasattr(order_event.symbol, 'underlying_symbol') and order_event.symbol.underlying_symbol == self.equity_symbol:
                    self.log(f"ON_ORDER_EVENT: Strategy closing order filled at {order_event.fill_price}")
                    # This is likely a complete fill of the spread
                    self.reset_spread_state("SpreadClosedSuccessfully")
                    return
                
                # Check if all positions are now closed - specifically check our tracked positions
                short_position_closed = self.opened_short_put_symbol not in self.portfolio or not self.portfolio[self.opened_short_put_symbol].invested
                long_position_closed = self.opened_long_put_symbol not in self.portfolio or not self.portfolio[self.opened_long_put_symbol].invested
                
                if short_position_closed and long_position_closed:
                    self.log("ON_ORDER_EVENT: Spread fully closed. All positions are now flat.")
                    self.reset_spread_state("SpreadClosedSuccessfully")
                
            elif order_event.status in [OrderStatus.CANCELED, OrderStatus.INVALID]:
                self.log(f"ON_ORDER_EVENT: Closing order failed or canceled: {order_event.status}. Message: {order_event.message}")
                self.pending_close = False
                self.log("ON_ORDER_EVENT: Will retry closing at next opportunity.")
        
        # Handle exercise/assignment events that weren't matched to our tickets
        elif order_event.is_assignment and order_event.status == OrderStatus.FILLED:
            self.log(f"ON_ORDER_EVENT: Exercise/Assignment detected: {order_event.symbol.value}")
            
            # If this is for our tracked spread, we'll try to close any resulting positions
            if self.spread_is_open and (order_event.symbol == self.opened_short_put_symbol or order_event.symbol == self.opened_long_put_symbol):
                self.log("ON_ORDER_EVENT: Exercise/Assignment happened on our tracked spread. Setting flag to liquidate all positions.")
                self.pending_close = True
                
            # If we're getting assigned on the short put and end up with equity, handle it
            if order_event.symbol == self.equity_symbol and self.portfolio[self.equity_symbol].invested:
                self.log(f"ON_ORDER_EVENT: Holding equity position from assignment: {self.portfolio[self.equity_symbol].quantity} shares")
                self.liquidate(self.equity_symbol) # Immediately liquidate any equity position
        
        # Any other untracked orders
        else:
            self.log(f"ON_ORDER_EVENT: Received event for untracked OrderID {order_event.order_id}. Status: {order_event.status}")

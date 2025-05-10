from AlgorithmImports import *

class Basic_Credit_SpreadAlgorithm(QCAlgorithm):
    def initialize(self):
        """Initialize algorithm parameters, data subscriptions, and scheduling."""
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)

        # Add equity and options
        equity = self.add_equity("SPY", Resolution.MINUTE)
        self.equity_symbol = equity.Symbol
        
        option = self.add_option("SPY", Resolution.MINUTE)
        # Filter for 0-DTE options only - we need to include all options and filter in on_data
        option.set_filter(lambda u: u.include_weeklys()
                                     .strikes(-20, +20)
                                     .expiration(0, 30))  # Wider filter to ensure we get data
        self.option_symbol = option.Symbol
        
        # Set benchmark
        self.set_benchmark(self.equity_symbol)

        # Track active spread position
        self.spread_open = False
        self.spread_orders = []
        self.pending_open = False
        self.pending_close = False

        # Schedule algorithm entry points at specific times
        # Enter at 10:00 AM ET
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(10, 0), 
                         self.open_trades)
        # Exit at 3:00 PM ET
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(15, 0), 
                         self.close_positions)

    def open_trades(self):
        """Set flag to open a bull put credit spread at 10:00 AM ET"""
        if self.spread_open:
            self.debug("Spread already open, skipping")
            return
            
        # We need to wait for the next data slice to get the option chain
        self.debug("Setting flag to open trades on next data slice")
        self.pending_open = True

    def close_positions(self):
        """Set flag to close the bull put spread at 3:00 PM ET"""
        if not self.spread_open:
            self.debug("No spread position open to close")
            return

        # We need to wait for the next data slice
        self.debug("Setting flag to close positions on next data slice")
        self.pending_close = True

    def on_data(self, slice):
        """Process option data and execute trades based on scheduled flags"""
        # Check if we need to open a new position
        if self.pending_open:
            self.try_open_spread(slice)
            self.pending_open = False
            
        # Check if we need to close positions
        if self.pending_close:
            self.try_close_spread()
            self.pending_close = False
    
    def try_open_spread(self, slice):
        """Attempt to open a bull put credit spread using option chain data"""
        # Check if we have option chain data
        if not self.option_symbol in slice.option_chains:
            self.debug("No option chain data available")
            return
            
        chain = slice.option_chains[self.option_symbol]
        if not chain:
            self.debug("Empty option chain")
            return
        
        # Get current date and find options expiring today (0-DTE)
        current_date = self.time.date()
        self.debug(f"Current date: {current_date}")
        
        # Filter for put options expiring today (0-DTE)
        puts = [x for x in chain if x.right == OptionRight.PUT and x.expiry.date() == current_date]
        
        if not puts:
            self.debug(f"No 0-DTE put options available for today ({current_date})")
            # Log all available expiration dates to help debug
            all_expiries = sorted(list(set([x.expiry.date() for x in chain])))
            self.debug(f"Available expiration dates: {all_expiries}")
            return

        # Get current price of underlying
        underlying_price = self.securities[self.equity_symbol].price
        self.debug(f"Current SPY price: {underlying_price}")

        # Get all available strikes for today's expiration
        available_strikes = sorted(list(set([x.strike for x in puts])))
        self.debug(f"Available strikes: {available_strikes[:5]}... (showing first 5)")
        
        if len(available_strikes) < 2:
            self.debug("Not enough strikes available")
            return

        # Find strikes for bull put spread (below current price)
        # We want OTM puts for a bull put spread
        otm_strikes = [strike for strike in available_strikes if strike < underlying_price]
        
        if len(otm_strikes) < 2:
            self.debug("Not enough OTM strikes available")
            # Try to use strikes closer to ATM if not enough OTM strikes
            all_strikes_sorted = sorted(available_strikes)
            if len(all_strikes_sorted) >= 2:
                # Use the two lowest strikes available
                long_strike = all_strikes_sorted[0]
                short_strike = all_strikes_sorted[1]
                self.debug(f"Using closest available strikes: Short {short_strike}, Long {long_strike}")
            else:
                return
        else:
            # Ideally we want strikes that are 1-5% OTM
            # Short put (higher strike, closer to ATM)
            short_strike_candidates = [s for s in otm_strikes if s >= underlying_price * 0.95]
            # Long put (lower strike, further OTM)
            long_strike_candidates = [s for s in otm_strikes if s < underlying_price * 0.95]
            
            if short_strike_candidates and long_strike_candidates:
                short_strike = max(short_strike_candidates)  # Highest of the short candidates (closest to ATM)
                long_strike = max(long_strike_candidates)    # Highest of the long candidates (closest to short)
            elif len(otm_strikes) >= 2:
                # If we can't find ideal strikes, just use the two highest OTM strikes
                otm_strikes_sorted = sorted(otm_strikes, reverse=True)
                short_strike = otm_strikes_sorted[0]  # Highest OTM strike (closest to ATM)
                long_strike = otm_strikes_sorted[1]   # Second highest OTM strike
            else:
                self.debug("Could not find appropriate strikes for spread")
                return

        # Find the specific option contracts
        short_put = None
        long_put = None
        expiry = current_date  # We already filtered for today's expiration

        for put in puts:
            if abs(put.strike - short_strike) < 0.001 and put.expiry.date() == current_date:
                short_put = put.symbol
            elif abs(put.strike - long_strike) < 0.001 and put.expiry.date() == current_date:
                long_put = put.symbol

        if not short_put or not long_put:
            self.debug(f"Could not find specific option contracts for strikes {short_strike} and {long_strike}")
            return

        # Create bull put spread (sell higher strike put, buy lower strike put)
        self.debug(f"Creating bull put spread: Short {short_strike} Put, Long {long_strike} Put")
        
        # Place the orders as a spread
        self.spread_orders = [
            self.sell(short_put, 1),  # Sell to open short put
            self.buy(long_put, 1)     # Buy to open long put
        ]
        
        self.spread_open = True
        
    def try_close_spread(self):
        """Close any open option positions"""
        # Close any open positions
        has_positions = False
        
        # First check if we have any positions
        for kvp in self.portfolio:
            holding = kvp.Value
            if holding.invested and holding.type == SecurityType.OPTION:
                has_positions = True
                break
                
        if not has_positions:
            self.debug("No positions to close")
            self.spread_open = False
            self.spread_orders = []
            return
            
        self.debug("Closing open option positions")
        for kvp in self.portfolio:
            holding = kvp.Value
            if holding.invested and holding.type == SecurityType.OPTION:
                symbol = holding.symbol
                quantity = holding.quantity
                if quantity > 0:  # Long position
                    self.sell(symbol, abs(quantity))
                    self.debug(f"Closing long position in {symbol}")
                elif quantity < 0:  # Short position
                    self.buy(symbol, abs(quantity))
                    self.debug(f"Closing short position in {symbol}")

        self.spread_open = False
        self.spread_orders = []

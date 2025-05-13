from AlgorithmImports import *

class Basic_Credit_SpreadAlgorithm(QCAlgorithm):

    def initialize(self) -> None:
        """Initialize algorithm parameters, data subscriptions, and scheduling."""
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 3, 31)
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
        self.schedule.on(self.date_rules.every_day(self.equity_symbol), 
                         self.time_rules.at(10, 0), 
                         self.open_trades)
        # Exit 15 mins before close
        self.schedule.on(self.date_rules.every_day(self.equity_symbol), 
                         self.time_rules.before_market_close(self.option_symbol, 15), 
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
        
        # Get current price of underlying
        underlying_price = self.securities[self.equity_symbol].price
        self.debug(f"Current SPY price: {underlying_price}")
        
        # Step 1: Find all put options expiring today
        puts = [x for x in chain if x.right == OptionRight.PUT]
        
        # Step 2: Group contracts by expiration date
        contracts_by_expiry = {}
        for put in puts:
            expiry_date = put.expiry.date()
            if expiry_date not in contracts_by_expiry:
                contracts_by_expiry[expiry_date] = []
            contracts_by_expiry[expiry_date].append(put)
        
        # Step 3: Prioritize today's expiration (0-DTE)
        if current_date in contracts_by_expiry and len(contracts_by_expiry[current_date]) >= 2:
            self.debug(f"Found {len(contracts_by_expiry[current_date])} put contracts expiring today")
            target_expiry = current_date
            target_contracts = contracts_by_expiry[current_date]
        else:
            # If no 0-DTE options, find the nearest expiration with at least 2 contracts
            available_expiries = sorted(contracts_by_expiry.keys())
            if not available_expiries:
                self.debug("No put options available in the chain")
                return
                
            self.debug(f"No 0-DTE options available. Available expirations: {available_expiries}")
            
            # Find the nearest expiration with at least 2 contracts
            target_expiry = None
            for expiry in available_expiries:
                if len(contracts_by_expiry[expiry]) >= 2:
                    target_expiry = expiry
                    break
                    
            if target_expiry is None:
                self.debug("No expiration date has at least 2 put contracts")
                return
                
            target_contracts = contracts_by_expiry[target_expiry]
            self.debug(f"Using expiration date {target_expiry} with {len(target_contracts)} contracts")
        
        # Step 4: Find valid strikes for bull put spread (short_strike > long_strike)
        # Group contracts by strike
        contracts_by_strike = {}
        for contract in target_contracts:
            contracts_by_strike[contract.strike] = contract
        
        # Get all available strikes, sorted ascending
        available_strikes = sorted(contracts_by_strike.keys())
        self.debug(f"Available strikes for {target_expiry}: {available_strikes}")
        
        if len(available_strikes) < 2: # Need at least two strikes to form a spread
            self.debug("Not enough distinct strikes available for this expiration to form a spread.")
            return
        
        # NEW Step 5: Select Short Put based on Delta criteria
        self.debug(f"Filtering {len(target_contracts)} contracts for {target_expiry} to find short put candidate based on delta...")
        short_put_candidates = []
        for contract in target_contracts: # target_contracts are already puts for the target_expiry
            if contract.greeks and contract.greeks.delta is not None:
                delta = contract.greeks.delta
                # User requirement: short put absolute delta <= 0.30
                if abs(delta) <= 0.30:
                    short_put_candidates.append(contract)
                    self.debug(f"  Delta Candidate (Short): {contract.symbol.value}, Strike: {contract.strike}, Delta: {delta:.4f}")
            else:
                self.debug(f"  Skipping {contract.symbol.value} (Strike: {contract.strike}) for short put selection due to missing Greeks/Delta.")

        if not short_put_candidates:
            self.debug(f"No suitable short put candidates found with abs(delta) <= 0.30 for {target_expiry}.")
            return

        # Sort candidates by strike price, highest strike first (to pick the one closest to ATM or most OTM that fits delta)
        short_put_candidates.sort(key=lambda x: x.strike, reverse=True)
        
        selected_short_put_contract = short_put_candidates[0] # Take the one with the highest strike
        short_put_strike = selected_short_put_contract.strike
        self.debug(f"Selected Short Put: {selected_short_put_contract.symbol.value}, Strike: {short_put_strike}, Delta: {selected_short_put_contract.greeks.delta:.4f}")

        # NEW Step 5b: Select Long Put (next strike below selected short_put_strike)
        long_put_strike = None
        try:
            # available_strikes is sorted ascending. Find index of short_put_strike.
            short_strike_index_in_list = available_strikes.index(short_put_strike)
            if short_strike_index_in_list > 0: # Ensure there is a strike at a lower index (i.e., a smaller strike)
                long_put_strike = available_strikes[short_strike_index_in_list - 1]
            else:
                self.debug(f"Short put strike {short_put_strike} is the lowest available strike for {target_expiry}. Cannot form spread with a leg below it.")
                return
        except ValueError: 
            self.debug(f"Critical error: Selected short put strike {short_put_strike} not found in available_strikes list. Aborting.")
            return

        if long_put_strike is None: # Should generally be caught by index check, but as a safeguard
            self.debug(f"Could not determine a suitable long put strike below short put strike {short_put_strike}.")
            return
        
        selected_long_put_contract = contracts_by_strike.get(long_put_strike)
        if not selected_long_put_contract: # Should not happen if long_put_strike came from available_strikes
            self.debug(f"Failed to retrieve contract for determined long_put_strike: {long_put_strike} from contracts_by_strike. Aborting.")
            return
            
        self.debug(f"Selected Long Put: {selected_long_put_contract.symbol.value}, Strike: {long_put_strike}" +
                   (f", Delta: {selected_long_put_contract.greeks.delta:.4f}" if selected_long_put_contract.greeks and selected_long_put_contract.greeks.delta is not None else ", Delta: N/A"))

        # Step 6: Final validation checks
        # Assign to variables used by OptionStrategies and for existing validation
        short_put = selected_short_put_contract
        long_put = selected_long_put_contract
        
        # Verify short_strike > long_strike (this is inherent in our selection of long_put_strike)
        if short_put.strike <= long_put.strike: # Should ideally never be true with new logic but good failsafe
            self.debug(f"Invalid strike configuration from delta selection: short_strike ({short_put.strike}) must be > long_strike ({long_put.strike})")
            return
            
        # Get the actual contracts
        short_put = selected_short_put_contract
        long_put = selected_long_put_contract
        
        # Verify both contracts have the same expiration
        if short_put.expiry != long_put.expiry:
            self.debug(f"Contract expirations don't match: {short_put.expiry} vs {long_put.expiry}")
            return
            
        # Step 7: Create the bull put spread
        self.debug(f"Creating bull put spread with verified contracts:")
        self.debug(f"Short Put: Strike={short_put.strike}, Expiry={short_put.expiry}")
        self.debug(f"Long Put: Strike={long_put.strike}, Expiry={long_put.expiry}")
        
        try:
            # Create the bull put spread using OptionStrategies
            # For bull put spread: short_strike MUST be > long_strike
            bull_put_spread = OptionStrategies.bull_put_spread(
                self.option_symbol,  # Option symbol
                short_put.strike,     # Higher strike (short put)
                long_put.strike,      # Lower strike (long put)
                short_put.expiry      # Expiration date (same for both)
            )
            
            # Execute the spread order
            self.spread_orders = [self.buy(bull_put_spread, 1)]
            self.debug("Successfully created bull put spread order")
            self.spread_open = True
        except Exception as e:
            self.error(f"Failed to create bull put spread: {str(e)}")
            return
        
    def try_close_spread(self):
        """Close any open option positions using the OptionStrategies approach"""
        # Check if we have any positions
        has_positions = False
        
        # First check if we have any positions
        for kvp in self.portfolio:
            holding = kvp.value
            if holding.invested and holding.type == SecurityType.OPTION:
                has_positions = True
                break
                
        if not has_positions:
            self.debug("No positions to close")
            self.spread_open = False
            self.spread_orders = []
            return
        
        # Find our current bull put spread details
        short_put_symbol = None
        long_put_symbol = None
        short_put_strike = None
        long_put_strike = None
        expiry = None
        
        # Identify the short and long put legs of our spread
        for kvp in self.portfolio:
            holding = kvp.value
            if holding.invested and holding.type == SecurityType.OPTION:
                symbol = holding.symbol
                if symbol.id.option_right == OptionRight.PUT: # Access via symbol.id
                    if holding.quantity < 0:  # Short position
                        short_put_symbol = symbol
                        short_put_strike = symbol.id.strike_price # Access via symbol.id
                        expiry = symbol.id.date # Access via symbol.id, expiry is 'date'
                        self.debug(f"Found short put: {short_put_symbol} Strike: {short_put_strike}")
                    elif holding.quantity > 0:  # Long position
                        long_put_symbol = symbol
                        long_put_strike = symbol.id.strike_price # Access via symbol.id
                        self.debug(f"Found long put: {long_put_symbol} Strike: {long_put_strike}")
        
        # If we found both legs of the spread and they have the same expiry
        if short_put_symbol and long_put_symbol and expiry and short_put_symbol.id.date == long_put_symbol.id.date:
            self.debug(f"Closing bull put spread: Short {short_put_strike} Put, Long {long_put_strike} Put, Expiry {expiry}")
            
            try:
                # Create the same bull put spread strategy
                bull_put_spread = OptionStrategies.bull_put_spread(
                    self.option_symbol,
                    short_put_strike,  # Higher strike (short put)
                    long_put_strike,   # Lower strike (long put)
                    expiry             # Expiration date
                )
                
                # Sell the strategy (opposite of buy when we opened it)
                self.debug("Using OptionStrategies to close the spread")
                close_orders = self.sell(bull_put_spread, 1)
                self.debug("Successfully created close order for bull put spread")
            except Exception as e:
                self.error(f"Error closing bull put spread with OptionStrategies: {str(e)}")
                self.debug("Falling back to closing individual legs")
                
                # Fall back to closing individual legs if the strategy approach fails
                if short_put_symbol:
                    self.buy(short_put_symbol, abs(self.portfolio[short_put_symbol].quantity))
                    self.debug(f"Closing short position in {short_put_symbol}")
                    
                if long_put_symbol:
                    self.sell(long_put_symbol, abs(self.portfolio[long_put_symbol].quantity))
                    self.debug(f"Closing long position in {long_put_symbol}")
        else:
            # Fall back to closing individual positions if we couldn't identify the spread
            self.debug("Could not identify complete bull put spread, closing individual positions")
            for kvp in self.portfolio:
                holding = kvp.value
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

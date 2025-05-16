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

        # MODIFIED Step 5b: Select Long Put to achieve a $5 spread width
        long_put_strike_target = short_put_strike - 5.0  # Target a $5 wider spread
        long_put_strike = None # Initialize

        if long_put_strike_target in available_strikes:
            long_put_strike = long_put_strike_target
            self.debug(f"Targeting long put strike ${long_put_strike_target:.2f} for a $5 spread from short strike ${short_put_strike:.2f}.")
        else:
            # Log available strikes if the target $5 spread isn't possible
            available_strikes_str_preview = ", ".join(map(str, available_strikes[:5])) + ("..." if len(available_strikes) > 5 else "")
            self.debug(f"Could not find desired long put strike ${long_put_strike_target:.2f} (for a $5 spread from ${short_put_strike:.2f}) " +
                       f"for expiry {selected_short_put_contract.expiry.strftime('%Y-%m-%d')}. " +
                       f"Available strikes near short strike (sorted): {available_strikes_str_preview}. Skipping trade.")
            return
        
        selected_long_put_contract = contracts_by_strike.get(long_put_strike)
        if not selected_long_put_contract:
            self.debug(f"CRITICAL: Failed to retrieve contract for determined long_put_strike: {long_put_strike} from contracts_by_strike, " +
                       "even though it was found in available_strikes. This indicates an inconsistency. Aborting trade.")
            return
            
        self.debug(f"Selected Long Put: {selected_long_put_contract.symbol.value}, Strike: {long_put_strike}" +
                   (f", Delta: {selected_long_put_contract.greeks.delta:.4f}" if selected_long_put_contract.greeks and selected_long_put_contract.greeks.delta is not None else ", Delta: N/A"))

        # Step 6: Final validation checks
        # Assign to variables used by OptionStrategies and for existing validation
        short_put = selected_short_put_contract
        long_put = selected_long_put_contract
        
        # Verify short_strike > long_strike (this is inherent in our selection of long_put_strike)
        if short_put.strike <= long_put.strike: # Should ideally never be true with new logic but good failsafe
            self.debug(f"Short put strike {short_put.strike} is not greater than long put strike {long_put.strike}. Skipping trade.")
            return

        # Ensure we have both contracts (should always be true by now)
        if not short_put or not long_put:
            self.debug("Missing either short or long put contract. This should not happen. Skipping trade.")
            return

        # Step 7: Construct and place the Bull Put Spread order using OptionStrategies
        self.debug(f"Attempting to open Bull Put Spread: Short {short_put.symbol.value} (Strike {short_put.strike}), Long {long_put.symbol.value} (Strike {long_put.strike})")
        
        bull_put_spread = OptionStrategies.bull_put_spread(self.option_symbol, short_put.strike, long_put.strike, target_expiry)
        
        # Calculate initial credit (premium) for the spread
        short_put_price = self.securities[short_put.symbol].price
        long_put_price = self.securities[long_put.symbol].price
        initial_credit = short_put_price - long_put_price
        self.debug(f"  Short Put ({short_put.symbol.value}) Price: ${short_put_price:.2f}")
        self.debug(f"  Long Put ({long_put.symbol.value}) Price: ${long_put_price:.2f}")
        self.debug(f"  Calculated Initial Credit: ${initial_credit:.2f}")

        # Check if calculated credit is positive (meaning we receive money)
        if initial_credit <= 0:
            self.debug(f"  Initial credit ${initial_credit:.2f} is not positive. Skipping trade to avoid debit spread.")
            return

        # Set order properties for asynchronous handling
        # order_properties = AsyncOrderProperties(TimeInForce.Day)

        self.spread_orders = self.buy(bull_put_spread, 1) #, asynchronous=True, order_properties=order_properties)
        self.spread_open = True
        self.debug(f"Submitted Bull Put Spread order. Short Put: {short_put.symbol.value}, Long Put: {long_put.symbol.value}. Order IDs: {[o.id for o in self.spread_orders]}")

    def try_close_spread(self):
        """Attempt to close the active bull put spread position"""
        if not self.spread_open or not self.spread_orders:
            self.debug("No open spread or spread orders to close.")
            return

        self.debug(f"Attempting to close spread. Current orders: {[o.id for o in self.spread_orders]}")
        
        # Liquidate each leg of the spread
        # IMPORTANT: This iterates through the original order IDs. If legs fill separately, 
        # portfolio may show individual option holdings. We need to liquidate based on current holdings.
        
        closed_count = 0
        for holding in self.portfolio.values:
            if holding.type == SecurityType.OPTION and holding.symbol.canonical == self.option_symbol and holding.invested:
                self.debug(f"Liquidating option position: {holding.symbol.value}, Quantity: {holding.quantity}")
                self.liquidate(holding.symbol)
                closed_count +=1

        if closed_count > 0:
            self.debug(f"Submitted liquidation orders for {closed_count} option legs.")
        else:
            self.debug("No option holdings found to liquidate for the spread.")

        self.spread_open = False
        self.spread_orders = [] # Clear order IDs after attempting to close
        self.debug("Spread position marked as closed.")

    def on_order_event(self, order_event: OrderEvent):
        """Handle order events for tracking and debugging"""
        self.debug(f"Order Event: {order_event}")
        if order_event.status == OrderStatus.FILLED:
            order = self.transactions.get_order_by_id(order_event.order_id)
            fill_price = order_event.fill_price
            fill_quantity = order_event.fill_quantity
            direction = "Bought" if fill_quantity > 0 else "Sold"
            self.debug(f"  Filled: {direction} {abs(fill_quantity)} contracts of {order.symbol} at ${fill_price:.2f}")
            
            # If it's part of the spread opening
            if any(o.id == order_event.order_id for o in self.spread_orders if self.pending_open): # Check pending_open to ensure this is opening leg
                # Check if all legs of the spread are filled to confirm spread is fully open
                # This simplified logic assumes two legs for the spread
                filled_legs = 0
                for parent_order in self.spread_orders:
                    if self.transactions.get_order_by_id(parent_order.id).status == OrderStatus.FILLED:
                        filled_legs +=1
                
                if filled_legs == len(self.spread_orders):
                    self.debug("All legs of the spread have been filled. Spread is now fully open.")
                    # self.pending_open = False # Already set in on_data, but good for clarity
                else:
                    self.debug(f"{filled_legs}/{len(self.spread_orders)} legs filled for opening spread.")
        
        elif order_event.status == OrderStatus.CANCELED:
            self.debug(f"  Order Canceled: {order_event.order_id}")
            # If an order to open a spread is canceled, reset flags
            if any(o.id == order_event.order_id for o in self.spread_orders):
                self.debug("A spread order was canceled. Resetting spread_open flag.")
                self.spread_open = False
                self.spread_orders = []
                # self.pending_open = False # Already set in on_data, but good for clarity
        
        elif order_event.status == OrderStatus.INVALID:
            self.debug(f"  Order Invalid: {order_event.order_id} - Message: {order_event.message}")
            if any(o.id == order_event.order_id for o in self.spread_orders):
                self.debug("An invalid order occurred for the spread. Resetting spread_open flag.")
                self.spread_open = False
                self.spread_orders = []
                # self.pending_open = False # Already set in on_data

        # elif order_event.status == OrderStatus.SUBMITTED:
        #     self.debug(f"  Order Submitted: {order_event.order_id}")
        # elif order_event.status == OrderStatus.PARTIALLY_FILLED:
        #     self.debug(f"  Order Partially Filled: {order_event.order_id}")

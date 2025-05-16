from AlgorithmImports import *
from datetime import datetime # Ensure datetime is imported

class Basic_Credit_SpreadAlgorithm(QCAlgorithm):
    def initialize(self) -> None:
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 3, 1) 
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)

        self.equity_symbol = self.add_equity("SPY", Resolution.MINUTE).symbol
        option = self.add_option("SPY", resolution=Resolution.MINUTE)
        option.set_filter(lambda u: u.include_weeklys().expiration(0, 30)) # Filter for options expiring within 0 to 30 days
        self.option_symbol = option.symbol
        self.set_benchmark(self.equity_symbol)

        # Algorithm parameters
        self.min_credit_threshold = 0.10  # Minimum credit to receive for opening a spread
        self.stop_loss_multiplier = 2.0  # Stop loss if debit to close is 2x initial credit
        self.profit_target_percentage = 0.50 # Target 50% of max profit (initial credit)

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
            self.date_rules.every_day(self.equity_symbol),
            self.time_rules.at(10, 0),
            self.open_trades
        )
        self.schedule.on(
            self.date_rules.every_day(self.option_symbol),
            self.time_rules.before_market_close(self.option_symbol, 15),
            self.close_positions
        ) 

    def open_trades(self) -> None:
        if self.spread_is_open:
            self.log("Spread already open, skipping")
            return
        self.log("Setting flag to open trades on next data slice")
        self.pending_open = True

    def close_positions(self) -> None:
        if not self.spread_is_open:
            self.log("No spread position open to close")
            return
        self.log("Setting flag to close positions on next data slice")
        self.pending_close = True

    def on_data(self, slice: Slice) -> None:
        # First, handle pending open if not already open
        if self.pending_open and not self.spread_is_open:
            self.log("ON_DATA: Opening trade initiated")
            self.try_open_spread(slice)
            self.pending_open = False  # Reset flag regardless of success
            return  # Exit to avoid checking other conditions in the same bar
            
        # Then, handle pending close if spread is open
        if self.pending_close and self.spread_is_open:
            self.log("ON_DATA: EOD close initiated")
            self.try_close_spread("EOD")
            return  # Exit to avoid checking other conditions in the same bar
            
        # Check stop loss first (dedicated method for reliability)
        if self.spread_is_open and not self.pending_close:
            self.check_stop_loss(slice)
            if self.pending_close:  # If stop loss triggered, skip profit check
                return
            
        # Finally, if spread is open and no pending close, monitor for take-profit
        if self.spread_is_open and not self.pending_close:
            self.log("ON_DATA: Checking profit target")
            self.monitor_profit_target(slice)
            
    def check_stop_loss(self, slice: Slice) -> None:
        """Dedicated method to check if stop loss has been hit"""
        if not self.spread_is_open or not self.initial_credit or not self.opened_short_put_symbol or not self.opened_long_put_symbol:
            return  # Not fully set up
            
        try:
            # Get current security data
            short_put_security = self.securities[self.opened_short_put_symbol]
            long_put_security = self.securities[self.opened_long_put_symbol]
            
            # Get ask/bid prices with fallbacks
            short_put_ask = short_put_security.ask_price
            long_put_bid = long_put_security.bid_price
            
            # Fallback to price if ask/bid is zero
            if short_put_ask == 0 and short_put_security.price != 0: 
                short_put_ask = short_put_security.price
            if long_put_bid == 0 and long_put_security.price != 0: 
                long_put_bid = long_put_security.price
                
            # Skip calculation if we still have zero prices
            if short_put_ask == 0 or long_put_bid == 0:
                self.log(f"STOP_LOSS_CHECK: Market data unavailable or zero. Short Ask: {short_put_ask}, Long Bid: {long_put_bid}")
                return
                
            # Calculate current debit to close
            current_debit = short_put_ask - long_put_bid
            
            # Log the check (only when values are available)
            self.log(f"STOP_LOSS_CHECK: Current debit: ${current_debit:.2f}, Stop loss: ${self.stop_loss_target_debit:.2f}")
            
            # Check if stop loss is hit
            if current_debit >= self.stop_loss_target_debit:
                self.log(f"STOP LOSS HIT: Current debit ${current_debit:.2f} >= Target ${self.stop_loss_target_debit:.2f}")
                self.pending_close = True
                self.try_close_spread("StopLoss")
        except Exception as e:
            self.error(f"Error in check_stop_loss: {str(e)}")
            
    def monitor_profit_target(self, slice: Slice) -> None:
        """Monitors an open spread for profit target"""
        if not self.spread_is_open or not self.initial_credit:
            return
            
        try:
            current_debit = self.calculate_current_debit_to_close(slice)
            if current_debit is None:
                return
                
            self.log(f"MONITOR: Current debit: ${current_debit:.2f}, Profit target: ${self.profit_target_value_debit:.2f}")
            
            # Take profit check
            if current_debit <= self.profit_target_value_debit:
                self.log(f"PROFIT TARGET HIT: Current debit ${current_debit:.2f} <= Target ${self.profit_target_value_debit:.2f}")
                self.pending_close = True
                self.try_close_spread("ProfitTarget")
        except Exception as e:
            self.error(f"Error in monitor_profit_target: {str(e)}")

    def try_open_spread(self, slice: Slice) -> None:
        """Attempts to open a bull put spread if conditions are met."""
        self.log(f"TRY_OPEN_SPREAD: Attempting to open spread. Current Time: {self.time}")
        
        chain = slice.option_chains.get(self.option_symbol)
        if not chain:
            self.log("TRY_OPEN_SPREAD: No option chain found for SPY.")
            return

        # Select puts, filter OTM, sort by closest to 0.3 delta for short, 0.1-0.15 for long
        otm_puts = [c for c in chain if c.right == OptionRight.PUT and c.strike < chain.underlying.price]
        if not otm_puts:
            self.log("TRY_OPEN_SPREAD: No OTM puts found.")
            return

        # Sort by expiry (closest first), then by delta difference for short, then by strike for long
        sorted_contracts = sorted(otm_puts, key=lambda c: (c.expiry, abs(abs(c.greeks.delta) - 0.3)))
        
        short_put = None
        for contract in sorted_contracts:
            delta = abs(contract.greeks.delta)
            if 0.25 <= delta <= 0.35: # Target delta for short put
                short_put = contract
                break
        
        if not short_put:
            self.log("TRY_OPEN_SPREAD: No suitable short put found (delta 0.25-0.35).")
            return

        # Select long put: same expiry, lower strike, delta ~0.1-0.15, strike difference 1-5 points
        long_candidates = [c for c in otm_puts if c.expiry == short_put.expiry and 
                                                c.strike < short_put.strike and 
                                                (short_put.strike - c.strike) >= 1 and 
                                                (short_put.strike - c.strike) <= 15] # Max spread width
        
        long_put = None
        if long_candidates:
            sorted_long_candidates = sorted(long_candidates, key=lambda c: abs(abs(c.greeks.delta) - 0.15))
            for lc in sorted_long_candidates:
                if 0.1 <= abs(lc.greeks.delta) <= 0.20: # Wider delta range for long, prioritize closer to 0.15
                    long_put = lc
                    break
        
        if not long_put:
            self.log("TRY_OPEN_SPREAD: No suitable long put found (delta 0.1-0.2, lower strike, same expiry).")
            return

        # Ensure strikes are different
        if short_put.strike == long_put.strike:
            self.log("TRY_OPEN_SPREAD: Short and Long put strikes are the same. Skipping.")
            return

        # Calculate estimated credit. Short Put Bid - Long Put Ask.
        estimated_credit = short_put.bid_price - long_put.ask_price
        self.log(f"TRY_OPEN_SPREAD: Short Put {short_put.symbol.value} (Delta: {short_put.greeks.delta:.2f}, Bid: {short_put.bid_price}) Long Put {long_put.symbol.value} (Delta: {long_put.greeks.delta:.2f}, Ask: {long_put.ask_price}). Est. Credit: {estimated_credit:.2f}")

        if estimated_credit < self.min_credit_threshold:
            self.log(f"TRY_OPEN_SPREAD: Estimated credit ${estimated_credit:.2f} is less than minimum threshold ${self.min_credit_threshold:.2f}. Skipping.")
            return

        self.opened_short_put_symbol = short_put.symbol
        self.opened_long_put_symbol = long_put.symbol

        # Create the bull put spread strategy
        bull_put_spread_strategy = OptionStrategies.bull_put_spread(self.option_symbol, short_put.strike, long_put.strike, short_put.expiry)
        quantity = 1 

        # CRITICAL: For bull put credit spread, we BUY the strategy to open the position
        # This seems counter-intuitive, but the OptionStrategies.bull_put_spread defines a short put and long put
        # When we BUY this strategy, we're buying the defined structure (selling the short put and buying the long put)
        order_ticket = self.buy(bull_put_spread_strategy, quantity) 

        if order_ticket: 
            # Make sure we're storing a list of OrderTicket objects
            if isinstance(order_ticket, list):
                self.opening_order_tickets.extend(order_ticket)
            else:
                self.opening_order_tickets.append(order_ticket)
            self.log(f"Submitted Bull Put Spread. Short: {short_put.symbol.value}, Long: {long_put.symbol.value}, Est. Credit: ${estimated_credit:.2f}, Qty: {quantity}. Ticket ID: {order_ticket.order_id if not isinstance(order_ticket, list) else [t.order_id for t in order_ticket]}")
        else:
            self.log(f"Failed to submit Bull Put Spread. No order tickets returned.")
            self.opened_short_put_symbol = None 
            self.opened_long_put_symbol = None

    def try_close_spread(self, reason: str = "Unknown") -> None:
        if not self.spread_is_open or not self.opened_short_put_symbol or not self.opened_long_put_symbol:
            self.log(f"TRY_CLOSE_SPREAD ({reason}): No open spread with defined legs to close.")
            self.pending_close = False
            return

        self.log(f"TRY_CLOSE_SPREAD ({reason}): Attempting to close spread. Short: {self.opened_short_put_symbol}, Long: {self.opened_long_put_symbol}")
        try:
            closed_count = 0
            # Liquidate both options positions - check for our specific option symbols
            if self.opened_short_put_symbol in self.portfolio and self.portfolio[self.opened_short_put_symbol].invested:
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



    def on_order_event(self, order_event: OrderEvent) -> None:
        self.log(f"ON_ORDER_EVENT: {order_event}")
        
        # Check if this is part of a strategy order (need to check for both parent and child orders)
        found_in_opening_tickets = False
        found_in_closing_tickets = False
        opening_ticket = None
        closing_ticket = None
        
        # Check if this is directly one of our tickets
        for ticket in self.opening_order_tickets:
            # Make sure ticket is an OrderTicket object before accessing order_id
            if hasattr(ticket, 'order_id') and ticket.order_id == order_event.order_id:
                found_in_opening_tickets = True
                opening_ticket = ticket
                break
                
        for ticket in self.closing_order_tickets:
            # Make sure ticket is an OrderTicket object before accessing order_id
            if hasattr(ticket, 'order_id') and ticket.order_id == order_event.order_id:
                found_in_closing_tickets = True
                closing_ticket = ticket
                break
        
        # If not found directly, check if this is a child order of a spread strategy
        # Since OrderTicket doesn't have order_ids attribute, we need to check if the leg symbols match
        if not found_in_opening_tickets and not found_in_closing_tickets and order_event.symbol in [self.opened_short_put_symbol, self.opened_long_put_symbol]:
            found_in_opening_tickets = True

        if found_in_opening_tickets:
            self.log(f"ON_ORDER_EVENT: Event for opening ticket. Status: {order_event.status}, Symbol: {order_event.symbol.value}")
            
            # For strategy orders using OptionStrategies, we need to track the child fills
            if order_event.status == OrderStatus.FILLED:
                # Check if we're getting exercised/assigned (should not happen with newly opened spreads)
                if order_event.is_assignment:
                    self.log("ON_ORDER_EVENT: Assignment detected on opening spread leg. This is unexpected.")
                    self.reset_spread_state("OpeningLegAssigned")
                    return
                
                # If this is for our specifically tracked options
                if order_event.symbol == self.opened_short_put_symbol or order_event.symbol == self.opened_long_put_symbol:
                    self.log(f"ON_ORDER_EVENT: Leg fill for {order_event.symbol.value}, Quantity: {order_event.fill_quantity}, Price: {order_event.fill_price}")
                    
                # Check if both legs are now in the portfolio (indicating spread is open)
                if self.portfolio.invested and \
                   self.opened_short_put_symbol in self.portfolio and self.portfolio[self.opened_short_put_symbol].invested and \
                   self.opened_long_put_symbol in self.portfolio and self.portfolio[self.opened_long_put_symbol].invested:
                    
                    # Mark spread as open and calculate initial credit
                    if not self.spread_is_open:  # Only do this once
                        self.spread_is_open = True
                        # Get the realized credit based on actual fill prices
                        # Convert query results to list before indexing
                        short_put_fill_orders = list(self.transactions.get_orders(lambda o: o.symbol == self.opened_short_put_symbol and o.status == OrderStatus.FILLED))
                        long_put_fill_orders = list(self.transactions.get_orders(lambda o: o.symbol == self.opened_long_put_symbol and o.status == OrderStatus.FILLED))
                        
                        if short_put_fill_orders and long_put_fill_orders:
                            short_put_fill = short_put_fill_orders[-1]
                            long_put_fill = long_put_fill_orders[-1]
                            self.initial_credit = short_put_fill.price - long_put_fill.price
                        else:
                            # Fallback if order data is not available
                            self.log("ON_ORDER_EVENT: Warning - Could not find fill data for legs. Using spread credit estimate.")
                            self.initial_credit = 0.20 # Default fallback value
                        self.log(f"ON_ORDER_EVENT: Bull Put Spread is now open. Actual credit received: ${self.initial_credit:.2f}")
                        self.stop_loss_target_debit = self.initial_credit * self.stop_loss_multiplier
                        self.profit_target_value_debit = self.initial_credit * (1 - self.profit_target_percentage)
                        self.log(f"ON_ORDER_EVENT: Stop Loss Target: ${self.stop_loss_target_debit:.2f}, Profit Target: ${self.profit_target_value_debit:.2f}")
                    
            elif order_event.status in [OrderStatus.CANCELED, OrderStatus.INVALID]:
                self.log(f"ON_ORDER_EVENT: Opening order failed or canceled: {order_event.status}. Message: {order_event.message}")
                # Reset if the order is canceled/invalid
                self.reset_spread_state(f"OpeningOrderFailed_{order_event.status}")
        
        elif found_in_closing_tickets:
            self.log(f"ON_ORDER_EVENT: Event for closing ticket. Status: {order_event.status}, Symbol: {order_event.symbol.value}")
            
            if order_event.status == OrderStatus.FILLED:
                self.log(f"ON_ORDER_EVENT: Closing leg {order_event.symbol} filled.")
                
                # Check if all positions are now closed - specifically check our tracked positions
                short_position_closed = self.opened_short_put_symbol not in self.portfolio or not self.portfolio[self.opened_short_put_symbol].invested
                long_position_closed = self.opened_long_put_symbol not in self.portfolio or not self.portfolio[self.opened_long_put_symbol].invested
                
                if short_position_closed and long_position_closed:
                    self.log("ON_ORDER_EVENT: Spread fully closed. All positions are now flat.")
                    self.reset_spread_state("SpreadClosedSuccessfully")
                
            elif order_event.status in [OrderStatus.CANCELED, OrderStatus.INVALID]:
                self.log(f"ON_ORDER_EVENT: Closing order failed or canceled: {order_event.status}. Message: {order_event.message}")
                # Only if the main liquidation order was canceled/invalid
                if order_event.order_id == closing_ticket.order_id:
                    self.pending_close = False
                    self.log("ON_ORDER_EVENT: Will retry closing at next opportunity.")
        
        # Handle exercise/assignment events that weren't matched to our tickets
        elif order_event.is_assignment and order_event.status == OrderStatus.FILLED:
            self.log(f"ON_ORDER_EVENT: Exercise/Assignment detected outside of normal order flow: {order_event.symbol.value}")
            
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

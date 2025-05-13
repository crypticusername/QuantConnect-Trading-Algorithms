from AlgorithmImports import *
from datetime import timedelta

class BearCreditSpreadAlgorithm(QCAlgorithm):
    """0-DTE Bear Call Credit Spread Algorithm on SPY.
    This algorithm opens a bear call credit spread each trading day
    and attempts to close it 15 minutes before market close.
    """

    def initialize(self) -> None:
        """Initialize algorithm parameters, data subscriptions, and scheduling."""
        # --- Algorithm Settings ---
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 3, 31)
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)

        # --- Underlying Asset ---
        underlying_ticker = "SPY"

        # --- Data Subscriptions ---
        equity = self.add_equity(underlying_ticker, Resolution.MINUTE)
        self.equity_symbol = equity.Symbol

        option = self.add_option(underlying_ticker, Resolution.MINUTE)
        self.option_symbol = option.Symbol

        # Option filter – include weeklys, ±20 strikes around ATM, expirations 0-35 days
        option.set_filter(lambda u: u.include_weeklys()
                                     .strikes(-20, +20)
                                     .expiration(0, 35))

        self.set_benchmark(self.equity_symbol)

        # Position Tracking Flags
        self.spread_is_open = False
        self.pending_open_trade_flag = False
        self.pending_close_trade_flag = False
        self.opening_order_ids = []
        self.filled_short_leg_symbol = None
        self.filled_long_leg_symbol = None
        self.trade_close_flagged = False

        # --- Scheduling ---
        # Schedule trade opening attempts (sets a flag for OnData)
        self.schedule.on(self.date_rules.every_day(self.equity_symbol),
                         self.time_rules.at(10, 0), # Corrected: Use .at() for specific time
                         self.schedule_open_trades)

        # Schedule trade closing attempts (sets a flag for OnData)
        self.schedule.on(self.date_rules.every_day(self.equity_symbol),
                         self.time_rules.before_market_close(self.option_symbol, 15), # Corrected: Use .before_market_close()
                         self.schedule_close_trades)

    # ---------------- Scheduling Methods ----------------
    def schedule_open_trades(self):
        """Sets a flag to attempt opening trades on the next OnData call."""
        self.debug(f"STATE_DEBUG: schedule_open_trades check. self.spread_is_open: {self.spread_is_open}, self.opening_order_ids non-empty: {bool(self.opening_order_ids)}")
        if self.spread_is_open or len(self.opening_order_ids) > 0:
            self.debug(f"{self.time}: Spread is already open or pending open, skipping schedule_open_trades.")
            return
        self.pending_open_trade_flag = True
        self.debug(f"{self.time}: Flagged to attempt opening trades on next data slice.")

    def schedule_close_trades(self):
        """Sets a flag to attempt closing trades on the next OnData call."""
        self.debug(f"STATE_DEBUG: schedule_close_trades check. self.spread_is_open: {self.spread_is_open}, self.opening_order_ids non-empty: {bool(self.opening_order_ids)}")
        if not self.spread_is_open:
            self.debug(f"{self.time}: No spread open, skip close schedule.")
            return
        self.pending_close_trade_flag = True
        self.trade_close_flagged = True
        self.debug(f"{self.time}: Flagged to attempt closing trades on next data slice.")

    # ---------------- Main Data Handler ----------------
    def on_data(self, slice: Slice) -> None:
        """Main data handler, called on every data slice."""
        if self.pending_open_trade_flag:
            self._try_open_spread_strategy(slice)
            self.pending_open_trade_flag = False

        if self.pending_close_trade_flag:
            self._try_close_spread_strategy(slice)
            self.pending_close_trade_flag = False

    # ---------------- Strategy Logic Methods ----------------
    def _try_open_spread_strategy(self, slice: Slice):
        """Attempts to open a bear call spread if conditions are met."""
        if self.spread_is_open or len(self.opening_order_ids) > 0:
            return

        self.debug(f"{self.time}: Available Margin before opening: {self.portfolio.margin_remaining}, Used Margin: {self.portfolio.total_margin_used}")

        # Ensure chain data available
        if self.option_symbol not in slice.option_chains:
            self.debug(f"{self.time}: No option chain data for {self.option_symbol}.")
            return
        
        chain = slice.option_chains[self.option_symbol]
        if not chain:
            self.debug(f"{self.time}: Option chain for {self.option_symbol} is empty.")
            return

        # Find 0-DTE call options
        current_date = self.time.date()
        target_expiry_date = current_date
        
        # Filter for calls expiring today
        calls_expiring_today = [c for c in chain 
                                if c.right == OptionRight.CALL and 
                                c.expiry.date() == target_expiry_date]

        if not calls_expiring_today or len(calls_expiring_today) < 2:
            self.debug(f"{self.time}: Not enough call options expiring today ({target_expiry_date}) to form a spread.")
            return

        # Sort by strike price: OTM calls have higher strikes
        # For a bear call spread: Sell OTM call (lower strike), Buy further OTM call (higher strike)
        # We want short call closer to ATM, long call further OTM.
        # Let's select strikes based on Delta, aiming for a common 0-DTE setup.
        # Example: Short call delta around 0.20-0.30, Long call delta around 0.10-0.15
        
        # Sort by strike (ascending for calls)
        sorted_calls = sorted(calls_expiring_today, key=lambda c: c.strike)

        # Simple selection: find first OTM call, then next one up
        # This is a placeholder; a more robust selection would use Delta or other criteria.
        underlying_price = self.securities[self.equity_symbol].price
        
        short_call_candidates = [c for c in sorted_calls if c.strike > underlying_price]
        if not short_call_candidates:
            self.debug(f"{self.time}: No OTM calls found for {target_expiry_date}.")
            return

        # Choose the OTM call closest to the money as the short leg
        short_call = short_call_candidates[0]
        
        # Find the next strike up for the long leg
        long_call_index = sorted_calls.index(short_call) + 1
        if long_call_index >= len(sorted_calls):
            self.debug(f"{self.time}: Not enough strikes available above the selected short call {short_call.strike}.")
            return
        long_call = sorted_calls[long_call_index]

        if not short_call or not long_call:
            self.debug(f"{self.time}: Could not select short and long call legs for {target_expiry_date}.")
            return

        self.debug(f"{self.time}: Bear Call Spread selection (Exp: {target_expiry_date}): Short {short_call.strike}, Long {long_call.strike}.")
        self.debug(f"{self.time}: Available Margin before submitting spread: {self.portfolio.margin_remaining}, Used Margin: {self.portfolio.total_margin_used}")

        try:
            bear_call_strategy = OptionStrategies.bear_call_spread(
                self.option_symbol,
                short_call.strike,   # Corrected: Lower strike for the short call (leg1Strike)
                long_call.strike,    # Corrected: Higher strike for the long call (leg2Strike)
                target_expiry_date
            )
            quantity = 1
            orders = self.buy(bear_call_strategy, quantity)  
            self.opening_order_ids = [o.order_id for o in orders]
            self.filled_short_leg_symbol = None 
            self.filled_long_leg_symbol = None  
            self.log(f"{self.time}: Submitted Bear Call Spread. Order IDs: {self.opening_order_ids}")
        except Exception as e:
            self.error(f"{self.time}: Error opening spread: {e}")
            self.opening_order_ids = [] 

    def _try_close_spread_strategy(self, slice: Slice):
        """Liquidates the bear call spread if it's open and flagged for closure."""
        if not self.spread_is_open:
            self.debug(f"{self.time}: No spread open to close.")
            self.trade_close_flagged = False 
            return

        self.debug(f"{self.time}: Attempting to close spread. Margin before closing: {self.portfolio.margin_remaining}, Used Margin: {self.portfolio.total_margin_used}")

        if self.filled_short_leg_symbol and self.portfolio[self.filled_short_leg_symbol].invested:
            self.liquidate(self.filled_short_leg_symbol)
            self.log(f"{self.time}: Liquidation submitted for short leg: {self.filled_short_leg_symbol.value}.")
        
        if self.filled_long_leg_symbol and self.portfolio[self.filled_long_leg_symbol].invested:
            self.liquidate(self.filled_long_leg_symbol)
            self.log(f"{self.time}: Liquidation submitted for long leg: {self.filled_long_leg_symbol.value}.")
        
        # Note: Actual closure confirmation and state reset happens in OnOrderEvent

    # ---------------- Order Events ----------------
    def on_order_event(self, order_event: OrderEvent):
        self.debug(f"ON_ORDER_EVENT_V4_ENTRY_POINT_CONFIRMATION: ID={order_event.order_id}, Status={order_event.status}") # <-- NEW DISTINCT LOG

        order = self.transactions.get_order_by_id(order_event.order_id)
        self.debug(f"{self.time}: OrderEvent: {order_event.symbol} - Status: {order_event.status} - FillP: {order_event.fill_price} Qty: {order_event.fill_quantity} ID: {order_event.order_id} Msg: {order_event.message}")

        if order_event.status == OrderStatus.FILLED:
            self.debug(f"Order FILLED: {order_event.symbol.value} – Qty: {order_event.fill_quantity} @ {order_event.fill_price if order_event.fill_price is not None else 'N/A'}")
            
            is_opening_leg_fill = False
            if order_event.order_id in self.opening_order_ids:
                is_opening_leg_fill = True
                # Temp store previous state for logging
                prev_short_sym = self.filled_short_leg_symbol
                prev_long_sym = self.filled_long_leg_symbol

                if order_event.fill_quantity < 0: 
                    self.filled_short_leg_symbol = order_event.symbol
                    self.debug(f"Short call leg {self.filled_short_leg_symbol} filled. Order ID: {order_event.order_id}. Prev short: {prev_short_sym}, Prev long: {prev_long_sym}")
                elif order_event.fill_quantity > 0: 
                    self.filled_long_leg_symbol = order_event.symbol
                    self.debug(f"Long call leg {self.filled_long_leg_symbol} filled. Order ID: {order_event.order_id}. Prev short: {prev_short_sym}, Prev long: {prev_long_sym}")
                
                # More detailed debug block
                self.debug(f"STATE_DEBUG_ON_EVENT: OrderID {order_event.order_id} (FillQ: {order_event.fill_quantity}) processed.")
                self.debug(f"  Current filled_short_leg_symbol: {self.filled_short_leg_symbol}")
                self.debug(f"  Current filled_long_leg_symbol: {self.filled_long_leg_symbol}")
                self.debug(f"  Current spread_is_open: {self.spread_is_open}")
                
                cond_filled_short_exists = bool(self.filled_short_leg_symbol)
                cond_filled_long_exists = bool(self.filled_long_leg_symbol)
                cond_not_spread_is_open = not self.spread_is_open
                self.debug(f"  Condition check components: (filled_short: {cond_filled_short_exists}) AND (filled_long: {cond_filled_long_exists}) AND (not spread_open: {cond_not_spread_is_open})")
                
                final_condition = cond_filled_short_exists and cond_filled_long_exists and cond_not_spread_is_open
                self.debug(f"  Final condition for opening state update: {final_condition}")

                if final_condition: # Use the calculated final_condition
                    self.debug(f"STATE_DEBUG: About to set spread_is_open = True. Current val: {self.spread_is_open}")
                    self.spread_is_open = True
                    self.debug(f"Bear Call Spread officially open with Short: {self.filled_short_leg_symbol}, Long: {self.filled_long_leg_symbol}")
                    self.opening_order_ids = [] 
            
            is_closing_leg_fill = False
            # Check if this fill corresponds to a closing trade
            if not is_opening_leg_fill and self.trade_close_flagged:
                if (self.filled_short_leg_symbol and order_event.symbol == self.filled_short_leg_symbol and order_event.fill_quantity > 0) or \
                   (self.filled_long_leg_symbol and order_event.symbol == self.filled_long_leg_symbol and order_event.fill_quantity < 0):
                    self.debug(f"A leg of the spread was liquidated: {order_event.symbol}")
                    is_closing_leg_fill = True
            
            if is_closing_leg_fill and self.spread_is_open: 
                # Check if both legs are now closed (i.e., no longer invested)
                short_leg_closed = not self.portfolio[self.filled_short_leg_symbol].invested if self.filled_short_leg_symbol else True
                long_leg_closed = not self.portfolio[self.filled_long_leg_symbol].invested if self.filled_long_leg_symbol else True

                if short_leg_closed and long_leg_closed:
                    self.debug(f"STATE_DEBUG: About to set spread_is_open = False. Current val: {self.spread_is_open}")
                    self.debug(f"Both legs confirmed closed. Spread is now closed.")
                    self.spread_is_open = False
                    self.filled_short_leg_symbol = None
                    self.filled_long_leg_symbol = None
                    self.trade_close_flagged = False 

        elif order_event.status == OrderStatus.CANCELED:
            self.log(f"{self.time}: Order CANCELED: {order_event.symbol}, OrderId: {order_event.order_id}. Message: {order_event.message}")
            if order_event.order_id in self.opening_order_ids:
                self.log(f"An opening leg order ({order_event.symbol}) was canceled. Resetting relevant opening state.")
                # Remove from opening_order_ids, and if it was the only one, reset flags
                self.opening_order_ids.remove(order_event.order_id)
                if not self.opening_order_ids: 
                    self.filled_short_leg_symbol = None
                    self.filled_long_leg_symbol = None
                    self.spread_is_open = False 
                    self.pending_open_trade_flag = False 
                self.trade_close_flagged = False 

        elif order_event.status == OrderStatus.INVALID:
            self.error(f"{self.time}: Order INVALID: {order_event.symbol}, OrderId: {order_event.order_id}. Message: {order_event.message}")
            if order_event.order_id in self.opening_order_ids:
                self.error(f"An opening leg order ({order_event.symbol}) was invalid. Resetting opening state.")
                self.opening_order_ids = [] 
                self.filled_short_leg_symbol = None
                self.filled_long_leg_symbol = None
                self.spread_is_open = False
                self.pending_open_trade_flag = False 
                self.trade_close_flagged = False
            elif self.trade_close_flagged and (
                (self.filled_short_leg_symbol and order_event.symbol == self.filled_short_leg_symbol) or 
                (self.filled_long_leg_symbol and order_event.symbol == self.filled_long_leg_symbol)
            ):
                self.error(f"A closing leg order for {order_event.symbol} was invalid. The spread may still be open. Manual review needed. Message: {order_event.message}")
                # Do not reset trade_close_flagged here, algorithm might retry or require manual intervention/logic.
                # self.spread_is_open remains true as liquidation failed.
            else:
                self.error(f"An INVALID order event occurred for {order_event.symbol} that was not tied to current strategy opening or closing. Message: {order_event.message}")
            
        elif order_event.status == OrderStatus.SUBMITTED:
            self.debug(f"{self.time}: Order SUBMITTED: {order_event.symbol}, OrderId: {order_event.order_id}")

        else:
            self.log(f"{self.time}: Order Event: {order_event.symbol} Status: {order_event.status} Message: {order_event.message}")

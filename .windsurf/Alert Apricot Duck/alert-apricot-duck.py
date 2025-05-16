from AlgorithmImports import *
from datetime import datetime # Ensure datetime is imported

class Basic_Credit_SpreadAlgorithm(QCAlgorithm):
    def initialize(self) -> None:
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 3, 31)
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)

        equity = self.add_equity("SPY", Resolution.MINUTE)
        self.equity_symbol = equity.symbol
        option = self.add_option("SPY", Resolution.MINUTE)
        option.set_filter(lambda u: u.include_weeklys().strikes(-20, +20).expiration(0, 30))
        self.option_symbol = option.symbol
        self.set_benchmark(self.equity_symbol)

        # Spread state variables
        self.spread_open = False
        self.spread_orders = []  # Stores OrderTicket objects from self.buy() or self.sell()
        self.pending_open = False
        self.pending_close = False
        self.initial_credit = None
        self.stop_loss_target_debit = None
        self.opened_short_put_symbol = None
        self.opened_long_put_symbol = None
        self.min_credit_threshold = 0.10  # Configurable credit threshold

        # For refining credit in on_order_event
        self.last_short_fill_price = None
        self.last_long_fill_price = None

        # Schedule functions
        self.schedule.on(self.date_rules.every_day(self.equity_symbol),
                         self.time_rules.at(10, 0),
                         self.open_trades)
        self.schedule.on(self.date_rules.every_day(self.equity_symbol),
                         self.time_rules.before_market_close(self.option_symbol, 15),
                         self.close_positions)

    def open_trades(self):
        if self.spread_open:
            self.debug("Spread already open, skipping")
            return
        self.debug("Setting flag to open trades on next data slice")
        self.pending_open = True

    def close_positions(self):
        if not self.spread_open:
            self.debug("No spread position open to close")
            return
        self.debug("Setting flag to close positions on next data slice")
        self.pending_close = True

    def on_data(self, slice: Slice) -> None:
        if self.spread_open and not self.pending_close and self.initial_credit is not None and self.opened_short_put_symbol and self.opened_long_put_symbol:
            self.check_stop_loss(slice)
        
        if self.pending_open and not self.spread_open:
            self.try_open_spread(slice)
            self.pending_open = False # Reset flag regardless of outcome of try_open_spread
        
        if self.pending_close and self.spread_open:
            self.try_close_spread()
            self.pending_close = False # Reset flag regardless of outcome of try_close_spread

    def try_open_spread(self, slice: Slice) -> None:
        if self.option_symbol not in slice.option_chains:
            self.debug("No option chain data available for SPY")
            return

        chain = slice.option_chains[self.option_symbol]
        if not chain:
            self.debug("Empty option chain for SPY")
            return

        current_date = self.time.date()
        puts = [x for x in chain if x.right == OptionRight.PUT]
        if not puts:
            self.debug("No puts in the option chain.")
            return

        contracts_by_expiry = {}
        for put in puts:
            expiry_date = put.expiry.date()
            if expiry_date not in contracts_by_expiry:
                contracts_by_expiry[expiry_date] = []
            contracts_by_expiry[expiry_date].append(put)

        target_expiry_date = None
        if current_date in contracts_by_expiry and len(contracts_by_expiry[current_date]) >= 2:
            target_expiry_date = current_date
        else:
            available_expiries = sorted(contracts_by_expiry.keys())
            if not available_expiries:
                self.debug("No put options available with any expiry.")
                return
            for expiry in available_expiries:
                if len(contracts_by_expiry[expiry]) >= 2:
                    target_expiry_date = expiry
                    break
        
        if target_expiry_date is None:
            self.debug("No expiration date has at least 2 put contracts.")
            return
            
        target_contracts = contracts_by_expiry[target_expiry_date]
        target_expiry_dt = datetime(target_expiry_date.year, target_expiry_date.month, target_expiry_date.day)
        
        contracts_by_strike = {contract.strike: contract for contract in target_contracts}
        available_strikes = sorted(contracts_by_strike.keys())
        if len(available_strikes) < 2:
            self.debug(f"Not enough distinct strikes available for {target_expiry_date} to form a spread.")
            return

        short_put_candidates = [c for c in target_contracts if c.greeks and c.greeks.delta is not None and abs(c.greeks.delta) <= 0.30]
        if not short_put_candidates:
            self.debug(f"No suitable short put candidates found with abs(delta) <= 0.30 for {target_expiry_date}.")
            return
        
        short_put_candidates.sort(key=lambda x: x.strike, reverse=True)
        selected_short_put_contract = short_put_candidates[0]
        short_put_strike = selected_short_put_contract.strike

        long_put_strike_target = short_put_strike - 5.0 # Assuming $5 spread width
        if long_put_strike_target not in available_strikes:
            self.debug(f"Could not find desired long put strike {long_put_strike_target:.2f} (for $5 spread) for expiry {target_expiry_date}. Skipping trade.")
            return

        selected_long_put_contract = contracts_by_strike.get(long_put_strike_target)
        if not selected_long_put_contract:
            self.debug(f"Could not retrieve contract for long put strike {long_put_strike_target}. Skipping spread.")
            return
        
        if short_put_strike <= long_put_strike_target: # Should be redundant if selection logic is correct
            self.debug(f"Short put strike {short_put_strike} <= Long put strike {long_put_strike_target}. Skipping trade.")
            return

        short_put = selected_short_put_contract
        long_put = selected_long_put_contract

        # Ensure prices are available
        if self.securities[short_put.symbol].price == 0 or self.securities[long_put.symbol].price == 0:
            self.debug(f"Stale or zero price for one or both option legs. Short: ${self.securities[short_put.symbol].price}, Long: ${self.securities[long_put.symbol].price}. Skipping.")
            return

        short_put_price = self.securities[short_put.symbol].price
        long_put_price = self.securities[long_put.symbol].price
        estimated_credit = short_put_price - long_put_price

        if estimated_credit < self.min_credit_threshold:
            self.debug(f"Skipping spread: estimated credit {estimated_credit:.2f} is below min credit threshold {self.min_credit_threshold:.2f}.")
            return

        self.opened_short_put_symbol = short_put.symbol
        self.opened_long_put_symbol = long_put.symbol
        self.initial_credit = estimated_credit # Store estimated credit
        self.stop_loss_target_debit = estimated_credit * 2.0 # Example stop-loss target

        bull_put_spread_strategy = OptionStrategies.bull_put_spread(
            self.option_symbol, # Underlying symbol
            short_put.strike,
            long_put.strike,
            target_expiry_dt # datetime object
        )

        self.spread_orders = self.buy(bull_put_spread_strategy, 1) # Submit opening order
        self.spread_open = True # Optimistically set spread as open
        self.debug(f"Submitted Bull Put Spread. Short: {short_put.symbol.value}, Long: {long_put.symbol.value}, Est. Credit: ${estimated_credit:.2f}")
        self.last_short_fill_price = None # Reset for new spread
        self.last_long_fill_price = None  # Reset for new spread

    def try_close_spread(self):
        if not self.spread_open or not self.opened_short_put_symbol or not self.opened_long_put_symbol:
            self.debug("No open spread with defined legs to close.")
            return

        try:
            # Ensure we have the Symbol objects
            short_leg_symbol = self.opened_short_put_symbol
            long_leg_symbol = self.opened_long_put_symbol

            # Get strike and expiry from the stored symbols
            # Assuming both legs have the same expiry, which they should for a spread
            expiry_dt = short_leg_symbol.id.date 
            
            closing_spread_strategy = OptionStrategies.bull_put_spread(
                self.option_symbol, # Underlying
                short_leg_symbol.id.strike_price,
                long_leg_symbol.id.strike_price,
                expiry_dt # datetime object
            )
            # Submit closing combo order by SELLING the spread
            closing_orders = self.sell(closing_spread_strategy, 1)
            # self.spread_orders.extend(closing_orders) # Add closing orders to tracked list - careful if self.spread_orders is used for opening only
            # Create a new list for closing orders or manage self.spread_orders carefully if it's reused.
            # For simplicity here, let's assume self.spread_orders can be cleared and repopulated if needed for event tracking.
            # For this merge, MIA's original didn't add closing orders to self.spread_orders. Let's stick to that for now.
            self.debug(f"Submitted combo SELL order to close Bull Put Spread. Short: {short_leg_symbol.value}, Long: {long_leg_symbol.value}")

        except Exception as e:
            self.error(f"Error in try_close_spread: {str(e)}")
            # Reset state carefully if an error occurs during close attempt
            # This might involve clearing self.opened_short_put_symbol, etc. if the close fails catastrophically
            # For now, just log the error.

    def check_stop_loss(self, slice: Slice) -> None:
        if not self.opened_short_put_symbol or not self.opened_long_put_symbol or self.initial_credit is None:
            # self.debug("Stop loss check: Spread not fully defined or initial credit missing.")
            return # Not fully set up

        try:
            if self.opened_short_put_symbol not in self.securities or self.opened_long_put_symbol not in self.securities:
                self.debug("Stop loss check: Securities not found for opened spread legs.")
                return

            short_put_security = self.securities[self.opened_short_put_symbol]
            long_put_security = self.securities[self.opened_long_put_symbol]

            short_put_ask = short_put_security.ask_price
            long_put_bid = long_put_security.bid_price

            if short_put_ask == 0 and short_put_security.price != 0: short_put_ask = short_put_security.price
            if long_put_bid == 0 and long_put_security.price != 0: long_put_bid = long_put_security.price

            if short_put_ask == 0 or long_put_bid == 0 : # Still zero, cannot calculate
                self.debug(f"Stop loss check: Market data (ask/bid or price) unavailable or zero for one or both legs. ShortAsk: {short_put_ask}, LongBid: {long_put_bid}. Cannot calculate debit to close.")
                return

            current_debit_to_close = short_put_ask - long_put_bid # Cost to buy back short, sell long
            # self.debug(f"Stop loss check: Debit to close ${current_debit_to_close:.2f}, Target Debit ${self.stop_loss_target_debit:.2f}")

            if current_debit_to_close >= self.stop_loss_target_debit:
                self.log(f"STOP LOSS HIT: Current debit to close ${current_debit_to_close:.2f} >= Target ${self.stop_loss_target_debit:.2f}. Will close spread.")
                self.pending_close = True
        except Exception as e:
            self.error(f"Error in stop-loss check: {str(e)}")

    def on_order_event(self, order_event: OrderEvent) -> None:
        if order_event.status == OrderStatus.FILLED:
            order = self.transactions.get_order_by_id(order_event.order_id)
            if order is None:
                self.error(f"Order not found for OrderID: {order_event.order_id}")
                return
            
            # Check if this order is part of the currently tracked opening spread_orders
            # This is crucial if self.spread_orders contains OrderTicket objects for the *opening* combo
            is_opening_leg_fill = False
            for ot in self.spread_orders: # self.spread_orders should hold tickets from the self.buy() call
                if ot.order_id == order_event.order_id:
                    is_opening_leg_fill = True
                    break
                # If the combo order itself filled, its child leg orders also get fill events.
                # We need to capture those child leg fills.
                for leg_order_id in ot.order_ids:
                    if leg_order_id == order_event.order_id:
                        is_opening_leg_fill = True
                        break
                if is_opening_leg_fill: break

            if not is_opening_leg_fill:
                # This fill event is not for the initial opening legs we are tracking.
                # It could be for a closing order, or an unrelated order if the algo did other things.
                # If it IS a closing order, we need to reset our state.
                # self.debug(f"Filled order {order_event.order_id} is not an opening leg. Symbol: {order_event.symbol}")
                if self.opened_short_put_symbol and order_event.symbol == self.opened_short_put_symbol and order.direction == OrderDirection.BUY:
                    self.log(f"Detected closing fill for short leg: {order_event.symbol.value} @ {order_event.fill_price:.2f}")
                    # Part of spread closure
                elif self.opened_long_put_symbol and order_event.symbol == self.opened_long_put_symbol and order.direction == OrderDirection.SELL:
                    self.log(f"Detected closing fill for long leg: {order_event.symbol.value} @ {order_event.fill_price:.2f}")
                    # Part of spread closure
                
                # Check if both legs of a *closed* spread have reported fills. This is a simple check.
                # A more robust way would be to track closing order IDs and their fills.
                if not self.portfolio[self.opened_short_put_symbol].invested and \ 
                   not self.portfolio[self.opened_long_put_symbol].invested and \ 
                   self.spread_open: # Was open, now legs are not invested.
                    self.log(f"Both spread legs {self.opened_short_put_symbol.value} and {self.opened_long_put_symbol.value} are no longer invested. Resetting spread state.")
                    self.reset_spread_state() # Critical to reset state after closing
                return

            # Logic for handling fills of opening legs
            if order.tag and "Bull Put Spread" in order.tag: # Assuming combo order tag
                self.debug(f"Combo order fill: {order_event.order_id}, {order_event.symbol.value}, {order_event.message}")
            
            # Distinguish between short and long leg fills for the opening spread
            if order_event.symbol == self.opened_short_put_symbol:
                self.last_short_fill_price = order_event.fill_price
                self.debug(f"Opening Short Put Leg Filled: {order_event.symbol.value} @ ${order_event.fill_price:.2f}")
            elif order_event.symbol == self.opened_long_put_symbol:
                self.last_long_fill_price = order_event.fill_price
                self.debug(f"Opening Long Put Leg Filled: {order_event.symbol.value} @ ${order_event.fill_price:.2f}")

            # If both opening legs are filled, refine initial_credit and stop_loss_target_debit
            if self.last_short_fill_price is not None and self.last_long_fill_price is not None:
                self.initial_credit = self.last_short_fill_price - self.last_long_fill_price
                self.stop_loss_target_debit = self.initial_credit * 2.0  # Recalculate stop loss with actual fill credit
                self.spread_open = True # Confirm spread is open based on fills
                self.pending_open = False # Ensure this is false now
                self.log(f"Both opening legs filled. Actual Initial Credit: ${self.initial_credit:.2f}, Stop Loss Target Debit: ${self.stop_loss_target_debit:.2f}")
                # self.spread_orders = [] # Clear opening orders once filled and processed, if not needed for further tracking

        elif order_event.status == OrderStatus.CANCELED:
            self.log(f"Order Canceled: {order_event.order_id}, Symbol: {order_event.symbol.value}")
            # If it was an opening order that got canceled, reset relevant flags
            is_opening_order_cancel = False
            for ot in self.spread_orders:
                if ot.order_id == order_event.order_id or order_event.order_id in ot.order_ids:
                    is_opening_order_cancel = True
                    break
            
            if is_opening_order_cancel:
                self.log(f"Opening spread order {order_event.order_id} was canceled. Resetting spread state.")
                self.reset_spread_state()

        elif order_event.status == OrderStatus.INVALID or order_event.status == OrderStatus.SUBMITTED_REJECTED or order_event.status == OrderStatus.BROKER_REJECTED:
            self.error(f"Order Failed: {order_event.order_id}, Status: {order_event.status}, Message: {order_event.message}")
            is_opening_order_failure = False
            for ot in self.spread_orders:
                if ot.order_id == order_event.order_id or order_event.order_id in ot.order_ids:
                    is_opening_order_failure = True
                    break
            
            if is_opening_order_failure:
                self.log(f"Opening spread order {order_event.order_id} failed. Resetting spread state.")
                self.reset_spread_state()
    
    def reset_spread_state(self):
        self.debug("Resetting all spread state variables.")
        self.spread_open = False
        self.pending_open = False
        self.pending_close = False
        self.initial_credit = None
        self.stop_loss_target_debit = None
        self.opened_short_put_symbol = None
        self.opened_long_put_symbol = None
        self.spread_orders = []
        self.last_short_fill_price = None
        self.last_long_fill_price = None

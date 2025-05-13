from AlgorithmImports import *

class Futures_Bull_Credit_SpreadAlgorithm(QCAlgorithm):
    """
    Algorithm for trading Bull Put Credit Spreads on E-mini S&P 500 (ES) Futures Options.
    """

    def initialize(self) -> None:
        """Initialize algorithm parameters, data subscriptions, and scheduling."""
        # --- Algorithm Settings ---
        self.set_start_date(2023, 1, 1)
        self.set_end_date(2023, 12, 31)
        self.set_cash(25000)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.set_warm_up(10, Resolution.DAILY)

        # --- Configurable Parameters ---
        self.min_dte = self.get_parameter("MinDTE", 7)       # Minimum Days To Expiration
        self.max_dte = self.get_parameter("MaxDTE", 45)      # Maximum Days To Expiration
        self.spread_width_target = self.get_parameter("SpreadWidth", 20) # Target strike width for ES
        self.num_contracts_to_trade = self.get_parameter("Contracts", 1)  # Number of spread contracts
        self.target_delta_short_put = self.get_parameter("TargetDeltaShortPut", 0.30) # Target delta for short put

        # --- Futures and Future Options Subscription ---
        self.future_root = Futures.Indices.SP500EMini # ES E-mini S&P 500
        self.future = self.add_future(self.future_root, Resolution.MINUTE)
        self.future.set_filter(0, 90) # Filter for futures contracts expiring in 0-90 days

        self.option = self.add_future_option(self.future.symbol, Resolution.MINUTE)
        self.canonical_option_symbol = self.option.symbol
        # Wider preliminary filter; specific selection in trade logic
        self.option.set_filter(lambda u: u.strikes(-75, 75).expiration(0, 60))

        # --- Benchmarking ---
        self.set_benchmark(self.future.symbol)

        # --- Position Tracking & Scheduling Flags ---
        self.spread_is_open = False
        self.pending_open_trade_flag = False
        self.pending_close_trade_flag = False
        self.active_spread_legs = [] # Store symbols of active spread legs

        # --- Event Scheduling ---
        self.schedule.on(self.date_rules.every_day(self.future.symbol),
                         self.time_rules.at(10, 0), # 10:00 AM NY time
                         self.schedule_open_trades_event)
        self.schedule.on(self.date_rules.every_day(self.future.symbol),
                         self.time_rules.before_market_close(self.canonical_option_symbol, 15),
                         self.schedule_close_trades_event)

    def schedule_open_trades_event(self):
        """Scheduled event to set a flag for opening a trade."""
        if self.spread_is_open:
            self.debug(f"{self.time}: Spread already open, skipping open schedule.")
            return
        self.pending_open_trade_flag = True
        self.debug(f"{self.time}: Flag set to attempt opening trades on next data slice.")

    def schedule_close_trades_event(self):
        """Scheduled event to set a flag for closing a trade."""
        if not self.spread_is_open:
            self.debug(f"{self.time}: No spread position open to schedule for closure.")
            return
        self.pending_close_trade_flag = True
        self.debug(f"{self.time}: Flag set to attempt closing positions on next data slice.")

    def on_data(self, slice: Slice):
        """Main data handler. Processes flags set by scheduled events."""
        if self.pending_open_trade_flag:
            self.try_open_spread_strategy(slice)
            self.pending_open_trade_flag = False
        if self.pending_close_trade_flag:
            self.try_close_spread_strategy(slice)
            self.pending_close_trade_flag = False

    def try_open_spread_strategy(self, slice: Slice):
        """Attempts to open a Bull Put Credit Spread on ES Futures Options."""
        if self.portfolio.invested and self.spread_is_open:
            self.debug(f"{self.time}: Already invested in a spread.")
            return

        active_future_contract = self.get_active_future_contract(slice)
        if not active_future_contract: return

        underlying_future_symbol = active_future_contract.symbol
        underlying_price = self.securities[underlying_future_symbol].price
        if underlying_price == 0:
            self.debug(f"{self.time}: Underlying future price for {underlying_future_symbol} is 0.")
            return
        self.debug(f"{self.time}: Active Future: {underlying_future_symbol}, Price: {underlying_price:.2f}")

        chain = self.get_option_chain_for_future(slice, underlying_future_symbol)
        if not chain: return

        target_expiry_date = self.find_target_expiration(chain)
        if not target_expiry_date: return

        puts = [c for c in chain if c.expiry.date() == target_expiry_date and c.right == OptionRight.PUT]
        if len(puts) < 2:
            self.debug(f"{self.time}: Not enough puts for expiry {target_expiry_date}.")
            return

        # Find short put (closest to target delta, OTM)
        otm_puts_for_short = sorted([p for p in puts if p.strike < underlying_price and p.greeks.delta < 0 and (p.bid_price > 0 or p.ask_price > 0)],
                                    key=lambda p: abs(p.greeks.delta - (-self.target_delta_short_put)))
        if not otm_puts_for_short:
            self.debug(f"{self.time}: No OTM puts found for delta selection for short leg.")
            return
        short_put_contract = otm_puts_for_short[0]

        # Find long put (spread_width_target away from short_put_contract's strike)
        long_put_strike_target = short_put_contract.strike - self.spread_width_target
        available_long_puts = sorted([p for p in puts if p.strike < short_put_contract.strike and p.strike != short_put_contract.strike and (p.bid_price > 0 or p.ask_price > 0)],
                                     key=lambda p: abs(p.strike - long_put_strike_target))
        if not available_long_puts:
            self.debug(f"{self.time}: No suitable long put found near target strike {long_put_strike_target}.")
            return
        long_put_contract = available_long_puts[0]

        if short_put_contract.strike <= long_put_contract.strike:
            self.debug(f"{self.time}: Invalid strikes: short {short_put_contract.strike} <= long {long_put_contract.strike}")
            return

        self.debug(f"{self.time}: Selected Bull Put: Short {short_put_contract.symbol.value} @ {short_put_contract.strike} (Delta: {short_put_contract.greeks.delta:.2f}), Long {long_put_contract.symbol.value} @ {long_put_contract.strike}")

        # Use the specific future contract symbol for the strategy
        bull_put_spread = OptionStrategies.bull_put_spread(
            underlying_future_symbol,
            short_put_contract.strike,
            long_put_contract.strike,
            target_expiry_date
        )

        if self.marketable_option_strategy(bull_put_spread, slice, chain):
            tickets = self.buy(bull_put_spread, self.num_contracts_to_trade)
            self.spread_is_open = True
            self.active_spread_legs = [leg.symbol for leg in bull_put_spread.option_legs] # Store specific option leg symbols
            self.log(f"{self.time}: Submitted Bull Put Spread. IDs: {[t.order_id for t in tickets]}")
        else:
            self.debug(f"{self.time}: Spread not marketable: Short {short_put_contract.symbol.value}, Long {long_put_contract.symbol.value}")

    def get_active_future_contract(self, slice: Slice) -> FutureContract:
        """Gets the front-month (or most liquid) active future contract."""
        future_chain = slice.futures_chains.get(self.future.symbol)
        if not future_chain:
            self.debug(f"{self.time}: No future chain for {self.future.symbol}.")
            return None
        # Prefer contracts with some volume or open interest
        active_contracts = sorted([contract for contract in future_chain if contract.open_interest > 10 or contract.volume > 10],
                                  key=lambda c: c.expiry)
        if not active_contracts:
            # Fallback to any contract if none have OI/Volume (less ideal)
            active_contracts = sorted([contract for contract in future_chain], key=lambda c: c.expiry)

        return active_contracts[0] if active_contracts else None

    def get_option_chain_for_future(self, slice: Slice, future_symbol: Symbol) -> OptionChain:
        """Gets the option chain for a specific future contract symbol."""
        option_chains_for_canonical = slice.option_chains.get(self.canonical_option_symbol)
        if not option_chains_for_canonical:
            self.debug(f"{self.time}: No option chains for canonical {self.canonical_option_symbol}.")
            return None
        chain_for_specific_future = option_chains_for_canonical.get(future_symbol)
        if not chain_for_specific_future:
            self.debug(f"{self.time}: No option chain for specific future {future_symbol} in slice.")
        return chain_for_specific_future

    def find_target_expiration(self, chain: OptionChain) -> datetime.date:
        """Finds a suitable expiration date within the DTE range."""
        available_expiries = sorted(list(chain.expiries))
        for expiry_dt_obj in available_expiries: # QC Expiries are datetime objects
            expiry_date = expiry_dt_obj.date()
            dte = (expiry_date - self.time.date()).days
            if self.min_dte <= dte <= self.max_dte:
                self.debug(f"{self.time}: Target expiry {expiry_date} found (DTE: {dte}).")
                return expiry_date
        self.debug(f"{self.time}: No suitable option expiration found within DTE {self.min_dte}-{self.max_dte}.")
        return None

    def marketable_option_strategy(self, strategy: OptionStrategy, slice: Slice, chain_for_specific_future: OptionChain) -> bool:
        """Check if all legs of the strategy have market data (bid/ask > 0)."""
        if not chain_for_specific_future: return False # Ensure the specific chain is available

        for leg in strategy.option_legs:
            contract_symbol_obj = leg.symbol # This is the specific option contract symbol

            # Check if contract exists in the provided specific chain
            if contract_symbol_obj not in chain_for_specific_future:
                 self.debug(f"Marketability: {contract_symbol_obj} not in its specific future's chain ({chain_for_specific_future.underlying_symbol}).")
                 return False

            option_contract_security = self.securities.get(contract_symbol_obj)
            if option_contract_security is None or option_contract_security.ask_price == 0 or option_contract_security.bid_price == 0:
                self.debug(f"Marketability: {contract_symbol_obj} has no quote or zero bid/ask.")
                return False
            if option_contract_security.is_delisted or not option_contract_security.is_tradable:
                self.debug(f"Marketability: {contract_symbol_obj} is delisted or not tradable.")
                return False
        return True

    def try_close_spread_strategy(self, slice: Slice):
        """Attempts to close any open option spread positions."""
        if not self.spread_is_open or not self.portfolio.invested:
            self.spread_is_open = False # Ensure flag consistency
            self.active_spread_legs = []
            self.debug(f"{self.time}: No open spread or not invested, ensuring flags are reset.")
            return

        self.log(f"{self.time}: Attempting to close open spread position. Legs: {[leg.value for leg in self.active_spread_legs]}")
        legs_closed_count = 0
        for leg_symbol in self.active_spread_legs:
            if self.portfolio[leg_symbol].invested:
                self.liquidate(leg_symbol)
                self.log(f"{self.time}: Submitted liquidation for {leg_symbol.value}")
            else:
                legs_closed_count +=1 # Count if already closed or zeroed out

        # If all legs were already not invested, reset state
        if legs_closed_count == len(self.active_spread_legs):
             self.spread_is_open = False
             self.active_spread_legs = []
             self.debug(f"{self.time}: All active legs were already closed/not invested.")


    def on_order_event(self, order_event: OrderEvent):
        order = self.transactions.get_order_by_id(order_event.order_id)
        if order_event.status == OrderStatus.FILLED:
            self.log(f"{self.time}: Order FILLED: {order}. Quantity: {order_event.fill_quantity}")
            # Check if all legs of the spread are now closed
            if not self.portfolio.invested and self.spread_is_open: # Check if any option position still exists
                all_legs_cleared = True
                for leg_symbol in self.active_spread_legs:
                    if self.portfolio[leg_symbol].invested:
                        all_legs_cleared = False
                        break
                if all_legs_cleared:
                    self.log(f"{self.time}: All spread legs confirmed closed after fill.")
                    self.spread_is_open = False
                    self.active_spread_legs = []

        elif order_event.status in [OrderStatus.CANCELED, OrderStatus.INVALID, OrderStatus.SUBMISSION_REJECTED]:
            self.log(f"{self.time}: Order FAILED/CANCELED: {order_event.order_id} - {order_event.status} - {order_event.message}")
            # If part of a spread opening failed, we might need to cancel other pending parts
            # or liquidate filled parts if it's an unrecoverable situation.
            # For simplicity, we'll assume that if one leg of an opening spread fails,
            # we might not want the other leg. If it's a closing order, we keep trying.
            if self.pending_open_trade_flag: # If it was an attempt to open
                self.log(f"{self.time}: An order to open a spread leg failed. Resetting open flag.")
                # Potentially liquidate any legs that DID fill if this was part of an opening combo
                # For now, just reset the flag and avoid opening more.
                self.spread_is_open = False # Mark as not open if any leg fails
                self.active_spread_legs = []


        if not self.portfolio.invested and self.spread_is_open: # Double check after event
             all_legs_cleared = True
             for leg_symbol_check in self.active_spread_legs:
                 if self.portfolio[leg_symbol_check].invested:
                     all_legs_cleared = False
                     break
             if all_legs_cleared:
                 self.log(f"{self.time}: Confirmed all legs cleared after order event. Spread closed.")
                 self.spread_is_open = False
                 self.active_spread_legs = []

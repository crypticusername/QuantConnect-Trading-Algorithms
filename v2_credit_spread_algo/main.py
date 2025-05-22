from AlgorithmImports import *

# Module imports
from universe_builder import UniverseBuilder   # M1: Universe building
from spread_selector import SpreadSelector     # M3: Strike selection
from order_executor import OrderExecutor       # M4: Order execution 
# Future modules:
# from risk_manager import RiskManager         # M5: Risk management

class V2CreditSpreadAlgoAlgorithm(QCAlgorithm):
    """
    Bull put credit spread strategy with modular architecture.
    
    Modules: M1 Universe, M3 Spread Selection, M4 Order Execution, M5 Risk Management
    Schedule: 9:30 Load chains, 10:00 Open trades, 15:30 Close positions
    Risk rules: Stop-loss at 2× credit, take-profit at 50% max gain
    """
    
    def initialize(self):
        """Initialize algorithm parameters, modules, and scheduling."""
        # Algorithm parameters
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 2, 1)  # Shorter period for testing
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.set_warm_up(10, Resolution.DAILY)
        
        self.log("Algorithm initialized with $10,000 starting capital")
        
        # Initialize modules
        self.universe_builder = UniverseBuilder(self)                # M1
        self.universe_builder.initialize_universe("SPY", Resolution.MINUTE)
        self.equity_symbol = self.universe_builder.equity_symbol
        self.option_symbol = self.universe_builder.option_symbol
        self.set_benchmark(self.equity_symbol)
        
        # Spread selection module (M3)
        # Note: Using default parameters (target_delta=0.15, max_delta=0.30, min_credit_pct=0.20, etc.)
        # These can be customized in spread_selector.py or by passing parameters here
        self.spread_selector = SpreadSelector(self)
        
        # Order execution module (M4)
        self.order_executor = OrderExecutor(self)                  # M4
        
        # Future modules
        # self.risk_manager = RiskManager(self)                      # M5
        
        # Schedule trading events
        # Load chains at market open with fallback attempts each minute
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(9, 30), self.load_option_chains)
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(9, 31), self.load_option_chains_fallback)
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(9, 32), self.load_option_chains_fallback)
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(9, 33), self.load_option_chains_fallback)
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(9, 34), self.load_option_chains_fallback)
        
        # Trade entry and exit
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(10, 0), self.open_trades)
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(15, 30), self.close_positions)
        
        # State variables
        self._option_chain = None
        self._chains_loaded_today = False

    def load_option_chains(self):
        """Initial attempt to load option chains at market open."""
        # Add day start marker for better log tracking
        self.log(f"=== Trading day start: {self.time.strftime('%Y-%m-%d')} ===")
        
        # Reset daily state
        self._chains_loaded_today = False
        self._option_chain = None
        
        # Reset the order executor state at market open
        self.order_executor.reset_state()
        
        equity_price = self.universe_builder.get_latest_equity_price()
        self.log(f"SPY price at 9:30 AM ET: ${equity_price:.2f}")
        self.log(f"Attempting to load option chain for {self.time.strftime('%Y-%m-%d')}")
        self.log("Prepared to load option chains at market open")

    def load_option_chains_fallback(self):
        """Fallback attempts to load option chains if not loaded at market open."""
        if not self._chains_loaded_today:
            current_minute = self.time.minute
            self.log(f"Fallback chain loading attempt at 9:{current_minute} AM ET")
            # Try to get some diagnostics
            try:
                chain_status = self.universe_builder.get_option_chains(None)
                if chain_status is None:
                    self.log(f"Fallback diagnostics: Option chain is None")
                else:
                    contracts = list(chain_status)
                    self.log(f"Fallback diagnostics: Found {len(contracts)} contracts, but not properly loaded")
            except Exception as e:
                self.log(f"Fallback diagnostics error: {str(e)}")

    def open_trades(self):
        """Open bull put credit spreads at 10:00 AM ET."""
        if not self._chains_loaded_today:
            self.log("No option chains loaded for today. Skipping trade entry.")
            return
            
        if self._option_chain is not None:
            try:
                # Get current equity price for reference
                equity_price = self.universe_builder.get_latest_equity_price()
                self.log(f"SPY price at trade entry: ${equity_price:.2f}")
                
                # Count available contracts and verify today's expiry is available
                contracts = [contract for contract in self._option_chain]
                put_count = sum(1 for contract in contracts if contract.right == OptionRight.PUT)
                call_count = sum(1 for contract in contracts if contract.right == OptionRight.CALL)
                self.log(f"Option chain loaded with {len(contracts)} contracts: {put_count} puts, {call_count} calls")
                
                # Verify today's expiry is available
                today = self.time.date()
                expiries = set(contract.expiry.date() for contract in contracts)
                if today not in expiries:
                    self.log(f"Warning: No 0 DTE options found for today ({today})")
                    return
                
                # Use SpreadSelector (M3) to find suitable bull put spread
                self.log(f"Starting spread selection with {len(contracts)} option contracts")
                self.log(f"Underlying price: ${equity_price:.2f}")
                self.log(f"Selection criteria: target delta {self.spread_selector.target_delta}, max delta {self.spread_selector.max_delta}, min credit {self.spread_selector.min_credit_pct*100}% of width")
                
                # Log available strikes
                today = self.time.date()
                put_contracts = [contract for contract in contracts if contract.right == OptionRight.PUT and contract.expiry.date() == today]
                if put_contracts:
                    self.log(f"Found {len(put_contracts)} put contracts for today's expiration ({today})")
                    strikes = sorted(set([contract.strike for contract in put_contracts]))
                    self.log(f"Strike range: ${min(strikes):.2f} to ${max(strikes):.2f}")
                    
                    # Skip delta logging as it's just for diagnostic purposes
                    # We'll let the SpreadSelector handle the actual delta filtering
                    self.log(f"Will evaluate put contracts against delta ≤ {self.spread_selector.max_delta} criteria")
                    # Note: In the future, if delta diagnostics are needed, implement a
                    # calculate_option_delta method in the UniverseBuilder class
                
                spread, max_profit, max_loss, breakeven = self.spread_selector.select_bull_put_spread(
                    self._option_chain, equity_price)
                
                if spread is not None:
                    self.log(f"Found suitable bull put spread - Breakeven: ${breakeven:.2f}")
                    self.log(f"Max profit: ${max_profit:.2f}, Max loss: ${max_loss:.2f}")
                    # Execute the trade with M4 (Order Executor)
                    self.order_executor.place_spread_order(spread, max_profit, max_loss, breakeven)
                else:
                    self.log("No suitable spread found meeting selection criteria")
                    self.log(f"Possible reasons: Delta > {self.spread_selector.max_delta} or credit < {self.spread_selector.min_credit_pct*100}% of width")
            except Exception as e:
                self.error(f"Error in spread selection: {str(e)}")
        else:
            self.log("No option chain data available at 10:00 AM ET")

    def close_positions(self):
        """Mandatory closing of any open positions at 15:30 ET."""
        self.log("15:30 ET: Mandatory position close check")
        
        # First, directly check if we have any option positions
        # This is the most reliable way to determine if we need to close positions
        has_positions = self._has_option_positions()
        
        # Verify our state reflects reality and update flags
        positions_exist = self.order_executor.daily_state_verification()
        
        # Double-check that verification agrees with our direct check
        if has_positions != positions_exist:
            self.log(f"WARNING: Position detection inconsistency - direct check: {has_positions}, verification: {positions_exist}")
        
        # Use has_positions as the source of truth since it directly checks the portfolio
        if has_positions:
            self.log("Mandatory end-of-day position closure initiated based on direct position check")
            
            # Ensure the flag is set correctly (belt and suspenders approach)
            self.order_executor.spread_is_open = True
            
            # Attempt to close using standard method
            success = self.order_executor.close_spread_position(reason="(mandatory end-of-day close)")
            
            # If standard close failed, force close as a last resort
            if not success:
                self.log("Standard close method failed - forcing position liquidation")
                self.order_executor.force_close_positions(reason="(mandatory EOD liquidation)")
        else:
            self.log("No open positions to close at end of day")
            
        # Final verification that we have no positions at end of day
        still_has_positions = self._has_option_positions()
                
        if still_has_positions:
            self.log("CRITICAL: Failed to close all positions by end of day. Forcing liquidation.")
            self.order_executor.force_close_positions(reason="(final EOD liquidation)")
    
    def _has_option_positions(self):
        """Helper method to directly check if we have any open option positions.
        
        Returns:
            bool: True if we have any option positions, False otherwise
        """
        for symbol, holding in self.portfolio.items():
            if symbol.SecurityType == SecurityType.OPTION and abs(holding.quantity) > 0:
                self.log(f"Found option position: {symbol} with {holding.quantity} shares")
                return True
        return False

    def on_data(self, slice):
        """Process market data - load chains and monitor risk.
        
        Serves two purposes:
        1. Load option chains as soon as available after market open
        2. Continuous risk monitoring (stop-loss, take-profit)
        """
        # We don't need to store the slice - OrderExecutor will use universal_builder directly
        
        # Load option chains if not already loaded today
        if not self._chains_loaded_today:
            option_chain = self.universe_builder.get_option_chains(slice)
            if option_chain is not None:
                chain_list = list(option_chain)
                if len(chain_list) > 0:
                    self._option_chain = option_chain
                    self._chains_loaded_today = True
                    
                    current_time = self.time.strftime("%H:%M:%S")
                    self.log(f"Option chain loaded successfully at {current_time} with {len(chain_list)} contracts")
                    
                    # Log today's expiry details
                    today = self.time.date()
                    today_contracts = [c for c in chain_list if c.expiry.date() == today]
                    if today_contracts:
                        self.log(f"Found {len(today_contracts)} contracts expiring today ({today})")
                    else:
                        self.log(f"WARNING: No contracts found expiring today ({today})")
                else:
                    self.log(f"Option chain received but contains 0 contracts at {current_time}")
            else:
                # Only log this if it's before noon to avoid excessive logging
                if self.time.hour < 12:
                    self.log(f"Still waiting for option chain data at {self.time.strftime('%H:%M:%S')}")
        
        # Perform state verification to ensure flags match reality
        self.order_executor.reset_state()
        
        # Risk monitoring - implemented in M4 module (OrderExecutor)
        # Check for stop-loss (2× credit) and take-profit (50% max gain)
        if self._option_chain is not None and self.order_executor.spread_is_open:
            # Check if we should close based on stop-loss or take-profit
            self.order_executor.check_stop_loss(self._option_chain)
            self.order_executor.check_take_profit(self._option_chain)

    def on_order_event(self, order_event):
        """Handle order events for tracking spread status.
        
        Routes events to the order executor module to manage positions.
        
        Parameters:
            order_event (OrderEvent): The order event
        """
        # Forward to order executor module
        self.order_executor.on_order_event(order_event)

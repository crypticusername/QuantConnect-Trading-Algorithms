from AlgorithmImports import *

# Module imports
from universe_builder import UniverseBuilder   # M1: Universe building
from spread_selector import SpreadSelector     # M3: Strike selection
from order_executor import OrderExecutor       # M4: Order execution 
from risk_manager import RiskManager           # M5: Risk management

class V2CreditSpreadAlgoAlgorithm(QCAlgorithm):
    """
    Bull put credit spread strategy with modular architecture.
    
    Modules: M1 Universe, M3 Spread Selection, M4 Order Execution, M5 Risk Management
    Schedule: 9:30 Load chains, 10:00 Open trades, 15:30 Close positions
    Risk rules: Stop-loss at 2× credit, take-profit at 50% max gain
    """
    
    def log(self, message):
        """Enhanced logging that skips messages during warm-up period.
        
        Parameters:
            message: The message to log
        """
        # Skip logging during warm-up period
        if not self.is_warming_up:
            # Call the parent class's log method
            super().log(message)
    
    def critical_log(self, message):
        """Log critical messages even during warm-up period.
        
        Parameters:
            message: The message to log
        """
        # Always log critical messages regardless of warm-up
        super().log(message)
    
    def initialize(self):
        """Initialize algorithm parameters, modules, and scheduling."""
        # Algorithm parameters
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 2, 1)  # Shorter period for testing
        self.set_cash(10000)
        self.set_time_zone(TimeZones.NEW_YORK)
        self.set_warm_up(10, Resolution.DAILY)
        
        # Use critical_log for essential initialization messages
        self.critical_log("Algorithm initialized with $10,000 starting capital")
        
        # Initialize modules
        self.universe_builder = UniverseBuilder(self)                # M1
        self.universe_builder.initialize_universe("SPY", Resolution.MINUTE)
        self.universe_builder.log_method = self.log  # Pass our log method
        self.equity_symbol = self.universe_builder.equity_symbol
        self.option_symbol = self.universe_builder.option_symbol
        self.set_benchmark(self.equity_symbol)
        
        # Spread selection module (M3)
        # Note: Using default parameters (target_delta=0.15, max_delta=0.30, min_credit_pct=0.20, etc.)
        # These can be customized in spread_selector.py or by passing parameters here
        self.spread_selector = SpreadSelector(self)
        self.spread_selector.log_method = self.log  # Pass our log method
        
        # Order execution module (M4)
        self.order_executor = OrderExecutor(self)                  # M4
        self.order_executor.log_method = self.log    # Pass our log method
        
        # Risk management module (M5)
        self.risk_manager = RiskManager(self, self.order_executor)   # M5
        
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
        # Reset daily state
        self._chains_loaded_today = False
        self._option_chain = None
        
        # Reset OrderExecutor state
        self.order_executor.reset_state()
        
        # Check if we have any open positions
        has_positions = False
        for security in self.portfolio.keys():
            if "SPY" in str(security) and abs(self.portfolio[security].quantity) > 0:
                has_positions = True
                break
        
        # Consolidated log message with clear section header
        self.log(f"DAILY RESET - {'Open positions found' if has_positions else 'No open positions found'}")
        
        # Get current equity price
        equity_price = self.universe_builder.get_latest_equity_price()
        self.log(f"MARKET DATA - SPY price: ${equity_price:.2f}, Checking for option chain {self.time.strftime('%Y-%m-%d')}")

    def load_option_chains_fallback(self):
        """Fallback attempts to load option chains if not loaded at market open."""
        if not self._chains_loaded_today:
            # Try to get the option chains without verbose logging
            try:
                chain_status = self.universe_builder.get_option_chains(None)
                if chain_status is not None:
                    contracts = list(chain_status)
                    if len(contracts) > 0:
                        # Get contract breakdown
                        put_count = sum(1 for contract in contracts if contract.right == OptionRight.PUT)
                        call_count = sum(1 for contract in contracts if contract.right == OptionRight.CALL)
                        today = self.time.date()
                        today_contracts = [c for c in contracts if c.expiry.date() == today]
                        
                        # Consolidated log message for option chain data
                        self.log(f"MARKET DATA - Option chain loaded with {len(contracts)} contracts ({put_count} puts, {call_count} calls), {len(today_contracts)} expiring today")
                        self._option_chain = chain_status
                        self._chains_loaded_today = True
            except Exception as e:
                # Always log exceptions even during warm-up
                self.critical_log(f"ERROR - Option chain loading error: {str(e)}")

    def open_trades(self):
        """Open bull put credit spreads at 10:00 AM ET."""
        if not self._chains_loaded_today:
            self.log("TRADE ANALYSIS - SKIPPED - No option chains loaded for today")
            return
            
        if self._option_chain is not None:
            try:
                # Get current equity price for reference
                equity_price = self.universe_builder.get_latest_equity_price()
                
                # Consolidated trade analysis log with clear section header
                self.log(f"TRADE ANALYSIS - SPY price: ${equity_price:.2f}, Chain loaded: {self._chains_loaded_today}")
                
                # Verify today's expiry is available
                contracts = [contract for contract in self._option_chain]
                today = self.time.date()
                expiries = set(contract.expiry.date() for contract in contracts)
                if today not in expiries:
                    self.log(f"TRADE ANALYSIS - SKIPPED - No 0 DTE options found for today ({today})")
                    return
                # Format selection criteria with structured header
                self.log(f"SELECTION CRITERIA - Target delta: {self.spread_selector.target_delta}, Max delta: {self.spread_selector.max_delta}, Min credit: {self.spread_selector.min_credit_pct*100}% of width")
                
                # Log available strikes with structured header
                today = self.time.date()
                put_contracts = [contract for contract in contracts if contract.right == OptionRight.PUT and contract.expiry.date() == today]
                if put_contracts:
                    strikes = sorted(set([contract.strike for contract in put_contracts]))
                    # Consolidated options universe information
                    self.log(f"OPTIONS UNIVERSE - Strike range: ${min(strikes):.2f}-${max(strikes):.2f}, Found {len(put_contracts)} put contracts expiring today ({today})")
                    # Note: In the future, if delta diagnostics are needed, implement a
                    # calculate_option_delta method in the UniverseBuilder class
                
                spread, max_profit, max_loss, breakeven = self.spread_selector.select_bull_put_spread(
                    self._option_chain, equity_price)
                
                if spread is not None:
                    # Consolidated spread summary in a single log
                    self.log(f"SPREAD SUMMARY - Bull Put Spread selected, Breakeven: ${breakeven:.2f}, Max P/L: ${max_profit:.2f}/${max_loss:.2f}")
                    # Execute the trade with M4 (Order Executor)
                    self.order_executor.place_spread_order(spread, max_profit, max_loss, breakeven)
                else:
                    # Consolidated message for no suitable spread
                    self.log(f"SPREAD SUMMARY - No suitable spread found. Reasons: Delta > {self.spread_selector.max_delta} or credit < {self.spread_selector.min_credit_pct*100}% of width")
            except Exception as e:
                self.error(f"Error in spread selection: {str(e)}")
        else:
            self.log("No option chain data available at 10:00 AM ET")

    def close_positions(self):
        """Mandatory closing of any open positions at 15:30 ET."""
        self.log("CLOSE POSITION - Mandatory EOD close check initiated")
        # Directly check if we have any option positions
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
                    
                    # Get contract breakdown
                    put_count = sum(1 for contract in chain_list if contract.right == OptionRight.PUT)
                    call_count = sum(1 for contract in chain_list if contract.right == OptionRight.CALL)
                    today = self.time.date()
                    today_contracts = [c for c in chain_list if c.expiry.date() == today]
                    
                    # Consolidated log message for option chain data
                    self.log(f"MARKET DATA - Option chain loaded with {len(chain_list)} contracts ({put_count} puts, {call_count} calls), {len(today_contracts)} expiring today")
                else:
                    self.log(f"MARKET DATA - Warning: Option chain received but contains 0 contracts")
            else:
                # Only log this if it's before noon to avoid excessive logging
                if self.time.hour < 12:
                    self.log(f"MARKET DATA - Waiting for option chain data")
        
        # Perform state verification to ensure flags match reality
        self.order_executor.reset_state()
        
        # Risk monitoring - now implemented in M5 module (RiskManager)
        if self._option_chain is not None and self.order_executor.spread_is_open:
            # Use Risk Manager to monitor positions (currently only checking stop-loss)
            self.risk_manager.monitor_positions(self._option_chain)
            # Note: Take-profit is disabled per user request

    def on_order_event(self, order_event):
        """Handle order events for tracking spread status.
        
        Routes events to the order executor module to manage positions.
        Does not log any order events to reduce log volume.
        
        Parameters:
            order_event (OrderEvent): The order event
        """
        # No order event logging - only pass the event to the executor module
        # to reduce log volume and focus on critical algorithm information
        
        # Pass the event to the order executor module
        self.order_executor.on_order_event(order_event)

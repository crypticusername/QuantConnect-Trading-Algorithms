from AlgorithmImports import *

# Module imports
from universe_builder import UniverseBuilder   # M1: Universe building
from spread_selector import SpreadSelector     # M3: Strike selection
# Future modules:
# from order_executor import OrderExecutor     # M4: Order execution 
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
        
        # Future modules
        # self.order_executor = OrderExecutor(self)                  # M4
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
        self._current_spread = None            # Will track active spread details once M4 is added

    def load_option_chains(self):
        """Initial attempt to load option chains at market open."""
        # Reset daily state
        self._chains_loaded_today = False
        self._option_chain = None
        
        equity_price = self.universe_builder.get_latest_equity_price()
        self.log(f"SPY price at 9:30 AM ET: ${equity_price:.2f}")
        self.log("Prepared to load option chains at market open")

    def load_option_chains_fallback(self):
        """Fallback attempts to load option chains if not loaded at market open."""
        if not self._chains_loaded_today:
            current_minute = self.time.minute
            self.log(f"Fallback chain loading attempt at 9:{current_minute} AM ET")

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
                spread, max_profit, max_loss, breakeven = self.spread_selector.select_bull_put_spread(
                    self._option_chain, equity_price)
                
                if spread is not None:
                    self.log(f"Found suitable bull put spread - Breakeven: ${breakeven:.2f}")
                    self.log(f"Max profit: ${max_profit:.2f}, Max loss: ${max_loss:.2f}")
                    # Will execute the trade in M4 (Order Executor)
                    # self.order_executor.place_spread_order(spread)
                else:
                    self.log("No suitable spread found meeting selection criteria")
            except Exception as e:
                self.error(f"Error in spread selection: {str(e)}")
        else:
            self.log("No option chain data available at 10:00 AM ET")

    def close_positions(self):
        """Mandatory closing of any open positions at 15:30 ET."""
        self.log("15:30 ET: Mandatory position close check (no positions yet in this stage)")

    def on_data(self, slice):
        """Process market data - load chains and monitor risk.
        
        Serves two purposes:
        1. Load option chains as soon as available after market open
        2. Future: Continuous risk monitoring (stop-loss, take-profit)
        """
        # Load option chains if not already loaded today
        if not self._chains_loaded_today:
            option_chain = self.universe_builder.get_option_chains(slice)
            if option_chain is not None and len(list(option_chain)) > 0:
                self._option_chain = option_chain
                self._chains_loaded_today = True
                
                current_time = self.time.strftime("%H:%M:%S")
                self.log(f"Option chain loaded successfully at {current_time}")
        
        # Risk monitoring - to be implemented in M5 module
        # Will check for stop-loss (2× credit) and take-profit (50% max gain)


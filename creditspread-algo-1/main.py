from AlgorithmImports import *

class Creditspread_Algo_1Algorithm(QCAlgorithm):
    """Credit Spread Algorithm that trades 0-DTE SPY options based on directional signals.
    
    This algorithm implements a systematic credit spread strategy on SPY ETF, selling
    bull put spreads on bullish signals and bear call spreads on bearish signals.
    Trades are entered mid-morning and managed through the day to capture theta decay.
    
    Phase 1 Implementation: Basic Framework Setup
    """
    
    def Initialize(self):
        """Initialize algorithm parameters, data subscriptions, and scheduling."""
        # Set algorithm parameters
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(100000)
        self.set_time_zone(TimeZones.EASTERN_STANDARD)
        
        # Set warm-up period to ensure option Greeks are properly calculated
        self.set_warm_up(10, Resolution.DAILY)
        
        # Initialize logging
        self.debug_mode = True  # Set to False in production
        self.log("Initializing Credit Spread Algorithm")
        
        # Initialize algorithm state variables
        self.previous_day_close = 0
        self.today_open = 0
        self.entry_price = 0
        self.active_trades = {}
        
        # Add SPY equity data subscription
        self.spy = self.add_equity("SPY", Resolution.MINUTE)
        self.equity_symbol = self.spy.Symbol
        
        # Add SPY options data subscription
        self.spy_options = self.add_option("SPY", Resolution.MINUTE)
        
        # Set initial option chain filter - will be refined in Phase 2
        # For now, we're looking at options expiring within 7 days with strikes ±5 from ATM
        self.spy_options.set_filter(lambda universe: universe
                                   .include_weeklys()
                                   .strikes(-5, 5)
                                   .expiration(0, 7))
        
        self.option_symbol = self.spy_options.Symbol
        
        # Schedule algorithm entry points
        # Enter trades at 10:30 AM ET
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.at(10, 30, TimeZones.EASTERN_STANDARD), 
                         self.enter_trades)
        
        # Exit trades at 3:30 PM ET (30 min before market close)
        self.schedule.on(self.date_rules.every_day(), 
                         self.time_rules.before_market_close("SPY", 30), 
                         self.exit_trades)
        
        # Store previous day's close at the end of each day
        self.schedule.on(self.date_rules.every_day(),
                         self.time_rules.before_market_close("SPY", 5),
                         self.store_previous_close)
    
    def OnData(self, slice):
        """Event-driven method called on each data update.
        
        In Phase 1, we'll use this primarily for logging and tracking.
        More complex logic will be added in later phases.
        """
        # Store today's open price when market opens
        if self.Time.hour == 9 and self.Time.minute == 30 and self.today_open == 0:
            if self.equity_symbol in slice.Bars:
                self.today_open = slice.Bars[self.equity_symbol].Open
                self.log(f"Today's open price: ${self.today_open}")
        
        # Track option chain data for debugging
        if self.debug_mode and self.option_symbol in slice.OptionChains:
            chain = slice.OptionChains[self.option_symbol]
            # Log some basic info about the option chain
            self.log(f"Option chain contains {len(chain)} contracts")
            
            # In Phase 2, we'll add more detailed option chain analysis here
    
    def enter_trades(self):
        """Scheduled method for entering credit spread trades.
        
        In Phase 1, this is a placeholder that will be implemented in later phases.
        """
        self.log("Enter trades method called at 10:30 AM ET")
        self.log(f"Current SPY price: ${self.Securities[self.equity_symbol].Price}")
        self.log(f"Previous day's close: ${self.previous_day_close}")
        
        # Store entry price for reference
        self.entry_price = self.Securities[self.equity_symbol].Price
        
        # Credit spread construction will be implemented in Phase 3
        # Signal generation will be implemented in Phase 5
        # For now, just log the directional signal we would use
        if self.entry_price >= self.previous_day_close:
            self.log("Bullish signal detected - would enter bull put spread")
        else:
            self.log("Bearish signal detected - would enter bear call spread")
    
    def exit_trades(self):
        """Scheduled method for exiting credit spread trades.
        
        In Phase 1, this is a placeholder that will be implemented in later phases.
        """
        self.log("Exit trades method called at 3:30 PM ET")
        self.log(f"Current SPY price: ${self.Securities[self.equity_symbol].Price}")
        
        # Exit management will be implemented in Phase 6
    
    def store_previous_close(self):
        """Store the previous day's closing price for SPY."""
        self.previous_day_close = self.Securities[self.equity_symbol].Close
        self.log(f"Stored previous day's close: ${self.previous_day_close}")
    
    def log(self, message):
        """Enhanced logging method with timestamps and log levels."""
        if self.debug_mode or self.IsWarmingUp:
            self.Debug(f"{self.Time} [INFO] {message}")
        else:
            # In production, only log important messages
            self.Debug(f"{self.Time} [INFO] {message}")


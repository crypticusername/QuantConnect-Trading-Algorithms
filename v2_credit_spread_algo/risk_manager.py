from AlgorithmImports import *
import datetime

class RiskManager:
    """
    Risk Manager handles position monitoring, enforcing stop-loss, take-profit, 
    and mandatory end-of-day closures.
    
    Responsible for determining WHEN to close positions based on risk rules,
    while the Order Executor handles HOW to close positions (the mechanics).
    """
    
    def __init__(self, algorithm, order_executor):
        """
        Initialize the risk manager with configuration parameters.
        
        Parameters:
            algorithm: The algorithm instance
            order_executor: The order executor instance for closing positions
        """
        self.algorithm = algorithm
        self.order_executor = order_executor
        
        # Risk management parameters from strategy spec
        self.stop_loss_multiple = 2.0      # Close when debit ≥ 2× initial credit
        self.take_profit_pct = 0.5         # Close when P/L ≥ 50% of max profit
        self.eod_close_time = datetime.time(15, 30)  # 15:30 ET
        
        # Risk monitoring state
        self.last_check_time = None
        self.max_drawdown = 0
        self.daily_loss_limit_pct = 0.05   # 5% portfolio limit (configurable)
        
        self.algorithm.log("RISK MANAGER - Initialized with stop-loss multiple: " + 
                         f"{self.stop_loss_multiple}x, take-profit %: {self.take_profit_pct*100}%")
    
    def monitor_positions(self, option_chain):
        """
        Monitor all open positions and enforce risk parameters.
        
        Parameters:
            option_chain: Current option chain
            
        Returns:
            bool: True if any risk action was taken, False otherwise
        """
        # No active positions to monitor
        if not self.order_executor.spread_is_open:
            return False
        
        # Initialize check time if not set
        if self.last_check_time is None:
            self.last_check_time = self.algorithm.time
        
        # Check stop-loss condition (our priority)
        if self._check_stop_loss(option_chain):
            return True
        
        # We'll implement other risk checks in future updates
        return False
    
    def _check_stop_loss(self, option_chain):
        """
        Check if stop-loss threshold has been reached.
        Closes position when debit to close ≥ 2× initial credit.
        
        Parameters:
            option_chain: Current option chain
            
        Returns:
            bool: True if stop-loss triggered, False otherwise
        """
        if not self.order_executor.spread_is_open or self.order_executor.pending_close:
            return False
            
        # Get current spread details
        initial_credit = self.order_executor.current_spread_details.get('initial_credit')
        
        if initial_credit is None:
            # Skip check if we don't have initial credit information
            return False
            
        # Calculate current debit to close
        current_debit = self.order_executor.calculate_current_spread_value(option_chain)
        
        if current_debit is None:
            # Skip check if we can't calculate current spread value
            return False
            
        # Stop-loss threshold (debit ≥ 2× initial credit)
        stop_loss_threshold = initial_credit * self.stop_loss_multiple
        
        if current_debit >= stop_loss_threshold:
            # Calculate loss amount and percentage
            loss_amount = (current_debit - initial_credit) * 100  # Per contract
            max_possible_profit = initial_credit * 100  # Per contract
            loss_percentage = (loss_amount / max_possible_profit) * 100 if max_possible_profit > 0 else 0
            
            # Log stop-loss event with detailed metrics
            self.algorithm.log(f"RISK MANAGER - STOP-LOSS TRIGGERED: Current debit ${current_debit:.2f} exceeds " +
                             f"{self.stop_loss_multiple}x initial credit ${initial_credit:.2f}")
            self.algorithm.log(f"RISK MANAGER - Loss amount: ${loss_amount:.2f}, " +
                             f"Percentage of max profit: {loss_percentage:.1f}%")
            
            # Close the position
            return self.order_executor.close_spread_position(reason="stop-loss")
            
        return False
    
    def update_parameters(self, stop_loss_multiple=None, take_profit_pct=None, 
                         eod_close_time=None, daily_loss_limit_pct=None):
        """
        Update risk management parameters.
        
        Parameters:
            stop_loss_multiple: Multiple of initial credit to trigger stop-loss
            take_profit_pct: Percentage of max profit to trigger take-profit
            eod_close_time: Time to close positions (datetime.time object)
            daily_loss_limit_pct: Daily loss limit as percentage of portfolio
        """
        if stop_loss_multiple is not None:
            self.stop_loss_multiple = stop_loss_multiple
            
        if take_profit_pct is not None:
            self.take_profit_pct = take_profit_pct
            
        if eod_close_time is not None:
            self.eod_close_time = eod_close_time
            
        if daily_loss_limit_pct is not None:
            self.daily_loss_limit_pct = daily_loss_limit_pct
            
        self.algorithm.log(f"RISK MANAGER - Parameters updated: SL={self.stop_loss_multiple}x, " + 
                         f"TP={self.take_profit_pct*100}%, EOD={self.eod_close_time.strftime('%H:%M')}, " +
                         f"Daily limit={self.daily_loss_limit_pct*100}%")

from AlgorithmImports import *
from typing import Callable, Optional

class UniverseBuilder:
    """
    Module responsible for building and managing option universes.
    
    Responsibilities:
    1. Subscribe to option data
    2. Apply appropriate filters (DTE, strike range)
    3. Provide access to filtered option chains
    """
    
    def __init__(self, algorithm: QCAlgorithm):
        """
        Initialize the universe builder with algorithm reference.
        
        Parameters:
        algorithm (QCAlgorithm): The algorithm instance
        """
        self.algorithm = algorithm
        self.option_symbol = None
        self.equity_symbol = None
        self.strike_range = 20  # ±20 strikes around ATM
        self._log_method = None  # Will be set by main algorithm
    
    @property
    def log_method(self) -> Optional[Callable]:
        """Getter for log_method property"""
        return self._log_method
    
    @log_method.setter
    def log_method(self, method: Callable):
        """Setter for log_method property"""
        self._log_method = method
        
    def log(self, message: str) -> None:
        """Log a message using the provided log method or fall back to algorithm.log
        
        Parameters:
        message (str): Message to log
        """
        if self._log_method:
            self._log_method(message)
        else:
            self.algorithm.log(message)
        
    def initialize_universe(self, equity_ticker: str, resolution: Resolution) -> None:
        """
        Initialize the option universe for a given equity.
        
        Parameters:
        equity_ticker (str): Ticker symbol (e.g., 'SPY')
        resolution (Resolution): Data resolution enum
        
        Returns:
        None
        """
        # Add the equity
        equity = self.algorithm.add_equity(equity_ticker, resolution)
        self.equity_symbol = equity.Symbol
        self.log(f"Added equity {equity_ticker}")
        
        # Add the option
        option = self.algorithm.add_option(equity_ticker, resolution)
        
        # Set the filter for 0 DTE (include weeklys to get same-day expiry options)
        # and limit strike range to ±20 strikes around ATM to keep chain scan light
        option.set_filter(self._option_filter_function)
        
        # Save the option symbol
        self.option_symbol = option.Symbol
        self.log(f"Added option chain for {equity_ticker} with 0 DTE filter")
        
    def _option_filter_function(self, universe: OptionFilterUniverse) -> OptionFilterUniverse:
        """
        Filter function for option universe to select 0 DTE options within strike range.
        
        Parameters:
        universe (OptionFilterUniverse): The universe to filter
        
        Returns:
        OptionFilterUniverse: Filtered universe
        """
        # Include weeklys is essential for 0 DTE strategies
        return universe.include_weeklys() \
                      .expiration(0, 0) \
                      .strikes(-self.strike_range, self.strike_range)
    
    def get_option_chains(self, slice: Slice) -> OptionChain:
        """
        Get option chains from the current slice.
        
        Parameters:
        slice (Slice): Current data slice
        
        Returns:
        OptionChain or None: Option chain if available
        """
        # Detailed diagnostics for option chain loading
        if slice is None:
            # This can happen during diagnostic calls when slice isn't available
            # Check if we can get any option data from securities
            try:
                option_security = self.algorithm.securities[self.option_symbol]
                if option_security is not None:
                    self.log(f"Option security exists but no slice available")
                return None
            except Exception as e:
                self.log(f"Cannot access option security: {str(e)}")
                return None
        
        # Check if slice has option chains at all
        if not slice.option_chains:
            # Only log this before noon to avoid spamming logs
            if self.algorithm.time.hour < 12 and self.algorithm.time.minute % 10 == 0:  # Log every 10 minutes
                self.log(f"No option chains in slice at {self.algorithm.time.strftime('%H:%M:%S')}")
            return None
        
        # Check if our specific option symbol is in the chains
        if self.option_symbol.value not in slice.option_chains:
            # Only log this before noon to avoid spamming logs
            if self.algorithm.time.hour < 12 and self.algorithm.time.minute % 10 == 0:  # Log every 10 minutes
                available_symbols = list(slice.option_chains.keys())
                symbol_count = len(available_symbols)
                if symbol_count > 0:
                    self.log(f"Option chain slice has {symbol_count} symbols, but {self.option_symbol.value} not found")
                else:
                    self.log(f"Option chain slice is empty (has keys but no content)")
            return None
        
        # We have the chain, now check if it has content
        chain = slice.option_chains[self.option_symbol.value]
        if chain is None or len(list(chain)) == 0:
            self.log(f"Found empty option chain for {self.option_symbol.value}")
            return None
            
        # Check if today's expiry is in the chain
        today = self.algorithm.time.date()
        expiries = [contract.expiry.date() for contract in chain]
        unique_expiries = set(expiries)
        
        if today not in unique_expiries and self.algorithm.time.hour < 12:
            expiry_str = ', '.join([d.strftime('%Y-%m-%d') for d in sorted(unique_expiries)])
            self.log(f"Chain loaded but missing today's expiry. Available expiries: {expiry_str}")
        
        return chain
    
    def get_latest_equity_price(self) -> float:
        """
        Get the latest price for the underlying equity.
        
        Returns:
        float: Latest equity price
        """
        return self.algorithm.securities[self.equity_symbol].price
        
    def calculate_option_delta(self, contract) -> float:
        """
        Calculate the delta of an option contract.
        
        Parameters:
        contract (OptionContract): The option contract to calculate delta for
        
        Returns:
        float: The delta value (absolute value)
        """
        try:
            # Use the contract symbol to look up the security and get the delta from greeks
            if contract.symbol in self.algorithm.securities:
                security = self.algorithm.securities[contract.symbol]
                # If we have greeks data available, use it
                if hasattr(security, 'greeks') and security.greeks is not None and security.greeks.delta is not None:
                    return abs(security.greeks.delta)
                    
            # Fallback: use approximation based on moneyness
            # This is a simple approximation that should only be used when proper greeks are unavailable
            equity_price = self.get_latest_equity_price()
            strike_price = contract.strike
            days_to_expiry = (contract.expiry.date() - self.algorithm.time.date()).days
            
            # Very rough delta approximation
            if days_to_expiry == 0:
                # 0 DTE options - delta is approximately binary
                if contract.right == OptionRight.CALL:
                    return 1.0 if equity_price > strike_price else 0.1
                else:  # PUT
                    return 1.0 if equity_price < strike_price else 0.1
            else:
                # Simple moneyness-based approximation for non-zero DTE
                moneyness = equity_price / strike_price
                if contract.right == OptionRight.CALL:
                    # For calls: higher delta when in the money
                    return min(0.99, max(0.01, (moneyness - 0.9) * 5)) 
                else:  # PUT
                    # For puts: higher delta when in the money
                    return min(0.99, max(0.01, (1.1 - moneyness) * 5))
                    
        except Exception as e:
            self.log(f"Error calculating delta: {str(e)}")
            return 0.5  # Return a mid-range value as fallback

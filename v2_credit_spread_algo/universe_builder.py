from AlgorithmImports import *

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
        self.algorithm.log(f"Added equity {equity_ticker}")
        
        # Add the option
        option = self.algorithm.add_option(equity_ticker, resolution)
        
        # Set the filter for 0 DTE (include weeklys to get same-day expiry options)
        # and limit strike range to ±20 strikes around ATM to keep chain scan light
        option.set_filter(self._option_filter_function)
        
        # Save the option symbol
        self.option_symbol = option.Symbol
        self.algorithm.log(f"Added option chain for {equity_ticker} with 0 DTE filter")
        
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
        if slice.option_chains and self.option_symbol.value in slice.option_chains:
            return slice.option_chains[self.option_symbol.value]
        return None
    
    def get_latest_equity_price(self) -> float:
        """
        Get the latest price for the underlying equity.
        
        Returns:
        float: Latest equity price
        """
        return self.algorithm.securities[self.equity_symbol].price

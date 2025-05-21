from AlgorithmImports import *

class SpreadSelector:
    """
    Module responsible for selecting option spreads based on specified criteria.
    
    Handles:
    - Finding put options with delta ≤ 0.30, prioritizing lower delta options
    - Creating bull put spreads with appropriate width for the underlying
    - Returning spread parameters for order execution
    """
    
    def __init__(self, algorithm: QCAlgorithm, 
                 target_delta: float = 0.15, 
                 max_delta: float = 0.30, 
                 max_spread_width: float = 5.0, 
                 min_spread_width: float = 1.0,
                 min_credit_pct: float = 0.20,
                 min_credit_fallback_pct: float = 0.15,
                 width_fallbacks: list = None):
        """Initialize with reference to parent algorithm and customizable parameters.
        
        Parameters:
            algorithm: Reference to parent QCAlgorithm instance
            target_delta: Target delta to start short put selection (default: 0.15)
            max_delta: Maximum allowed delta for short puts (default: 0.30)
            max_spread_width: Maximum spread width in dollars (default: $5.00)
            min_spread_width: Minimum spread width in dollars (default: $1.00, appropriate for SPY)
            min_credit_pct: Minimum required credit as percentage of width (default: 30%)
            min_credit_fallback_pct: Minimum required credit as percentage of width for fallback (default: 15%)
            width_fallbacks: Optional list of width options to try (default: [$5.00, $4.00, $3.00, $2.00, $1.00])
        """
        self.algorithm = algorithm
        self.target_delta = target_delta  # Target delta to start short put selection
        self.max_delta = max_delta  # Maximum allowed delta for short puts
        self.max_spread_width = max_spread_width  # Maximum spread width
        self.min_spread_width = min_spread_width  # Minimum spread width
        self.min_credit_pct = min_credit_pct  # Minimum credit as percentage of width
        self.min_credit_fallback_pct = min_credit_fallback_pct  # Minimum credit as percentage of width
        
        # Set default width fallbacks if none provided
        if width_fallbacks is None:
            self.width_fallbacks = [5.0, 4.0, 3.0, 2.0, 1.0]  # Width options in priority order
        else:
            self.width_fallbacks = width_fallbacks
        
    def select_bull_put_spread(self, option_chain, underlying_price: float):
        """
        Select the best bull put spread from available options.
        Prioritizes options with delta close to target_delta, then tries different widths.
        
        Parameters:
            option_chain: Option chain containing available contracts
            underlying_price: Current price of the underlying asset
            
        Returns:
            tuple: (spread, max_profit, max_loss, breakeven) or (None, None, None, None) if no suitable spread
        """
        # Start of selection process - log initial state
        num_contracts = len(list(option_chain)) if option_chain else 0
        self.algorithm.log(f"Starting spread selection with {num_contracts} option contracts")
        self.algorithm.log(f"Underlying price: ${underlying_price:.2f}")
        self.algorithm.log(f"Selection criteria: target delta {self.target_delta:.2f}, max delta {self.max_delta:.2f}, min credit {self.min_credit_pct*100:.0f}% of width")
        
        if not option_chain or num_contracts == 0:
            self.algorithm.log("No option chain available for spread selection")
            return None, None, None, None
            
        # Extract only put options that expire today (0 DTE)
        today = self.algorithm.time.date()
        put_contracts = [contract for contract in option_chain 
                        if contract.right == OptionRight.PUT 
                        and contract.expiry.date() == today]
        
        # Log information about available put contracts
        num_puts = len(put_contracts)
        self.algorithm.log(f"Found {num_puts} put contracts for today's expiration ({today})")
        
        if not put_contracts:
            self.algorithm.log("No put options available for today's expiration")
            return None, None, None, None
            
        # Log range of available strikes and deltas
        if num_puts > 0:
            deltas = [abs(contract.greeks.delta) if contract.greeks and contract.greeks.delta else 0 for contract in put_contracts]
            strikes = [contract.strike for contract in put_contracts]
            self.algorithm.log(f"Strike range: ${min(strikes):.2f} to ${max(strikes):.2f}")
            if any(deltas):
                self.algorithm.log(f"Delta range: {min(deltas):.4f} to {max(deltas):.4f}")
            else:
                self.algorithm.log("Warning: No valid delta values found in the option chain")
            
        # Identify all valid put contracts with delta <= max_delta
        valid_short_candidates = []
        for contract in put_contracts:
            # Check if greeks exist and delta is valid
            if contract.greeks and contract.greeks.delta is not None:
                delta = abs(contract.greeks.delta)
                if delta <= self.max_delta:
                    valid_short_candidates.append(contract)
            else:
                self.algorithm.log(f"Skipping contract with strike ${contract.strike:.2f} - missing or invalid greeks")
        
        self.algorithm.log(f"Found {len(valid_short_candidates)} potential short put candidates with delta ≤ {self.max_delta}")
        
        if not valid_short_candidates:
            self.algorithm.log(f"No put options found with delta ≤ {self.max_delta}")
            return None, None, None, None
        
        # Sort ALL candidates by delta (ascending)
        valid_short_candidates.sort(key=lambda x: abs(x.greeks.delta))
        
        # Find strikes with delta less than or equal to target_delta
        target_candidates = [c for c in valid_short_candidates if abs(c.greeks.delta) <= self.target_delta]
        
        # If no strikes meet target delta criteria, start with lowest delta available
        if not target_candidates:
            self.algorithm.log(f"No strikes with delta ≤ {self.target_delta}, starting with lowest delta available")
            # Get candidates sorted by delta (ascending)
            starting_candidates = valid_short_candidates
        else:
            # Find the strike with delta closest to target_delta
            target_candidates.sort(key=lambda x: abs(self.target_delta - abs(x.greeks.delta)))
            closest_to_target = target_candidates[0]
            closest_delta = abs(closest_to_target.greeks.delta)
            
            # Get all candidates with delta >= the closest match, sorted by ascending delta
            # This ensures we start at or near our target and move UP in delta
            starting_candidates = [c for c in valid_short_candidates if abs(c.greeks.delta) >= closest_delta]
            starting_candidates.sort(key=lambda x: abs(x.greeks.delta))
        
        # Try each short strike candidate, starting with delta closest to target (0.15) and moving UP to higher deltas if needed
        for short_put in starting_candidates:
            short_strike = short_put.strike
            short_delta = abs(short_put.greeks.delta)
            short_price = short_put.LastPrice
            short_bid = short_put.BidPrice
            
            # Skip if bid price is zero or insufficient for a viable spread
            if short_bid <= 0:
                self.algorithm.log(f"Skipping short put: Strike=${short_strike:.2f}, Delta={short_delta:.4f} - No bid available")
                continue
                
            self.algorithm.log(f"Testing short put: Strike=${short_strike:.2f}, Delta={short_delta:.4f}, Bid=${short_bid:.2f}")
            
            # First pass: Check all widths for preferred credit threshold (20%)
            preferred_spread_found = False
            valid_spreads = []
            
            # Store valid spreads for both preferred and fallback thresholds
            preferred_spreads = []
            fallback_spreads = []
            
            # Try different spread widths for this short strike (starting with widest)  
            for target_width in self.width_fallbacks:
                # Skip widths below our minimum threshold
                if target_width < self.min_spread_width:
                    continue
                    
                self.algorithm.log(f"Testing width: ${target_width:.2f} with short strike ${short_strike:.2f} (delta {short_delta:.4f})")
                
                # Find long put candidates that create a spread with width <= target_width
                long_candidates = [c for c in put_contracts if c.strike < short_strike and 
                                 (short_strike - c.strike) <= target_width]
                
                if not long_candidates:
                    self.algorithm.log(f"No suitable long put options for width ≤ ${target_width:.2f}")
                    continue
                    
                # Sort by spread width descending (wider spreads first, but all ≤ target_width)
                # This prioritizes spreads closer to our target width without exceeding it
                long_candidates.sort(key=lambda x: short_strike - x.strike, reverse=True)
                
                # Select the long put with the widest spread (while still ≤ target_width)
                long_put = long_candidates[0]
                long_strike = long_put.strike
                long_delta = abs(long_put.greeks.delta) if long_put.greeks and long_put.greeks.delta else 0
                long_price = long_put.LastPrice
                long_ask = long_put.AskPrice
                
                # Calculate actual spread width
                spread_width = short_strike - long_strike
                
                # Skip if spread width is below minimum
                if spread_width < self.min_spread_width:
                    self.algorithm.log(f"Spread width ${spread_width:.2f} below minimum ${self.min_spread_width:.2f}")
                    continue
                
                # Calculate spread details
                net_credit = short_bid - long_ask  # Conservative estimate using bid-ask
                credit_percentage = (net_credit / spread_width) * 100 if spread_width > 0 else 0
                
                if net_credit <= 0:
                    self.algorithm.log(f"REJECTED: Spread has negative or zero credit: ${net_credit:.2f}")
                    continue
                
                # Check if meets preferred threshold (20%)
                min_required_credit = spread_width * self.min_credit_pct
                fallback_required_credit = spread_width * self.min_credit_fallback_pct
                
                # Store valid spreads for later comparison
                spread_info = {
                    'short_strike': short_strike,
                    'short_delta': short_delta,
                    'short_bid': short_bid,
                    'long_strike': long_strike,
                    'long_delta': long_delta,
                    'long_ask': long_ask,
                    'width': spread_width,
                    'credit': net_credit,
                    'credit_percentage': credit_percentage
                }
                
                if net_credit >= min_required_credit:
                    self.algorithm.log(f"FOUND PREFERRED: Credit ${net_credit:.2f} is {credit_percentage:.2f}% of width (≥ {self.min_credit_pct*100:.0f}%)")
                    preferred_spreads.append(spread_info)
                elif net_credit >= fallback_required_credit:
                    self.algorithm.log(f"FOUND FALLBACK: Credit ${net_credit:.2f} is {credit_percentage:.2f}% of width (≥ {self.min_credit_fallback_pct*100:.0f}%)")
                    fallback_spreads.append(spread_info)
                else:
                    self.algorithm.log(f"REJECTED: Credit ${net_credit:.2f} is only {credit_percentage:.2f}% of width (< {self.min_credit_fallback_pct*100:.0f}%)")
            
            # After checking all widths, select the best spread
            selected_spread = None
            
            # Prefer 20% spreads
            if preferred_spreads:
                # Get the spread with the highest absolute credit
                preferred_spreads.sort(key=lambda x: x['credit'], reverse=True)
                selected_spread = preferred_spreads[0]
                spread_type = "PREFERRED"
            # Fall back to 15% spreads only if no 20% spreads found
            elif fallback_spreads:
                # Get the spread with the highest absolute credit
                fallback_spreads.sort(key=lambda x: x['credit'], reverse=True)
                selected_spread = fallback_spreads[0]
                spread_type = "FALLBACK"
            
            # If we found a valid spread, return it
            if selected_spread:
                # Pull out the values from the selected spread
                short_strike = selected_spread['short_strike']
                short_delta = selected_spread['short_delta']
                short_bid = selected_spread['short_bid']
                long_strike = selected_spread['long_strike']
                long_delta = selected_spread['long_delta']
                long_ask = selected_spread['long_ask']
                spread_width = selected_spread['width']
                net_credit = selected_spread['credit']
                credit_percentage = selected_spread['credit_percentage']
                
                self.algorithm.log(f"{spread_type}: Credit ${net_credit:.2f} is {credit_percentage:.2f}% of width")
                self.algorithm.log(f"ACCEPTED: Found valid spread with width ${spread_width:.2f}, credit ${net_credit:.2f} ({credit_percentage:.2f}%)")
                self.algorithm.log(f"SPREAD DETAILS - Short: ${short_strike} (Δ{short_delta:.4f}, Bid=${short_bid:.2f}), Long: ${long_strike} (Δ{long_delta:.4f}, Ask=${long_ask:.2f})")

                    
                # Create the bull put spread using OptionStrategies
                expiry = short_put.expiry
                # Use the underlying symbol from the option chain and construct canonical option symbol
                # This gets the option symbol directly from the option contract being used
                canonical_option = short_put.symbol.canonical
                spread = OptionStrategies.bull_put_spread(canonical_option, short_strike, long_strike, expiry)
                
                # Calculate breakeven, max profit and max loss
                breakeven = short_strike - net_credit
                max_profit = net_credit * 100  # Per contract (100 shares)
                max_loss = (spread_width - net_credit) * 100  # Per contract
                risk_reward = max_loss / max_profit if max_profit > 0 else float('inf')
                
                # Log comprehensive details in a consolidated format
                self.algorithm.log(f"TRADE METRICS - Max profit: ${max_profit:.2f}, Max loss: ${max_loss:.2f}, Breakeven: ${breakeven:.2f}, Risk/Reward: {risk_reward:.2f}")
                
                return spread, max_profit, max_loss, breakeven
        
        # If we've tried all short strikes and none worked
        self.algorithm.log("Could not find any valid spread after trying all short strikes and widths")
        return None, None, None, None
    
    def calculate_current_spread_value(self, option_chain, short_strike, long_strike, initial_credit):
        """
        Calculate the current value to close an existing spread.
        
        Parameters:
            option_chain: Current option chain
            short_strike: Strike price of the short put
            long_strike: Strike price of the long put
            initial_credit: Initial credit received when opening spread
            
        Returns:
            float: Current debit to close, or None if can't be calculated
        """
        if not option_chain or len(list(option_chain)) == 0:
            return None
            
        # Get today's date
        today = self.algorithm.time.date()
        
        # Find the current prices for our strikes
        put_contracts = [contract for contract in option_chain 
                        if contract.right == OptionRight.PUT 
                        and contract.expiry.date() == today]
        
        # Find the specific contracts that match our spread
        short_put = next((c for c in put_contracts if c.strike == short_strike), None)
        long_put = next((c for c in put_contracts if c.strike == long_strike), None)
        
        if short_put is None or long_put is None:
            return None
            
        # Calculate debit to close (buy back short, sell long)
        # Using conservative prices (ask for short, bid for long)
        current_debit = short_put.AskPrice - long_put.BidPrice
        
        # Calculate profit percentage
        if initial_credit > 0:
            profit_percentage = (initial_credit - current_debit) / initial_credit
            profit_dollars = (initial_credit - current_debit) * 100  # Per contract
            
            # Only log when there's a significant change
            if abs(profit_percentage) >= 0.1:  # 10% change
                self.algorithm.log(f"Current spread value: debit ${current_debit:.2f}, " +
                                  f"P/L: ${profit_dollars:.2f} ({profit_percentage:.1%})")
        
        return current_debit

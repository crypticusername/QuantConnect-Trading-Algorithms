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
        # Start of selection process - use structured headers for logging
        num_contracts = len(list(option_chain)) if option_chain else 0
        
        # We don't need to log this as the main algorithm already logs a TRADE ANALYSIS header
        
        if not option_chain or num_contracts == 0:
            self.algorithm.log("No option chain available for spread selection")
            return None, None, None, None
            
        # Extract only put options that expire today (0 DTE)
        today = self.algorithm.time.date()
        put_contracts = [contract for contract in option_chain 
                        if contract.right == OptionRight.PUT 
                        and contract.expiry.date() == today]
        
        # Log information about available put contracts with structured header
        num_puts = len(put_contracts)
        
        if not put_contracts:
            self.algorithm.log("OPTIONS UNIVERSE - No put options available for today's expiration")
            return None, None, None, None
            
        # Consolidated logging of available options universe
        if num_puts > 0:
            deltas = [abs(contract.greeks.delta) if contract.greeks and contract.greeks.delta else 0 for contract in put_contracts]
            strikes = [contract.strike for contract in put_contracts]
            delta_info = f", Delta range: {min(deltas):.4f}-{max(deltas):.4f}" if any(deltas) else ", No valid deltas found"
            self.algorithm.log(f"OPTIONS UNIVERSE - Strike range: ${min(strikes):.2f}-${max(strikes):.2f}, {num_puts} put contracts expiring today{delta_info}")
            
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
        
        # Log candidates with structured header and more compact format
        if valid_short_candidates:
            # Sort candidates by strike price for clearer presentation
            sorted_candidates = sorted(valid_short_candidates, key=lambda x: x.strike)
            
            # Format the candidates in a compact way, limiting to key information
            if len(sorted_candidates) > 10:
                # For many candidates, show count and key statistics
                avg_delta = sum(abs(c.greeks.delta) for c in sorted_candidates) / len(sorted_candidates)
                key_strikes = sorted([c.strike for c in sorted_candidates])
                strike_range = f"${key_strikes[0]:.0f}-${key_strikes[-1]:.0f}"
                
                self.algorithm.log(f"CANDIDATES - Found {len(sorted_candidates)} potential short puts with delta ≤ {self.max_delta}, Strike range: {strike_range}, Avg delta: {avg_delta:.4f}")
            else:
                # For fewer candidates, show details of each
                candidates_details = ", ".join([f"${c.strike:.0f}/{abs(c.greeks.delta):.4f}" for c in sorted_candidates])
                self.algorithm.log(f"CANDIDATES - Found {len(sorted_candidates)} potential short puts: {candidates_details}")
        
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
                
            # Track all tested spreads for later comprehensive logging
            all_tested_spreads = []
            
            # Try different spread widths
            preferred_spreads = []
            fallback_spreads = []
            
            # Sort width fallbacks by preference (largest to smallest)
            for target_width in self.width_fallbacks:
                # Skip widths that exceed our maximum spread width
                if target_width > self.max_spread_width:
                    continue
                    
                # Skip if width is greater than distance to furthest long strike
                min_strike = min([c.strike for c in put_contracts])
                if short_strike - min_strike < target_width:
                    continue
                
                # Find long put candidates that create a spread with width <= target_width
                long_candidates = [c for c in put_contracts if c.strike < short_strike and 
                                 (short_strike - c.strike) <= target_width]
                
                if not long_candidates:
                    # Don't log individual width failures
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
                    continue
                
                # Calculate spread details
                net_credit = short_bid - long_ask  # Conservative estimate using bid-ask
                credit_percentage = (net_credit / spread_width) * 100 if spread_width > 0 else 0
                
                if net_credit <= 0:
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
                
                # Add to all_tested_spreads for summary logging
                test_result = "PREFERRED" if net_credit >= min_required_credit else \
                              "FALLBACK" if net_credit >= fallback_required_credit else "REJECTED"
                
                # Add result to the spread_info dict
                spread_info['result'] = test_result
                spread_info['required_credit'] = min_required_credit
                spread_info['fallback_required_credit'] = fallback_required_credit
                
                # Add to all tested spreads
                all_tested_spreads.append(spread_info)
                
                # Add to appropriate list for selection
                if net_credit >= min_required_credit:
                    preferred_spreads.append(spread_info)
                elif net_credit >= fallback_required_credit:
                    fallback_spreads.append(spread_info)
            
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
                
                # Create the bull put spread using OptionStrategies
                expiry = short_put.expiry
                # Use the underlying symbol from the option chain and construct canonical option symbol
                canonical_option = short_put.symbol.canonical
                spread = OptionStrategies.bull_put_spread(canonical_option, short_strike, long_strike, expiry)
                
                # Calculate breakeven, max profit and max loss
                breakeven = short_strike - net_credit
                max_profit = net_credit * 100  # Per contract (100 shares)
                max_loss = (spread_width - net_credit) * 100  # Per contract
                risk_reward = max_loss / max_profit if max_profit > 0 else float('inf')
                
                # Log summary of all tested spreads
                self._log_spread_test_summary(all_tested_spreads, short_strike)
                
                # Consolidated logging with a single comprehensive entry - keep the SPREAD SELECTED format
                self.algorithm.log(f"SPREAD SELECTED: Bull Put ${short_strike}/{long_strike}, Width=${spread_width:.2f}, Credit=${net_credit:.2f} ({credit_percentage:.2f}%), Max P/L=${max_profit:.2f}/${max_loss:.2f}, Breakeven=${breakeven:.2f}, R/R={risk_reward:.2f}")
                
                return spread, max_profit, max_loss, breakeven
        
        # If we've tried all short strikes and none worked - use consistent format
        self.algorithm.log("SPREAD SUMMARY - No valid spread found after evaluating all candidates")
        return None, None, None, None
    
    def _log_spread_test_summary(self, tested_spreads, short_strike):
        """
        Log a summary of all spreads tested during the selection process.
        
        Parameters:
            tested_spreads: List of spread info dictionaries that were tested
            short_strike: The short strike price that was being tested
        """
        if not tested_spreads:
            return
            
        # Count spread results by category
        preferred_count = sum(1 for s in tested_spreads if s['result'] == "PREFERRED")
        fallback_count = sum(1 for s in tested_spreads if s['result'] == "FALLBACK")
        rejected_count = sum(1 for s in tested_spreads if s['result'] == "REJECTED")
        
        # Get spread widths tested
        widths = sorted(set([s['width'] for s in tested_spreads]))
        width_range = f"${widths[0]:.1f}-${widths[-1]:.1f}" if len(widths) > 1 else f"${widths[0]:.1f}"
        
        # Log summary counts
        self.algorithm.log(f"SPREAD TESTS - Short strike ${short_strike}: Tested {len(tested_spreads)} combinations, " + 
                          f"Width range: {width_range}, Results: {preferred_count} preferred, {fallback_count} fallback, {rejected_count} rejected")
        
        # Log details of valid spreads (preferred and fallback)
        valid_spreads = [s for s in tested_spreads if s['result'] in ("PREFERRED", "FALLBACK")]
        if valid_spreads:
            # Sort by credit percentage descending
            valid_spreads.sort(key=lambda x: x['credit_percentage'], reverse=True)
            
            # Take top 5 at most to avoid verbose logging
            top_spreads = valid_spreads[:5]
            
            # Format details
            spread_details = []
            for s in top_spreads:
                spread_details.append(f"${s['short_strike']:.1f}/${s['long_strike']:.1f} (W=${s['width']:.1f}, C=${s['credit']:.2f}, {s['credit_percentage']:.1f}%)")
            
            # Log top spreads
            if spread_details:
                self.algorithm.log(f"TOP SPREADS - {', '.join(spread_details)}")
    
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

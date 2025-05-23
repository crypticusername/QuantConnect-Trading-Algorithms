from AlgorithmImports import *
import datetime

class OrderExecutor:
    """
    Handles order execution for credit spreads.
    Responsible for placing orders, tracking order status, and closing positions.
    """
    
    def __init__(self, algorithm):
        """
        Initialize the OrderExecutor.
        
        Parameters:
            algorithm: The algorithm instance
        """
        self.algorithm = algorithm
        self.order_tickets = []  # The most recent order tickets
        self.active_spread_orders = {}  # Dictionary to track all spread orders
        
        # State flags
        self.spread_is_open = False
        self.pending_open = False
        self.pending_close = False
        self.last_reset_date = None  # Track the last date state was reset
        
        # Logging control
        self.last_monitoring_log_time = None
        
        # Current spread details
        self.current_spread_details = {
            'short_strike': None,
            'long_strike': None, 
            'initial_credit': None,
            'max_profit': None,
            'max_loss': None,
            'breakeven': None,
            'expiry': None
        }
        
    def reset_state(self):
        """
        Reset the state flags and spread details based on current portfolio holdings.
        Should be called at the beginning of each trading day.
        """
        current_date = self.algorithm.time.date()
        
        # Only reset once per day
        if self.last_reset_date == current_date:
            return
            
        self.algorithm.log("Performing daily state reset")
        
        # Check if we actually have any option positions
        has_positions = False
        for symbol, holding in self.algorithm.portfolio.items():
            # Skip non-option holdings
            if symbol.SecurityType != SecurityType.OPTION:
                continue
                
            # We have at least one option position
            if holding.invested or abs(holding.quantity) > 0:
                has_positions = True
                self.algorithm.log(f"Found existing position in {symbol}: {holding.quantity} shares")
                break
        
        # Reset state flags if no positions actually exist
        if not has_positions:
            if self.spread_is_open or self.pending_open or self.pending_close:
                self.algorithm.log("Resetting state flags - no actual positions found")
                self.spread_is_open = False
                self.pending_open = False
                self.pending_close = False
                self._reset_spread_details()
        else:
            # Positions exist, make sure our flags reflect this
            if not self.spread_is_open and not self.pending_open and not self.pending_close:
                self.algorithm.log("Detected positions but flags were not set - correcting state")
                self.spread_is_open = True
        
        # Record that we reset state today
        self.last_reset_date = current_date
    
    def place_spread_order(self, spread, max_profit, max_loss, breakeven):
        """
        Place a bull put credit spread order using leg-by-leg limit orders.
        
        Parameters:
            spread: The spread object (from OptionStrategies)
            max_profit: Maximum profit for the spread
            max_loss: Maximum loss for the spread
            breakeven: Breakeven price for the spread
            
        Returns:
            bool: True if order was placed, False otherwise
        """
        # Verify state is correct before placing order
        self.reset_state()
        
        if self.spread_is_open or self.pending_open:
            self.algorithm.log("Cannot place order - position already open or pending")
            return False
            
        try:
            # For a bull put spread, breakeven = short_strike - net_credit
            net_credit = max_profit / 100.0  # Convert max_profit back to actual credit amount
            short_strike = breakeven + net_credit
            
            # Calculate width from max loss and profit (width = (max_loss + max_profit) / 100)
            width = (max_loss + max_profit) / 100.0
            long_strike = short_strike - width
            
            # Store the strikes for later reference - these are the actual strikes used for the spread
            # Get the expiry from today's date since we're doing 0 DTE
            expiry = self.algorithm.time.date()
            
            # Create the option contract symbols using proper QuantConnect API methods
            underlying_symbol = self.algorithm.Securities["SPY"].Symbol
            
            # Get option chain for today
            option_chain = self.algorithm.option_chain(underlying_symbol)
            
            # Get option contracts from the chain by filtering for the right strike and expiry
            # First find the option contracts that match our criteria
            short_options = [x.symbol for x in option_chain 
                           if x.right == OptionRight.PUT and abs(x.strike - short_strike) < 0.001 
                           and x.expiry.date() == expiry]
            
            long_options = [x.symbol for x in option_chain 
                          if x.right == OptionRight.PUT and abs(x.strike - long_strike) < 0.001 
                          and x.expiry.date() == expiry]
            
            # Check if we found matching contracts
            if not short_options or not long_options:
                self.algorithm.log(f"Error: Could not find matching option contracts for strikes {short_strike}/{long_strike}")
                return False
                
            short_option = short_options[0]
            long_option = long_options[0]
            
            # Already calculated net_credit earlier, don't need to recalculate
            
            # Apply a small buffer to ensure we get filled (95% of theoretical credit)
            # This means we'll accept slightly less credit to improve fill probability
            target_net_credit = net_credit * 0.95
            
            # Calculate order parameters - no logging here to reduce log volume
            
            # Get current prices to inform our limit prices
            short_option_data = self.algorithm.securities[short_option]
            long_option_data = self.algorithm.securities[long_option]
            
            # For a bull put spread, we sell the higher strike put and buy the lower strike put
            # Determine reasonable price targets for each leg based on current bid/ask
            short_bid = short_option_data.bid_price
            long_ask = long_option_data.ask_price
            
            # Calculate target prices for each leg
            # We'll accept a slightly lower price for our short option (selling)
            # and pay a slightly higher price for our long option (buying)
            # but ensure the total net credit meets our target
            short_min_price = short_bid * 0.98  # Min price we'll accept for short leg (98% of bid)
            long_max_price = short_min_price - target_net_credit  # Max price we'll pay for long leg
            
            # Ensure we're not paying more than ask for long leg
            if long_max_price > long_ask * 1.02:
                long_max_price = long_ask * 1.02  # Max 2% slippage on ask
                short_min_price = long_max_price + target_net_credit  # Adjust short price to maintain net credit
            
            # Create and submit the limit orders
            tag = f"TargetCredit:{target_net_credit}"
            
            # Placing leg-by-leg orders with consolidated logging
            self.algorithm.log(f"TRADE ORDER: Bull Put Spread ${short_strike:.2f}/${long_strike:.2f}, Width=${width:.2f}, Target Credit=${target_net_credit:.2f} - Short: ${short_min_price:.2f}, Long: ${long_max_price:.2f}")
            
            # In QuantConnect Python API, we need to use the limit_order method
            # The direction is specified as a negative quantity for selling and positive for buying
            
            # Sell the short put with a limit order (negative quantity = sell)
            short_ticket = self.algorithm.limit_order(short_option, -1, short_min_price, tag)
            
            # Buy the long put with a limit order (positive quantity = buy)
            long_ticket = self.algorithm.limit_order(long_option, 1, long_max_price, tag)
            
            # Store the tickets
            tickets = [short_ticket, long_ticket]
            self.order_tickets = tickets
            
            if not tickets or len(tickets) == 0:
                self.algorithm.log("Failed to place spread order - no order tickets returned")
                return False
            
            # No detailed ticket logging to reduce log volume
                
            # Update tracking info
            self.pending_open = True
            self.current_spread_details['short_strike'] = short_strike
            self.current_spread_details['long_strike'] = long_strike
            self.current_spread_details['expiry'] = expiry
            self.current_spread_details['initial_credit'] = target_net_credit
            self.current_spread_details['max_profit'] = max_profit
            self.current_spread_details['max_loss'] = max_loss
            self.current_spread_details['breakeven'] = breakeven
            
            # No need for detailed spread logging here - will log on fill instead
            return True
            
        except Exception as e:
            self.algorithm.error(f"Error placing spread order: {str(e)}")
            self.pending_open = False
            return False
            
    def check_stop_loss(self, option_chain):
        """
        Check if stop-loss threshold has been reached.
        
        Parameters:
            option_chain: Current option chain
            
        Returns:
            bool: True if stop-loss triggered, False otherwise
        """
        if not self.spread_is_open or self.pending_close:
            return False
            
        # Get current spread details
        short_strike = self.current_spread_details['short_strike']
        long_strike = self.current_spread_details['long_strike']
        initial_credit = self.current_spread_details['initial_credit']
        
        if initial_credit is None:
            # This is an error condition, so always log it
            self.algorithm.log("Warning: initial_credit is None, cannot evaluate stop-loss")
            return False
            
        # Calculate current debit to close
        current_debit = self.calculate_current_spread_value(option_chain)
        
        if current_debit is None:
            # Error condition, so always log it
            self.algorithm.log("Cannot calculate current spread value for stop-loss check")
            return False
            
        # Check stop-loss threshold (debit ≥ 2× credit)
        stop_loss_threshold = initial_credit * 2
        
        if current_debit >= stop_loss_threshold:
            # Always log stop-loss triggers regardless of time interval
            self.algorithm.log(f"STOP-LOSS TRIGGERED: Current debit ${current_debit:.2f} ≥ 2× initial credit ${initial_credit:.2f}")
            # Close the position
            return self.close_spread_position(reason="(stop-loss triggered)")
            
        return False
    
    def check_take_profit(self, option_chain):
        """
        Check if take-profit threshold has been reached.
        
        Parameters:
            option_chain: Current option chain
            
        Returns:
            bool: True if take-profit triggered, False otherwise
        """
        if not self.spread_is_open or self.pending_close:
            return False
            
        # Get current spread details
        initial_credit = self.current_spread_details['initial_credit']
        max_profit = self.current_spread_details['max_profit']
        
        if initial_credit is None or max_profit is None:
            # This is an error condition, so always log it
            self.algorithm.log("Warning: initial_credit or max_profit is None, cannot evaluate take-profit")
            return False
            
        # Calculate current debit to close
        current_debit = self.calculate_current_spread_value(option_chain)
        
        if current_debit is None:
            # Error condition, so always log it
            self.algorithm.log("Cannot calculate current spread value for take-profit check")
            return False
            
        # Calculate current profit
        current_profit = (initial_credit - current_debit) * 100  # Per contract
        
        # Take-profit threshold (P/L ≥ 50% of maximum profit)
        take_profit_threshold = max_profit * 0.5
        
        if current_profit >= take_profit_threshold:
            # Always log take-profit triggers regardless of time interval
            profit_percentage = (current_profit / max_profit) * 100
            self.algorithm.log(f"TAKE-PROFIT TRIGGERED: Current profit ${current_profit:.2f} is {profit_percentage:.1f}% of max profit ${max_profit:.2f}")
            # Close the position
            return self.close_spread_position(reason="take-profit")
            
        return False
    
    def close_spread_position(self, reason=""):
        """
        Close an open spread position using OptionStrategies.
        Always tries to close the spread as a single unit first, with multiple fallback methods.
        
        Parameters:
            reason: Description of why position is being closed
            
        Returns:
            bool: True if close order was placed, False otherwise
        """
        if not self.spread_is_open or self.pending_close:
            self.algorithm.log(f"Cannot close position - no open position or close already pending")
            return False
            
        # Store trade start time for duration calculation
        self.current_spread_details['close_time'] = self.algorithm.time
        self.current_spread_details['close_reason'] = reason
            
        # Format a clear POSITION CLOSE header with reason
        self.algorithm.log(f"POSITION CLOSE - {reason or 'manual close'} initiated for Bull Put ${self.current_spread_details['short_strike']}/${self.current_spread_details['long_strike']}")
            
        try:
            # STRATEGY 1: Close using OptionStrategies with current spread details
            if self._try_close_with_current_details(reason):
                return True
                
            # STRATEGY 2: Try to identify the spread from actual holdings
            if self._try_close_with_holdings(reason):
                return True
                
            # STRATEGY 3: Last resort - close positions individually
            self.algorithm.log("Could not close spread as a unit - falling back to individual orders")
            return self.force_close_positions(reason)
            
        except Exception as e:
            self.algorithm.error(f"Error closing spread position: {str(e)} - attempting force close")
            return self.force_close_positions(reason)
            
    def _try_close_with_current_details(self, reason):
        """
        Try to close the spread using current spread details and OptionStrategies.
        
        Parameters:
            reason: Description of why position is being closed
            
        Returns:
            bool: True if close order was placed, False otherwise
        """
        # Validate that we have all required details
        if (self.current_spread_details['short_strike'] is None or
            self.current_spread_details['long_strike'] is None or
            self.current_spread_details['expiry'] is None):
            self.algorithm.log("Missing required spread details for closing")
            return False
            
        # Create the spread object from current details - must use canonical option symbol
        # We need to find the canonical option symbol from the option chain
        canonical_option = None
        option_chain = None
        
        # Try to get the option chain from the algorithm's universe builder
        if hasattr(self.algorithm, 'universe_builder') and hasattr(self.algorithm, '_option_chain'):
            # Just use the existing option chain that's already loaded by on_data
            option_chain = self.algorithm._option_chain
        
        # If we can't get the option chain, we can't create the right strategy object
        if option_chain is None or len(list(option_chain)) == 0:
            self.algorithm.log("No option chain available for creating OptionStrategies object")
            return False
        
        # Find the canonical option symbol from the chain
        for contract in option_chain:
            if contract is not None and contract.symbol is not None:
                canonical_option = contract.symbol.canonical
                break
                
        if canonical_option is None:
            self.algorithm.log("Could not find canonical option symbol for closing spread")
            return False
            
        try:
            # Create the spread object - remember it needs canonical option symbol
            spread = OptionStrategies.bull_put_spread(
                canonical_option,
                self.current_spread_details['short_strike'],
                self.current_spread_details['long_strike'],
                self.current_spread_details['expiry']
            )
            
            self.algorithm.log(f"Closing bull put spread using stored details")
            
            # Sell to close (reverse of buy)
            tickets = self.algorithm.sell(spread, 1)
            
            if not tickets or len(tickets) == 0:
                self.algorithm.log("Failed to place close order via stored details")
                return False
                
            self.order_tickets = tickets
            self.pending_close = True
            
            self.algorithm.log(f"Placed spread close order: {len(tickets)} tickets created")
            return True
            
        except Exception as e:
            self.algorithm.error(f"Error closing with stored details: {str(e)}")
            return False
            
    def _try_close_with_holdings(self, reason):
        """
        Try to identify and close the spread by analyzing current holdings.
        
        Parameters:
            reason: Description of why position is being closed
            
        Returns:
            bool: True if close order was placed, False otherwise
        """
        # Find our option positions
        option_positions = []
        for symbol, holding in self.algorithm.portfolio.items():
            if symbol.SecurityType == SecurityType.OPTION and abs(holding.quantity) > 0:
                option_positions.append((symbol, holding.quantity))
                
        # We should have exactly 2 option positions for a spread
        if len(option_positions) != 2:
            self.algorithm.log(f"Expected 2 option positions, found {len(option_positions)}")
            return False
            
        # Extract details from the existing positions
        try:
            # Get the canonical symbol from either position
            canonical_option = None
            short_position = None
            long_position = None
            
            # Sort into short and long positions
            for symbol, quantity in option_positions:
                if quantity < 0:  # Short position
                    short_position = (symbol, quantity)
                else:  # Long position
                    long_position = (symbol, quantity)
                    
                # Extract canonical symbol
                if canonical_option is None and symbol.canonical is not None:
                    canonical_option = symbol.canonical
                    
            # Verify we have both positions
            if short_position is None or long_position is None:
                self.algorithm.log("Could not identify both short and long positions")
                return False
                
            # Extract strike prices
            short_strike = short_position[0].strike
            long_strike = long_position[0].strike
            
            # Verify this is a put spread (both should be puts)
            if short_position[0].right != OptionRight.PUT or long_position[0].right != OptionRight.PUT:
                self.algorithm.log("Not a put spread - unexpected option types")
                return False
                
            # Get expiry (should be the same for both)
            expiry = short_position[0].expiry.date()
            
            # Verify they have the same expiry
            if expiry != long_position[0].expiry.date():
                self.algorithm.log("Legs have different expiration dates")
                return False
                
            # Verify we have a proper bull put spread (short strike > long strike)
            if short_strike <= long_strike:
                self.algorithm.log(f"Not a bull put spread: short strike {short_strike} <= long strike {long_strike}")
                return False
                
            # Verify canonical_option is not None before creating the spread
            if canonical_option is None:
                self.algorithm.log("Error: canonical_option is None, cannot create spread to close")
                return False
                
            # Create the spread strategy object
            spread = OptionStrategies.bull_put_spread(
                canonical_option,
                short_strike,
                long_strike,
                expiry
            )
            
            # Sell to close (reverse of buy)
            tickets = self.algorithm.sell(spread, 1)
            
            if not tickets or len(tickets) == 0:
                self.algorithm.log("Failed to place close order via holdings analysis")
                return False
                
            self.order_tickets = tickets
            self.pending_close = True
            
            self.algorithm.log(f"Placed spread close order: {len(tickets)} tickets created")
            return True
            
        except Exception as e:
            self.algorithm.error(f"Error closing with holdings analysis: {str(e)}")
            return False
    
    def force_close_positions(self, reason=""):
        """
        Force close all option positions directly.
        This is a last-resort method when all spread-based closure methods fail.
        
        Parameters:
            reason: Description of why position is being closed
            
        Returns:
            bool: True if liquidation orders were placed, False if no positions to close
        """
        self.algorithm.log(f"POSITION CLOSE - Last resort: Closing individual legs {reason or ''}")
        
        # Verify we have positions to close
        has_positions = False
        liquidation_orders = []
        
        # Loop through all holdings and close option positions
        for symbol, holding in self.algorithm.portfolio.items():
            # Skip any non-option holdings or zero-quantity positions
            if symbol.SecurityType != SecurityType.OPTION or abs(holding.quantity) == 0:
                continue
                
            has_positions = True
            quantity = holding.quantity
            
            self.algorithm.log(f"Liquidating position: {symbol} x {quantity}")
            
            # Place liquidation order
            if quantity > 0:
                # Long position - Sell to close
                order = self.algorithm.sell(symbol, abs(quantity))
            else:
                # Short position - Buy to close
                order = self.algorithm.buy(symbol, abs(quantity))
                
            if order is not None:
                liquidation_orders.append(order)
        
        if not has_positions:
            self.algorithm.log("No positions found to force close - resetting state flags")
            self.spread_is_open = False
            self.pending_open = False
            self.pending_close = False
            self._reset_spread_details()
            return False
            
        if liquidation_orders:
            self.algorithm.log(f"Placed {len(liquidation_orders)} individual liquidation orders")
            self.pending_close = True
            return True
        else:
            self.algorithm.log("No liquidation orders were created - force close failed")
            return False
    
    def on_order_event(self, order_event):
        """
        Handle order events to track position status.
        
        Parameters:
            order_event: The OrderEvent
        """
        # Get information about the status
        order_status = order_event.status
        order_id = order_event.order_id
        
        # Skip order event status logging to reduce verbosity
        
        # Process based on status
        if order_status == OrderStatus.FILLED:
            self.on_order_filled(order_id, order_event.fill_price, order_event.fill_quantity, order_event)
        elif order_status == OrderStatus.CANCELED:
            self.on_order_canceled(order_event)
        elif order_status == OrderStatus.INVALID:
            self.on_order_invalid(order_event)
        # Add handlers for other statuses as needed
        elif order_status == OrderStatus.SUBMITTED:
            # Skip order submitted logging
            pass
        elif order_status == OrderStatus.PARTIALLY_FILLED:
            # Skip partial fill logging
            pass
        elif order_status == OrderStatus.NONE:
            self.algorithm.log(f"Order status none: {order_id}")
        else:
            self.algorithm.log(f"Unhandled order status: {order_status} for order {order_id}")
    
    def daily_state_verification(self):
        """
        Perform verification of state flags against actual portfolio holdings.
        This should be called daily to ensure consistency.
        Returns True if positions exist, False otherwise.
        """
        self.reset_state()
        
        # Additional verification specifically for EOD
        # This will help ensure we don't leave positions open overnight
        has_positions = False
        option_positions = []
        
        for symbol, holding in self.algorithm.portfolio.items():
            if symbol.SecurityType == SecurityType.OPTION and abs(holding.quantity) > 0:
                has_positions = True
                option_positions.append(f"{symbol}: {holding.quantity} shares")
        
        if has_positions:
            positions_str = ", ".join(option_positions)
            self.algorithm.log(f"EOD Verification found positions: {positions_str}")
            # CRITICAL: Always set spread_is_open to True if positions exist, regardless of current flags
            # This ensures we never miss closing a position due to flag inconsistency
            if not self.spread_is_open:
                self.algorithm.log("Setting spread_is_open flag to True based on actual portfolio holdings")
            self.spread_is_open = True
            return True  # Indicate positions exist
        else:
            # No positions exist - make sure flags reflect this
            if self.spread_is_open or self.pending_open or self.pending_close:
                self.algorithm.log("State flags incorrect - no positions found but flags indicated positions")
                self.spread_is_open = False
                self.pending_open = False
                self.pending_close = False
                self._reset_spread_details()
            return False  # Indicate no positions exist
    
    def on_order_filled(self, order_id, fill_price, fill_quantity, order_event):
        """
        Handler for order filled events.
        
        Parameters:
            order_id: The order id
            fill_price: The fill price
            fill_quantity: The fill quantity 
            order_event: The order event
        """
        order_ticket = self.algorithm.transactions.get_order_ticket(order_id)
        # Get the actual order object to access properties that OrderEvent doesn't have
        order = self.algorithm.transactions.get_order_by_id(order_id)
        order_tag = order.tag if order is not None else "Unknown"
        filled_asset = order_event.symbol
        
        # Add the order to active orders if not already there
        if order_id not in self.active_spread_orders:
            self.active_spread_orders[order_id] = {
                'asset': filled_asset,
                'quantity': fill_quantity,
                'price': fill_price,
                'tag': order_tag
            }
        
        # Skip detailed order logging to reduce log volume
        
        if self.pending_open:
            # Check if all legs of the spread are filled
            tickets_filled = all(ticket.status == OrderStatus.FILLED for ticket in self.order_tickets)
            
            if tickets_filled:
                # All legs are filled
                # Calculate the net credit received
                net_credit = self._calculate_net_credit()
                
                if net_credit > 0:
                    # Consolidated fill logging with single comprehensive entry
                    short_strike = self.current_spread_details['short_strike']
                    long_strike = self.current_spread_details['long_strike']
                    width = short_strike - long_strike
                    max_profit = net_credit * 100
                    max_loss = (width - net_credit) * 100
                    breakeven = short_strike - net_credit
                    
                    self.algorithm.log(f"TRADE FILLED: Bull Put Spread ${short_strike:.2f}/${long_strike:.2f}, Width=${width:.2f}, Actual Credit=${net_credit:.2f}, Max P/L=${max_profit:.2f}/${max_loss:.2f}, Breakeven=${breakeven:.2f}")
                    
                    self.spread_is_open = True
                    self.pending_open = False
                    
                    # Update the position details with actual fill values
                    self.current_spread_details['initial_credit'] = net_credit
                    self.current_spread_details['entry_time'] = self.algorithm.time
                else:
                    self.algorithm.log(f"Warning: Negative or zero net credit received: ${net_credit:.2f}")
                    
        elif self.pending_close:
            # Check if all closing orders are filled
            tickets_filled = all(ticket.status == OrderStatus.FILLED for ticket in self.order_tickets)
            
            if tickets_filled:
                # Calculate the net debit paid to close
                net_debit = self._calculate_net_debit()
                
                # Calculate profit or loss
                initial_credit = self.current_spread_details.get('initial_credit')
                short_strike = self.current_spread_details.get('short_strike')
                long_strike = self.current_spread_details.get('long_strike')
                width = 0
                if short_strike is not None and long_strike is not None:
                    width = short_strike - long_strike
                
                # Calculate trade duration if we have both open and close times
                trade_duration = ""
                start_time = self.current_spread_details.get('entry_time')
                close_time = self.current_spread_details.get('close_time')
                if start_time is not None and close_time is not None:
                    duration_minutes = int((close_time - start_time).total_seconds() / 60)
                    hours, minutes = divmod(duration_minutes, 60)
                    trade_duration = f"{hours}h {minutes}m"
                
                # Generate comprehensive trade summary
                if initial_credit is not None:
                    profit_loss = (initial_credit - net_debit) * 100  # Per contract
                    profit_pct = profit_loss / (width * 100) * 100 if width > 0 else 0
                    reason = self.current_spread_details.get('close_reason') or "manual"
                    
                    # Format a structured TRADE SUMMARY log with all key metrics
                    self.algorithm.log(
                        f"TRADE SUMMARY - Bull Put ${short_strike}/{long_strike}, Width=${width:.2f}\n" +
                        f"Entry: Credit=${initial_credit:.2f}, Exit: Debit=${net_debit:.2f}\n" +
                        f"P/L: ${profit_loss:.2f} ({profit_pct:.1f}%), Duration: {trade_duration}\n" +
                        f"Close reason: {reason}"
                    )
                else:
                    self.algorithm.log(f"POSITION CLOSED - Net debit: ${net_debit:.2f}")
                
                # Reset position flags
                self.spread_is_open = False
                self.pending_close = False
                self.order_tickets = []
                
                # Clear active orders
                self.active_spread_orders = {}
                
                # Reset position details
                self._reset_spread_details()
    
    def on_order_canceled(self, order_event):
        """
        Process canceled order events.
        
        Parameters:
            order_event: The OrderEvent from the cancellation
        """
        self.algorithm.log(f"Order {order_event.order_id} was canceled: {order_event.message}")
        
        # Reset the pending flags if all orders are canceled
        if self._all_orders_done():
            if self.pending_open:
                self.pending_open = False
                self.algorithm.log("Open order canceled")
            elif self.pending_close:
                self.pending_close = False
                self.algorithm.log("Close order canceled")
    
    def on_order_invalid(self, order_event):
        """
        Process invalid order events.
        
        Parameters:
            order_event: The OrderEvent
        """
        self.algorithm.log(f"Order {order_event.order_id} is invalid: {order_event.message}")
        
        # Reset the pending flags if all orders are invalid
        if self._all_orders_done():
            if self.pending_open:
                self.pending_open = False
                self.algorithm.log("Open order invalid")
            elif self.pending_close:
                self.pending_close = False
                self.algorithm.log("Close order invalid")
    
    def _all_orders_filled(self):
        """Check if all orders in the current batch are filled."""
        if not self.order_tickets:
            return False
            
        return all(ticket.status == OrderStatus.FILLED for ticket in self.order_tickets)
    
    def _all_orders_done(self):
        """Check if all orders in the current batch are in a terminal state."""
        if not self.order_tickets:
            return True
            
        terminal_states = [
            OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.INVALID
        ]
        
        return all(ticket.status in terminal_states for ticket in self.order_tickets)
    
    def _calculate_net_credit(self):
        """
        Calculate the net credit received from opening a spread.
        
        Returns:
            float: Net credit amount
        """
        total_credit = 0.0
        
        # Loop through all active orders
        for order_id, order_info in self.active_spread_orders.items():
            quantity = order_info['quantity']
            price = order_info['price']
            
            # Skip detailed fill logging
            # Add to total - but negate it because credit spreads are sells
            # For bull put spreads, we sell the short put (positive) and buy the long put (negative)
            total_credit -= quantity * price
            
        return total_credit
    
    def _calculate_net_debit(self):
        """
        Calculate the net debit paid when closing a spread.
        
        Returns:
            float: Net debit amount
        """
        total_debit = 0.0
        
        # Loop through all active orders
        for order_id, order_info in self.active_spread_orders.items():
            quantity = order_info['quantity']
            price = order_info['price']
            
            # Skip detailed close fill logging - remove verbosity
            
            # Add to total - but negate it because when closing a credit spread,
            # we're buying back the short put (negative) and selling the long put (positive)
            total_debit += quantity * price
            
        return total_debit
    
    def should_log_monitoring_data(self):
        """
        Determine if we should log monitoring data based on time interval.
        Only logs once per hour to reduce log volume.
        
        Returns:
            bool: True if we should log, False otherwise
        """
        current_time = self.algorithm.time
        
        # Always log in these cases
        if self.last_monitoring_log_time is None:
            self.last_monitoring_log_time = current_time
            return True
            
        # Log if it's been at least an hour since the last log
        time_diff = current_time - self.last_monitoring_log_time
        if time_diff.total_seconds() >= 3600:  # 3600 seconds = 1 hour
            self.last_monitoring_log_time = current_time
            return True
            
        # Also log if P&L changes significantly (can add this later if needed)
        
        # Default case - don't log
        return False
        
    def calculate_current_spread_value(self, option_chain):
        """
        Calculate the current value to close an existing spread.
        
        Parameters:
            option_chain: Current option chain
            
        Returns:
            float: Current debit to close, or None if can't be calculated
        """
        if not option_chain or len(list(option_chain)) == 0:
            return None
            
        # Get today's date
        today = self.algorithm.time.date()
        
        # Get our position details
        short_strike = self.current_spread_details['short_strike']
        long_strike = self.current_spread_details['long_strike']
        initial_credit = self.current_spread_details['initial_credit']
        
        if short_strike is None or long_strike is None:
            if self.should_log_monitoring_data():
                self.algorithm.log(f"Missing strike prices: short={short_strike}, long={long_strike}")
            return None
        
        should_log = self.should_log_monitoring_data()
        
        # Find the current prices for our strikes
        put_contracts = [contract for contract in option_chain 
                        if contract.right == OptionRight.PUT 
                        and contract.expiry.date() == today]
        
        if not put_contracts:
            if should_log:
                self.algorithm.log(f"POSITION UPDATE - No put contracts found for today's expiration ({today})")
            return None
        
        # Find the specific contracts that match our spread
        short_put = next((c for c in put_contracts if abs(c.strike - short_strike) < 0.001), None)
        long_put = next((c for c in put_contracts if abs(c.strike - long_strike) < 0.001), None)
        
        if short_put is None or long_put is None:
            if should_log:
                self.algorithm.log(f"POSITION UPDATE - Could not find contracts for ${short_strike}/${long_strike} spread")
            return None
            
        # Calculate debit to close (buy back short, sell long)
        # Using conservative prices (ask for short, bid for long)
        current_debit = short_put.AskPrice - long_put.BidPrice
        
        # Calculate profit percentage and log consolidated position update
        if initial_credit > 0 and should_log:
            profit_percentage = (initial_credit - current_debit) / initial_credit
            profit_dollars = (initial_credit - current_debit) * 100  # Per contract
            
            # Calculate monitoring hour (assuming 9:30 market open)
            market_open = datetime.datetime.combine(today, datetime.time(9, 30))
            # Convert to algorithm timezone
            market_open = market_open.replace(tzinfo=self.algorithm.time.tzinfo)
            hours_since_open = max(1, int((self.algorithm.time - market_open).total_seconds() / 3600) + 1)
            
            # Log consolidated position update
            self.algorithm.log(f"POSITION UPDATE - Hour {hours_since_open} - Bull Put ${short_strike}/${long_strike}: " +
                              f"Debit to close=${current_debit:.2f}, P/L=${profit_dollars:.2f} ({profit_percentage:.1%})")
        
        return current_debit
    
    def _log_active_spread(self):
        """Log the details of the active spread."""
        details = self.current_spread_details
        
        # Calculate width from short strike and long strike
        width = None
        if details['short_strike'] is not None and details['long_strike'] is not None:
            width = details['short_strike'] - details['long_strike']
        
        # Build the log message
        log_message = f"Active Bull Put Spread - "
        
        if details['short_strike'] is not None:
            log_message += f"Short=${details['short_strike']:.2f}, "
        
        if details['long_strike'] is not None:
            log_message += f"Long=${details['long_strike']:.2f}, "
        
        if width is not None:
            log_message += f"Width=${width:.2f}, "
        
        if details['max_profit'] is not None:
            log_message += f"Max Profit=${details['max_profit']:.2f}, "
        
        if details['max_loss'] is not None:
            log_message += f"Max Loss=${details['max_loss']:.2f}, "
        
        if details['breakeven'] is not None:
            log_message += f"Breakeven=${details['breakeven']:.2f}"
        
        if details['initial_credit'] is not None:
            log_message += f", Initial Credit=${details['initial_credit']:.2f}"
        
        self.algorithm.log(log_message)
    
    def _reset_spread_details(self):
        """Reset the current spread details."""
        self.current_spread_details = {
            'symbol': None,
            'short_strike': None,
            'long_strike': None,
            'expiry': None,
            'width': None,
            'initial_credit': None,
            'max_profit': None,
            'max_loss': None,
            'breakeven': None
        }

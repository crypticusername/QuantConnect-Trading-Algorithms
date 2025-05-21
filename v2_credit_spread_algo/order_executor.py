from AlgorithmImports import *

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
        
    def place_spread_order(self, spread, max_profit, max_loss, breakeven):
        """
        Place a bull put credit spread order.
        
        Parameters:
            spread: The spread object (from OptionStrategies)
            max_profit: Maximum profit for the spread
            max_loss: Maximum loss for the spread
            breakeven: Breakeven price for the spread
            
        Returns:
            bool: True if order was placed, False otherwise
        """
        if self.spread_is_open or self.pending_open:
            self.algorithm.log("Cannot place order - position already open or pending")
            return False
            
        try:
            # We get the strikes and expiry directly from the SpreadSelector
            # These parameters are passed to us with the correct values
            
            # Parse the spread's description to extract information
            description = str(spread)
            self.algorithm.log(f"Spread description: {description}")
            
            # We can't directly access the legs of the OptionStrategy object
            # Instead, let's use the description to log information about the spread
            self.algorithm.log(f"Working with a bull put spread strategy")
                
            # The max_profit and breakeven are already correct - passed from SpreadSelector
            # We'll get the actual short_strike and long_strike from the parameters
            # In a bull put spread, short_strike > long_strike
            # This matches the way SpreadSelector builds the spread
            
            # Calculate width from max loss and profit (width = (max_loss + max_profit) / 100)
            width = (max_loss + max_profit) / 100.0
            
            # These values are already correctly calculated by SpreadSelector
            short_strike = breakeven + (max_profit / 100.0)
            long_strike = short_strike - width
            
            # Store the strikes for later reference - these are the actual strikes used for the spread
            self.algorithm.log(f"Storing spread details - Short: {short_strike}, Long: {long_strike}")
            
            # Get the expiry from today's date since we're doing 0 DTE
            expiry = self.algorithm.time.date()
            
            self.algorithm.log(f"Placing bull put spread - Short: {short_strike}, Long: {long_strike}, Expiry: {expiry.strftime('%Y-%m-%d')}")
            
            # Calculate the width
            width = short_strike - long_strike
            
            # Place the spread order (1 contract in Stage 1)
            tickets = self.algorithm.buy(spread, 1)
            
            if not tickets or len(tickets) == 0:
                self.algorithm.log("Failed to place spread order - no order tickets returned")
                return False
                
            self.order_tickets = tickets
            self.pending_open = True
            
            # Record trade details
            self.current_spread_details = {
                'short_strike': short_strike,
                'long_strike': long_strike,
                'initial_credit': None,  # Set when filled
                'max_profit': max_profit, 
                'max_loss': max_loss,
                'breakeven': breakeven,
                'expiry': expiry
            }
            
            # Log the spread details we're about to use
            self._log_active_spread()
            
            self.algorithm.log(f"Placed bull put spread order: {len(tickets)} tickets created")
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
            self.algorithm.log("Warning: initial_credit is None, cannot evaluate stop-loss")
            return False
            
        # Calculate current debit to close
        current_debit = self.calculate_current_spread_value(option_chain)
        
        if current_debit is None:
            self.algorithm.log("Cannot calculate current spread value for stop-loss check")
            return False
            
        # Check stop-loss threshold (debit ≥ 2× credit)
        stop_loss_threshold = initial_credit * 2
        
        if current_debit >= stop_loss_threshold:
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
            self.algorithm.log("Warning: initial_credit or max_profit is None, cannot evaluate take-profit")
            return False
            
        # Calculate current debit to close
        current_debit = self.calculate_current_spread_value(option_chain)
        
        if current_debit is None:
            self.algorithm.log("Cannot calculate current spread value for take-profit check")
            return False
            
        # Calculate current profit
        current_profit = (initial_credit - current_debit) * 100  # Per contract
        
        # Take-profit threshold (P/L ≥ 50% of maximum profit)
        take_profit_threshold = max_profit * 0.5
        
        if current_profit >= take_profit_threshold:
            profit_percentage = (current_profit / max_profit) * 100
            self.algorithm.log(f"TAKE-PROFIT TRIGGERED: Current profit ${current_profit:.2f} is {profit_percentage:.1f}% of max profit ${max_profit:.2f}")
            # Close the position
            return self.close_spread_position(reason="(take-profit triggered)")
            
        return False
    
    def close_spread_position(self, reason=""):
        """
        Close an open spread position.
        
        Parameters:
            reason: Description of why position is being closed
            
        Returns:
            bool: True if close order was placed, False otherwise
        """
        if not self.spread_is_open or self.pending_close:
            self.algorithm.log(f"Cannot close position - no open position or close already pending")
            return False
            
        try:
            # Create the spread object from current details - must use canonical option symbol
            # We need to find the canonical option symbol from the option chain
            canonical_option = None
            option_chain = None
            
            # Try to get the option chain from the algorithm's universe builder
            if hasattr(self.algorithm, 'universe_builder') and hasattr(self.algorithm, '_option_chain'):
                # Just use the existing option chain that's already loaded by on_data
                option_chain = self.algorithm._option_chain
            
            # If that didn't work, we can't access the option chain
            if option_chain is None or len(list(option_chain)) == 0:
                self.algorithm.log("No option chain available for closing spread - retry next data update")
                return False
            
            # Check if we have an option chain now
            if option_chain is not None and len(list(option_chain)) > 0:
                # Find the first contract to get its canonical symbol
                for contract in option_chain:
                    if contract is not None and contract.symbol is not None:
                        canonical_option = contract.symbol.canonical
                        break
                
                if canonical_option is not None:
                    spread = OptionStrategies.bull_put_spread(
                        canonical_option,
                        self.current_spread_details['short_strike'],
                        self.current_spread_details['long_strike'],
                        self.current_spread_details['expiry']
                    )
                else:
                    self.algorithm.log("Could not find canonical option symbol for closing spread")
                    return False
            else:
                self.algorithm.log("No option chain available for closing spread")
                return False
            
            self.algorithm.log(f"Closing bull put spread {reason}")
            
            # Sell to close (reverse of buy)
            tickets = self.algorithm.sell(spread, 1)
            
            if not tickets or len(tickets) == 0:
                self.algorithm.log("Failed to place close order - no order tickets returned")
                return False
                
            self.order_tickets = tickets
            self.pending_close = True
            
            self.algorithm.log(f"Placed spread close order: {len(tickets)} tickets created")
            return True
            
        except Exception as e:
            self.algorithm.error(f"Error closing spread position: {str(e)}")
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
        
        # Log the event for tracking
        self.algorithm.log(f"Order Event: ID={order_id}, Status={order_status}")
        
        # Process based on status
        if order_status == OrderStatus.FILLED:
            self.on_order_filled(order_id, order_event.fill_price, order_event.fill_quantity, order_event)
        elif order_status == OrderStatus.CANCELED:
            self.on_order_canceled(order_event)
        elif order_status == OrderStatus.INVALID:
            self.on_order_invalid(order_event)
        # Add handlers for other statuses as needed
        elif order_status == OrderStatus.SUBMITTED:
            self.algorithm.log(f"Order submitted: {order_id}")
        elif order_status == OrderStatus.PARTIALLY_FILLED:
            self.algorithm.log(f"Order partially filled: {order_id}, Quantity: {order_event.fill_quantity}")
        elif order_status == OrderStatus.NONE:
            self.algorithm.log(f"Order status none: {order_id}")
        else:
            self.algorithm.log(f"Unhandled order status: {order_status} for order {order_id}")
    
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
        
        self.algorithm.log(f"ORDER FILLED: OrderId: {order_id}, Tag: {order_tag}, " + 
                           f"{filled_asset}, qty: {fill_quantity}, price: ${fill_price:.2f}")
        
        if self.pending_open:
            self.algorithm.log("This is a fill for an opening order")
            # Check if all legs of the spread are filled
            tickets_filled = all(ticket.status == OrderStatus.FILLED for ticket in self.order_tickets)
            
            if tickets_filled:
                # All legs are filled
                # Calculate the net credit received
                net_credit = self._calculate_net_credit()
                
                if net_credit > 0:
                    self.algorithm.log(f"Spread position opened - Net credit: ${net_credit:.2f}")
                    self.spread_is_open = True
                    self.pending_open = False
                    
                    # Update the position details with actual fill values
                    self.current_spread_details['initial_credit'] = net_credit
                    
                    # Log detailed opening information
                    self._log_active_spread()
                else:
                    self.algorithm.log(f"Warning: Negative or zero net credit received: ${net_credit:.2f}")
                    
        elif self.pending_close:
            self.algorithm.log("This is a fill for a closing order")
            # Check if all closing orders are filled
            tickets_filled = all(ticket.status == OrderStatus.FILLED for ticket in self.order_tickets)
            
            if tickets_filled:
                # Calculate the net debit paid to close
                net_debit = self._calculate_net_debit()
                
                # Calculate profit or loss
                initial_credit = self.current_spread_details.get('initial_credit')
                
                if initial_credit is not None:
                    profit_loss = (initial_credit - net_debit) * 100  # Per contract
                    self.algorithm.log(f"Spread position closed - Net debit: ${net_debit:.2f}, P/L: ${profit_loss:.2f}")
                else:
                    self.algorithm.log(f"Spread position closed - Net debit: ${net_debit:.2f}")
                
                # Reset position flags
                self.spread_is_open = False
                self.pending_close = False
                self.order_tickets = []
                
                # Clear active orders
                self.active_spread_orders = {}
                
                # Log that we're resetting the spread details
                self.algorithm.log("Resetting spread details after successful close")
                
                # Reset position details
                self.current_spread_details = {
                    'short_strike': None,
                    'long_strike': None, 
                    'initial_credit': None,
                    'max_profit': None,
                    'max_loss': None,
                    'breakeven': None,
                    'expiry': None
                }
    
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
            
            self.algorithm.log(f"Fill details: Quantity={quantity}, Price=${price:.2f}")
            
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
            
            self.algorithm.log(f"Close fill details: Quantity={quantity}, Price=${price:.2f}")
            
            # Add to total - but negate it because when closing a credit spread,
            # we're buying back the short put (negative) and selling the long put (positive)
            total_debit += quantity * price
            
        return total_debit
    
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
            self.algorithm.log(f"Missing strike prices: short={short_strike}, long={long_strike}")
            return None
        
        self.algorithm.log(f"Looking for put contracts at strikes {short_strike} and {long_strike}")
        
        # Find the current prices for our strikes
        put_contracts = [contract for contract in option_chain 
                        if contract.right == OptionRight.PUT 
                        and contract.expiry.date() == today]
        
        if not put_contracts:
            self.algorithm.log(f"No put contracts found for today's expiration ({today})")
            return None
            
        # Log available strikes to debug
        strikes = sorted([c.strike for c in put_contracts])
        self.algorithm.log(f"Available put strikes: {strikes[:5]}...{strikes[-5:]}")
        
        # Find the specific contracts that match our spread
        short_put = next((c for c in put_contracts if abs(c.strike - short_strike) < 0.001), None)
        long_put = next((c for c in put_contracts if abs(c.strike - long_strike) < 0.001), None)
        
        if short_put is None:
            self.algorithm.log(f"Could not find short put at strike {short_strike}")
            return None
            
        if long_put is None:
            self.algorithm.log(f"Could not find long put at strike {long_strike}")
            return None
            
        # Calculate debit to close (buy back short, sell long)
        # Using conservative prices (ask for short, bid for long)
        current_debit = short_put.AskPrice - long_put.BidPrice
        
        self.algorithm.log(f"Found contracts - Short Put: ${short_strike} (Ask=${short_put.AskPrice:.2f}), Long Put: ${long_strike} (Bid=${long_put.BidPrice:.2f})")
        self.algorithm.log(f"Current debit to close: ${current_debit:.2f}")
        
        # Calculate profit percentage
        if initial_credit > 0:
            profit_percentage = (initial_credit - current_debit) / initial_credit
            profit_dollars = (initial_credit - current_debit) * 100  # Per contract
            
            self.algorithm.log(f"Current P/L: ${profit_dollars:.2f} ({profit_percentage:.1%})")
        
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

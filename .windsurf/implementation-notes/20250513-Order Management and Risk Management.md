# Implementation Notes: Order Management and Risk Management

## Problem/Feature Description
Implementing stop-loss orders (e.g., StopMarketOrder, StopLimitOrder) for option credit spreads. The stop should be triggered based on the net value/price of the spread, and both legs of the spread must be closed simultaneously.

## Documentation Research Summary
The refined searches confirm that there isn't a built-in QuantConnect feature to place a stop-loss directly on the net value of an option spread that automatically closes all legs. This means we'll need to implement this logic manually.

Here's a summary of the findings:

1.  **No Direct Stop-Loss for Spreads:** The documentation and examples do not show a method like `StopMarketOrder(spread_symbol, net_spread_stop_price)`. Standard stop orders (`StopMarketOrder`, `StopLimitOrder`) are designed for individual securities based on their own prices.

2.  **Manual Implementation is Key:** To achieve your goal, we'll need to:
    *   **Track Spread Legs:** After opening a spread (e.g., using `OptionStrategies.bear_call_spread`), keep references to the individual option contracts or their `OrderTicket`s/`SecurityHolding` objects.
    *   **Calculate Net Spread Value/P&L:** In `on_data` (or a scheduled method):
        *   Get the current market price (bid/ask/last) of each leg.
        *   Calculate the current mark-to-market net value of the spread. For a credit spread, this is typically (Credit Received Initially) + (Current Value of Short Leg(s)) - (Current Value of Long Leg(s)). Or, more simply, monitor the P&L of the combined position.
        *   The P&L of the strategy can be tracked by summing the P&L of individual legs: `self.portfolio[short_leg_symbol].unrealized_profit + self.portfolio[long_leg_symbol].unrealized_profit`.
    *   **Implement Stop-Loss Logic:**
        *   Define your stop-loss condition (e.g., if net P&L < -X dollars, or if current net credit drops by Y%).
        *   If the condition is met, trigger the closure of all legs.
    *   **Simultaneous Closure:**
        *   When the stop condition is hit, iterate through the contracts forming the spread.
        *   Submit `MarketOrder()` or `LimitOrder()` for each leg to liquidate the position (e.g., buy back short options, sell long options). This ensures both legs are targeted for closure as simultaneously as possible. Using `OptionStrategies` is primarily for *entering* positions with defined risk. Exiting based on a custom net value stop-loss will likely require manual closure of each leg.

3.  **Relevant QuantConnect Tools:**
    *   `OptionStrategies` for initiating the spread.
    *   `self.portfolio[symbol].invested`, `self.portfolio[symbol].unrealized_profit`, `self.portfolio[symbol].quantity`.
    *   `self.market_order(symbol, quantity_to_close)`.
    *   Storing initial credit received or debit paid for P&L calculations.

The example algorithms like `BasicTemplateOptionsDailyAlgorithm.py` (from previous search results) show basics of handling options but don't cover this specific advanced stop-loss mechanism for spreads. We'll need to synthesize these concepts.

## Key Code Examples

```python
# Placeholder for relevant code examples as they are developed/found.
# Example: How to access portfolio holdings for spread legs
# if self.portfolio[short_put_symbol].invested and self.portfolio[long_put_symbol].invested:
#     current_short_value = self.securities[short_put_symbol].price
#     current_long_value = self.securities[long_put_symbol].price
#     # Further P&L or net value calculation...
```

## Implementation Approach
1.  Define a class or data structure to manage active credit spreads, including their legs and initial credit.
2.  In `on_data` or a scheduled method, iterate through active spreads.
3.  For each spread, calculate its current net P&L.
4.  Check if the P&L has breached the defined stop-loss level.
5.  If breached, generate `MarketOrder` (or `LimitOrder`) calls to liquidate all legs of that specific spread.
6.  Ensure order tags or other mechanisms are used to associate the closing orders with the specific spread being stopped out.

## References
- [Documentation Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/Documentation)
- [Lean CLI Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/lean-cli)
- [Lean Engine Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/Lean)


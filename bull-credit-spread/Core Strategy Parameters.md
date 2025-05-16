# Core Strategy Parameters & Future Enhancements for Bull/Bear Credit Spread Algorithm

This document outlines the key parameters, current settings, and planned future enhancements for the credit spread trading algorithm.

## I. Core Strategy Parameters (Currently Implemented & Tuned)

These parameters are active in the current version of the `bull-credit-spread` algorithm.

1.  **Short Put Delta Target (for Bull Put Spreads):**
    *   *Current Value:* `<= 0.30` (absolute value)
    *   *Status:* Implemented and actively tested.
    *   *Note:* This will have a counterpart for Bear Call Spreads (e.g., Short Call Delta Target).

2.  **Spread Width:**
    *   *Current Value:* `$5`
    *   *Status:* Implemented and actively tested.

3.  **Trade Entry Time (Scheduled):**
    *   *Current Value:* 10:00 AM ET (via `self.schedule.on` and `self.time_rules.at(10, 0)`)
    *   *Status:* Implemented.
    *   *Optimization Potential:* Could be made a parameter (e.g., try 9:45 AM, 10:15 AM, various times based on market conditions).

4.  **Trade Exit Time (Scheduled):**
    *   *Current Value:* 15 minutes before market close on the day the option is set to expire (via `self.schedule.on` and `self.time_rules.before_market_close(self.option_symbol, 15)`)
    *   *Status:* Implemented.
    *   *Optimization Potential:* Could be made a parameter (e.g., 30 mins before close, 60 mins before close, or X days prior to expiration to manage gamma/assignment risk).

5.  **Stop Loss:**
    *   *Current Value:* Triggered if the current debit to close the spread is `>= 2x` the initial credit received.
    *   *Status:* Implemented and actively tested.
    *   *Implementation Details:*
        *   Initial credit is estimated at order submission and refined upon fill.
        *   Stop-loss target debit is calculated as `initial_credit * 2.0`.
        *   Checked periodically; if triggered, sets a flag to close the position.

## II. Key Parameters for Future Implementation & Optimization

These are parameters and features planned for addition and subsequent optimization.

6.  **Days to Expiration (DTE) for Entry:**
    *   *Current Logic:* The `option.set_filter` uses a broad `expiration(0, 30)` days, and the code currently picks the soonest available expiry from this filtered set.
    *   *Status:* Partially implemented (initial broad filter).
    *   *Future Intent:* To target a specific DTE range (e.g., 7-14 DTE, 21-35 DTE, 30-45 DTE) as a configurable and optimizable parameter.

7.  **Profit Target:**
    *   *Current Value:* Not implemented.
    *   *Status:* To be added.
    *   *Example:* Close spread if 50% of maximum potential profit (initial credit received) is achieved.

8.  **Directional Indicator:**
    *   *Current Value:* Not implemented.
    *   *Status:* To be added. This is a **critical component** and represents the true "edge" of the strategy beyond simple rules-based option selling.
    *   *Elaboration:* The intent is for this to be an expansive and evolving feature. It can incorporate various types of indicators, which will be implemented and experimented with incrementally:
        *   **Technical Indicators:** E.g., Moving Averages (simple, exponential), RSI, MACD, Bollinger Bands, Volume Profiles.
        *   **Fundamental Indicators:** E.g., analysis based on earnings events, economic data releases, sector strength.
        *   **Sentiment Indicators:** E.g., news sentiment analysis, social media sentiment, VIX term structure.
        *   **AI-Driven/Machine Learning Models:** Predictive models trained on various market data.
    *   *Goal:* To identify robust signals for predicting short-to-medium term market direction for the chosen underlying(s).

9.  **Strategy Direction (Bi-Directional Trading):**
    *   *Current State:* Uni-directional (Bull Put Spreads only).
    *   *Status:* To be added.
    *   *Future Intent:* To evolve into a bi-directional strategy capable of trading:
        *   **Bull Put Spreads:** For bullish or neutral-to-bullish market outlooks.
        *   **Bear Call Spreads:** For bearish or neutral-to-bearish market outlooks.
    *   *Implementation Notes:* The selection between bull puts and bear calls will likely be driven by the `Directional Indicator`. This major feature might be implemented in stages, potentially before or after a sophisticated directional indicator is fully developed.

## III. Foundational Strategy Settings (Currently In Place or Planned Expansion)

These are broader settings that define the operational context of the strategy.

10. **Underlying Asset(s):**
    *   *Current Value:* SPY (single asset).
    *   *Status:* Implemented (hardcoded for SPY).
    *   *Future Intent:* To significantly expand this into a **multi-asset strategy**. The goal is to apply the core logic to a diverse basket of liquid, optionable underlying assets (e.g., other major indices like QQQ, IWM; potentially individual large-cap stocks or ETFs from various sectors). This will involve parameterizing asset selection or creating a dynamic framework to manage trades across multiple symbols.

11. **Number of Contracts per Spread:**
    *   *Current Value:* 1 contract per spread.
    *   *Status:* Implemented (hardcoded in `self.buy(bull_put_spread, 1)`).
    *   *Future Intent:* To make this dynamic, potentially based on account size, risk tolerance, position sizing rules (e.g., fixed fractional, Kelly criterion variant).

12. **Maximum Active Spreads (Portfolio Level):**
    *   *Current Value:* Effectively 1 (due to `self.spread_open` flag logic for a single asset).
    *   *Status:* Implemented for single-asset context.
    *   *Future Intent:* With multi-asset and bi-directional trading, this will need to be a more sophisticated risk management parameter (e.g., max concurrent spreads per asset, max total capital allocated to spreads, overall portfolio heat limits).

13. **Option Chain Strike Range Filter (Initial Filter):**
    *   *Current Value:* `strikes(-20, +20)` relative to ATM in the initial `option.set_filter`.
    *   *Status:* Implemented.
    *   *Note:* This is a broad initial filter to ensure necessary contracts are available. The precise leg selection is then driven by delta, spread width, and DTE rules.

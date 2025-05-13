# Futures Bull Credit Spread Strategy

## Overview
This strategy implements a Bull Put Credit Spread on E-mini S&P 500 (ES) futures options. The goal is to profit from the underlying future's price staying above the short put strike or rising, collecting a net premium when the spread is established.

## Market Hypothesis
The strategy assumes that the E-mini S&P 500 future will not decline significantly below the chosen short put strike price by the option's expiration. It aims to capitalize on time decay (theta) and potentially a rise in the underlying future's price.

## Key Components
- **Assets**:
    - Underlying: E-mini S&P 500 Futures (ES)
    - Traded Instruments: Options on ES Futures (Puts)
- **Time Frame**:
    - Options DTE: Configurable, typically 7-45 days (MinDTE, MaxDTE parameters).
    - Entry Time: Scheduled, e.g., 10:00 AM New York Time.
    - Exit Time: Scheduled, e.g., 15 minutes before options market close.
- **Entry Criteria**:
    1. Identify the active (e.g., front-month) ES future contract.
    2. Select put options for this specific future contract with DTE between `MinDTE` and `MaxDTE`.
    3. **Short Put**: Select an Out-of-the-Money (OTM) put option with a delta around a configurable target (e.g., 0.30).
    4. **Long Put**: Select an OTM put option with a strike price approximately `SpreadWidth` points below the short put's strike.
    5. Construct a Bull Put Spread (Sell higher strike Put, Buy lower strike Put).
    6. Ensure the spread is marketable (legs have valid bid/ask quotes).
- **Exit Criteria**:
    - Scheduled exit time (e.g., 15 minutes before market close on expiration day or a predefined earlier exit).
    - The current implementation liquidates all legs of the spread.
- **Position Sizing**:
    - Fixed number of spread contracts (configurable via `Contracts` parameter).
- **Risk Management**:
    - **Max Loss**: Defined by (Difference in Strikes - Net Credit Received) * Number of Spreads * Multiplier.
    - **Max Profit**: Net Credit Received * Number of Spreads * Multiplier.
    - Stop losses are not explicitly implemented in this version but can be added based on spread value or underlying price movement.

## Expected Performance
*[Performance expectations, drawdowns, Sharpe ratio targets, etc. should be determined through backtesting and parameter optimization.]*

## Limitations
- Sensitive to correct DTE and delta selection.
- Futures options can have wider bid-ask spreads than equity options, impacting fill prices.
- Assignment risk on short options, although typically managed by closing before expiration.
- Requires careful management of futures contract rollovers if holding positions across expirations (this version focuses on shorter-term option trades).

## Implementation Notes
- The `underlying_future_symbol` passed to `OptionStrategies.bull_put_spread` must be the specific future contract symbol (e.g., `/ESM4`), not the canonical root symbol (`/ES`).
- `marketable_option_strategy` ensures that both legs of the spread have valid quotes before attempting to trade.
- Delta calculation for futures options is available via `contract.greeks.delta`.
- The `active_spread_legs` list tracks the specific option contract symbols that form the open spread for easier liquidation.

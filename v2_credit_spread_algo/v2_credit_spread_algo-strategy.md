# V2 Credit Spread Algorithm Strategy

## Overview
A modular credit spread trading algorithm designed to systematically sell vertical option spreads on liquid ETFs, indices, and futures. The strategy capitalizes on option time decay (theta) through well-defined, risk-controlled positions with specific entry and exit parameters.

## Market Hypothesis
This strategy exploits:
1. The statistical tendency of markets to remain within expected ranges
2. Accelerated time decay (theta) of options approaching expiration
3. Mean-reversion mechanics in liquid markets
4. The ability to precisely define and limit risk with vertical spreads

## Key Components

### Static Parameters (Stage 1 - Bull Put MVP)
- **Assets**: SPY options (expanding to SPX, NQ, ES, QQQ, IWM in later stages)
- **Time Frame**: 0 DTE only (same-day expiries)
- **Strategy Type**: Bull put spreads only (calls disabled in Stage 1)
- **Short-leg Delta**: ≤ 0.30 (targeting ~70% probability of profit)
- **Spread Width**: $5.00 cap (accepting 0.5-5.0 if needed)
- **Entry Time**: 10:00 ET (avoiding open-bell volatility)
- **Mandatory Exit**: 15:30 ET (30 minutes before market close)
- **Stop-loss**: Close when debit to close ≥ 2× initial credit (hard exit)
- **Take-profit**: Close when P/L ≥ 50% of maximum potential profit
- **Position Size**: 1 contract in Stage 1 (later: 1-2% NAV per spread)
- **Max Concurrent**: 1 per asset (SPY only in Stage 1)
- **Strike Filter**: ±20 strikes around ATM (keeping chain scan efficient)

### Execution Flow
1. **09:50 ET**: Load SPY option chain with appropriate filters
2. **10:00 ET**: Evaluate puts with delta ≤ 0.30, select short put and long put $5 lower
3. **Intraday**: Monitor for stop-loss and take-profit conditions
4. **15:30 ET**: Mandatory closure of any open spreads before end of day
5. **Logging**: Record P/L, drawdown, and fill information

## Development Roadmap

| Stage | Goal                           | Modules Activated    | Success Criteria                           |
| ----- | ------------------------------ | -------------------- | ------------------------------------------ |
| **0** | Scaffold + logging             | M1                   | Pulls option chains                        |
| **1** | MVP bull-put 0‑DTE on SPY      | M1, M3, M4, basic M5 | Opens/closes 1 spread/day; respects params |
| **2** | Risk refinement                | Enhanced M5          | Stop-loss & take-profit validate           |
| **3** | Bear-call capability           | M3                   | Symmetric behavior for calls               |
| **4** | Direction selector integration | M2                   | Trades put vs call per signal              |
| **5** | Position sizing & multi-asset  | M6, expanded M1      | ≤2% NAV per spread; 1 trade per asset      |
| **6** | Analytics & optimisation       | M7                   | Walk-forward tests; dashboards             |

## Architectural Modules

| #  | Module                | Core Responsibility                             |
| -- | --------------------- | ----------------------------------------------- |
| M1 | Universe Builder      | Gather option chains, apply strike-range filter |
| M2 | Signal Engine         | Output BULL / BEAR / NONE for the session       |
| M3 | Spread Selector       | Choose strikes & width to meet Δ and risk specs |
| M4 | Order Executor        | Route orders, verify fills, record net credit   |
| M5 | Risk Manager          | Enforce stop-loss, take-profit, hard EOD close  |
| M6 | Portfolio Controller  | Size trades, limit concurrent risk              |
| M7 | Analytics & Optimiser | Capture metrics, run walk-forward tests         |

## Limitations
- Susceptible to sudden volatility spikes and gap moves
- Underperforms in strongly directional markets counter to position bias
- Early assignment risk (though mitigated by using spreads)
- Path dependency can impact performance despite correct directional bias
- 0 DTE approach requires careful timing around market close

## Implementation Approach
- Each module implemented as its own `.py` file alongside `main.py`
- Modular testing with short backtests after each component addition
- Small, focused commits for easy rollback capability
- Incremental feature activation following the development roadmap

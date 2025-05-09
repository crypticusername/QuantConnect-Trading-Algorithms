Creditspread Algo 1 Strategy

Overview

A systematic 0-DTE credit spread strategy on the SPY ETF that sells defined-risk bull-put spreads on mild bullish signals and bear-call spreads on mild bearish signals. Trades enter mid-morning, size to risk a fixed percentage of capital, and manage exits intraday to capture theta decay while avoiding assignment.

Market Hypothesis

Short-dated options often misprice near expiration due to rapid time decay and intraday mean-reversion. By selling OTM credit spreads when SPY gaps slightly above or below prior close, the strategy collects premium while relying on limited directional moves and time decay to generate consistent profits.

Key Components
	•	Assets:
SPY (SPDR S&P 500 ETF) and its same-day-expiry (0-DTE) options.
	•	Time Frame:
Intraday; enter at 10:30 AM ET, exit by 3:30 PM ET (30 min before close).
	•	Entry Criteria:
	•	Price at entry ≥ previous day’s close → sell bull-put spread
	•	Price at entry < previous day’s close → sell bear-call spread
	•	Short-leg Δ target ≈ 0.30 ± 0.05 to balance premium vs. probability
	•	Exit Criteria:
	•	Stop-Loss: buy back if cost to close ≥ 1.25 × initial credit
	•	Pre-Close Exit: close any ITM spreads at 3:30 PM ET
	•	OTM Expiry: allow out-of-the-money spreads to expire worthless
	•	Position Sizing:
	•	Risk per trade = 2 % of portfolio value
	•	Contracts = ⌊(port × 2 %) / (max_loss_per_contract)⌋ with minimum 1
	•	Risk Management:
	•	Minimum credit ≥ 25 % of spread width (e.g. $0.25 on $1 width)
	•	Use defined-risk combo orders (OptionStrategies.BullPutSpread / BearCallSpread) to limit assignment risk

Expected Performance
	•	Sharpe Ratio: target > 1.0
	•	Win Rate: ~ 60–75 % of spreads expire worthless
	•	Maximum Drawdown: aim to keep < 5 % during normal market conditions
	•	Return Profile: small, consistent premiums with limited downside

Limitations
	•	Gamma Risk: rapid directional moves can blow past strikes before time decay accrues
	•	VIX Spikes: sudden volatility surges can widen spreads and increase cost to close
	•	Liquidity Constraints: OTM strikes on 0-DTE may have wide bid/ask spreads before 10:30 AM
	•	Black-Swan Events: unanticipated gap moves overnight or intraday can overwhelm stop-loss

Implementation Notes
	•	Use from AlgorithmImports import * and subclass QCAlgorithm
	•	Subscribe via self.add_option("SPY", Resolution.MINUTE) with opt.set_filter(lambda u: u.include_weeklys().strikes(-n,n).expiration(0,0))
	•	Schedule entry at self.schedule.on(self.time_rules.at(10, 30, TimeZones.EASTERN_STANDARD), self.enter_trades)
	•	Schedule exit at self.schedule.on(self.time_rules.before_market_close("SPY", 30), self.exit_trades)
	•	Warm up Greeks with self.set_warm_up(10, Resolution.DAILY) to ensure option Greeks are available
	•	Use Lean CLI cloud commands (lean cloud backtest, lean cloud push) to iterate on main.py only
	•	Implement spreads via OptionStrategies.bull_put_spread / OptionStrategies.bear_call_spread for correct margin handling

Development & Implementation Plan

The strategy will be implemented incrementally in the following order of priority:

1. **Basic Framework Setup**
   - Set up data subscriptions and logging
   - Configure algorithm parameters (cash, dates, etc.)
   - Implement basic event handlers

2. **Option Chain Filtering & Expiration Control**
   - Create flexible filters to target specific expirations (0-DTE, 1-DTE, etc.)
   - Implement functions to select appropriate expiration dates
   - Test chain filtering with different DTE parameters

3. **Credit Spread Construction**
   - Implement bull put and bear call spread creation
   - Ensure proper use of OptionStrategies API
   - Verify margin requirements are correctly calculated
   - Test spread creation with different width parameters

4. **Order Execution & Error Handling**
   - Implement robust entry and exit execution
   - Add error handling for common option execution issues
   - Implement retry logic for failed orders
   - Add safeguards against partial fills

5. **Signal Generation & Position Sizing**
   - Implement directional signals based on previous close
   - Add risk-based position sizing (2% risk per trade)
   - Test with different delta targets

6. **Exit Management**
   - Implement stop-loss logic (1.25× initial credit)
   - Add time-based exit before market close
   - Test with different market conditions

This phased approach prioritizes the core mechanics of option spread construction and execution before adding strategy-specific logic, ensuring a solid foundation for the algorithm.
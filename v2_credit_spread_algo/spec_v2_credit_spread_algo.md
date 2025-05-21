# v2 Credit Spread Algorithm – Vision & Build Specification

---

## 1 · Credit-Spread Primer

### 1.1 Key Option Terminology

* **Option**: A contract granting the buyer the right, but not the obligation, to buy (call) or sell (put) an underlying asset at a specified strike price before or at expiration.
* **Underlying Asset**: The stock, ETF, futures contract, or index on which the option contract is based (e.g., SPY, SPX).
* **Expiration**: The specific date and time when the option contract expires and the right to exercise ends.
* **Strike Price**: The price at which the underlying asset can be bought (call) or sold (put) if the option is exercised.
* **Premium**: The price paid by the buyer (and received by the seller) for the option contract.
* **Net Credit**: The total premium received from selling the short leg minus the premium paid for buying the long leg; represents the maximum profit.
* **Short Leg**: The option position that is sold to collect premium. It generates income but introduces risk, as it obligates the trader to fulfill the contract if the option is exercised.
* **Long Leg**: The option position that is bought to hedge the risk of the short leg. It provides a cap on potential losses and defines the maximum risk of the trade.
* **Spread Width**: The difference between the strike prices of the long and short legs; determines maximum risk range.
* **Maximum Profit**: Equal to the net credit; realized if both legs expire worthless.
* **Maximum Risk**: Calculated as (spread width – net credit); the worst-case loss if the spread is fully in-the-money.
* **Breakeven**: The underlying price at which the position neither gains nor loses. For put spreads: short strike – net credit. For call spreads: short strike + net credit.
* **Theta (Time Decay)**: The rate at which an option’s value decreases as time passes, particularly towards expiration.
* **Probability of Profit (POP)**: The statistical chance that a position will expire with profit, often approximated by delta.

---

### 1.2 What Is a Vertical Credit Spread?

A vertical credit spread is an options strategy that simultaneously:

1. **Sells** one option (short leg) to collect premium, and
2. **Buys** another option (long leg) with the same expiration but a different strike as insurance.

Key characteristics:

* Net credit at entry (cash received).
* Limited profit equal to the net credit.
* Limited risk equal to spread width minus net credit.
* Time decay (theta) works in favor of the seller once established.

Vertical spreads are categorized by option type and market bias:

* **Bull Put Credit Spread**: Uses puts, profits when the underlying stays above the short strike.
* **Bear Call Credit Spread**: Uses calls, profits when the underlying stays below the short strike.

---

### 1.3 Bull Put Credit Spread (Neutral-to-Bullish)

A bull put credit spread is deployed when you expect the underlying asset to remain at or rise above a certain level by expiration.

How it works (narrative):
First, you sell an out-of-the-money (OTM) put option at a strike safely below the current market price, collecting premium. Then, you buy a further OTM put at a lower strike to cap potential downside. If the underlying stays above the short put strike, both options expire worthless and you retain the entire net credit. If the market falls, your loss is limited by the long put.

| Leg                | Action       | Example (XYZ @ \$105)    |
| ------------------ | ------------ | ------------------------ |
| **Short Put**      | Sell 100 put | +\$3.20 credit           |
| **Long Put**       | Buy 95 put   | –\$1.30 debit            |
| **Net Credit**     |              | **\$1.90**               |
| **Spread Width**   |              | **\$5.00**               |
| **Maximum Profit** |              | \$1.90                   |
| **Maximum Risk**   |              | \$5.00 – \$1.90 = \$3.10 |
| **Breakeven**      |              | \$100 – \$1.90 = \$98.10 |

---

### 1.4 Bear Call Credit Spread (Neutral-to-Bearish)

A bear call credit spread is used when you expect the underlying asset to remain at or fall below a certain level by expiration.

How it works (narrative):
You sell an OTM call option at a strike safely above current price, receiving premium. Then, you buy a further OTM call at a higher strike to limit upside risk. If the underlying stays below the short call strike, both options expire worthless and you keep the net credit. Should the market rally, your loss stops at the long call strike.

| Leg                | Action        | Example (XYZ @ \$98)      |
| ------------------ | ------------- | ------------------------- |
| **Short Call**     | Sell 100 call | +\$3.20 credit            |
| **Long Call**      | Buy 105 call  | –\$1.30 debit             |
| **Net Credit**     |               | **\$1.90**                |
| **Spread Width**   |               | **\$5.00**                |
| **Maximum Profit** |               | \$1.90                    |
| **Maximum Risk**   |               | \$5.00 – \$1.90 = \$3.10  |
| **Breakeven**      |               | \$100 + \$1.90 = \$101.90 |


## --- STRATEGY SPECIFICATIONS: -----

## 2 · Target End-State ("Dream Algo")

The finished system will:

1. **Trade both bull-put and bear-call credit spreads** on liquid futures, indices, and equity ETFs (e.g., SPX, NQ, ES, SPY, QQQ, IWM, etc.).
2. **Select direction** each morning using a pluggable signal stack (price action, IV structure, macro events, ML forecasts, etc.).
3. **Operate 0 DTE by default**, with an option to widen to 0–5 DTE weekly expiries.
4. **Support multi-asset rotation**, position-sizing at 1–2% portfolio risk per spread, and portfolio-level margin caps.
5. Provide **automated logging, analytics, and parameter optimisation**.

### 2.1 Architectural Modules

| #  | Module                | Core Responsibility                             |
| -- | --------------------- | ----------------------------------------------- |
| M1 | Universe Builder      | Gather option chains, apply strike-range filter |
| M2 | Signal Engine         | Output **BULL / BEAR / NONE** for the session   |
| M3 | Spread Selector       | Choose strikes & width to meet Δ and risk specs |
| M4 | Order Executor        | Route orders, verify fills, record net credit   |
| M5 | Risk Manager          | Enforce stop-loss, take-profit, hard EOD close  |
| M6 | Portfolio Controller  | Size trades, limit concurrent risk              |
| M7 | Analytics & Optimiser | Capture metrics, run walk-forward tests         |

---

## 3 · Incremental Development Roadmap

| Stage | Goal                           | Modules Activated    | Success Criteria                           |
| ----- | ------------------------------ | -------------------- | ------------------------------------------ |
| **0** | Scaffold + logging             | M1                   | Pulls option chains                        |
| **1** | MVP bull-put 0‑DTE on SPY      | M1, M3, M4, basic M5 | Opens/closes 1 spread/day; respects params |
| **2** | Risk refinement                | Enhanced M5          | Stop-loss & take-profit validate           |
| **3** | Bear-call capability           | M3                   | Symmetric behavior for calls               |
| **4** | Direction selector integration | M2                   | Trades put vs call per signal              |
| **5** | Position sizing & multi-asset  | M6, expanded M1      | ≤2% NAV per spread; 1 trade per asset      |
| **6** | Analytics & optimisation       | M7                   | Walk-forward tests; dashboards             |

---

## 4 · Stage 1 Build Specification – Bull Put 0‑DTE MVP

### 4.1 Static Parameters

| Parameter           | Value            | Notes                     |   |                   |
| ------------------- | ---------------- | ------------------------- | - | ----------------- |
| DTE                 | **0 only**       | Same-day expiries         |   |                   |
| Strategy type       | Bull-put spreads | Calls disabled in Stage 1 |   |                   |
| Short-leg Δ         | ≤                | 0.30                      |   | Targets \~70% POP |
| Spread width        | **\$5.00** cap   | Accept 0.5–5.0 if needed  |   |                   |
| Entry time          | **10:00 ET**     | Avoid open-bell noise     |   |                   |
| Mandatory EOD close | **15:30 ET**     | 30 min before close       |   |                   |
| Stop-loss           | Debit ≥2× credit | Hard exit                 |   |                   |
| Take-profit         | P/L ≥50% of max  | Lock in gains             |   |                   |
| Position size       | **1 contract**   | Later → 1–2% NAV          |   |                   |
| Max concurrent      | **1 per asset**  | SPY only in Stage 1       |   |                   |
| Strike-range filter | ±20 strikes ATM  | Keeps chain scan light    |   |                   |

### 4.2 Execution Flow

1. **09:50 ET** – Load SPY option chain; apply filter.
2. **10:00 ET** –

   * Evaluate Δ ≤0.30; pick short put.
   * Choose long put \$5 lower.
   * Submit vertical; record net credit.
3. **Intraday loop** –

   * If debit ≥2× credit → close (stop-loss).
   * If profit ≥50% → close (take-profit).
4. **15:30 ET** – Close any open spread.
5. Log P/L, drawdown, fills.

---

## 5 · Modular Testing &  Development Workflow Integration

This specification assumes a **single QC project folder** (`v2_credit_spread_algo`) that contains:

* **main.py**: QCAlgorithm subclass entry point
* **config.json**: Lean CLI config
* **Multiple module files**: Each core component (M1–M7) lives in its own `.py` file at the project root (e.g., `universe_builder.py`, `signal_engine.py`, etc.).

**Consolidated Development Workflow:**

1. **Implement** each feature as its own `.py` file alongside `main.py`.
2. **Import** modules in `main.py` using standard Python `from module_name import ...` syntax.
3. **Run** short back-tests (e.g., one week or one month) in QC Cloud to validate functionality immediately after each change.
4. **Commit** small, focused changes to version control, making rollbacks straightforward.


    In sumamry, we test each component (e.g., M1–M7) independently by developing it in its own .py file, then wire into the main.py file to run a short QC Cloud back-tests. This approach helps to separate modular components in the algorithm, enabiling simple debugging and preventing unintentional editing of working code.

---

## 6 · Change Log (placeholder)

| Date | Author | Change |
| ---- | ------ | ------ |

---

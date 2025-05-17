# Bull Put Spread Algorithm: Modular Component Reference

## 1. Overview
This document provides a comprehensive reference for the modular components of the Bull Put Spread algorithm. It serves as both documentation and a development guide, outlining the current implementation status and areas for improvement.

## 2. Core Components

### 2.1. Initialization Module
**File**: `main.py` (initialize method)

**Purpose**: 
- Sets up the algorithm's configuration, security subscriptions, and scheduled events.

**Key Parameters**:
```python
# Core Configuration
self.set_start_date(2023, 10, 1)
self.set_end_date(2023, 12, 31)
self.set_cash(10000)
self.set_time_zone(TimeZones.NEW_YORK)

# Security Setup
self.equity_symbol = self.add_equity("SPY", Resolution.MINUTE).symbol
option = self.add_option("SPY", resolution=Resolution.MINUTE)
option.set_filter(lambda u: u.include_weeklys().expiration(0, 30))
```

**Status**:
- ✅ Functional: Basic setup and security configuration
- ✅ Functional: Option chain filtering for 0-30 DTE
- ⚠️ Needs Review: Expiry filter includes 0-30 DTE but strategy focuses on 0DTE

### 2.2. Strategy Parameters Module
**File**: `main.py` (initialize method)

**Purpose**:
- Defines and manages all strategy parameters and risk settings.

**Key Parameters**:
```python
# Core Risk/Reward
self.min_credit_threshold = 0.10
self.enable_stop_loss = True
self.stop_loss_multiplier = 2.0
self.profit_target_percentage = 0.50

# Option Selection
self.short_put_delta_mode = "MAX"
self.short_put_delta_exact = 0.30
self.short_put_delta_min = 0.25
self.short_put_delta_max = 0.30

# Spread Configuration
self.spread_width_mode = "FIXED"
self.spread_width_fixed = 5.0
self.long_put_selection_mode = "WIDTH"
```

**Status**:
- ✅ Functional: Core parameters implemented
- ⚠️ Needs Testing: Some parameters (like delta modes) may not be fully utilized

### 2.3. State Management Module
**File**: `main.py` (class variables)

**Purpose**:
- Tracks the current state of the algorithm and open positions.

**State Variables**:
```python
self.spread_is_open = False
self.pending_open = False
self.pending_close = False
self.opened_short_put_symbol = None
self.opened_long_put_symbol = None
self.initial_credit = None
self.stop_loss_target_debit = None
self.profit_target_value_debit = None
self.opening_order_tickets = []
self.closing_order_tickets = []
```

**Status**:
- ✅ Functional: Basic state tracking
- ❌ Issues: Order ticket tracking needs improvement (untracked OrderID warnings)
- ⚠️ Needs Enhancement: Position state validation

### 2.4. Trade Entry Module
**File**: `main.py` (try_open_spread method)

**Purpose**:
- Identifies and enters bull put spread positions based on strategy parameters.

**Key Functions**:
- `open_trades()`: Schedules trade entry
- `try_open_spread()`: Main logic for spread entry
- `select_short_put()`: Selects short put strike
- `select_long_put()`: Selects long put strike

**Status**:
- ✅ Functional: Basic spread entry
- ❌ Issues: May not handle all market conditions
- ⚠️ Needs Testing: Edge cases around market open

### 2.5. Trade Exit Module
**File**: `main.py` (multiple methods)

**Purpose**:
- Manages trade exits via stop-loss, profit target, or scheduled close.

**Key Functions**:
- `close_positions()`: Schedules position closure
- `close_all_option_positions_force()`: Force closes all positions
- `check_stop_loss()`: Monitors for stop-loss conditions
- `monitor_profit_target()`: Tracks profit targets

**Status**:
- ✅ Functional: Basic exit mechanisms
- ❌ Issues: Stop-loss execution reliability
- ✅ Functional: Forced close before market close

### 2.6. Risk Management Module
**File**: `main.py` (distributed methods)

**Purpose**:
- Implements risk controls and position sizing.

**Key Components**:
- Fixed position sizing (1 contract)
- Stop-loss at 2x initial credit
- Profit target at 50% of max profit
- Forced position closure before market close

**Status**:
- ✅ Functional: Basic risk controls
- ⚠️ Needs Enhancement: More sophisticated position sizing

## 3. Order Management System

### 3.1. Order Tracking
**File**: `main.py` (on_order_event method)

**Purpose**:
- Tracks order status and updates algorithm state.

**Status**:
- ❌ Issues: "Untracked OrderID" warnings
- ⚠️ Needs Work: Order ticket management

### 3.2. Position Tracking
**File**: `main.py` (on_securities_changed method)

**Purpose**:
- Monitors position changes and updates state.

**Status**:
- ✅ Functional: Basic position tracking
- ⚠️ Needs Enhancement: More robust state validation

## 4. Market Hours Handling

### 4.1. Trading Schedule
**File**: `main.py` (initialize method)

**Scheduled Events**:
- Trade Entry: 10:00 AM ET
- Regular Close: 30 minutes before market close
- Force Close: 15 minutes before market close

**Status**:
- ✅ Functional: Basic scheduling
- ⚠️ Needs Testing: Early market closures and holidays

## 5. Known Issues

1. **Order Tracking**
   - "Untracked OrderID" warnings in logs
   - Inconsistent state between orders and positions

2. **Position Management**
   - Potential for position state desynchronization
   - Limited validation of position state

3. **Market Hours**
   - Basic handling of early market closures
   - No special handling for holidays

4. **Stop-Loss Execution**
   - May not trigger reliably in fast-moving markets

## 6. Recommended Improvements

1. **Immediate Fixes**
   - Implement proper order ticket tracking
   - Add position state validation
   - Enhance error handling and logging

2. **Short-term Enhancements**
   - Improve stop-loss reliability
   - Add market hours validation
   - Implement proper order status tracking

3. **Long-term Features**
   - Add directional indicators
   - Implement bi-directional trading
   - Add multi-asset support

## 7. Reference Implementation

For each component, refer to the corresponding methods in `main.py`:

```python
# Initialization
def initialize(self)

# Trade Entry
def open_trades(self)
def try_open_spread(self, slice)

# Trade Exit
def close_positions(self)
def close_all_option_positions_force(self)
def check_stop_loss(self, slice)
def monitor_profit_target(self, slice)

# Order Management
def on_order_event(self, order_event)
def on_securities_changed(self, changes)
```

## 8. Usage Notes

1. **Backtesting**: Ensure proper data subscription for the selected time period.
2. **Live Trading**: Thoroughly test all exit conditions before deploying.
3. **Monitoring**: Regularly review logs for any "Untracked OrderID" warnings.
4. **Risk Management**: Adjust position sizing and risk parameters according to account size and risk tolerance.

---
*Document last updated: 2025-05-15*
*This document should be updated whenever significant changes are made to the algorithm's structure or behavior.*

## Memory: `de731945-342a-4f8b-9a4c-551a1d644e44`

**Title:** `QuantConnect Naming Conventions`

**Tags:** `quantconnect`, `python`, `naming_conventions`, `code_standards`

**Content:**
```text
Based on examination of the QuantConnect repositories, the following naming conventions must be followed:

1. Method names in Python algorithms must use snake_case (e.g., `initialize`, `on_data`, `set_time_zone`)
2. TimeZones enumeration values must be in UPPERCASE (e.g., `TimeZones.NEW_YORK`, `TimeZones.UTC`)
3. Resolution enumeration values must be in UPPERCASE (e.g., `Resolution.MINUTE`, `Resolution.DAILY`)
4. Option chain access should use the modern Python-friendly syntax (e.g., `chain = self.option_chain[symbol]`, `expiry = sorted(chain.expiry_dates)[0]`)

These conventions have been verified against the official QuantConnect repositories and are critical for ensuring algorithm compatibility.
```
---

## Memory: `40870fd1-c057-4107-8109-98b54fced9de`

**Title:** `Using OptionStrategies Class in QuantConnect`

**Tags:** `quantconnect`, `options`, `best_practices`, `margin_requirements`, `option_strategies`

**Content:**
```text
When implementing option spread strategies in QuantConnect, always use the built-in OptionStrategies class methods (e.g., OptionStrategies.bull_put_spread(), OptionStrategies.bear_call_spread()) rather than placing separate orders for each leg. 

Using OptionStrategies:
1. Ensures proper margin calculation based on the defined risk of the spread
2. Prevents excessive margin requirements that would occur with separately placed orders
3. Helps avoid unwanted option exercises and assignments
4. Follows QuantConnect's best practices for options trading

Example:
```python
# CORRECT: Use OptionStrategies class
bull_put_spread = OptionStrategies.bull_put_spread(option_symbol, short_strike, long_strike, expiry)
orders = self.buy(bull_put_spread, 1)

# INCORRECT: Place separate orders
orders = [
    self.sell(short_put, 1),
    self.buy(long_put, 1)
]
```
```
---

## Memory: `80542224-fd0b-4d5d-949c-6b9af716ede1`

**Title:** `Enhanced QuantConnect Code Examples for Option Strategies`

**Tags:** `quantconnect`, `documentation`, `references`, `options_trading`

**Content:**
```text
Enhanced the QuantConnect code examples in `.windsurf/qc-code-examples.md` with comprehensive references to option strategy implementations across all asset classes:

1. **Index Options** - Added 9 index option strategies including bear/bull call/put spreads, butterflies, calendar spreads, and iron condors
2. **Equity Options** - Added 13 equity option strategies including straddles, strangles, butterflies, calendar spreads, covered/protective positions, naked options, and iron condors
3. **Future Options** - Added 8 future option examples including basic templates and various ITM/OTM expiry scenarios

This expanded reference section provides a complete catalog of option strategy implementations across all major asset classes, making it easier to find relevant examples when implementing specific trading strategies.
```
---

## Memory: `8aede62c-f34d-4923-9d01-b8d04e9b115e`

**Title:** `Fix for Early Market Closure Handling in QuantConnect`

**Tags:** `quantconnect`, `options_trading`, `scheduling`, `market_hours`, `bug_fix`

**Content:**
```text
Successfully fixed early market closure handling in the 'basic-credit-spread' algorithm. The issue of unwanted option exercises on holidays (July 3rd, Nov 29th, Dec 24th) was resolved by changing the self.schedule.on() for closing positions to use `self.time_rules.before_market_close(self.option_symbol, 15)` instead of `self.equity_symbol`. This ensures the closing logic is tied directly to the option's specific trading hours. Backtest 'Alert Brown Pony' confirmed the fix.
```
---

## Memory: `ef157f91-16ec-4e7f-8eac-332701d017ae`

**Title:** `Streamlined Debugging Workflow for QuantConnect Algorithms`

**Tags:** `quantconnect`, `debugging`, `workflow`, `browser_automation`, `logs`

**Content:**
```text
Created a streamlined debugging workflow (`qc-debug-algorithm.md`) for QuantConnect algorithms that uses temporary storage and minimizes file size:

1. Uses `/tmp/qc_logs_*` directories for temporary log storage to avoid cluttering projects and prevent logs from being committed to Git
2. Condensed the Puppeteer browser automation script into a compact inline Node.js command
3. Simplified log analysis to focus on the most critical errors and patterns
4. Maintains a clean integration with the qc-docs-research workflow
5. Reduced the file size from ~10.9KB to ~5KB (under the 6KB limit)

This optimized workflow provides the same core functionality while being more maintainable and avoiding unnecessary storage of log files in the project directories.
```
---

## Memory: `ee6bddad-eecc-40c5-91da-e4e431b39958`

**Title:** `Local QuantConnect Documentation Repositories (Git Submodules)`

**Tags:** `quantconnect`, `documentation`, `git_submodules`, `workflow`

**Content:**
```text
The workspace now includes local copies of QuantConnect documentation repositories as Git submodules in `.windsurf/QC-Doc-Repos/`:

1. Documentation (primary reference)
2. lean-cli (deployment interface)
3. Lean (engine implementation)
4. Lean.Brokerages.InteractiveBrokers (IB-specific)

These repositories should be checked in this order before writing code, editing, or debugging algorithms. A workflow has been created to update these repositories (`/update-qc-docs`).

The quantconnect-python-guide.md has been updated to reflect this documentation-first approach with the local repositories.
```
---

## Memory: `a800933a-b2ac-4a27-8c79-c564d9e66f55`

**Title:** `QuantConnect Documentation Research Workflow`

**Tags:** `quantconnect`, `documentation`, `workflow`, `research`

**Content:**
```text
Created a documentation research workflow (`qc-docs-research.md`) that systematically searches through local QuantConnect documentation repositories to find relevant information for implementing new features or solving problems.

The workflow:
1. Takes a problem/feature description in plain English
2. Identifies relevant components and asset classes
3. Searches through all local documentation repositories in the recommended order:
   - Documentation (primary reference)
   - lean-cli (deployment interface)
   - Lean (engine implementation)
   - IB Brokerage (if relevant)
4. Finds example algorithms related to the problem
5. Searches for common issues and solutions
6. Creates implementation notes with findings and recommended approaches

This workflow complements the existing trading-strategy-to-implementation-plan workflow by focusing specifically on documentation research before implementation.
```
---

## Memory: `3a2cd5b9-efc3-4210-b0a1-d175b0b03b97`

**Title:** `QuantConnect CLI Limitations for Cloud Backtest Logs`

**Tags:** `quantconnect`, `cli_limitations`, `backtest_logs`, `cloud_backtests`

**Content:**
```text
The QuantConnect CLI does not support downloading logs from cloud backtests directly. Commands like `lean cloud download-backtest-data` or `lean cloud logs` do not exist. 

When working with QuantConnect algorithms, we need to:
1. Run backtests using `lean cloud backtest "project-name" --push`
2. View logs through the QuantConnect web interface
3. For local testing with logs, use `lean backtest "project-name"` (but this requires local data)

This limitation means we need to implement sufficient logging in the algorithm code itself and view results through the web UI rather than trying to download logs via CLI.
```
---

## Memory: `93cc5b3c-7c2e-4cb0-ae48-c0a188f8a824`

**Title:** `Logging Best Practices in QuantConnect Algorithms`

**Tags:** `quantconnect`, `logging`, `performance`, `backtesting`, `best_practices`

**Content:**
```text
When implementing logging in QuantConnect algorithms:

1. Keep logging minimal and strategic - excessive logging significantly slows down backtests
2. Only add detailed logging when specifically instructed
3. Focus on critical decision points rather than verbose data dumps
4. The user will provide logs as needed for debugging
5. Prioritize performance over verbose diagnostics

This approach balances the need for diagnostics with maintaining efficient backtest performance.
```
---

## Memory: `014432f2-badf-4b15-8f00-cdd2987706d5`

**Title:** `Cascade Command Execution Strategy (run_command tool)`

**Tags:** `cascade_behavior`, `command_execution`, `agentic_operations`, `workflow_handling`

**Content:**
```text
To address issues of appearing 'stuck' or running indefinitely, Cascade will adopt a refined strategy for using the `run_command` tool:

1.  **Categorize Commands**:
    *   **Type A: Interactive/Feedback-Needed**: Commands whose output is immediately required for Cascade's next analytical step or code modification (e.g., `grep_search`, `view_file`, linters, tests with parsable output). 
        *   **Execution**: Use `Blocking=true`. Be mindful of potential hangs and communicate if suspected.
    *   **Type B: Browser-Opening/Long-Running Background**: Commands that primarily launch an external GUI (e.g., browser via `lean cloud backtest --open`) or run for extended periods without direct terminal output critical for Cascade's immediate next action.
        *   **Execution**: Use `Blocking=false`. Set `WaitMsBeforeAsync` to a short duration (e.g., 3000-5000ms) to catch initial errors and allow process startup. Cascade will then proceed with the conversation without waiting for full command completion.
    *   **Type C: Workflow Step Commands**: Assess each command within a workflow. If output is critical for the *next immediate automated step by Cascade*, use Type A. Otherwise (e.g., fire-and-forget, launching external processes), use Type B.

2.  **Communication**: When initiating Type B commands, Cascade will explicitly state that it's running non-blockingly, will not wait for full completion, and will indicate where the user should expect results (e.g., 'in your browser').

3.  **Agentic Loops**: This strategy aims to balance responsiveness with agentic capabilities. Type A commands ensure Cascade gets necessary feedback for iterative tasks. Type B commands prevent hangs on processes where Cascade isn't the primary consumer of continuous terminal output.

4.  **Review and Refine**: This strategy should be reviewed if 'stuck' behavior persists, to further refine command categorization or timeout handling.
```
---

## Memory: `5861bd73-e13f-4d9f-aedb-795847c4d727`

**Title:** `QuantConnect Python API Lowercase Property Naming Conventions`

**Tags:** `quantconnect`, `python`, `api`, `case_sensitivity`, `portfolio`

**Content:**
```text
When working with QuantConnect's Python API, certain properties use lowercase naming conventions despite being capitalized in the C# API. Specifically:

1. When iterating through portfolio holdings, use `kvp.value` instead of `kvp.Value`
2. When accessing security properties, use lowercase property names (e.g., `holding.type` instead of `holding.Type`)
3. This is due to QuantConnect's C# to Python bridge translation conventions

This pattern applies to many other properties in the QuantConnect API when used from Python.
```
---

# Implementation Notes: Option Chains

## Problem/Feature Description
Implement delta-based strike selection for bull put credit spreads.
The short put (higher strike) should have an absolute delta of 0.3 or less (e.g., -0.3 <= delta < 0, so abs(delta) <= 0.30).
The long put (lower strike) will be the next available strike price below the selected short put strike.
Need to find how to access Option Greeks, specifically Delta, for option contracts in QuantConnect.

## Documentation Research Summary
- Access Option Greeks (Delta, Gamma, Vega, Theta) via the `greeks` property of an `OptionContract` object (e.g., `option_contract.greeks.delta`).
- `OptionContract` objects are obtained from an `OptionChain` which is available in the `Slice` object in `on_data`.
- Ensure that the `Option` subscription is set up correctly. Greeks are generally available if the option has a valid theoretical price.
- Filtering Logic:
    - Iterate through contracts in the `OptionChain`.
    - For each contract, check `contract.greeks.delta`.
    - Select the short put: `contract.right == OptionRight.PUT` and `abs(contract.greeks.delta) <= 0.30`. Puts typically have negative deltas, so this captures values like -0.30, -0.29, ..., down to near 0.
    - Select the long put: Find the next available strike price below the selected short put's strike.
- Example files to review: `BasicTemplateOptionsFilterUniverseAlgorithm.py`, `OptionUniverseFilterOptionsDataRegressionAlgorithm.py` may show relevant chain processing, though not direct Greek filtering.

## Key Code Examples

```python
# Conceptual example of accessing delta
# chain = slice.option_chains.get_value(self.option_symbol)
# if chain:
#     for contract in chain:
#         if contract.greeks and contract.greeks.delta is not None: # Check if greeks and delta are available
#             delta_value = contract.greeks.delta
#             # Your filtering logic here
#             # Example for short put selection:
#             if contract.right == OptionRight.PUT and abs(delta_value) <= 0.30:
#                 # This contract is a candidate for the short put leg
#                 self.debug(f"Candidate short put: {contract.symbol.value}, Strike: {contract.strike}, Delta: {delta_value:.4f}")
#                 pass 
```

## Implementation Approach
1. In `try_open_spread` method within `bull-credit-spread/main.py`:
2. After retrieving the `OptionChain` for the target expiration (0-DTE), filter for `OptionRight.PUT` contracts.
3. Create a list of candidate short puts: iterate through these put contracts and select those where `contract.greeks` is not `None`, `contract.greeks.delta` is not `None`, and `abs(contract.greeks.delta) <= 0.30`.
4. From this list of candidate short puts, select the one to use. A common approach is to select the one with the highest strike price (closest to the money but still meeting the delta criteria). If multiple have the same highest strike, other criteria could be used (e.g., highest premium, though this adds complexity).
5. If no short put candidates are found, log this and do not open a trade.
6. Once the short put strike is chosen, find the long put. This will be a contract with the same `OptionRight.PUT` and expiry, but with the next available strike price *immediately below* the chosen short put's strike. Ensure such a contract exists in the chain.
7. If a suitable long put cannot be found (e.g., no strikes available below the short, or the gap is too wide), log this and do not open a trade.
8. Construct the `OptionStrategies.bull_put_spread` using the selected short put strike and long put strike for the target expiry.
9. Add detailed logging for selected contracts, their strikes, and their deltas for verification during backtesting.
10. Consider edge cases: What if `greeks` or `greeks.delta` is `None` for some contracts? (The check `contract.greeks and contract.greeks.delta is not None` handles this.)

## References
- [Documentation Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/Documentation)
- [Lean CLI Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/lean-cli)
- [Lean Engine Repository](/Users/overton/CascadeProjects/QuantConnect Trading Algorithms/.windsurf/QC-Doc-Repos/Lean)


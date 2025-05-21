# M8 — BuyOnOpen Test
from AlgorithmImports import *

class BuyOnOpen:
    """Schedule a market order for 1 share of QQQ at market open."""
    @staticmethod
    def register(qc_algo):
        # First add QQQ to the algorithm
        qqq_symbol = qc_algo.add_equity("QQQ", Resolution.MINUTE).symbol
        
        # Define the buy QQQ function that will be called by the scheduler
        def buy_qqq_at_open():
            qc_algo.market_order(qqq_symbol, 1)
            qc_algo.log(f"Placed market order for 1 share of QQQ at {qc_algo.time}")
        
        # Schedule the order to execute at market open every day
        qc_algo.schedule.on(
            qc_algo.date_rules.every_day(qqq_symbol),
            qc_algo.time_rules.after_market_open(qqq_symbol, 0),
            buy_qqq_at_open
        )

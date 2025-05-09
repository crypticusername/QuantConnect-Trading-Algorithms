from AlgorithmImports import *

class Creditspread_Algo_1Algorithm(QCAlgorithm):
    def Initialize(self):
        self.set_start_date(2024, 1, 1)
        self.set_end_date(2024, 12, 31)
        self.set_cash(100000)
        self.set_time_zone(TimeZones.EASTERN_STANDARD)
        self.set_warm_up(10, Resolution.DAILY)

        # Add equity and options
        equity = self.add_equity("SPY", Resolution.MINUTE).Symbol
        opt = self.add_option("SPY", Resolution.MINUTE)
        opt.set_filter(lambda u: u.include_weeklys().strikes(-5, 5).expiration(0, 7))
        self.option_symbol = opt.Symbol

        # Schedule algorithm entry points
        self.schedule.on(self.date_rules.every_day(), self.time_rules.after_market_open("SPY", 5), self.OpenTrades)
        self.schedule.on(self.date_rules.every_day(), self.time_rules.before_market_close("SPY", 30), self.ClosePositions)

    def OpenTrades(self):
        """Logic for opening positions goes here"""
        pass

    def ClosePositions(self):
        """Logic for closing positions goes here"""
        pass

    def OnData(self, slice):
        """Event-driven trading logic goes here (optional)"""
        pass

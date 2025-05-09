from AlgorithmImports import *

class Creditspread_Algo1Algorithm(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2024, 1, 1)
        self.SetEndDate(2024, 12, 31)
        self.SetCash(100000)
        self.SetTimeZone(TimeZones.NEW_YORK)
        self.SetWarmUp(10, Resolution.Daily)

        # Add equity and options
        equity = self.AddEquity("SPY", Resolution.Minute).Symbol
        opt = self.AddOption("SPY", Resolution.Minute)
        opt.SetFilter(lambda u: u.IncludeWeeklys().Strikes(-5, 5).Expiration(0, 7))
        self.option_symbol = opt.Symbol

        # Schedule algorithm entry points
        self.Schedule.On(DateRules.EveryDay(), TimeRules.AfterMarketOpen("SPY", 5), self.OpenTrades)
        self.Schedule.On(DateRules.EveryDay(), TimeRules.BeforeMarketClose("SPY", 30), self.ClosePositions)

    def OpenTrades(self):
        """Logic for opening positions goes here"""
        pass

    def ClosePositions(self):
        """Logic for closing positions goes here"""
        pass

    def OnData(self, slice):
        """Event-driven trading logic goes here (optional)"""
        pass

"""Main Data and Object Classes"""

import datetime
import yfinance as yf
import pandas as pd

from .currency import Converter


class Depot:
    def __init__(self, name, trades, currency='EUR'):
        """The Depot

        name: string, name of the depot
        trades: list of dicts with trades.
        stock_corrections: Some properties are not correctly pulled
          by yahoofinance. Here they can be overwritten.

        """
        self._stocks = {}

        self.name = name
        self.trades = trades
        self.stock_corrections = stock_corrections
        self.currency = currency

    @property
    def stocks(self):
        """Dict with Stocks of the Depot. Key is the symbol of the Stock."""
        if self._stocks == {}:
            # Init empty Stocks
            for symbol in self.symbols:
                self._stocks[symbol] = Stock(symbol)

            # Apply trades to Stocks
            for trade in self.trades:
                self._stocks[trade.symbol].apply_trade(trade)
        return self._stocks

    @property
    def symbols(self):
        """Get unique set of symbols."""
        return set([trade.symbol for trade in self.trades])

    @property
    def trades(self):
        return self._trades

    def from_dict(depot_dict):
        """Generate depot from a configuration dict."""
        d = Depot(
            depot_dict['name'],
            depot_dict['trades'],
        )
        for stock_dict in depot_dict['stocks']:
            # This pop in the original dict
            symbol = stock_dict.pop('symbol')
            for key, value in stock_dict.items():
                setattr(d.stocks[symbol], key, value)
        return d

    @trades.setter
    def trades(self, trades):
        self._trades = []
        if not isinstance(trades, list):
            raise NotImplementedError
        for trade in trades:
            self._trades.append(Trade(**trade))

    @property
    def overview(self):
        """A pandas dataframe with overview information."""
        data = []
        for symbol, stock in self.stocks.items():
            data.append([
                stock.symbol,
                stock.amount,
                round(stock.price, 2),
                round(stock.price_current, 2),
                round(stock.performance*100-100 , 2),
                round(stock.cost, 2),
                round(stock.cost_yearly(), 2)
            ])
        return pd.DataFrame(data, columns = (
            "Symbol", "Amount", "Price", "Price Current", "Performance",
            "Cost", "Cost Yearly",
        ))

class Stock:
    def __init__(
            self, symbol, amount=0, price=0, cost=0, fee_yearly=None currency='EUR'
    ):
        """A single stock type"""
        self.symbol = str(symbol)
        self.amount = float(amount) # Sum of all trades
        self.ticker = yf.Ticker(self.symbol)
        self.price = float(price) # The total price we payed for the amount
        self.cost = float(cost) # Sum of all trade costs.
        #TODO. Add anual expense from  stock_corrections
        self.trades = []
        # Buffers info and hist
        self.info = self.ticker.info
        self.history = self.ticker.history(period="max")
        self.fee_yearly = fee_yearly
        self.currency = currency

    @property
    def symbol(self):
        return self._symbol

    @symbol.setter
    def symbol(self, symbol):
        self._symbol = symbol

    @property
    def value(self):
        """Return current value of the Stock."""
        # get current value from Stockexchange
        #TODO: Transform to € if $
        value = self.history.iloc[-1]
        if self.info['currency'] != self.currency:
            currency = Converter(
                self.info['currency'], self.currency
            )
            value = currency.convert(value)

        return value

    @property
    def fee_yearly(self):
        return self._fee_yearly

    @fee_yearly.setter
    def fee_yearly(self, value):
        self._fee_yearly = value
        if isinstance(value, type(None)):
            try:
                self._fee_yearly = float(self.info["annualReportExpenseRatio"])
            except TypeError:
                self._fee_yearly = 0
        return self._fee_yearly


    def cost_yearly(self, time=datetime.date.today()):
        """Return yearly cost.

        time: datetime.date, time untill the fee is payed.
            Default is today.
        """
        ret = 0
        for trade in self.trades:
            days = time - trade.date
            # This is not correct for Schaltjahre
            # Should this be based on amount or the hostry of value?
            # I could never find a clear explanation of it
            ret += trade.signum * trade.amount * days.days/365 * self.fee_yearly
        ret *= self.value['Open']
        return ret


    @property
    def price_current(self):
        return self.value['Open']*self.amount

    @property
    def performance(self):
        return self.price_current/self.price

    def from_trade(trade):
        """Generate Stock object from trade."""
        if trade.signum < 1:
            raise ValueError('Cant create Stock from a Sell')

        s = Stock(
            trade.symbol, trade.amount, trade.price, trade.cost,
        )
        s.trades.append(trade)
        return s

    def apply_trade(self, trade):
        """Apply a trade to this stock."""
        if self.symbol != trade.symbol:
            raise ValueError("Cant add different Stocks")
        self.amount += trade.signum * trade.amount
        # As this is the total money payed, we can just add it
        self.price += trade.signum * trade.price
        self.cost += trade.signum * trade.cost
        self.trades.append(trade)


# TODO base the stocks on a trace class to accurately cover all states
class Trade:
    def __init__(self, symbol, amount, price, cost, date, signum=1):
        self.symbol = str(symbol)
        self.amount = float(amount)
        self.cost = float(cost)
        self.price = float(price)
        self.date = date #datetime.datetime.strptime(date, '%Y-%m-%d')
        # Sign of transaction relative to Depot. Must be -1 or +1
        # TODO. Add a check here
        self.signum = signum

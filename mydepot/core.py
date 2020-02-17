"""Main Data and Object Classes"""

import datetime
import numpy as np
import yfinance as yf
import pandas as pd
import yaml

from .currency import Converter


class Depot:
    def __init__(self, name, trades, currency):
        """The Depot

        name: string, name of the depot
        trades: list of dicts with trades.
        """
        self._stocks = {}
        self._trades = []

        self.name = name
        self.trades = trades
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

    @trades.setter
    def trades(self, trades):
        self._trades = []
        self._stocks = {}
        if not isinstance(trades, list):
            raise NotImplementedError
        for trade in trades:
            self._trades.append(Trade(**trade))

    @property
    def overview_trades(self):
        ret = pd.DataFrame([trade.dict for trade in self.trades])
        return ret

    def from_dict(depot_dict):
        """Generate depot from a configuration dict."""
        d = Depot(
            depot_dict['name'],
            depot_dict['trades'],
            depot_dict['currency'],
        )
        for stock_dict in depot_dict['stocks']:
            # This pop in the original dict
            symbol = stock_dict.pop('symbol')
            for key, value in stock_dict.items():
                setattr(d.stocks[symbol], key, value)
        return d

    def from_yaml(ffile):
        with open(ffile) as file:
            # The FullLoader parameter handles the conversion from YAML
            # scalar values to Python the dictionary format
            depot_config = yaml.load(file, Loader=yaml.FullLoader)
            return Depot.from_dict(depot_config)

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
                round(stock.cost_running(), 2),
                round(stock.cost_yearly, 2),
            ])
        return pd.DataFrame(data, columns = (
            "Symbol", "Amount", "Price", "Price Current", "Performance",
            "Cost", "Total Running Costs", "Yearly Cost"
        ))



class Stock:
    def __init__(
            self, symbol, amount=0, price=0, cost=0, fee_yearly=None, currency='EUR'
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
        self.history = self.ticker.history(period="3mo")
        self.fee_yearly = fee_yearly
        self.currency = currency

    @property
    def symbol(self):
        return self._symbol

    @symbol.setter
    def symbol(self, symbol):
        self._symbol = symbol

    @property
    def value_current(self):
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
        """The yearly fee of the Stock. (TER)"""
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


    def cost_running(self, time=datetime.date.today()):
        """Return running costs.

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
        ret *= self.value_current['Open']
        return ret

    @property
    def cost_yearly(self):
        """Calculate the yearly cost."""
        return self.price_current * self.fee_yearly


    @property
    def price_current(self):
        """The current proce of all pieces."""
        return self.value_current['Open']*self.amount

    @property
    def performance(self):
        """The relative value gain of the stock."""
        return self.price_current/self.price

    @property
    def overview_trades(self):
        df = pd.DataFrame([trade.dict for trade in self.trades])
        # Recast date ti np.datetime64 because this works best with altair
        df['date'] = df['date'].apply(np.datetime64)
        # Because there is only day resolution, combine all trades of one
        # day, as altair gets intro trouble else.
        df = df.groupby('date').sum().reset_index()
        df['value_per_piece'] = df['price']/df['amount']
        df['total_cost'] = np.cumsum(df['cost'] + df['price'])
        df['total_amount'] = df['amount'].cumsum()
        df['total_value'] = df['total_amount'] * df['value_per_piece']
        return df

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

    @property
    def dict(self):
        return {
            'symbol': self.symbol,
            'amount': self.amount,
            'cost': self.cost,
            'price': self.price,
            'date': self.date,
            'signum': self.signum,
        }


    @property
    def dict(self):
        return {
            'symbol': self.symbol,
            'date': self.date,
            'amount': self.amount,
            'price': self.price,
            'cost': self.cost,
            'signum': self.signum,
        }

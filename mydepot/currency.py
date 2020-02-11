"""Convert currencies based on daly data"""

import yfinance as yf


class Converter():
    def __init__(self, currency, target='EUR'):
        """Use yahoofinance to convert currencies

        currency ist the yahoo finance short name of the currency.
        e.g. USD or NOK
        """

        symbol = target + currency + "=X"
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="1d")
        self.currencypertarget = hist.iloc[0]['Open']
        self.targetpercurrency = 1/hist.iloc[0]['Open']

    def convert(self, amount):
        """Convert amount into target currency."""
        return amount * self.targetpercurrency

"""Module to import data from ebase"""
from mydepot import Trade

import datetime
import pandas as pd
import numpy as np

def csv_to_df(*args, **kwargs):
    """Make pandas dataframe from raw ebase csv."""

    df = pd.read_csv(
        *args, encoding = "ISO-8859-1", sep=';', decimal=',', **kwargs
    )
    # Change Datum to np.datetime64
    df['Datum'] = df['Datum'].apply(np.datetime64)
    return df


def csv_to_avg_trades(ffile):
    """ Get average trade per ISIN from ebase csv.

    Returns: list of trades.
    """
    df = csv_to_df(ffile)

    fonts = df.groupby('ISIN').sum()
    #fonts[[
    #    'Zahlungsbetrag in ZW',
    #    'Anteile',
    #    'Anlagebetrag in ZW',
    #    'Vertriebsprovision in ZW (im Abrechnungskurs enthalten)',
    #    'Barausschüttung/Steuerliquidität in ZW',
    #    'Steuern in EUR'
    #]]
    trades = []
    for isin, font in fonts.iterrows():
        trades.append(Trade(
            symbol = isin,
            price = font['Zahlungsbetrag in ZW'] - font['Vertriebsprovision in ZW (im Abrechnungskurs enthalten)'],
            amount = font['Anteile'],
            cost = font['Vertriebsprovision in ZW (im Abrechnungskurs enthalten)']+font['Steuern in EUR'],
            date = datetime.date.today(),
        ))
    return trades

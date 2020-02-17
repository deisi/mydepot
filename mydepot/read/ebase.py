"""Module to import data from ebase"""
from mydepot import Trade

import datetime
import pandas as pd
import numpy as np

isintosymbol = {
    'AT0000973029': 'AT0000973029.VI',
    'DE000A0MQR01': '0P0000A1W7.F',
}

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

    fonts = df.groupby(['ISIN', 'Umsatzart']).sum()
    trades = []
    for isin, font in fonts.iterrows():
        symbol = isintosymbol.get(isin)
        if not symbol:
            continue
        trades.append(Trade(
            symbol = isin,
            price = font['Zahlungsbetrag in ZW'] - font['Vertriebsprovision in ZW (im Abrechnungskurs enthalten)'],
            amount = font['Anteile'],
            cost = font['Vertriebsprovision in ZW (im Abrechnungskurs enthalten)']+font['Steuern in EUR'],
            date = datetime.date.today(),
        ))
    return trades


def csv_to_trades(ffile, umsatzart='Ansparplan'):
    """Get trades from ebase csv file."""

    df = csv_to_df(ffile)
    trades = []
    for index, row in df.iterrows():
        if row['Umsatzart'] != umsatzart:
            continue
        symbol = isintosymbol.get(row['ISIN'])
        if not symbol:
            continue
        cost = row['Vertriebsprovision in ZW (im Abrechnungskurs enthalten)']
        price = row['Anlagebetrag in ZW'] - cost
        trades.append(Trade(
            symbol=symbol,
            amount=row['Anteile'],
            cost=cost,
            price=price,
            date=row['Datum']
        ))
    return trades


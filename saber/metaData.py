from saber import metaLib as mtlib
import pandas as pd
import numpy as np

import datetime

from saber import metaData as mtd
from saber import metaLib as mtlib

mtw = mtlib.meta5_wrapper()


asset_map = {"US Equities": "US500",
             "China Equities": "CHINA50",
             "Oil": "XBRUSD",
             "Gold": "XAUUSD",
             "USD": "EURUSD",
             "EM FX": "USDMXN",
             "Cryptocurrencies":"ETHUSD"}


def update_tick_data(dir = r'C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv'):
    df = [mtw.get_tick_data(asset,'1d',2500) for asset in asset_map.values()]
    df = pd.concat(df)
    #df = pd.concat([df, prev_data])
    df = df.groupby('asset').apply(lambda x: x.drop_duplicates())
    df.index = df.index.get_level_values(1)
    df.to_csv(dir)    

def update_trade_sized_close():
    close = mtd.get_close_data()
    trade_contract_size_map = {}
    for sym in close.columns:
        trade_contract_size_map[sym] = mtw.get_symbol_info(sym).trade_contract_size
    trade_sized_close = close*trade_contract_size_map
    trade_sized_close.to_csv(r'C:\Users\kmavy\Documents\mydocs\4Sight\attachments\trade_sized_close.csv')

def get_close_data(directory = r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv"):
    raw_data = pd.read_csv(directory,index_col = 0)
    close= pd.pivot_table(raw_data, index='Date', columns='asset', values='close').ffill().dropna()
    return close

def get_open_data(directory = r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv"):
    raw_data = pd.read_csv(directory,index_col = 0)
    open= pd.pivot_table(raw_data, index='Date', columns='asset', values='open').ffill().dropna()
    return open

def get_trade_sized_close(directory = r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\trade_sized_close.csv"):
    return pd.read_csv(directory,index_col = 0)

def get_volume_data(directory = r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv"):
    raw_data = pd.read_csv(directory,index_col = 0)
    volume= pd.pivot_table(raw_data, index='Date', columns='asset', values='real_volume').ffill().dropna()
    return volume
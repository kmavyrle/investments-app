import pandas as pd
import numpy as np
import datetime

import yfinance as yf

from saber import PyFolio as pf
from saber import utilities as ut
from saber import mailer as mail
from saber import metaLib as mtlib
from saber import metaData as mtd
from saber import riskEngine as risk
from saber import PcEngine as pe
from saber import implementationEngine as ie
import time

mtw = mtlib.meta5_wrapper()
close = mtd.get_close_data()
def get_trade_hist(start_dt = datetime.datetime(2025,8,1)):
    end_dt = datetime.datetime.today()
    cols = ['ticket','order','date','date_msc','type','entry','magic','position_id','reason','volume','price','commmission','swap','profit','fee','symbol','comment','external_id']
    hist = pd.DataFrame(mtw.mt5.history_deals_get(start_dt,end_dt))
    hist.columns = cols
    hist['Date'] = [pd.to_datetime(ts,unit = 's').tz_localize("UTC").tz_convert("Asia/Singapore") for ts in hist.date]
    hist.set_index('Date',inplace = True)
    hist.sort_index(inplace = True)
    hist.index = [dt.strftime("%Y-%m-%d") for dt in hist.index]
    #hist['direction'] = [-1 if t == 1 else 1 for t in hist.type]
    #hist['position'] = [direct*pos for direct,pos in zip(hist.direction,hist.volume)]
    #hist['close_px'] = [get_asset_close_data(sym,dt,close) for sym,dt in zip(hist.symbol,hist.index)]
    hist = hist[hist.symbol!=""]
    #hist['trade_cont_size'] = [mtw.get_trade_contract_size(sym) for sym in hist.symbol]
    #hist['flip_pos_sign'] = [-1 if sym in ["EURUSD"] else 1 for sym in hist.symbol]
    #hist['position'] = hist.position*hist.flip_pos_sign
    return hist
def get_asset_close_data(sym,datestamp,close):
    if sym not in close.columns:
        return np.NaN
    df = close[[sym]]
    df = df.loc[datestamp].values[0]
    return df

def get_daily_pnl():
    hist = get_trade_hist()
    pnl = hist.groupby([hist.index,hist.symbol]).sum()[['profit']].reset_index()
    pnl.columns = ['Date','symbol','profit']
    pnl = pd.pivot(pnl,index = 'Date',columns = 'symbol',values = 'profit').fillna(0)
    pnl['TOTAL'] = pnl.sum(axis = 1)
    return pnl

def get_portfolio_details():
    positions = mtw.get_positions()
    portfolio_map = {}
    for key, value in positions.items():
        volume_list = value['volume']
        direction_list  = value['type']
        direction_list = [1 if d ==0 else -1 for d in direction_list]
        position = sum(v*d for v,d in zip(volume_list,direction_list))
        profit = sum(value['profit'])
        portfolio_map[key] = [position,profit]
    portfolio_dets = pd.DataFrame(portfolio_map).T
    portfolio_dets.columns = ['Position','PnL']
    return portfolio_dets

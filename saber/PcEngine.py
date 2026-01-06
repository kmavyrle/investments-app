import pandas as pd
import numpy as np

import datetime

from saber import metaLib as mtlib
from saber import metaData as mtd 
from saber import riskEngine as rke



asset_map = {"US Equities": "US500",
             "China Equities": "CHINA50",
             "Oil": "XBRUSD",
             "Gold": "XAUUSD",
             "USD": "EURUSD",
             "EM FX": "USDMXN",
             "Cryptocurrencies":"ETHUSD"}
### Inputs for portfolio construction
trade_sized_close = mtd.get_trade_sized_close()


class PortfolioConstructor:
    def __init__(self):
        self.mtw = mtlib.meta5_wrapper()                   #mt5 wrapper to access metatrader5 functions
        self.mtd = mtd                                     #accessor for metatrader5 data
        self.rke = rke.riskMgr()
        self.min_lot_size_map = {}
        for asset in asset_map.values():
            self.min_lot_size_map[asset] = self.mtw.get_symbol_info(asset).volume_min
        self.trade_sized_close = trade_sized_close

    def inv_vol_solver(self,signal,wdw = 250):
        px_chg = self.trade_sized_close.diff().iloc[-wdw:]#.std()
        vol = px_chg.std()
        raw_pos = signal/vol

        ### Try to create a function for this; this is because the signal is for USD, but we are trading EURUSD, hence we need to change the signal direction
        raw_pos['EURUSD'] = -raw_pos['EURUSD']
        
        return raw_pos

    def solve_wts(self,signal,method = 'INVOL',wdw = 250):
        if method == "INVOL":
            raw_pos = self.inv_vol_solver(signal,wdw)
        return raw_pos



    def get_target_positions(self,signal,method = "INVOL",port_var_target = 1000,percentile = 5,wdw = 250):
        """
        Function gets the target positions given a signal and a portfolio VAR target
        """
        raw_pos = self.solve_wts(signal,method = method, wdw = wdw)
        raw_pos_var = self.rke.get_pos_theoretical_var(raw_pos,percentile,wdw)
        scaling_factor = port_var_target/raw_pos_var
        target_pos = raw_pos*scaling_factor
        target_positions = {}

        ### Next size adjusts the target positions to be exact multiples of the minimum lot size
        for sym in target_pos.index:
            target_positions[sym] = round(target_pos[sym]//self.min_lot_size_map[sym]*self.min_lot_size_map[sym],2)
        return target_positions
    
    def get_min_lot_size_map(self):
        return self.min_lot_size_map
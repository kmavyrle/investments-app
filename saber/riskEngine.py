from saber import metaLib as mtlib
from saber import metaData as mtd
import pandas as pd
import numpy as np

import datetime

asset_map = {"US Equities": "US500",
             "China Equities": "CHINA50",
             "Oil": "XBRUSD",
             "Gold": "XAUUSD",
             "USD": "EURUSD",
             "EM FX": "USDMXN",
             "Cryptocurrencies":"ETHUSD"}



class riskMgr:
    """
    Risk Manager class
    The Risk Manager is responsible for managing risk of the trading book.
    """
    def __init__(self):
        """
        Initialize the risk manager
        mte: metaTrader5 wrapper. mte will be used to connect the riskEngine to live trading data and allows the riskEngine to access account data.
        Account data includes current positions, balance, equity, margin, etc which allows the riskEngine to obtain risk-related data.
        """
        self.mte = mtlib.meta5_wrapper()
        self.mtd = mtd
        self.positions = self.mte.get_positions()
        self.histData = pd.read_csv(r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv")
        self.px = pd.pivot_table(self.histData, index='Date', columns='asset', values='close')

    def get_hist_pxchg(self):
        """
        Function gets the historical price changes for all assets in the database
        """
        px_chg = self.px.diff().fillna(0)
        return px_chg
    
    def get_total_posn_by_symbol(self,symbol):
        """
        Given an asset we calculate the total position in the book by volume * direction
        Note: This could possibly be in a
        """
        direction = self.positions[symbol]['type']
        direction = [-1 if drtn == 1 else 1 for drtn in direction]
        volumes = self.positions[symbol]['volume']
        total_posn = sum(x*y for x,y in zip(direction,volumes))
        return total_posn
    
    def get_portfolio_posns(self):
        """
        Function gets all the trade size. Trade size is referred to the position held in the trading book multiplied
        by the trade contract size.
        If contract size is 10 lots, and the trading book holds 2 lots. Trade size is 20.
        """
        portfolio_positions = {}
        for sym in asset_map.values():
            try:
                ## If portfolio does not have position then ok
                portfolio_positions[sym] = self.get_total_posn_by_symbol(sym)
                ## Please code up new one to remove this try except
            except:
                pass

        return portfolio_positions
    

    def get_trade_tickets(self):
        """
        Function gets all the trade size. Trade size is referred to the position held in the trading book multiplied
        by the trade contract size.
        If contract size is 10 lots, and the trading book holds 2 lots. Trade size is 20.
        """
        positions = self.positions
        wanted_keys = ["ticket"]
        trade_tickets = {
            outer_k: {k: v for k, v in inner_d.items() if k in wanted_keys}
            for outer_k, inner_d in positions.items()
        }
        flat_dict = {k: v['ticket'] for k, v in trade_tickets.items()}
        return flat_dict
            
    
    def get_indiv_pos_var(self,pctage = 5):
        """
        Function returns the individual position VAR given a percentage level.
        This takes into account the size of the position and uses it to calculate the historical VaR
        """
        px_chg = self.get_hist_pxchg()
        positions = self.positions
        trade_size = self.get_portfolio_posns()
        assets = positions.keys()
        px_chg = px_chg[assets]
        px_chg = px_chg.fillna(0)
        indiv_var = {}
        for asset in assets:
            ts = trade_size[asset]
            chg = px_chg[asset]*ts
            chg = chg[chg<np.percentile(chg,pctage)]
            indiv_var[asset] = chg.mean()
        return indiv_var
    
    def get_positions(self):
        """
        Function returns the current positions in a dataframe
        """
        pos = self.positions
        pos = pd.DataFrame(pos)
        return pos
    
    def get_portfolio_var(self,pctage = 5,wdw = 250):
        """
        Function returns the portfolio VAR given a percentage and past window (in days)
        Uses historical price changes and trade size multiplied by price changes.
        Identify portfolio change on the worst x%

        Inputs:
        1. pctage: What is the VAR percentage (5% is common)
        2. wdw: How many days of historical data to use
        """
        px_chg = self.mtd.get_trade_sized_close().diff()
        portfolio_posns = self.get_portfolio_posns()
        px_chg = px_chg[portfolio_posns.keys()]
        # Multiply matching columns by their trade size
        portHist = px_chg*portfolio_posns
        
        portHist = portHist.sum(axis = 1)
        portHist = portHist.tail(wdw)
        vaR = np.percentile(portHist,pctage)
        port_var = portHist[portHist<vaR]
        port_var = port_var.mean()
        return port_var
    

    def get_pos_theoretical_var(self,theoretical_pos,percentile = 5,wdw = 250):
        """
        Function gets the theorteical var given a target position
        """
        trade_sized_close = self.mtd.get_trade_sized_close().ffill()
        px_chg = trade_sized_close.diff()
        portHist = px_chg*theoretical_pos
        portHist = portHist.dropna().iloc[-wdw:]
        #return portHist
        portHist = portHist.sum(axis = 1)
        vaR = np.percentile(portHist, percentile)
        port_var = portHist[portHist<vaR]
        port_var = port_var.mean()
        return -port_var




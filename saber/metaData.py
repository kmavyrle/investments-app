from saber import metaLib as mtlib
import pandas as pd
import numpy as np

import datetime


#mtw = mtlib.meta5_wrapper()


_asset_map_df = pd.read_csv(r'C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\asset_map.csv')
asset_map = dict(zip(_asset_map_df['Name'], _asset_map_df['Symbol']))

class data:
    def __init__(self, mtw):
        self.mtw = mtw

    def update_tick_data(self,dir = r'C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv'):
        df = []
        for asset in asset_map.values():
            try:
                df.append(self.mtw.get_tick_data(asset,'1d',2500))
            except:
                print(asset,' download failed')
            
        df = pd.concat(df)
        #df = pd.concat([df, prev_data])
        df = df.groupby('asset').apply(lambda x: x.drop_duplicates())
        df.index = df.index.get_level_values(1)
        df.to_csv(dir)    

    def update_trade_sized_close(self):
        close = self.get_close_data()
        trade_contract_size_map = {}
        for sym in close.columns:
            trade_contract_size_map[sym] = self.mtw.get_symbol_info(sym).trade_contract_size
        trade_sized_close = close*trade_contract_size_map
        trade_sized_close.to_csv(r'C:\Users\kmavy\Documents\mydocs\4Sight\attachments\trade_sized_close.csv')

    def get_close_data(self,directory = r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv"):
        raw_data = pd.read_csv(directory,index_col = 0)
        close= pd.pivot_table(raw_data, index='Date', columns='asset', values='close').ffill()#.dropna()
        return close

    def get_open_data(self,directory = r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv"):
        raw_data = pd.read_csv(directory,index_col = 0)
        open= pd.pivot_table(raw_data, index='Date', columns='asset', values='open').ffill().dropna()
        return open

    def get_trade_sized_close(self,directory = r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\trade_sized_close.csv"):
        return pd.read_csv(directory,index_col = 0)

    def get_volume_data(self,directory = r"C:\Users\kmavy\Documents\mydocs\4Sight\attachments\tick_data.csv"):
        raw_data = pd.read_csv(directory,index_col = 0)
        volume= pd.pivot_table(raw_data, index='Date', columns='asset', values='real_volume').ffill().dropna()
        return volume
    
    def get_currencies_latest_close(self):
        """
        Get latest close for all FX pairs identified from asset_map
        """
        close_df = self.get_close_data()
        asset_map_df = pd.read_csv(r'C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\asset_map.csv')
        
        # Identify FX pairs from asset_map by name
        fx_names = ['AusieYen', 'DollarYen', 'EuroYen', 'AussieDollar', 'EuroDollar', 
                    'AussieKiwi', 'EuroAusie', 'CableDollar', 'DollarForint', 
                    'DollarRand', 'EuroSterling', 'EuroDollar', 'DollarPeso']
        
        fx_symbols = asset_map_df[asset_map_df['Name'].isin(fx_names)]['Symbol'].tolist()
        
        # Filter to only FX columns that exist in close_df
        fx_cols = [col for col in close_df.columns if col in fx_symbols]
        
        return close_df[fx_cols].iloc[-1]

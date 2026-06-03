import pandas as pd
import numpy as np
import os


class DataLake:
    def __init__(self,base_path = r"C:\Users\kmavy\Documents\mydocs\Investments\data_lake"):
        self.base_path = base_path
        
    def _path(self, dataclass, dataype, asset_class, filename):
        return os.path.join(self.base_path, dataclass, dataype, asset_class, filename)

    def read_data(self,dataclass,dataype,asset_class,filename,index_col):
        '''
        Function reads the data from the cleaned data lake
        dataclass: str, raw, cleaned, transformed
        dataype: str, equities, fixed_income, commodities, fx
        asset_class: str, equities - us,cn,in,kr etc
        index_col: name of the intended index column
        '''
        path = self._path(dataclass,dataype,asset_class,filename)
        #path = os.path.join(r"lake",dataclass,datatype,asset_class,filename)
        df = pd.read_csv(path,index_col=index_col,parse_dates=True)
        return df

    def incremental_update_no_override(self,saved_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Function performs an incremental update of a saved DataFrame with a new DataFrame.
        '''
        # Union index
        #saved_df = saved_df[~saved_df.index.duplicated(keep="last")]
        idx = saved_df.index.union(new_df.index)
        saved = saved_df.reindex(idx)

        for col in new_df.columns:
            if col not in saved.columns:
                saved[col] = new_df[col]
            else:
                saved[col] = saved[col].combine_first(new_df[col])

        return saved.sort_index()

    def save_data(
        self,
        dataclass,
        dataype,
        asset_class,
        df,
        filename,
        index_col
    ):
        prefix = self.base_path
        folder = os.path.join(prefix, dataclass, dataype, asset_class)
        os.makedirs(folder, exist_ok=True)

        file_path = os.path.join(folder, filename)
        #print(file_path)
        if not os.path.exists(file_path):
            df.to_csv(file_path, index=True)
            return
        if dataclass =='transformed':
            df.to_csv(file_path, index=True)
            return
        old_df = self.read_data(dataclass,dataype,asset_class,filename,index_col)
        #return old_df
        merged = self.incremental_update_no_override(old_df, df)
        merged.to_csv(file_path, index=True)



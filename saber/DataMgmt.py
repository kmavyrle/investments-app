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

        # Peek at headers to check if named index columns exist
        headers = pd.read_csv(path, nrows=0).columns.tolist()
        if isinstance(index_col, list):
            actual_index = index_col if all(c in headers for c in index_col) else list(range(len(index_col)))
        else:
            actual_index = index_col if index_col in headers else 0

        df = pd.read_csv(path, index_col=actual_index)

        # Restore expected index names if we fell back to positional
        if isinstance(index_col, list) and isinstance(df.index, pd.MultiIndex):
            df.index.names = index_col
        elif not isinstance(index_col, list) and not isinstance(df.index, pd.MultiIndex):
            df.index.name = index_col

        if isinstance(df.index, pd.MultiIndex):
            for i, name in enumerate(df.index.names):
                if name and 'date' in name.lower():
                    df.index = df.index.set_levels(pd.to_datetime(df.index.levels[i], errors='coerce'), level=i)
        else:
            df.index = pd.to_datetime(df.index, errors='coerce')
        return df

    def incremental_update_no_override(self,saved_df: pd.DataFrame, new_df: pd.DataFrame) -> pd.DataFrame:
        '''
        Function performs an incremental update of a saved DataFrame with a new DataFrame.
        '''
        # Union index
        saved_df = saved_df[~saved_df.index.duplicated(keep="last")]
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
        # Align new df index to match old df index
        if isinstance(index_col, list):
            cols_to_set = [c for c in index_col if c in df.columns and c not in (df.index.names or [])]
            if cols_to_set:
                df = df.reset_index().set_index(index_col)
        merged = self.incremental_update_no_override(old_df, df)
        merged.to_csv(file_path, index=True)

    def generate_read_path(self, dataclass=None, dataype=None, asset_class=None, filename=None, miscell=None):
        # Filter out None values and build path from remaining parts
        parts = [self.base_path]
        for part in [dataclass, dataype, asset_class, filename, miscell]:
            if part is not None:
                parts.append(part)
        return os.path.join(*parts)



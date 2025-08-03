import pandas as pd
import numpy as np


import statsmodels.api as sm
from scipy.stats import norm
from sklearn.feature_selection import RFE
from sklearn.linear_model import LassoCV, RidgeCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import datetime

class featureClean:
    def __init__(self,X,Y):
        self.X = X
        self.Y = Y
    def generate_features(self,change_cols = None,level_cols = None):
        '''
        Given a set of raw feature data, the function separates the features into level and change features.
        Essentially, answers the question is the level of inflation, or change of inflation a driver of returns.
        Level and change features are selected qualitatively.
        Function also drops data with more than 10pct NaN values
        Function also allows for standardization of data

        Parameters:
        ---------------------------------------------------------
        data: dataframe of independent variables
        change_cols: Column names from the raw feature dataframe that will become the change features
        level_cols: Column names from the raw feature dataframe that will become the level features
        na_threshold: Threshold for NaN values before we drop the columns
        '''
        #X = self.X
        data = self.X
        if level_cols is None and change_cols is None:
            return data

        elif level_cols is None:
            change_features = data[change_cols].diff()
            change_features.columns = [c+"_chg" for c in change_features.columns]
            features = change_features
        else:
            level_features = data[level_cols]
            level_features.columns = [c+'_lvl' for c in level_cols]
            change_features = data[change_cols].diff()
            change_features.columns = [c+"_chg" for c in change_cols]
            features = pd.concat([level_features,change_features],axis = 1)


        
        return features
    
    def clean_features(self,features,standardize = True,na_threshold = 0.1):
        if standardize == True:
            features = (features - features.mean())/features.std()
        na_pct = features.isna().mean()
        cols_to_drop = na_pct[na_pct > na_threshold].index.tolist()
        
        # Drop columns
        features = features.drop(columns=cols_to_drop)
        features = features.ffill().fillna(0)
        return features

    def custom_reindex(self,df_to_reindex, df_with_target_index):
        """
        Reindex df_to_reindex using df_with_target_index's index.
        For missing indices, finds the closest available row.
        Function main purpose is to align the indices of the dependent and independent variables
        
        Parameters:
        -----------
        df_to_reindex : pd.DataFrame
            The DataFrame to be reindexed
        df_with_target_index : pd.DataFrame
            The DataFrame whose index will be used as the target
        """
        tgt_columns = df_to_reindex.columns
        #For certain target index, there may be missing values for the independent variable, forward fill those
        df = pd.concat([df_to_reindex,df_with_target_index],axis = 1).ffill()
        df = df[tgt_columns]
        df = df.reindex(index = df_with_target_index.index)
        return df

class featureSelect:
    def __init__(self,X,Y):
        self.X = X
        self.Y = Y


    def feature_selection_mk1(
        self,
        min_corr=0.15,  # Lower initial threshold
        model_type='ridge', 
        n_features=20
        ):
        """
        Improved feature selection that:
        1. Pre-filters with correlation
        2. Uses model-based selection
        3. Validates with cross-validation

        Function first filters out features that have > threshold level of correlation with the dependent variable.
        Next it uses model based recursive features selection, either ridge or lasso, this will help reduce multicollinearity
        """
        X,Y = self.X,self.Y
        # 1. Initial correlation filter (broader net)
        target_col = Y.columns
        data = pd.concat([X,Y],axis = 1)
        corr = data.corr()[target_col].abs()
        #print(corr)
        candidates = corr[corr > min_corr].index.tolist()
        candidates.remove(target_col)
        
        if not candidates:
            raise ValueError("No features meet initial correlation threshold")
        
        X = data[candidates]
        y = data[target_col]
        
        # 2. Model-based selection
        if model_type == 'lasso':
            model = LassoCV(cv=5, max_iter=10)
        else:
            model = RidgeCV(cv=5)
        
        # 3. Recursive Feature Elimination
        pipeline = Pipeline([
            ('scaler', StandardScaler()),
            ('rfe', RFE(estimator=model, n_features_to_select=n_features))
        ])
        
        pipeline.fit(X, y)
        selected_features = X.columns[pipeline.named_steps['rfe'].support_].tolist()
        
        return selected_features
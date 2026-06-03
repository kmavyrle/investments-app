import requests
import pandas as pd
import numpy as np
import os

from functools import reduce

from saber import DataMgmt as dmgmt
from saber import fundEQ_lib as f_eq

dm = dmgmt.DataLake()
cn_eq_tkrs = ['1398.HK',"0939.HK","1288.HK","0857.HK","0386.HK","1088.HK","600519.SS","0941.HK","TCEHY","9988.HK","1211.HK","300750.SZ"]
us_eq_tkrs = ['AAPL','MSFT',"JPM","GOOG","NVDA","GS","XOM","CVX","JNJ","UNH","V","WMT","CAT","AMD","AMZN"]
in_eq_tkrs = ["RELIANCE.NS","TCS.NS","INFY.NS","HDFCBANK.NS","SBIN.NS","LT.NS","ULTRACEMCO.NS","NTPC.NS", "BHARTIARTL.NS","ITC.NS","HINDUNILVR.NS", "MARUTI.NS", "TATAMOTORS.NS","SUNPHARMA.NS", "ADANIPORTS.NS"]
kr_eq_tkrs = ["005930.KS","000660.KS",  "373220.KS","010950.KS", "051910.KS", "005380.KS",  "000270.KS", "005490.KS",  "035420.KS", "035720.KS", "329180.KS", "010140.KS",  "105560.KS",  "055550.KS", "207940.KS"]
eu_eq_tkrs = ["ASML.AS","SAP.DE", "TTE.PA","SIE.DE", "ALV.DE",  "BNP.PA",  "AIR.PA", "SAN.PA", "VOW3.DE", "ABI.BR", "IBE.MC","SAN.MC",  "ENI.MI",    "ISP.MI","SHEL.L" ]
uranium_producers = [
    "CCJ",      # Cameco
    "KAP.L",    # Kazatomprom (London)
    "UEC",      # Uranium Energy Corp
    "UUUU",     # Energy Fuels
    "URG",      # Ur-Energy
    "EU",       # enCore Energy
    "PDN.AX",   # Paladin Energy
    "BOE.AX",   # Boss Energy
    "PEN.AX",   # Peninsula Energy
    "LOT.AX",   # Lotus Resources
    "BMN.AX",   # Bannerman Energy
    "DYL.AX",   # Deep Yellow
    "GLO.TO",   # Global Atomic
    "CGNMF",    # CGN Mining
    "RIO",
    "BHP",
    "GXU.V",    # GoviEx
    "1164.HK",  # CGN Mining
    "DNN",
]
mk_custom_eq = ['CHA',"FLY","LKNCY","ENPH","SNDK","MU","NTR","CF"]

uranium_eq_transcripts = f_eq.get_multi_earnings_transcripts(uranium_producers,2020)
mk_custom_eq_transcripts = f_eq.get_multi_earnings_transcripts(mk_custom_eq, 2020)
cn_eq_tkrs_transcripts = f_eq.get_multi_earnings_transcripts(cn_eq_tkrs,2020)

uranium_eq = f_eq.get_multi_equity_fundamental_data(uranium_producers,start_dt = "2000-01-01",statement = 'all')
mk_custom_eq = f_eq.get_multi_equity_fundamental_data(mk_custom_eq,start_dt = "2000-01-01",statement = 'all')
cn_eq_tkrs = f_eq.get_multi_equity_fundamental_data(cn_eq_tkrs,start_dt = "2000-01-01",statement = 'all')

dm.save_data('raw','fundamental','equities',uranium_eq_transcripts,'uranium_producers_earnings_transcripts.csv',["ticker","year","quarter"])
dm.save_data('raw','fundamental','equities',mk_custom_eq_transcripts,'mk_custom_earnings_transcripts.csv',["ticker","year","quarter"])    
dm.save_data('raw','fundamental','equities',cn_eq_tkrs_transcripts,'cn_eq_tkrs_earnings_transcripts.csv',["ticker","year","quarter"])

dm.save_data('raw','fundamental','equities',uranium_eq,'uranium_producers_full_acc_data.csv',['date','ticker'])
dm.save_data('raw','fundamental','equities',mk_custom_eq,'mk_custom_full_acc_data.csv',['date','ticker'])
dm.save_data('raw','fundamental','equities',cn_eq_tkrs,'cn_eq_tkrs_full_acc_data.csv',['date','ticker'])


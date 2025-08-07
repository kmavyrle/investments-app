from ib_insync import *
import pandas as pd
import numpy as np
util.startLoop()  # uncomment this line when in a notebook

ib = IB()
ib.connect('127.0.0.1', 7496, clientId=1)

def get_latest_fx_quote(pair,exchange="SMART",curncy="USD",
             durationStr = "10 Y",
             endDateTime = "",
             barSizeSetting = "1 day",
             whatToShow = "MIDPOINT",
             useRTH = False):
    contract = Forex(pair)
    pair = ib.reqHistoricalData(contract,durationStr=durationStr,barSizeSetting = barSizeSetting,whatToShow=whatToShow, endDateTime=endDateTime,useRTH=useRTH)#.bid
    return pair


## Get Positions
posns = ib.positions()
ids = [pos.contract.conId for pos in posns]
symbols = [pos.contract.symbol for pos in posns]
positions = [pos.position for pos in posns]
sec_types = [pos.contract.secType for pos in posns]
exchanges = [pos.contract.exchange for pos in posns]
curncy = ["USD"+pos.contract.currency for pos in posns]
volume = [pos.position for pos in posns]
notional_local_curncy = [pos.avgCost * pos.position for pos in posns]
fx_rate = [get_latest_fx_quote(fxpair,durationStr="1 D")[0].close  if fxpair != "USDUSD" else 1.0 for fxpair in curncy]
notional_usd = [pos.avgCost * pos.position / fx_rate[i] for i,pos in enumerate(posns)]

posn_report = pd.DataFrame({
    'ID': ids,
    'Symbol': symbols,
    'Position': positions,
    'Type': sec_types,
    'Exchange': exchanges,
    'Currency': curncy,
    'Volume':volume,
    "notional_local_curncy": notional_local_curncy,
    "exchange_rate": fx_rate,
    "notional_usd": notional_usd
})

ticker_to_sector = {
    'LKNCY': 'Technology',               # Luckin Coffee (Consumer Tech)
    'EXE': 'Energy',                    # Expanad Energy (Oil & Gas)
    'BABA': 'Consumer Cyclical',        # Alibaba (E-commerce)
    '9698': 'Technology',               # XD Inc (Gaming/Software)
    '81810': 'Technology',              # Xiaomi (Consumer Electronics/Tech)
    'UNH': 'Healthcare',                # UnitedHealth Group
    'GRAB': 'Technology',               # Grab Holdings (Ride-hailing/Tech)
    'BILI': 'Communication Services',   # Bilibili (Social Media/Streaming)
    '002594': 'Consumer Cyclical',      # BYD Company (Automotive)
    'XPEV': 'Consumer Cyclical',        # XPeng Inc (Electric Vehicles)
    'IYH': 'Healthcare',               # iShares U.S. Healthcare ETF
    'DSCSY': 'Consumer Cyclical',       # Disco Corp (Electronics)
    'UEC': 'Energy',                   # Uranium Energy Corp
    'CEG': 'Utilities',                # Constellation Energy
    '600875': 'Industrials',           # Dongfang Electric (Heavy Electrical Equipment)
    '000333': 'Consumer Cyclical',     # Midea Group (Appliances)
    'MCHI': 'Financial',               # iShares MSCI China ETF
    'JD': 'Consumer Cyclical',         # JD.com (E-commerce)
    '1164': 'Basic Materials',         # CGN Mining (Uranium Mining)
    '6862': 'Consumer Cyclical',       # Haidilao International (Restaurants)
    'BIDU': 'Communication Services',  # Baidu (Search Engine/Tech)
    'DIDIY': 'Technology',             # DiDi Global (Ride-hailing)
    'PDD': 'Consumer Cyclical',        # Pinduoduo (E-commerce)
    'FVRR': 'Communication Services',  # Fiverr (Freelance Platform)
    'INDY': 'Financial',               # iShares India 50 ETF
    '3690': 'Technology',              # Meituan (E-commerce/Tech)
    'SBET': 'Consumer Cyclical'        # SharpLink Gaming (Gaming)
}

ticker_to_country = {
    # Chinese Companies (Mainland/HK)
    'LKNCY': 'China',         # Luckin Coffee (Pink Sheets, but China-based)
    'BABA': 'China',          # Alibaba (NYSE-listed, China HQ)
    '9698': 'China',          # XD Inc (SEHK-listed)
    '81810': 'China',         # Xiaomi (SEHK-listed)
    'BILI': 'China',          # Bilibili (NASDAQ-listed, China HQ)
    '002594': 'China',        # BYD (SZSE-listed)
    'XPEV': 'China',          # XPeng (NYSE-listed, China HQ)
    '600875': 'China',        # Dongfang Electric (SEHK-listed)
    '000333': 'China',        # Midea Group (SZSE-listed)
    'JD': 'China',            # JD.com (NASDAQ-listed)
    '1164': 'China',          # CGN Mining (SEHK-listed)
    '6862': 'China',          # Haidilao (SEHK-listed)
    'BIDU': 'China',          # Baidu (NASDAQ-listed)
    'DIDIY': 'China',         # DiDi Global (Pink Sheets)
    'PDD': 'China',           # Pinduoduo (NASDAQ-listed)
    '3690': 'China',          # Meituan (SEHK-listed)

    # US Companies
    'UNH': 'USA',             # UnitedHealth Group (NYSE)
    'CEG': 'USA',             # Constellation Energy (NASDAQ)
    'UEC': 'USA',             # Uranium Energy Corp (AMEX)
    'FVRR': 'USA',            # Fiverr (NYSE)
    'SBET': 'USA',            # SharpLink Gaming (NASDAQ)

    # ETFs/Other
    'IYH': 'USA',             # iShares U.S. Healthcare ETF (ARCA)
    'MCHI': 'China',          # iShares MSCI China ETF (NASDAQ)
    'INDY': 'India',          # iShares India 50 ETF (NASDAQ)

    # Other Countries
    'EXE': 'Canada',          # Expanad Energy (likely Canadian energy co)
    'GRAB': 'Singapore',      # Grab Holdings (NASDAQ, Singapore HQ)
    'DSCSY': 'Japan',         # Disco Corp (Pink Sheets, Japan HQ)
}


posn_report.set_index('ID', inplace=True)

stock_mask = posn_report['Type'] == 'STK'
posn_report_stock = posn_report[stock_mask]
posn_report_stock['Sector'] = [ticker_to_sector[tkr] for tkr in posn_report_stock.Symbol]
posn_report_stock['Geography'] = [ticker_to_country[tkr] for tkr in posn_report_stock.Symbol]

posn_report_stock.to_excel('mk_posn_report.xlsx')
#for pos in posns:
#    print(f"Account: {pos.account}, Symbol: {pos.contract.symbol}, Position: {pos.position}, Type: {pos.contract.secType}")


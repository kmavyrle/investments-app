import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import yfinance as yf

from saber import metaLib as mtlib
from saber import PyFolio as pf
from saber import utilities as ut
from saber import mailer as mail

from saber import metaData as mtd
from saber import riskEngine as risk
from saber import PcEngine as pe
from saber import implementationEngine as ie
from saber import PyFolio as pyf
from saber import PerformanceAnalytics as pa
import os

import mt5plalib as plalb

mtw = mtlib.meta5_wrapper(login = 7933713,pw = '1523@Rocket')
PerfA = pa.PA(mtw)
rkm = risk.riskMgr(mtw)
mtd.data(mtw).update_tick_data()
mtd.data(mtw).update_trade_sized_close()
strat_name = 'Discretionary Macro'
plalb.update_floating_pnl(PerfA,r"C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\discretionary_macro\floating_pnl")
plalb.update_realized_pnl(PerfA,r"C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\discretionary_macro\realized_pnl")
plalb.update_portfolio_var(rkm,r"C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\discretionary_macro\var")
pnl_df_dm = plalb.build_pnl_from_files(r"C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\discretionary_macro")
var_ts_dm = -plalb.build_var_timeseries(r"C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\discretionary_macro\var")
plalb.send_acc_summary_email(pnl_df_dm, var_ts_dm, mtw, 'kmavyrle@gmail.com',strategy_name=strat_name)

print(var_ts_dm)


# Usage:
mtw = mtlib.meta5_wrapper()
PerfA = pa.PA(mtw)
rkm = risk.riskMgr(mtw)
strat_name = 'Systematic'
plalb.update_floating_pnl(PerfA,r"C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\systematic\floating_pnl")
plalb.update_realized_pnl(PerfA,r"C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\systematic\realized_pnl")
plalb.update_portfolio_var(rkm,r"C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\systematic\var",wdw = 20)
pnl_df_sys = plalb.build_pnl_from_files(r'C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\systematic')
var_ts_sys = plalb.build_var_timeseries(r'C:\Users\kmavy\Documents\mydocs\My Docs\Investments\investments-app\systematic\var')
plalb.send_acc_summary_email(pnl_df_sys, var_ts_sys, mtw, 'kmavyrle@gmail.com', strategy_name=strat_name)
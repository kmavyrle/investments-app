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

BROKER_TZ = 'Europe/Athens'  # IC Markets server time: EET/EEST (UTC+2 winter, UTC+3 summer)


def _get_last_run_datetime(directory):
    """Load last run datetime (SGT) from last_run.json. Returns None if not found."""
    import json, os
    path = os.path.join(directory, 'last_run.json')
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        data = json.load(f)
    ts = pd.Timestamp(data['last_run_sgt'])
    if ts.tzinfo is None:
        ts = ts.tz_localize(BROKER_TZ)
    else:
        ts = ts.tz_convert(BROKER_TZ)
    return ts


def _save_last_run_datetime(directory, dt=None):
    """Save current (or given) SGT datetime to last_run.json."""
    import json, os
    if dt is None:
        dt = pd.Timestamp.utcnow().tz_convert(BROKER_TZ)
    path = os.path.join(directory, 'last_run.json')
    with open(path, 'w') as f:
        json.dump({'last_run_sgt': dt.isoformat()}, f)
    print(f"Last run timestamp saved: {dt.isoformat()}")


def update_realized_pnl(PerfA, directory, start_date="2026-01-01"):
    """
    Update realized PnL CSVs. Uses last_run.json to determine from_datetime
    so intraday trades are never missed between runs. Falls back to start_date
    if no prior run timestamp exists.
    """
    import os

    now_sgt = pd.Timestamp.utcnow().tz_convert(BROKER_TZ)
    today_str = now_sgt.strftime("%Y-%m-%d")

    # Determine the start date to use
    last_run = _get_last_run_datetime(directory)  # returns SGT-aware timestamp
    if last_run is not None:
        from_date_str = last_run.strftime("%Y-%m-%d")
        print(f"Resuming from last run: {last_run.isoformat()}")
    else:
        from_date_str = start_date if start_date else today_str
        print(f"No prior run found, using start_date: {from_date_str}")

    # Generate all dates from last run date (inclusive) to today
    date_range = pd.date_range(start=from_date_str, end=today_str, freq='D')

    for date in date_range:
        date_str = date.strftime("%Y-%m-%d")
        filename = f"realized_pnl_{date_str}.csv"
        filepath = os.path.join(directory, filename)

        # Past dates: skip if file already exists (can't change)
        # Last-run date and today: always refresh to capture any new trades
        is_refresh_date = (last_run is not None and date_str == from_date_str) or date_str == today_str
        if os.path.exists(filepath) and not is_refresh_date:
            print(f"Already exists: {filename} - skipping")
            continue

        try:
            df = PerfA.get_realized_pnl_by_date(date.to_pydatetime())

            if df is None or df.empty:
                print(f"No realized trades on {date_str} - skipping")
                continue

            if df.drop(columns='TOTAL', errors='ignore').sum().sum() == 0:
                print(f"No realized trades on {date_str} - skipping")
                continue

            df.to_csv(filepath, index_label='Date')
            print(f"Saved: {filename}")

        except Exception as e:
            print(f"Error on {date_str}: {e} - skipping")
            continue

    # Save the timestamp of this run so next call knows where to resume from
    _save_last_run_datetime(directory, now_sgt)



def update_floating_pnl(PerfA, directory):
    import os
    
    today = pd.Timestamp.utcnow().tz_convert(BROKER_TZ).strftime("%Y-%m-%d")
    filename = f"floating_pnl_{today}.csv"
    filepath = os.path.join(directory, filename)
    
    df = PerfA.get_acc_floating_pnl()
    
    if df.empty or df.drop(columns='TOTAL', errors='ignore').sum().sum() == 0:
        print(f"No open positions - skipping save")
        return
    
    df.to_csv(filepath, index_label='Date')
    print(f"Saved: {filename}")
    return df

def update_portfolio_var(rkm, directory,wdw = 250):
    import os
    
    today = pd.Timestamp.utcnow().tz_convert(BROKER_TZ).strftime("%Y-%m-%d")
    filename = f"portfolio_var_{today}.csv"
    filepath = os.path.join(directory, filename)
    
    var = rkm.get_portfolio_var(wdw = wdw)
    
    # Wrap in dataframe with today's date if not already a dataframe
    if not isinstance(var, pd.DataFrame):
        df = pd.DataFrame({'VaR': [var]}, index=[today])
        df.index.name = 'Date'
    else:
        df = var.copy()
        df.index = [today]
        df.index.name = 'Date'
    
    if df.empty:
        print(f"No VaR data - skipping save")
        return
    
    df.to_csv(filepath, index_label='Date')
    print(f"Saved: {filename}")
    return df



def build_pnl_from_files(directory):
    import os
    import glob
    
    floating_dir = os.path.join(directory, 'floating_pnl')
    realized_dir = os.path.join(directory, 'realized_pnl')
    
    # Read all floating PnL files
    floating_files = sorted(glob.glob(os.path.join(floating_dir, '*.csv')))
    floating_dfs = []
    for f in floating_files:
        df = pd.read_csv(f, index_col='Date')
        df.drop(columns='TOTAL', errors='ignore', inplace=True)
        df.index = pd.to_datetime(df.index, format='mixed', dayfirst=True).strftime('%Y-%m-%d')
        floating_dfs.append(df)
    
    # Read all realized PnL files
    realized_files = sorted(glob.glob(os.path.join(realized_dir, '*.csv')))
    realized_dfs = []
    for f in realized_files:
        df = pd.read_csv(f, index_col='Date')
        df.drop(columns='TOTAL', errors='ignore', inplace=True)
        df.index = pd.to_datetime(df.index, format='mixed', dayfirst=True).strftime('%Y-%m-%d')
        realized_dfs.append(df)
    
    # Combine floating
    if len(floating_dfs) > 0:
        floating_combined = pd.concat(floating_dfs, axis=0, join='outer').fillna(0)
        floating_combined = floating_combined.groupby(floating_combined.index).sum()
    else:
        floating_combined = pd.DataFrame()
    
    # Combine realized (daily values, not cumulated yet)
    if len(realized_dfs) > 0:
        realized_combined = pd.concat(realized_dfs, axis=0, join='outer').fillna(0)
        realized_combined = realized_combined.groupby(realized_combined.index).sum()
    else:
        realized_combined = pd.DataFrame()
    
    # Get all dates from both sources
    all_dates = sorted(set(
        floating_combined.index.tolist() + realized_combined.index.tolist()
    ))
    
    # Align columns
    all_cols = list(set(
        floating_combined.columns.tolist() + realized_combined.columns.tolist()
    ))
    
    # Reindex BEFORE cumsum - fill missing realized dates with 0
    if len(realized_combined) > 0:
        realized_combined = realized_combined.reindex(index=all_dates, columns=all_cols, fill_value=0)
        realized_combined = realized_combined.sort_index()
        # Now cumsum - missing dates contribute 0 but carry forward previous cumulative
        realized_cumulative = realized_combined.cumsum()
    else:
        realized_cumulative = pd.DataFrame(0, index=all_dates, columns=all_cols)
    
    # Reindex floating - use ffill for missing dates (carry forward last known floating value)
    if len(floating_combined) > 0:
        floating_combined = floating_combined.reindex(index=all_dates, columns=all_cols)
        floating_combined = floating_combined.sort_index().ffill().fillna(0)
    else:
        floating_combined = pd.DataFrame(0, index=all_dates, columns=all_cols)
    
    # Combined PnL = cumulative realized + floating
    pnl = realized_cumulative + floating_combined
    pnl['TOTAL'] = pnl.sum(axis=1)
    
    # Drop duplicates just in case
    pnl = pnl[~pnl.index.duplicated(keep='first')]
    
    return pnl



def build_var_timeseries(directory):
    """
    Read all VaR CSVs from directory and construct a timeseries
    
    Parameters:
    -----------
    directory : str
        Path to the var folder
    
    Returns:
    --------
    pd.DataFrame
        Timeseries with date as index and VaR as values
    """
    import os
    import glob
    
    var_files = sorted(glob.glob(os.path.join(directory, '*.csv')))
    
    dfs = []
    for f in var_files:
        df = pd.read_csv(f, index_col='Date')
        dfs.append(df)
    
    if len(dfs) > 0:
        var_ts = pd.concat(dfs)
        var_ts = var_ts.groupby(var_ts.index).last()  # Keep last if duplicate dates
        var_ts.index = pd.to_datetime(var_ts.index, format='mixed', dayfirst=True)
        var_ts.sort_index(inplace=True)
    else:
        var_ts = pd.DataFrame(columns=['VaR'])
    
    return var_ts



def get_risk_positions_notional(mtw):
    """
    Get notional value of all open positions
    Notional = lot_size * contract_size * current_price
    
    Returns:
    --------
    pd.DataFrame
        DataFrame with position details and notional values per asset
    """
    positions = mtw.mt5.positions_get()
    
    if positions is None or len(positions) == 0:
        print("No open positions")
        return pd.DataFrame(columns=['Volume', 'Contract Size', 'Price', 'Direction', 'Notional'])
    
    data = {}
    exclude_assets = ['USDJPY',"EURUSD","AUDUSD","GBPUSD","USDMXN","AUDJPY","GBPJPY","EURAUD",'USDCAD']
    for p in positions:
        symbol = p.symbol
        if symbol in exclude_assets:
            continue
        volume = p.volume
        price = p.price_current
        contract_size = mtw.get_symbol_info(symbol).trade_contract_size
        direction = 1 if p.type == 0 else -1  # 0 = Buy, 1 = Sell
        notional = volume * contract_size * price * direction
        
        if symbol in data:
            data[symbol]['Volume'] += volume * direction
            data[symbol]['Notional'] += notional
        else:
            data[symbol] = {
                'Volume': volume * direction,
                'Contract Size': contract_size,
                'Price': price,
                'Direction': 'Long' if direction == 1 else 'Short',
                'Notional': notional
            }
    
    df = pd.DataFrame(data).T
    df.index.name = 'Symbol'


    
    return df

def get_non_currency_longs(mtw):
    pos_df = get_risk_positions_notional(mtw)
    
    # FX pairs are 6 characters with no "." (e.g., EURUSD, USDJPY, AUDUSD)
    fx_pairs  = ['USDJPY','AUDJPY',"EURUSD","EURAUD","AUDNZD","GBPUSD","USDMXN","USDZAR","USDCAD"]
    fx_symbols = [sym for sym in pos_df.index if sym in fx_pairs]
    
    # Filter: long positions that are NOT FX
    non_fx_longs = pos_df[(pos_df['Notional'] > 0) & (~pos_df.index.isin(fx_symbols))]
    
    return non_fx_longs

    
def get_non_currency_shorts(mtw):
    pos_df = get_risk_positions_notional(mtw)
    
    # FX pairs are 6 characters with no "." (e.g., EURUSD, USDJPY, AUDUSD)
    fx_pairs  = ['USDJPY','AUDJPY',"EURUSD","EURAUD","AUDNZD","GBPUSD","USDMXN","USDZAR","USDCAD"]
    fx_symbols = [sym for sym in pos_df.index if sym in fx_pairs]
    
    # Filter: long positions that are NOT FX
    non_fx_shorts = pos_df[(pos_df['Notional'] < 0) & (~pos_df.index.isin(fx_symbols))]
    
    return non_fx_shorts

def plot_non_fx_pie_charts(mtw):
    non_fx_longs = get_non_currency_longs(mtw)
    non_fx_shorts = get_non_currency_shorts(mtw)
    
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    
    if len(non_fx_longs) > 0:
        longs_pct = non_fx_longs['Notional'] / non_fx_longs['Notional'].sum() * 100
        axes[0].pie(longs_pct, labels=longs_pct.index, autopct='%1.1f%%', startangle=90)
        axes[0].set_title('Non-FX Longs')
    else:
        axes[0].text(0.5, 0.5, 'No Long Positions', ha='center', va='center')
        axes[0].set_title('Non-FX Longs')
    
    if len(non_fx_shorts) > 0:
        shorts_pct = non_fx_shorts['Notional'].abs() / non_fx_shorts['Notional'].abs().sum() * 100
        axes[1].pie(shorts_pct, labels=shorts_pct.index, autopct='%1.1f%%', startangle=90)
        axes[1].set_title('Non-FX Shorts')
    else:
        axes[1].text(0.5, 0.5, 'No Short Positions', ha='center', va='center')
        axes[1].set_title('Non-FX Shorts')
    
    plt.tight_layout()
    plt.show()

# Usage:
# plot_non_fx_pie_charts(mtw)
def get_expanding_sharpe(pnl_df, column='TOTAL', annualization_factor=252):
    """
    Calculate expanding (cumulative) Sharpe ratio over time
    
    Parameters:
    -----------
    pnl_df : pd.DataFrame
        Cumulative PnL dataframe
    column : str
        Column to calculate Sharpe on (default 'TOTAL')
    annualization_factor : int
        Trading days per year (default 252)
    
    Returns:
    --------
    pd.Series
        Expanding Sharpe ratio at each date
    """
    # Get daily returns from cumulative PnL
    daily_returns = pnl_df[column].diff()
    
    # Expanding mean and std
    expanding_mean = daily_returns.expanding(min_periods=2).mean()
    expanding_std = daily_returns.expanding(min_periods=2).std()
    
    # Annualized Sharpe ratio
    sharpe = (expanding_mean / expanding_std) * np.sqrt(annualization_factor)
    sharpe.name = 'Sharpe Ratio'
    
    return sharpe



def send_acc_summary_email(pnl_df, var_ts, mtw, recipient, strategy_name):
    """
    Send discretionary macro portfolio summary email with charts
    
    Parameters:
    -----------
    pnl_df : pd.DataFrame
        Cumulative PnL dataframe (from build_pnl_from_files)
    var_ts : pd.DataFrame
        VaR timeseries (from build_var_timeseries)
    mtw : meta5_wrapper
        MT5 wrapper for getting positions
    recipient : str
        Email address to send to
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import base64
    import tempfile
    import os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from saber import mailer
    
    today = pd.Timestamp.utcnow().tz_convert(BROKER_TZ).strftime("%Y-%m-%d")
    chart_paths = []
    temp_dir = tempfile.mkdtemp()
    
    # Sort PnL by date
    df = pnl_df.copy()
    df.index = pd.to_datetime(df.index, format='mixed', dayfirst=True)
    df.sort_index(inplace=True)
    
    # --- Chart 1: Cumulative PnL ---
    fig, ax = plt.subplots(figsize=(8, 3))
    df['TOTAL'].plot(ax=ax)
    ax.set_title('Cumulative PnL')
    ax.set_ylabel('PnL (USD)')
    ax.grid(True, alpha=0.3)
    path1 = os.path.join(temp_dir, 'cum_pnl.png')
    fig.savefig(path1, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path1)
    
    # --- Chart 2: Daily VaR ---
    fig, ax = plt.subplots(figsize=(8, 3))
    var_ts.plot(ax=ax, kind = 'bar',color = 'red')
    ax.set_title('Daily Portfolio VaR (95% CVaR)')
    ax.set_ylabel('VaR (USD)')
    ax.grid(True, alpha=0.3)
    path2 = os.path.join(temp_dir, 'var.png')
    fig.savefig(path2, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path2)
    
    # --- Chart 3: Non-FX Long/Short Exposure ---
    non_fx_longs = get_non_currency_longs(mtw)
    non_fx_shorts = get_non_currency_shorts(mtw)
    
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    
    if len(non_fx_longs) > 0:
        longs_pct = non_fx_longs['Notional'] / non_fx_longs['Notional'].sum() * 100
        axes[0].pie(longs_pct, labels=longs_pct.index, autopct='%1.1f%%', startangle=90)
        axes[0].set_title('Non-FX Longs')
    else:
        axes[0].text(0.5, 0.5, 'No Long Positions', ha='center', va='center')
        axes[0].set_title('Non-FX Longs')
    
    if len(non_fx_shorts) > 0:
        shorts_pct = non_fx_shorts['Notional'].abs() / non_fx_shorts['Notional'].abs().sum() * 100
        axes[1].pie(shorts_pct, labels=shorts_pct.index, autopct='%1.1f%%', startangle=90)
        axes[1].set_title('Non-FX Shorts')
    else:
        axes[1].text(0.5, 0.5, 'No Short Positions', ha='center', va='center')
        axes[1].set_title('Non-FX Shorts')
    
    plt.tight_layout()
    path3 = os.path.join(temp_dir, 'exposure.png')
    fig.savefig(path3, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path3)
    
    # --- Chart 4: Expanding Sharpe Ratio ---
    expanding_sharpe = get_expanding_sharpe(df)
    
    fig, ax = plt.subplots(figsize=(8, 3))
    expanding_sharpe.plot(ax=ax)
    ax.set_title('Expanding Sharpe Ratio (Annualized)')
    ax.set_ylabel('Sharpe Ratio')
    ax.grid(True, alpha=0.3)
    path4 = os.path.join(temp_dir, 'sharpe.png')
    fig.savefig(path4, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path4)
    
    # --- Key Metrics ---
    total_pnl = df['TOTAL'].iloc[-1]
    latest_var = var_ts['VaR'].iloc[-1] if len(var_ts) > 0 else 0
    latest_sharpe = expanding_sharpe.iloc[-1] if len(expanding_sharpe.dropna()) > 0 else 0
    long_notional = non_fx_longs['Notional'].sum() if len(non_fx_longs) > 0 else 0
    short_notional = non_fx_shorts['Notional'].sum() if len(non_fx_shorts) > 0 else 0
    
    # --- Build Email ---
    msg = MIMEMultipart('related')
    msg['Subject'] = f'{strategy_name} Summary - {today}'
    msg['To'] = recipient
    
    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>{strategy_name} Summary - {today}</h2>
        
        <h3>Key Metrics</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
            <tr><td><b>Total PnL</b></td><td>{total_pnl:,.2f}</td></tr>
            <tr><td><b>Portfolio VaR (95% CVaR)</b></td><td>{latest_var:,.2f}</td></tr>
            <tr><td><b>Sharpe Ratio</b></td><td>{latest_sharpe:,.2f}</td></tr>
            <tr><td><b>Non-FX Long Notional</b></td><td>{long_notional:,.2f}</td></tr>
            <tr><td><b>Non-FX Short Notional</b></td><td>{short_notional:,.2f}</td></tr>
            <tr><td><b>Non-FX Net Notional</b></td><td>{long_notional + short_notional:,.2f}</td></tr>
        </table>
        
        <h3>Cumulative PnL</h3>
        <img src="cid:chart1" width="600">
        
        <h3>Daily Portfolio VaR</h3>
        <img src="cid:chart2" width="600">
        
        <h3>Non-FX Exposure Breakdown</h3>
        <img src="cid:chart3" width="600">
        
        <h3>Expanding Sharpe Ratio</h3>
        <img src="cid:chart4" width="600">
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    for i, path in enumerate(chart_paths, 1):
        with open(path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', f'<chart{i}>')
            msg.attach(img)
    
    # Send via Gmail API
    service = mailer.get_service()
    raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw_msg}).execute()
    
    # Cleanup
    for path in chart_paths:
        os.remove(path)
    
    print(f"Discretionary Macro summary sent to {recipient}")


def get_deposit_history(mtw, from_date="2020-01-01"):
    from_dt = datetime.datetime.strptime(from_date, "%Y-%m-%d")
    to_dt = datetime.datetime.utcnow() + datetime.timedelta(days=1)

    deals = mtw.mt5.history_deals_get(from_dt, to_dt)
    if deals is None or len(deals) == 0:
        return pd.DataFrame(columns=['deposit', 'cumulative_deposits'])

    rows = []
    for d in deals:
        if d.type == 2 and d.symbol == "":  # DEAL_TYPE_BALANCE = 2
            dt_sgt = pd.Timestamp(d.time, unit='s', tz='UTC').tz_convert(BROKER_TZ)
            rows.append({'date': dt_sgt.strftime('%Y-%m-%d'), 'amount': d.profit})

    if not rows:
        return pd.DataFrame(columns=['deposit', 'cumulative_deposits'])

    df = pd.DataFrame(rows).groupby('date')['amount'].sum().rename('deposit')
    df.index = pd.to_datetime(df.index)
    df = df.sort_index().to_frame()
    #df['cumulative_deposits'] = df['deposit'].cumsum()
    return df


def send_dgm_summary_email(pnl_df, var_ts, mtw, recipient):
    """
    Send discretionary macro portfolio summary email with charts
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import base64
    import tempfile
    import os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from saber import mailer

    today = pd.Timestamp.utcnow().tz_convert(BROKER_TZ).strftime("%Y-%m-%d")
    chart_paths = []
    temp_dir = tempfile.mkdtemp()

    df = pnl_df.copy()
    df.index = pd.to_datetime(df.index, format='mixed', dayfirst=True)
    df.sort_index(inplace=True)

    # Chart 1: Cumulative PnL
    fig, ax = plt.subplots(figsize=(8, 3))
    df['TOTAL'].plot(ax=ax)
    ax.set_title('Cumulative PnL')
    ax.set_ylabel('PnL (USD)')
    ax.grid(True, alpha=0.3)
    path1 = os.path.join(temp_dir, 'cum_pnl.png')
    fig.savefig(path1, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path1)

    # Chart 2: Daily VaR
    fig, ax = plt.subplots(figsize=(8, 3))
    var_ts.plot(ax=ax, kind='bar', color='red')
    ax.set_title('Daily Portfolio VaR (95% CVaR)')
    ax.set_ylabel('VaR (USD)')
    ax.grid(True, alpha=0.3)
    path2 = os.path.join(temp_dir, 'var.png')
    fig.savefig(path2, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path2)

    # Chart 3: Non-FX Long/Short Exposure
    non_fx_longs = get_non_currency_longs(mtw)
    non_fx_shorts = get_non_currency_shorts(mtw)

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    if len(non_fx_longs) > 0:
        longs_pct = non_fx_longs['Notional'] / non_fx_longs['Notional'].sum() * 100
        axes[0].pie(longs_pct, labels=longs_pct.index, autopct='%1.1f%%', startangle=90)
        axes[0].set_title('Non-FX Longs')
    else:
        axes[0].text(0.5, 0.5, 'No Long Positions', ha='center', va='center')
        axes[0].set_title('Non-FX Longs')
    if len(non_fx_shorts) > 0:
        shorts_pct = non_fx_shorts['Notional'].abs() / non_fx_shorts['Notional'].abs().sum() * 100
        axes[1].pie(shorts_pct, labels=shorts_pct.index, autopct='%1.1f%%', startangle=90)
        axes[1].set_title('Non-FX Shorts')
    else:
        axes[1].text(0.5, 0.5, 'No Short Positions', ha='center', va='center')
        axes[1].set_title('Non-FX Shorts')
    plt.tight_layout()
    path3 = os.path.join(temp_dir, 'exposure.png')
    fig.savefig(path3, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path3)

    # Chart 4: Expanding Sharpe Ratio
    expanding_sharpe = get_expanding_sharpe(df)
    fig, ax = plt.subplots(figsize=(8, 3))
    expanding_sharpe.plot(ax=ax)
    ax.set_title('Expanding Sharpe Ratio (Annualized)')
    ax.set_ylabel('Sharpe Ratio')
    ax.grid(True, alpha=0.3)
    path4 = os.path.join(temp_dir, 'sharpe.png')
    fig.savefig(path4, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path4)

    # Key Metrics
    total_pnl = df['TOTAL'].iloc[-1]
    latest_var = var_ts['VaR'].iloc[-1] if len(var_ts) > 0 else 0
    latest_sharpe = expanding_sharpe.iloc[-1] if len(expanding_sharpe.dropna()) > 0 else 0
    long_notional = non_fx_longs['Notional'].sum() if len(non_fx_longs) > 0 else 0
    short_notional = non_fx_shorts['Notional'].sum() if len(non_fx_shorts) > 0 else 0

    msg = MIMEMultipart('related')
    msg['Subject'] = f'Discretionary Macro Summary - {today}'
    msg['To'] = recipient

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>Discretionary Macro Summary - {today}</h2>
        <h3>Key Metrics</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
            <tr><td><b>Total PnL</b></td><td>{total_pnl:,.2f}</td></tr>
            <tr><td><b>Portfolio VaR (95% CVaR)</b></td><td>{latest_var:,.2f}</td></tr>
            <tr><td><b>Sharpe Ratio</b></td><td>{latest_sharpe:,.2f}</td></tr>
            <tr><td><b>Non-FX Long Notional</b></td><td>{long_notional:,.2f}</td></tr>
            <tr><td><b>Non-FX Short Notional</b></td><td>{short_notional:,.2f}</td></tr>
            <tr><td><b>Non-FX Net Notional</b></td><td>{long_notional + short_notional:,.2f}</td></tr>
        </table>
        <h3>Cumulative PnL</h3><img src="cid:chart1" width="600">
        <h3>Daily Portfolio VaR</h3><img src="cid:chart2" width="600">
        <h3>Non-FX Exposure Breakdown</h3><img src="cid:chart3" width="600">
        <h3>Expanding Sharpe Ratio</h3><img src="cid:chart4" width="600">
    </body>
    </html>
    """

    msg.attach(MIMEText(html, 'html'))
    for i, path in enumerate(chart_paths, 1):
        with open(path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', f'<chart{i}>')
            msg.attach(img)

    service = mailer.get_service()
    raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw_msg}).execute()

    for path in chart_paths:
        os.remove(path)

    print(f"Discretionary Macro summary sent to {recipient}")

def send_full_portfolio_email(dgm_pnl_df, sys_pnl_df, dgm_var_ts, sys_var_ts, mtw, recipient):
    """
    Send full portfolio summary email combining Discretionary Macro + Systematic strategies.
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import base64
    import tempfile
    import os
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    from saber import mailer

    today = pd.Timestamp.utcnow().tz_convert(BROKER_TZ).strftime("%Y-%m-%d")
    chart_paths = []
    temp_dir = tempfile.mkdtemp()

    # Align and combine PnL
    dgm = dgm_pnl_df.copy()
    sys = sys_pnl_df.copy()
    dgm.index = pd.to_datetime(dgm.index, format='mixed', dayfirst=True)
    sys.index = pd.to_datetime(sys.index, format='mixed', dayfirst=True)
    dgm.sort_index(inplace=True)
    sys.sort_index(inplace=True)

    combined_total = pd.DataFrame({
        'Discretionary Macro': dgm['TOTAL'],
        'Systematic': sys['TOTAL'],
    }).fillna(method='ffill').fillna(0)
    combined_total['Total Portfolio'] = combined_total.sum(axis=1)

    # Chart 1: Strategy PnL comparison
    fig, ax = plt.subplots(figsize=(10, 4))
    combined_total[['Discretionary Macro', 'Systematic', 'Total Portfolio']].plot(ax=ax)
    ax.set_title('Cumulative PnL by Strategy')
    ax.set_ylabel('PnL (USD)')
    ax.grid(True, alpha=0.3)
    path1 = os.path.join(temp_dir, 'combined_pnl.png')
    fig.savefig(path1, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path1)

    # Chart 2: Combined VaR
    dgm_var = dgm_var_ts.copy()
    sys_var = sys_var_ts.copy()
    dgm_var.index = pd.to_datetime(dgm_var.index, format='mixed', dayfirst=True)
    sys_var.index = pd.to_datetime(sys_var.index, format='mixed', dayfirst=True)
    combined_var = pd.DataFrame({
        'DGM VaR': dgm_var.iloc[:, 0],
        'Sys VaR': sys_var.iloc[:, 0],
    }).fillna(0)
    combined_var['Total VaR'] = combined_var.sum(axis=1)

    fig, ax = plt.subplots(figsize=(10, 3))
    combined_var[['DGM VaR', 'Sys VaR']].plot(ax=ax, kind='bar', stacked=True, color=['steelblue', 'tomato'])
    ax.set_title('Daily Portfolio VaR by Strategy (95% CVaR)')
    ax.set_ylabel('VaR (USD)')
    ax.grid(True, alpha=0.3)
    path2 = os.path.join(temp_dir, 'combined_var.png')
    fig.savefig(path2, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path2)

    # Chart 3: Non-FX Exposure
    non_fx_longs = get_non_currency_longs(mtw)
    non_fx_shorts = get_non_currency_shorts(mtw)

    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    if len(non_fx_longs) > 0:
        longs_pct = non_fx_longs['Notional'] / non_fx_longs['Notional'].sum() * 100
        axes[0].pie(longs_pct, labels=longs_pct.index, autopct='%1.1f%%', startangle=90)
        axes[0].set_title('Non-FX Longs')
    else:
        axes[0].text(0.5, 0.5, 'No Long Positions', ha='center', va='center')
        axes[0].set_title('Non-FX Longs')
    if len(non_fx_shorts) > 0:
        shorts_pct = non_fx_shorts['Notional'].abs() / non_fx_shorts['Notional'].abs().sum() * 100
        axes[1].pie(shorts_pct, labels=shorts_pct.index, autopct='%1.1f%%', startangle=90)
        axes[1].set_title('Non-FX Shorts')
    else:
        axes[1].text(0.5, 0.5, 'No Short Positions', ha='center', va='center')
        axes[1].set_title('Non-FX Shorts')
    plt.tight_layout()
    path3 = os.path.join(temp_dir, 'exposure.png')
    fig.savefig(path3, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path3)

    # Chart 4: Expanding Sharpe (total portfolio)
    total_df = combined_total[['Total Portfolio']].rename(columns={'Total Portfolio': 'TOTAL'})
    expanding_sharpe = get_expanding_sharpe(total_df)
    fig, ax = plt.subplots(figsize=(10, 3))
    expanding_sharpe.plot(ax=ax)
    ax.set_title('Expanding Sharpe Ratio - Full Portfolio (Annualized)')
    ax.set_ylabel('Sharpe Ratio')
    ax.grid(True, alpha=0.3)
    path4 = os.path.join(temp_dir, 'sharpe.png')
    fig.savefig(path4, bbox_inches='tight', dpi=100)
    plt.close(fig)
    chart_paths.append(path4)

    # Key Metrics
    dgm_pnl   = combined_total['Discretionary Macro'].iloc[-1]
    sys_pnl   = combined_total['Systematic'].iloc[-1]
    total_pnl = combined_total['Total Portfolio'].iloc[-1]
    latest_var = combined_var['Total VaR'].iloc[-1] if len(combined_var) > 0 else 0
    latest_sharpe = expanding_sharpe.iloc[-1] if len(expanding_sharpe.dropna()) > 0 else 0
    long_notional  = non_fx_longs['Notional'].sum()  if len(non_fx_longs)  > 0 else 0
    short_notional = non_fx_shorts['Notional'].sum() if len(non_fx_shorts) > 0 else 0

    msg = MIMEMultipart('related')
    msg['Subject'] = f'Full Portfolio Summary - {today}'
    msg['To'] = recipient

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2>Full Portfolio Summary - {today}</h2>
        <h3>Key Metrics</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse;">
            <tr><td><b>Total PnL</b></td><td>{total_pnl:,.2f}</td></tr>
            <tr><td><b>Discretionary Macro PnL</b></td><td>{dgm_pnl:,.2f}</td></tr>
            <tr><td><b>Systematic PnL</b></td><td>{sys_pnl:,.2f}</td></tr>
            <tr><td><b>Total VaR (95% CVaR)</b></td><td>{latest_var:,.2f}</td></tr>
            <tr><td><b>Sharpe Ratio (Full Port)</b></td><td>{latest_sharpe:,.2f}</td></tr>
            <tr><td><b>Non-FX Long Notional</b></td><td>{long_notional:,.2f}</td></tr>
            <tr><td><b>Non-FX Short Notional</b></td><td>{short_notional:,.2f}</td></tr>
            <tr><td><b>Non-FX Net Notional</b></td><td>{long_notional + short_notional:,.2f}</td></tr>
        </table>
        <h3>Cumulative PnL by Strategy</h3><img src="cid:chart1" width="700">
        <h3>Daily VaR by Strategy</h3><img src="cid:chart2" width="700">
        <h3>Non-FX Exposure Breakdown</h3><img src="cid:chart3" width="600">
        <h3>Expanding Sharpe Ratio (Full Portfolio)</h3><img src="cid:chart4" width="700">
    </body>
    </html>
    """

    msg.attach(MIMEText(html, 'html'))
    for i, path in enumerate(chart_paths, 1):
        with open(path, 'rb') as f:
            img = MIMEImage(f.read())
            img.add_header('Content-ID', f'<chart{i}>')
            msg.attach(img)

    service = mailer.get_service()
    raw_msg = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    service.users().messages().send(userId='me', body={'raw': raw_msg}).execute()

    for path in chart_paths:
        os.remove(path)

    print(f"Full portfolio summary sent to {recipient}")


def get_cumulative_deposits(mtw, from_date="2020-01-01"):
    deposit_history = get_deposit_history(mtw, from_date)
    if deposit_history.empty:
        return pd.DataFrame(columns=['cumulative_deposits'])
    deposit_history['cumulative_deposits'] = deposit_history['deposit'].cumsum()
    return deposit_history[['cumulative_deposits']]

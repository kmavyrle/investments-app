import streamlit as st

import pandas as pd
import numpy as np
import datetime
import yfinance as yf
import os

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from saber import ai_lib

#from saber import PerformanceAnalytics as pa
import DataMgmt as dm

from PIL import Image
import pyOptions as Op


image = Image.open('Purple Eye with Glowing Star Symbol.png')
#risk = re.riskMgr()
# Page config
st.set_page_config(
    page_title="DB",
    page_icon = image,
    layout="wide"
)

alib = ai_lib.mkAI()

### Create Key Classes
dl = dm.DataLake()
read_path = r"C:\Users\kmavy\Documents\mydocs\Investments\data_lake\raw\fundamental\equities"
eq_csv_files = [f for f in os.listdir(read_path) if f.endswith('_full_acc_data.csv')]
universe_map = {f.replace('_full_acc_data.csv', '').replace('_', ' ').upper(): f for f in eq_csv_files}
universe_options = ['All'] + sorted(universe_map.keys())


# Sidebar
with st.sidebar:
    #image = Image.open('4Sightlogo2.jpg')
    #st.image(image)
    st.title("Settings")
    
    #st.title("Settings")
    
    # Navigation
    st.subheader("Navigation")
    
    if st.button("Price Monitor", use_container_width=True):
        st.session_state.page = "Price Monitor"
    
    if st.button("Macro", use_container_width=True):
        st.session_state.page = "Macro"

    if st.button("Equity Fundamentals", use_container_width=True):
        st.session_state.page = "Equity Fundamentals"
    
    if st.button("Portfolio Analytics", use_container_width=True):
        st.session_state.page = "Portfolio Analytics"
    
    if st.button("Options", use_container_width=True):
        st.session_state.page = "Options"
    
    # Initialize page if not set
    if 'page' not in st.session_state:
        st.session_state.page = "Price Monitor"

    page = st.session_state.page


# Main content
st.markdown("## Analytics")

if page == "Price Monitor":
    st.markdown("### Price Monitor")
    tabs = st.tabs(["Returns Plot"])
    col1,col2 = st.columns(2)
    with col1:
        assets = st.text_input('Enter Assets: ', value = 'MCHI')
    with col2:
        start_dt_returns = st.text_input('Enter Start Date: ', value = '2021-01-01')
    assets = list(assets.split(','))
    data = yf.download(assets,start = start_dt_returns)[['Close']]
    data.columns = data.columns.get_level_values(1)
    data = data.pct_change().fillna(0)
    data = (1+data).cumprod()-1
    data = data.reset_index()

    fig = px.line(data, x='Date', y=assets)
    st.plotly_chart(fig)

    


elif page == "Macro":
    macro_tabs = st.tabs(['Global Macro','Interest Rates'])
    
    with macro_tabs[0]:
            #st.header("Global Macro")
        #Create columns
        #tabs = st.tabs(["Macro Monitor"])


        macro_df = pd.read_csv('fred_data.csv',index_col = 0)
        macro_options = list(set(macro_df.Name))



        macro_df= pd.pivot_table(macro_df,values='value',index = 'Date',columns = 'Name').ffill().astype(float)
        # Get last and second-to-last values
        # Get current (last) values
        current_values = macro_df.iloc[-1]

        # Function to find last different value for each column
        def find_last_different_value(series):
            current_val = series.iloc[-1]
            # Look backwards from second-to-last value
            for i in range(len(series) - 2, -1, -1):
                if series.iloc[i] != current_val:
                    return series.iloc[i]
            return current_val  # If no different value found, return current

        # Get last different values for each column
        last_different_values = macro_df.apply(find_last_different_value)

        # Calculate changes
        changes = current_values - last_different_values
        macro_df = macro_df.reset_index()

        



        # Create display dataframe
        display_df = pd.DataFrame({
            'Current Value': last_different_values,
            'Change': changes
        })

        # Function to change font color
        def highlight_changes(val):
            if val > 0:
                return 'color: green'
            elif val < 0:
                return 'color: red'
            else:
                return ''

        # Apply styling
        styled_df = display_df.style.map(highlight_changes, subset=['Change']).format(precision=3)


        # Display in Streamlit
        st.subheader("Macro Monitor")
        st.dataframe(styled_df, use_container_width=True)   
        #print(macro_df)
        col1,col2 = st.columns(2)
        with col1:

            st_macro_option = st.selectbox("Macro Indicator",macro_options)
        with col2:
            start_dt = st.text_input('Enter Start Date: ', value = '2021-01-01')
        macro_df = macro_df[macro_df.Date>=start_dt]    
        #st.subheader('Visualize')
        fig = px.line(macro_df,x = 'Date',y = st_macro_option)
        st.plotly_chart(fig)
    with macro_tabs[1]:
        ir_col1,ir_col2 = st.columns(2)
        with ir_col1:
            ir_hist = pd.read_csv("interest_rates.csv")
            st.write(ir_hist)

elif page == "Equity Fundamentals":
    selected_universe = st.selectbox("Investment Universe", universe_options, key="inv_universe")
    if selected_universe == 'All':
        load_files = eq_csv_files
    else:
        load_files = [universe_map[selected_universe]]
    full_acc_data = []
    for f in load_files:
        full_acc_data.append(dl.read_data("raw", 'fundamental', 'equities', f, index_col='date'))
    full_acc_data = pd.concat(full_acc_data)
    num_cols = full_acc_data.columns.difference(['ticker'])
    full_acc_data[num_cols] = full_acc_data[num_cols].apply(pd.to_numeric, errors='coerce')

    eq_tabs = ["Equity"]
    eq_tickers = sorted(full_acc_data["ticker"].unique())

    exclude_cols = {'ticker', 'period', 'period_label', 'symbol', 'fiscal_year', 'fiscal_period', 'calendar_year', 'calendar_period', 'currency'}
    acc_labels = [c for c in full_acc_data.columns if c not in exclude_cols and pd.api.types.is_numeric_dtype(full_acc_data[c])]

    # Categorize metrics by statement type
    def get_metric_category(col):
        if col.startswith('is_'):
            return 'Income Statement'
        elif col.startswith('bs_') or col in ['Working_Capital', 'NCWC']:
            return 'Balance Sheet'
        elif col.startswith('cf_'):
            return 'Cash Flow'
        elif col.endswith('_margin') or col in ['cur_ratio', 'cash_conversion_cycle', 'net_debt_to_shrhldr_eqty', 'tce_ratio', 'tot_debt_to_tot_cap', 'total_debt_to_ev', 'ROIC']:
            return 'Ratios'
        elif col.endswith('_per_sh') or col in ['eps', 'diluted_eps', 'eps_cont_ops', 'dil_eps_cont_ops', 'div_per_shr']:
            return 'Per Share'
        elif col in ['market_cap', 'enterprise_value', 'diluted_mkt_cap', 'diluted_ev', 'short_and_long_term_debt', 'net_debt'] or col.startswith('ev_to_') or col.startswith('pr_to_'):
            return 'Valuation'
        elif col.startswith('ttm_'):
            return 'TTM Metrics'
        else:
            return 'Other'

    # Build category to metrics mapping
    metric_categories = {}
    for col in acc_labels:
        cat = get_metric_category(col)
        if cat not in metric_categories:
            metric_categories[cat] = []
        metric_categories[cat].append(col)

    category_options = ['All'] + sorted(metric_categories.keys())

    with st.container():
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            selected_tickers = st.multiselect(
                "Select stock ticker(s)",
                eq_tickers,
                default=[eq_tickers[0]] if eq_tickers else []
            )

        with col2:
            selected_category = st.selectbox(
                "Select statement type",
                category_options
            )

        with col3:
            if selected_category == 'All':
                filtered_metrics = acc_labels
            else:
                filtered_metrics = metric_categories.get(selected_category, [])

            selected_metrics = st.multiselect(
                "Select accounting metric(s)",
                filtered_metrics,
                default=[filtered_metrics[0]] if len(filtered_metrics) > 0 else []
            )

        with col4:
            chart_start_date = st.text_input(
                "Chart start date",
                value="2015-01-01"
            )
            chart_start_dt = pd.Timestamp(chart_start_date)

    if not selected_tickers:
        st.warning("Please select at least one ticker.")
    else:
        # Calculate valuation ratios
        df_calc = full_acc_data.reset_index().copy()
        # Calculate TTM net income (sum of last 4 quarters per ticker)
        df_calc = df_calc.sort_values(['ticker', 'date'])
        df_calc['ttm_net_income'] = df_calc.groupby('ticker')['is_net_income'].transform(lambda x: x.rolling(4, min_periods=4).sum())
        df_calc['PE_Ratio'] = df_calc['market_cap'] / df_calc['ttm_net_income'].replace(0, np.nan)
        df_calc['Price_to_Book'] = df_calc['market_cap'] / df_calc['bs_total_equity'].replace(0, np.nan)
        df_calc['Price_to_Revenue'] = df_calc['market_cap'] / df_calc['ttm_net_sales'].replace(0, np.nan)
        df_calc['EV_EBITDA'] = df_calc['ev_to_ttm_ebitda']
        df_calc['Working_Capital'] = df_calc['bs_cur_asset_report'] - df_calc['bs_cur_liab']
        df_calc['FCF_Yield'] =100* df_calc['cf_free_cash_flow']/df_calc['market_cap']##(df_calc['free_cash_flow_per_sh'] * df_calc['bs_sh_out']) / df_calc['market_cap'].replace(0, np.nan) * 100

        colors = px.colors.qualitative.Plotly

        eq_tab_equity, eq_tab_valuation = st.tabs(["Equity Analysis", "Valuation Comparison"])

        with eq_tab_equity:
            # Fetch stock price returns for selected tickers
            price_data = yf.download(selected_tickers, start=chart_start_date)['Close']
            # Handle single ticker case - ensure it's a DataFrame with proper column name
            if isinstance(price_data, pd.Series):
                price_data = price_data.to_frame(name=selected_tickers[0])
            elif len(selected_tickers) == 1 and isinstance(price_data, pd.DataFrame):
                price_data.columns = selected_tickers
            price_returns = (price_data.pct_change().fillna(0) + 1).cumprod() - 1
            price_returns = price_returns.reset_index()
            price_returns['Date'] = pd.to_datetime(price_returns['Date']).dt.tz_localize(None)

            fig = make_subplots(specs=[[{"secondary_y": True}]])

            color_idx = 0
            for selected_metric in selected_metrics:
                df_plot = (
                    full_acc_data
                    .reset_index()
                    .pivot_table(
                        index="date",
                        columns="ticker",
                        values=selected_metric
                    )[selected_tickers]
                    .dropna()
                    .reset_index()
                )
                df_plot = df_plot[df_plot['date'] >= chart_start_dt]

                for ticker in selected_tickers:
                    fig.add_trace(
                        go.Bar(x=df_plot['date'], y=df_plot[ticker], name=f"{ticker} ({selected_metric})",
                               marker_color=colors[color_idx % len(colors)], opacity=0.7),
                        secondary_y=False
                    )
                    color_idx += 1

            for i, ticker in enumerate(selected_tickers):
                if ticker in price_returns.columns:
                    fig.add_trace(
                        go.Scatter(x=price_returns['Date'], y=price_returns[ticker], name=f"{ticker} Returns",
                                   line=dict(color=colors[i % len(colors)], width=2, dash='dot')),
                        secondary_y=True
                    )

            fig.update_layout(
                title=f"{', '.join(selected_tickers)} – {', '.join(selected_metrics)} vs Returns",
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            fig.update_yaxes(title_text=', '.join(selected_metrics), secondary_y=False)
            fig.update_yaxes(title_text="Cumulative Returns", tickformat=".0%", secondary_y=True)
            fig.update_xaxes(title_text="Date")

            st.plotly_chart(fig, use_container_width=True)

            # --- Financial Statement Subtabs ---
            stmt_tabs = st.tabs(["Income Statement", "Balance Sheet", "Cash Flow", "Ratios"])

            stmt_metrics = {
                "Income Statement": [
                    ('is_sales_revenue_turnover', 'Revenue'),
                    ('is_cogs', 'COGS'),
                    ('is_gross_profit', 'Gross Profit'),
                    ('is_sg_and_a_expense', 'SG&A'),
                    ('is_operating_expenses_r_and_d', 'R&D'),
                    ('is_oper_income', 'Operating Income'),
                    ('ebitda', 'EBITDA'),
                    ('is_pretax_income', 'Pre-tax Income'),
                    ('is_net_income', 'Net Income'),
                    ('diluted_eps', 'Diluted EPS'),
                ],
                "Balance Sheet": [
                    ('bs_tot_asset', 'Total Assets'),
                    ('bs_cur_asset_report', 'Current Assets'),
                    ('bs_c_and_ce_and_sti_detailed', 'Cash & Equivalents'),
                    ('bs_inventories', 'Inventories'),
                    ('bs_acct_note_rcv', 'Accounts Receivable'),
                    ('bs_cur_liab', 'Current Liabilities'),
                    ('bs_tot_liab', 'Total Liabilities'),
                    ('short_and_long_term_debt', 'Total Debt'),
                    ('net_debt', 'Net Debt'),
                    ('bs_total_equity', 'Total Equity'),
                    ('bs_sh_out', 'Shares Outstanding'),
                ],
                "Cash Flow": [
                    ('cf_cash_from_oper', 'Operating Cash Flow'),
                    ('cf_cap_expenditures', 'CapEx'),
                    ('cf_free_cash_flow', 'Free Cash Flow'),
                    ('cf_depr_amort', 'D&A'),
                    ('cf_cash_from_inv_act', 'Investing Cash Flow'),
                    ('cf_cash_from_fin_act', 'Financing Cash Flow'),
                    ('cf_dvd_paid', 'Dividends Paid'),
                    ('cf_chng_non_cash_work_cap', 'Change in Working Capital'),
                ],
                "Ratios": [
                    ('gross_margin', 'Gross Margin'),
                    ('oper_margin', 'Operating Margin'),
                    ('profit_margin', 'Profit Margin'),
                    ('ebitda_margin', 'EBITDA Margin'),
                    ('cur_ratio', 'Current Ratio'),
                    ('net_debt_to_shrhldr_eqty', 'Net Debt / Equity'),
                    ('tot_debt_to_tot_cap', 'Debt / Total Cap'),
                    ('cash_conversion_cycle', 'Cash Conversion Cycle'),
                    ('ROIC', 'ROIC'),
                ],
            }

            for tab, tab_name in zip(stmt_tabs, stmt_metrics):
                with tab:
                    metrics = [(col, label) for col, label in stmt_metrics[tab_name] if col in df_calc.columns]
                    if not metrics:
                        st.info(f"No {tab_name} data available.")
                        continue
                    cols_list = [col for col, _ in metrics]
                    label_map = {col: label for col, label in metrics}

                    for ticker in selected_tickers:
                        tk_data = (
                            df_calc[(df_calc['ticker'] == ticker) & (df_calc['date'] >= chart_start_dt)]
                            .sort_values('date')
                            .drop_duplicates(subset='date')
                            .set_index('date')[cols_list]
                            .rename(columns=label_map)
                        )
                        st.subheader(ticker)
                        st.dataframe(tk_data.style.format("{:,.2f}"), use_container_width=True)

            # --- 2x2 Analytics Grid ---
            with st.container(border=True):
                # Prepare data for all charts
                df_filtered = df_calc[df_calc['ticker'].isin(selected_tickers)].copy()
                df_filtered = df_filtered.sort_values(['ticker', 'date'])

                # Valuation multiples
                df_filtered['Price_FCF'] = df_filtered['pr_to_free_cash_flow']
                df_filtered['EV_Sales'] = df_filtered['ev_to_ttm_sales']

                # Growth metrics
                for col, label in [('revenue_per_sh', 'Revenue Growth'),
                                   ('cf_net_inc', 'Earnings Growth'),
                                   ('diluted_eps', 'EPS Growth'),
                                   ('cf_free_cash_flow', 'FCF Growth')]:
                    if col in df_filtered.columns:
                        lagged = df_filtered.groupby('ticker')[col].shift(4)
                        df_filtered[label] = df_filtered[col] - lagged.replace(0, np.nan)#) - 1

                # Earnings stability
                df_filtered['Earnings_Stdev'] = df_filtered.groupby('ticker')['ttm_net_income'].transform(
                    lambda x: x.rolling(8, min_periods=4).std()
                )
                df_filtered['Net_Debt_EBITDA'] = df_filtered['net_debt'] / df_filtered['ttm_ebitda'].replace(0, np.nan)

                df_plot_grid = df_filtered[df_filtered['date'] >= chart_start_dt]

                # Row 1
                row1_col1, row1_col2 = st.columns(2)

                with row1_col1:
                    val_multiples = {'PE_Ratio': 'PE Ratio', 'EV_EBITDA': 'EV / EBITDA',
                                     'EV_Sales': 'EV / Sales', 'Price_FCF': 'Price / FCF'}
                    val_fig = go.Figure()
                    for ticker in selected_tickers:
                        tk_data = df_plot_grid[df_plot_grid['ticker'] == ticker]
                        for col, label in val_multiples.items():
                            if col in tk_data.columns:
                                val_fig.add_trace(go.Scatter(
                                    x=tk_data['date'], y=tk_data[col],
                                    name=f"{ticker} {label}", mode='lines+markers'
                                ))
                    val_fig.update_layout(title="Valuation Multiples", height=350,
                                          legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                          margin=dict(l=40, r=20, t=80, b=40))
                    st.plotly_chart(val_fig, use_container_width=True)

                with row1_col2:
                    growth_cols = ['Revenue Growth', 'Earnings Growth', 'EPS Growth', 'FCF Growth']
                    growth_cols = [c for c in growth_cols if c in df_plot_grid.columns]
                    growth_fig = go.Figure()
                    for ticker in selected_tickers:
                        tk_data = df_plot_grid[df_plot_grid['ticker'] == ticker]
                        for gc in growth_cols:
                            growth_fig.add_trace(go.Scatter(
                                x=tk_data['date'], y=tk_data[gc],
                                name=f"{ticker} {gc}", mode='lines+markers'
                            ))
                    growth_fig.update_layout(title="YoY Growth Trends", height=350,
                                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                             margin=dict(l=40, r=20, t=80, b=40))
                    st.plotly_chart(growth_fig, use_container_width=True)

                # Row 2
                row2_col1, row2_col2 = st.columns(2)

                with row2_col1:
                    margin_fig = go.Figure()
                    for ticker in selected_tickers:
                        tk_data = df_plot_grid[df_plot_grid['ticker'] == ticker]
                        margin_fig.add_trace(go.Scatter(
                            x=tk_data['date'], y=tk_data['gross_margin'],
                            name=f"{ticker} Gross Margin", mode='lines+markers'
                        ))
                        margin_fig.add_trace(go.Scatter(
                            x=tk_data['date'], y=tk_data['oper_margin'],
                            name=f"{ticker} Oper Margin", mode='lines+markers',
                            line=dict(dash='dash')
                        ))
                    margin_fig.update_layout(title="Gross & Operating Margins", height=350,
                                             legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                             margin=dict(l=40, r=20, t=80, b=40))
                    st.plotly_chart(margin_fig, use_container_width=True)

                with row2_col2:
                    stab_fig = make_subplots(specs=[[{"secondary_y": True}]])
                    for i, ticker in enumerate(selected_tickers):
                        tk_data = df_plot_grid[df_plot_grid['ticker'] == ticker]
                        stab_fig.add_trace(go.Bar(
                            x=tk_data['date'], y=tk_data['Earnings_Stdev'],
                            name=f"{ticker} Earnings Stdev (Rolling 2-Year)", marker_color=colors[i % len(colors)], opacity=0.6
                        ), secondary_y=False)
                        stab_fig.add_trace(go.Scatter(
                            x=tk_data['date'], y=tk_data['Net_Debt_EBITDA'],
                            name=f"{ticker} Net Debt/EBITDA", line=dict(color=colors[i % len(colors)], width=2)
                        ), secondary_y=True)
                    stab_fig.update_layout(title="Earnings Stability & Leverage", barmode='group', height=350,
                                           legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                           margin=dict(l=40, r=20, t=80, b=40))
                    stab_fig.update_yaxes(title_text="Earnings Stdev", secondary_y=False)
                    stab_fig.update_yaxes(title_text="Net Debt / EBITDA", secondary_y=True)
                    st.plotly_chart(stab_fig, use_container_width=True)

        # --- Earnings Transcripts ---
        with st.container(border=True):
            st.subheader("Earnings Transcripts")

            transcript_path = r"C:\Users\kmavy\Documents\mydocs\Investments\data_lake\raw\fundamental\equities"
            transcript_files = [f for f in os.listdir(transcript_path) if f.endswith('_earnings_transcripts.csv')]

            if transcript_files:
                all_transcripts = pd.concat([
                    pd.read_csv(os.path.join(transcript_path, f))
                    for f in transcript_files
                ], ignore_index=True)
                all_transcripts = all_transcripts.drop(columns=['Unnamed: 0'], errors='ignore')
                all_transcripts['date'] = pd.to_datetime(all_transcripts['date'], format='mixed', utc=True).dt.tz_localize(None)
                ticker_transcripts = all_transcripts[all_transcripts['ticker'].isin(selected_tickers)]

                if ticker_transcripts.empty:
                    st.info("No earnings transcripts found for selected ticker(s).")
                else:
                    t_col1, t_col2, t_col3 = st.columns(3)
                    with t_col1:
                        transcript_ticker = st.selectbox("Ticker", sorted(ticker_transcripts['ticker'].unique()), key="transcript_ticker")
                    tk_transcripts = ticker_transcripts[ticker_transcripts['ticker'] == transcript_ticker].sort_values('date', ascending=False)
                    with t_col2:
                        transcript_options = [f"Q{row['quarter']} {row['year']} — {row['date'].strftime('%Y-%m-%d') if pd.notna(row['date']) else ''}" for _, row in tk_transcripts.iterrows()]
                        selected_transcript_idx = st.selectbox("Quarter", range(len(transcript_options)), format_func=lambda i: transcript_options[i], key="transcript_quarter")
                    with t_col3:
                        st.metric("Latest Quarter", transcript_options[0] if transcript_options else "N/A")

                    selected_row = tk_transcripts.iloc[selected_transcript_idx]
                    st.markdown(f"**{transcript_ticker} — Q{selected_row['quarter']} {selected_row['year']}**")
                    st.text_area("Transcript", value=selected_row['transcript'], height=400, key="transcript_text", disabled=True)

                    st.divider()
                    st.markdown("**AI Analysis**")
                    ai_prompt = st.text_area(
                        "Enter your prompt (will be prepended to the transcript)",
                        placeholder="e.g. Summarise the key risks mentioned in this earnings call.",
                        height=100,
                        key="ai_prompt_input"
                    )
                    if st.button("Analyze Transcript", key="ai_analyze_btn"):
                        if ai_prompt.strip():
                            full_prompt = f"{ai_prompt.strip()}\n\n{selected_row['transcript']}"
                            with st.spinner("Thinking..."):
                                ai_response = alib.ask(full_prompt)
                            st.session_state["ai_transcript_response"] = ai_response
                        else:
                            st.warning("Please enter a prompt before analyzing.")

                    if "ai_transcript_response" in st.session_state:
                        st.markdown("**Response:**")
                        st.markdown(st.session_state["ai_transcript_response"])
            else:
                st.info("No transcript files found in data lake.")

        with eq_tab_valuation:
            key_ratios = ['PE_Ratio', 'Price_to_Book', 'Price_to_Revenue', 'EV_EBITDA', 'FCF_Yield','cur_ratio','cash_conversion_cycle','net_debt_to_shrhldr_eqty','tce_ratio','tot_debt_to_tot_cap','total_debt_to_ev']
            latest_metrics = df_calc.pivot_table(index='date', columns='ticker', values=key_ratios).ffill().iloc[[-1]].unstack().reset_index().ffill()
            latest_metrics.columns = ['Metric', 'Ticker', 'Date of Calc', 'Latest Value']
            latest_metrics = latest_metrics.pivot_table(index='Metric', columns='Ticker', values='Latest Value')
            # Filter to only selected tickers
            latest_metrics = latest_metrics[[t for t in selected_tickers if t in latest_metrics.columns]]

            st.subheader("Valuation Comparison")
            st.dataframe(latest_metrics.style.format("{:.2f}"), use_container_width=True)

            # --- 2x2 Valuation Bar Charts ---
            df_val = df_calc[df_calc['ticker'].isin(selected_tickers)].copy()
            df_val = df_val.sort_values(['ticker', 'date'])
            # Get latest row per ticker
            df_latest = df_val.groupby('ticker').last().reset_index()

            # Calculate Dividend Yield (annualised div_per_shr / price proxy from market_cap/shares)
            if 'div_per_shr' in df_latest.columns and 'bs_sh_out' in df_latest.columns:
                price_approx = df_latest['market_cap'] / df_latest['bs_sh_out'].replace(0, np.nan)
                df_latest['Div_Yield'] = (df_latest['div_per_shr'].abs() / price_approx.replace(0, np.nan)) * 100
            else:
                df_latest['Div_Yield'] = np.nan

            with st.container(border=True):
                vr1c1, vr1c2 = st.columns(2)

                with vr1c1:
                    pe_sorted = df_latest.sort_values('PE_Ratio')
                    pe_fig = go.Figure(go.Bar(
                        x=pe_sorted['ticker'], y=pe_sorted['PE_Ratio'],
                        marker_color=colors[:len(pe_sorted)], text=pe_sorted['PE_Ratio'].round(1), textposition='outside'
                    ))
                    pe_fig.update_layout(title="PE Ratio", height=350,
                                         margin=dict(l=40, r=20, t=60, b=40), yaxis_title="PE",
                                         xaxis=dict(categoryorder='array', categoryarray=pe_sorted['ticker'].tolist()))
                    st.plotly_chart(pe_fig, use_container_width=True)

                with vr1c2:
                    ev_sorted = df_latest.sort_values('EV_EBITDA')
                    ev_fig = go.Figure(go.Bar(
                        x=ev_sorted['ticker'], y=ev_sorted['EV_EBITDA'],
                        marker_color=colors[:len(ev_sorted)], text=ev_sorted['EV_EBITDA'].round(1), textposition='outside'
                    ))
                    ev_fig.update_layout(title="EV / EBITDA", height=350,
                                         margin=dict(l=40, r=20, t=60, b=40), yaxis_title="EV/EBITDA",
                                         xaxis=dict(categoryorder='array', categoryarray=ev_sorted['ticker'].tolist()))
                    st.plotly_chart(ev_fig, use_container_width=True)

                vr2c1, vr2c2 = st.columns(2)

                with vr2c1:
                    dy_sorted = df_latest.sort_values('Div_Yield')
                    dy_fig = go.Figure(go.Bar(
                        x=dy_sorted['ticker'], y=dy_sorted['Div_Yield'],
                        marker_color=colors[:len(dy_sorted)], text=dy_sorted['Div_Yield'].round(2), textposition='outside'
                    ))
                    dy_fig.update_layout(title="Dividend Yield (%)", height=350,
                                         margin=dict(l=40, r=20, t=60, b=40), yaxis_title="Yield %",
                                         xaxis=dict(categoryorder='array', categoryarray=dy_sorted['ticker'].tolist()))
                    st.plotly_chart(dy_fig, use_container_width=True)

                with vr2c2:
                    mm_sorted = df_latest.sort_values('Price_to_Book')
                    mm_fig = go.Figure()
                    mm_fig.add_trace(go.Bar(
                        x=mm_sorted['ticker'], y=mm_sorted['Price_to_Book'],
                        name='Price / Book', marker_color=colors[0], text=mm_sorted['Price_to_Book'].round(1), textposition='outside'
                    ))
                    mm_fig.add_trace(go.Bar(
                        x=mm_sorted['ticker'], y=mm_sorted['Price_to_Revenue'],
                        name='Price / Sales', marker_color=colors[1], text=mm_sorted['Price_to_Revenue'].round(1), textposition='outside'
                    ))
                    mm_fig.add_trace(go.Bar(
                        x=mm_sorted['ticker'], y=mm_sorted['net_debt_to_shrhldr_eqty'],
                        name='Debt / Equity', marker_color=colors[2], text=mm_sorted['net_debt_to_shrhldr_eqty'].round(1), textposition='outside'
                    ))
                    mm_fig.update_layout(title="Market Multiples", height=350, barmode='group',
                                         legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                                         margin=dict(l=40, r=20, t=80, b=40), yaxis_title="Multiple",
                                         xaxis=dict(categoryorder='array', categoryarray=mm_sorted['ticker'].tolist()))
                    st.plotly_chart(mm_fig, use_container_width=True)


elif page == "Portfolio Analytics":
    port_tabs = st.tabs(['Equities Exposure','Agentic Trader'])
    with port_tabs[0]:
        st.markdown("### Portfolio Analytics")
        posn = pd.read_excel("mk_posn_report.xlsx")
        col1,col2,col3 = st.columns(3)

        with col1:
            st.subheader('Position Breakdown')
            posn_chart = px.pie(posn,names ='Symbol',values='notional_usd'  )
            st.plotly_chart(posn_chart)
        with col2:
            st.subheader('Sector Breakdown')
            sector_chart = px.pie(posn, names = 'Sector', values = 'notional_usd')
            st.plotly_chart(sector_chart)
        with col3:
            st.subheader('Geography Breakdown')
            geography_chart = px.pie(posn,names = 'Geography',values = 'notional_usd')
            st.plotly_chart(geography_chart)
        st.write(posn)
    #st.write("Reports content goes here")
    with port_tabs[1]:
        with st.container(border = True):
            
            pnl = pa.get_daily_pnl()
            start = pd.DataFrame([0,0,0,0,0,0,0,0,0,0])
            start = start.T
            start.columns = pnl.columns
            start.index = ['2025-09-20']
            start.index.names = ['Date']
            pnl = pd.concat([start,pnl])
            
            #print(pnl)

            sharpe = round((pnl['TOTAL'].mean()/pnl['TOTAL'].std())*np.sqrt(252),2)
            prev_sharpe = round((pnl.iloc[:-1]['TOTAL'].mean()/pnl.iloc[:-1]['TOTAL'].std())*np.sqrt(252),2)
            sharpe_chg = round(sharpe-prev_sharpe,2)
            pnl = pnl.cumsum()
            latest_pnl = int(pnl['TOTAL'].iloc[-1])
            prev_pnl = int(pnl['TOTAL'].iloc[-2])
            pnl_chg = latest_pnl-prev_pnl
                
            portfolio_var = risk.get_portfolio_var()
            p_var = round(portfolio_var,2)
            col1,col2 = st.columns([0.3,1])
            with col1:
                st.metric(label = 'Sharpe Ratio',value = sharpe,delta = sharpe_chg)
                st.metric(label = 'Total PnL', value = "$"+str(latest_pnl),delta = prev_pnl )
                st.metric(label = '95% CVaR', value = p_var)
                st.write(pa.get_portfolio_details())
            with col2:
                st.markdown("#### Daily PnL Chart")
                pnl_chart = px.line(pnl.reset_index(),x ='Date',y = pnl.columns)
                pnl_chart.update_traces(line = dict(width = 1.5))
                pnl_chart['data'][-1]['line']['color'] = 'darkblue'
                pnl_chart['data'][-1]['line']['width'] = 4
                st.plotly_chart(pnl_chart)
                
            
            
            

        st.markdown("#### Daily PnL")
        st.write(pnl)

elif page == "Options":
    option_tabs = st.tabs(["Option Pricer","Vol Surface"])
    with option_tabs[0]:
        noptions = st.text_input('Enter Number of Options', value =1) 
        col1,col2,col3,col4,col5,col6= st.columns(6)
        
        with col1:
            S = st.text_input('Enter S0: ', value = 100)
            S2 = st.text_input('Enter S0_2: ', value = 100)
        with col2:
            expiry = st.text_input('Enter Expiry: ', value = '2030-12-31')
            expiry2 = st.text_input('Enter Expiry 2: ', value = '2030-12-31')
        with col3:
            option_type = st.selectbox("Option Type", ["c", "p"])
            option_type2 = st.selectbox("Option Type 2", ["c", "p"])
        with col4:
            strike_price = st.number_input("Strike", value=100)
            strike_price2 = st.number_input("Strike 2", value=100)
        with col5:
            iv = st.text_input("Enter IV", value=0.2)
            iv2 = st.text_input("Enter IV    2", value=0.2)  
        with col6:
            operator = st.text_input("Volume & dir",value = "1")
            operator2 = st.text_input("Volume & dir 2",value = "1")


        noptions = int(noptions)
        expiry = datetime.datetime.strptime(expiry, '%Y-%m-%d').date()
        dte = (expiry - datetime.date.today()).days
        dte = dte/365
        opt = Op.Option(float(S),float(strike_price),0,dte,float(iv),cp = option_type)
        if noptions == 2:
            expiry2 = datetime.datetime.strptime(expiry2, '%Y-%m-%d').date()
            dte2 = (expiry2 - datetime.date.today()).days
            dte2 = dte2/365
            opt2 = Op.Option(float(S2),float(strike_price2),0,dte2,float(iv2),cp = option_type2)


        st.subheader("Option Details")
        st.write("Option Price 1: ",round(opt.bsprice(),4))
        if noptions == 2:
            st.write("Option Price 2: ",round(opt2.bsprice(),4))

        st.subheader("Payoff Profile")
        col7,col8 = st.columns(2)
        with col7:
            lower_bound = st.number_input("Enter Lower Bound", value=0)
        with col8:  
            upper_bound = st.number_input("Enter Upper Bound", value=200)
        payoff1 = opt.get_payoffs(np.arange(lower_bound, upper_bound, 1))
        if noptions == 2:
            payoff2 = opt2.get_payoffs(np.arange(lower_bound, upper_bound, 1))
            payoffs = pd.concat([payoff1, payoff2], axis=1)
            payoffs.columns = ['Payoff 1', 'Payoff 2']
            payoffs['Payoff'] = float(operator)*payoffs["Payoff 1"] + float(operator2) * payoffs['Payoff 2']
            payoffs = pd.DataFrame(payoffs, columns=['Payoff'])
        else:
            payoffs = payoff1
        st.plotly_chart(px.line(payoffs, x=payoffs.index, y='Payoff', title='Payoff Profile')) 




        # --- Quality Decision Tree ---
        '''with st.container(border=True):
            st.subheader("Quality Decision Tree")
            tree_ticker = st.selectbox("Analyze ticker", selected_tickers, key="tree_ticker")

            tk = df_filtered[df_filtered['ticker'] == tree_ticker].sort_values('date')
            if len(tk) >= 5:
                latest = tk.iloc[-1]
                prev4 = tk.iloc[-5]

                # --- Compute all checks ---
                rev_now = latest.get('ttm_net_sales', np.nan)
                rev_prev = prev4.get('ttm_net_sales', np.nan)
                rev_growing = (rev_now > rev_prev) if pd.notna(rev_now) and pd.notna(rev_prev) else None
                gm_now = latest.get('gross_margin', np.nan)
                gm_prev = prev4.get('gross_margin', np.nan)
                gm_stable = (gm_now >= gm_prev - 2) if pd.notna(gm_now) and pd.notna(gm_prev) else None
                om_now = latest.get('oper_margin', np.nan)
                om_positive = (om_now > 0) if pd.notna(om_now) else None
                income_pass = all(x is True for x in [rev_growing, gm_stable, om_positive])

                cfo = latest.get('cf_cash_from_oper', np.nan)
                ni = latest.get('is_net_income', np.nan)
                fcf = latest.get('cf_free_cash_flow', np.nan)
                fcf_prev = prev4.get('cf_free_cash_flow', np.nan)
                cfo_vs_ni = (cfo >= ni) if pd.notna(cfo) and pd.notna(ni) else None
                fcf_positive = (fcf > 0) if pd.notna(fcf) else None
                fcf_rising = (fcf > fcf_prev) if pd.notna(fcf) and pd.notna(fcf_prev) else None
                cash_pass = all(x is True for x in [cfo_vs_ni, fcf_positive])

                ncwc_change = latest.get('cf_chng_non_cash_work_cap', np.nan)
                ncwc_ok = (ncwc_change <= 0 or (pd.notna(rev_now) and pd.notna(rev_prev) and
                           abs(ncwc_change) < abs(rev_now - rev_prev))) if pd.notna(ncwc_change) else None

                debt_eq = latest.get('net_debt_to_shrhldr_eqty', np.nan)
                int_exp = abs(latest.get('is_net_interest_expense', np.nan)) if pd.notna(latest.get('is_net_interest_expense', np.nan)) else np.nan
                ebit = latest.get('is_oper_income', np.nan)
                int_coverage = (ebit / int_exp) if pd.notna(ebit) and pd.notna(int_exp) and int_exp > 0 else np.nan
                debt_ok = (debt_eq < 100) if pd.notna(debt_eq) else None
                coverage_ok = (int_coverage > 3) if pd.notna(int_coverage) else None
                leverage_pass = all(x is True for x in [x for x in [debt_ok, coverage_ok] if x is not None])

                tax_rate = 0.25
                nopat = ebit * (1 - tax_rate) if pd.notna(ebit) else np.nan
                tot_equity = latest.get('bs_total_equity', np.nan)
                net_debt_val = latest.get('net_debt', np.nan)
                invested_cap = (tot_equity + net_debt_val) if pd.notna(tot_equity) and pd.notna(net_debt_val) else np.nan
                roic = (nopat / invested_cap * 100) if pd.notna(nopat) and pd.notna(invested_cap) and invested_cap > 0 else np.nan
                roic_good = (roic >= 10) if pd.notna(roic) else None

                capex = abs(latest.get('cf_cap_expenditures', 0))
                capex_ratio = (capex / cfo * 100) if pd.notna(cfo) and cfo > 0 else np.nan
                capex_moderate = (capex_ratio < 50) if pd.notna(capex_ratio) else None

                score = sum(1 for x in [income_pass, cash_pass, ncwc_ok, leverage_pass,
                                         roic_good, capex_moderate] if x is True)

                if score >= 5:
                    verdict, v_color = "CASH MACHINE", "#00C853"
                elif score >= 3:
                    verdict, v_color = "CASH HUNGRY", "#FF9800"
                else:
                    verdict, v_color = "VALUE TRAP", "#F44336"

                def _fmt(val, pct=False, ratio=False):
                    if pd.isna(val) or val is None: return "N/A"
                    if pct: return f"{val:.1f}%"
                    if ratio: return f"{val:.1f}x"
                    return f"{val:,.0f}"

                # --- Build decision tree flowchart ---
                steps = [
                    {"label": "1. Income Statement",
                     "detail": f"Rev: {_fmt(rev_now)} | GM: {_fmt(gm_now,pct=True)} | OM: {_fmt(om_now,pct=True)}",
                     "passed": income_pass, "fail_label": "SPECULATIVE"},
                    {"label": "2. Cash Flow",
                     "detail": f"CFO: {_fmt(cfo)} | NI: {_fmt(ni)} | FCF: {_fmt(fcf)}",
                     "passed": cash_pass, "fail_label": "HIGH RISK"},
                    {"label": "3. Working Capital",
                     "detail": f"NCWC chg: {_fmt(ncwc_change)}",
                     "passed": ncwc_ok, "fail_label": "WC > Revenue"},
                    {"label": "4. Leverage",
                     "detail": f"D/E: {_fmt(debt_eq,pct=True)} | Int Cov: {_fmt(int_coverage,ratio=True)}",
                     "passed": leverage_pass, "fail_label": "OVERLEVERAGED"},
                    {"label": "5. ROIC",
                     "detail": f"ROIC: {_fmt(roic,pct=True)}",
                     "passed": roic_good, "fail_label": "No Moat (<10%)"},
                    {"label": "6. Capex",
                     "detail": f"Capex/CFO: {_fmt(capex_ratio,pct=True)}",
                     "passed": capex_moderate, "fail_label": "Heavy Capex"},
                ]

                tree_fig = go.Figure()

                # Layout: main path x=0, fail branches x=2.5, y goes 7 down to 0
                node_x, fail_x = 0, 2.8
                y_start = len(steps) + 1
                node_w, node_h = 1.8, 0.35

                # Draw nodes and edges
                for i, step in enumerate(steps):
                    y = y_start - i
                    passed = step["passed"]
                    color = "#4CAF50" if passed else "#F44336" if passed is False else "#9E9E9E"

                    # Main node box
                    tree_fig.add_shape(type="rect",
                        x0=node_x - node_w, y0=y - node_h, x1=node_x + node_w, y1=y + node_h,
                        fillcolor=color, line=dict(color="white", width=2),
                        layer="below")

                    # Node label
                    tree_fig.add_annotation(x=node_x, y=y + 0.08, text=f"<b>{step['label']}</b>",
                        showarrow=False, font=dict(color="white", size=12))
                    tree_fig.add_annotation(x=node_x, y=y - 0.15, text=step['detail'],
                        showarrow=False, font=dict(color="white", size=9))

                    # Arrow down to next node (if not last)
                    if i < len(steps) - 1:
                        next_y = y_start - (i + 1)
                        lbl = "PASS" if passed else "FAIL"
                        lbl_color = "#4CAF50" if passed else "#F44336"
                        tree_fig.add_annotation(
                            x=node_x, y=next_y + node_h + 0.02, ax=node_x, ay=y - node_h - 0.02,
                            xref="x", yref="y", axref="x", ayref="y",
                            showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2,
                            arrowcolor=lbl_color)
                        tree_fig.add_annotation(x=node_x + 0.25, y=(y - node_h + next_y + node_h) / 2,
                            text=f"<b>{lbl}</b>", showarrow=False,
                            font=dict(color=lbl_color, size=9))

                    # Fail branch to the right
                    if passed is False:
                        # Horizontal arrow to fail node
                        tree_fig.add_annotation(
                            x=fail_x - 0.9, y=y, ax=node_x + node_w + 0.02, ay=y,
                            xref="x", yref="y", axref="x", ayref="y",
                            showarrow=True, arrowhead=2, arrowsize=1.2, arrowwidth=2,
                            arrowcolor="#F44336")
                        # Fail node
                        tree_fig.add_shape(type="rect",
                            x0=fail_x - 0.9, y0=y - 0.25, x1=fail_x + 0.9, y1=y + 0.25,
                            fillcolor="#F44336", line=dict(color="#B71C1C", width=2),
                            layer="below")
                        tree_fig.add_annotation(x=fail_x, y=y,
                            text=f"<b>{step['fail_label']}</b>",
                            showarrow=False, font=dict(color="white", size=10))

                # Verdict node at bottom
                vy = y_start - len(steps)
                tree_fig.add_shape(type="rect",
                    x0=node_x - node_w - 0.2, y0=vy - 0.45, x1=node_x + node_w + 0.2, y1=vy + 0.45,
                    fillcolor=v_color, line=dict(color="white", width=3),
                    layer="below")
                tree_fig.add_annotation(x=node_x, y=vy + 0.1,
                    text=f"<b>{tree_ticker}: {verdict}</b>",
                    showarrow=False, font=dict(color="white", size=16))
                tree_fig.add_annotation(x=node_x, y=vy - 0.2,
                    text=f"Score: {score}/6",
                    showarrow=False, font=dict(color="white", size=12))

                # Arrow from last step to verdict
                tree_fig.add_annotation(
                    x=node_x, y=vy + 0.45 + 0.02, ax=node_x, ay=y_start - (len(steps) - 1) - node_h - 0.02,
                    xref="x", yref="y", axref="x", ayref="y",
                    showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=2,
                    arrowcolor="white")

                tree_fig.update_layout(
                    height=700, plot_bgcolor="#1a1a2e", paper_bgcolor="#1a1a2e",
                    xaxis=dict(range=[-3, 5], showgrid=False, zeroline=False, visible=False),
                    yaxis=dict(range=[vy - 0.8, y_start + 0.8], showgrid=False, zeroline=False, visible=False),
                    margin=dict(l=20, r=20, t=20, b=20),
                    showlegend=False)

                st.plotly_chart(tree_fig, use_container_width=True)
            else:
                st.warning(f"Not enough data for {tree_ticker} to run decision tree (need at least 5 quarters).")'''



# For line 178
    '''full_acc_data = full_acc_data.groupby('ticker', group_keys=False).apply(lambda g: g.ffill())
    full_acc_data['Working_Capital'] = full_acc_data['bs_cur_asset_report'] - full_acc_data['bs_cur_liab']
    full_acc_data['NCWC'] = (full_acc_data['bs_acct_note_rcv']
                             + full_acc_data['bs_inventories']
                             + full_acc_data['bs_other_current_assets_detailed']
                             - full_acc_data['bs_acct_payable']
                             - full_acc_data['bs_accrued_liabilities']
                             - full_acc_data['bs_st_deferred_revenue'])
    eff_tax_rate = (full_acc_data['is_inc_tax_exp'] / full_acc_data['is_pretax_income']).clip(0, 1)
    nopat = full_acc_data['is_oper_income'] * (1 - eff_tax_rate)
    invested_capital = (full_acc_data['NCWC']
                        + full_acc_data['bs_net_fix_asset']
                        + full_acc_data['bs_disclosed_intangibles']
                        + full_acc_data['bs_goodwill'])
    full_acc_data['ROIC'] = nopat / invested_capital'''
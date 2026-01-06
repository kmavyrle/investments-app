import streamlit as st

import pandas as pd
import numpy as np
import datetime
import yfinance as yf

import plotly.express as px
import plotly.graph_objects as go

from saber import PerformanceAnalytics as pa
from saber import riskEngine as re
from saber import DataMgmt as dm

from PIL import Image
import pyOptions as Op


image = Image.open('Purple Eye with Glowing Star Symbol.png')
risk = re.riskMgr()
# Page config
st.set_page_config(
    page_title="4Sight",
    page_icon = image,
    layout="wide"
)

### Create Key Classes
dl = dm.DataLake()

### Load Datasets
us_full_acc_data = dl.read_data("raw",'fundamental','equities','us_full_acc_data.csv',index_col = 'date')



# Sidebar
with st.sidebar:
    image = Image.open('4Sightlogo2.jpg')
    st.image(image)
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
st.markdown("## 4Sight Analytics")

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
    eq_tabs = ["Equity"]
    eq_tickers = sorted(us_full_acc_data["ticker"].unique())
    acc_labels = us_full_acc_data.columns[5:]

    with st.container():
        col1, col2 = st.columns(2)

        with col1:
            selected_ticker = st.selectbox(
                "Select stock ticker",
                eq_tickers
            )

        with col2:
            selected_metric = st.selectbox(
                "Select accounting metric",
                acc_labels
            )

    df_plot = (
        us_full_acc_data
        .reset_index()
        .pivot_table(
            index="date",
            columns="ticker",
            values=selected_metric
        )[[selected_ticker]]
        .dropna()
        .reset_index()
    )

    fig = px.bar(
        df_plot,
        x="date",
        y=selected_ticker,
        title=f"{selected_ticker} – {selected_metric}",
        labels={
            "date": "Date",
            selected_ticker: selected_metric
        }
    )

    st.plotly_chart(fig, use_container_width=True)



elif page == "Portfolio Analytics":
    port_tabs = st.tabs(['Equities Exposure','4Sight Agentic Trader'])
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




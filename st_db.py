import streamlit as st

import pandas as pd
import numpy as np
import datetime
import yfinance as yf

import plotly.express as px
import plotly.graph_objects as go



# Page config
st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide"
)

# Sidebar
with st.sidebar:
    st.title("Settings")
    
    #st.title("Settings")
    
    # Navigation
    st.subheader("Navigation")
    
    if st.button("Price Monitor", use_container_width=True):
        st.session_state.page = "Price Monitor"
    
    if st.button("Macro", use_container_width=True):
        st.session_state.page = "Macro"
    
    if st.button("Portfolio Analytics", use_container_width=True):
        st.session_state.page = "Portfolio Analytics"
    
    # Initialize page if not set
    if 'page' not in st.session_state:
        st.session_state.page = "Price Monitor"
    
    page = st.session_state.page


# Main content
st.title("Dashboard")

if page == "Price Monitor":
    st.header("Price Monitor")
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


elif page == "Portfolio Analytics":
    
    st.header("Portfolio Analytics")
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
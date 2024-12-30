import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Page Configurations
st.set_page_config(page_title="Daily SPY Dashboard", page_icon="📈", layout="wide")

# Fetch Historical SPY Data
def fetch_historical_data(symbol, period="1mo", interval="1d"):
    data = yf.download(symbol, period=period, interval=interval)
    data.reset_index(inplace=True)
    return data

# Calculate Levels
def calculate_levels(data):
    high = data['High'].max()
    low = data['Low'].min()
    close = data['Close'].iloc[-1]

    resistance_levels = [
        high,
        high - (high - low) * 0.236,
        high - (high - low) * 0.382,
        high - (high - low) * 0.618
    ]
    support_levels = [
        low,
        low + (high - low) * 0.236,
        low + (high - low) * 0.382,
        low + (high - low) * 0.618
    ]
    magnet_price = (high + low + close) / 3

    return resistance_levels, support_levels, magnet_price

# Generate Trading Plan
def generate_trading_plan(resistance, support, magnet):
    plan = f"""
    ### Bull Case
    - If price breaks above **{resistance[0]:.2f}**, look for longs targeting **{resistance[1]:.2f}** and **{resistance[2]:.2f}**.
    - Monitor **{magnet:.2f}** as a pivot point for continuation.

    ### Bear Case
    - If price falls below **{support[0]:.2f}**, look for shorts targeting **{support[1]:.2f}** and **{support[2]:.2f}**.
    - Watch for failed breakdowns near **{support[1]:.2f}** to confirm continuation.
    
    ### Key Notes
    - Volatility is elevated. Trade level to level.
    - Avoid chasing moves; wait for reclaim setups.
    - Size down in risky zones.
    """
    return plan

# Generate Recap
def generate_recap(data):
    today_high = data['High'].iloc[-1]
    today_low = data['Low'].iloc[-1]
    today_close = data['Close'].iloc[-1]

    recap = f"""
    ### Daily Recap
    - **High:** {today_high:.2f}
    - **Low:** {today_low:.2f}
    - **Close:** {today_close:.2f}

    Today's session saw a range between {today_low:.2f} and {today_high:.2f}, closing at {today_close:.2f}. Key movements included resistance tests and support reactions.
    """
    return recap

# Load Historical Data
symbol = "SPY"
data = fetch_historical_data(symbol)

# Calculate Levels
resistance_levels, support_levels, magnet_price = calculate_levels(data)

# Sidebar: User Input for Adjustments
st.sidebar.header("Level Adjustments")
dynamic_top = st.sidebar.number_input("Dynamic Zone Top", value=round(resistance_levels[1], 2))
dynamic_bottom = st.sidebar.number_input("Dynamic Zone Bottom", value=round(support_levels[1], 2))
magnet_price = st.sidebar.number_input("Magnet Price", value=round(magnet_price, 2))

st.sidebar.subheader("Support Levels")
support_levels = [
    st.sidebar.number_input(f"Support {i+1}", value=round(level, 2)) for i, level in enumerate(support_levels)
]
st.sidebar.subheader("Resistance Levels")
resistance_levels = [
    st.sidebar.number_input(f"Resistance {i+1}", value=round(level, 2)) for i, level in enumerate(resistance_levels)
]

# Main Content with Tabs
st.title("Daily SPY Dashboard")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Market Overview", "Key Levels", "Trading Plan", "Recap", "Chart"])

# Tab: Market Overview
with tab1:
    st.header("📊 Market Overview")
    status = "**Bullish**" if data['Close'].iloc[-1] > resistance_levels[1] else "**Bearish**" if data['Close'].iloc[-1] < support_levels[1] else "**Neutral**"
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="Market Status", value=status)
        st.metric(label="Last Close", value=f"{data['Close'].iloc[-1]:.2f}")
    with col2:
        st.metric(label="Dynamic Zone Top", value=f"{dynamic_top}")
        st.metric(label="Dynamic Zone Bottom", value=f"{dynamic_bottom}")

# Tab: Key Levels
with tab2:
    st.header("📈 Key Levels")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Resistance Levels")
        for i, level in enumerate(resistance_levels):
            st.write(f"Resistance {i+1}: **{level:.2f}**")

    with col2:
        st.subheader("Support Levels")
        for i, level in enumerate(support_levels):
            st.write(f"Support {i+1}: **{level:.2f}**")

    st.subheader("Dynamic Zones")
    st.write(f"Dynamic Top: **{dynamic_top:.2f}**")
    st.write(f"Dynamic Bottom: **{dynamic_bottom:.2f}**")

    st.subheader("Magnet Price")
    st.write(f"Magnet Price: **{magnet_price:.2f}**")

# Tab: Trading Plan
with tab3:
    st.header("📝 Trading Plan")
    trading_plan = generate_trading_plan(resistance_levels, support_levels, magnet_price)
    st.markdown(trading_plan)

# Tab: Recap
with tab4:
    st.header("🔍 Daily Recap")
    recap = generate_recap(data)
    st.markdown(recap)

# Tab: Interactive Chart
with tab5:
    st.header("📉 SPY Historical Chart")
    def plot_candlestick(data):
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=data['Date'],
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='SPY'
        ))

        # Add Dynamic Zone
        fig.add_hline(y=dynamic_top, line_dash="dash", line_color="red", annotation_text="Dynamic Top")
        fig.add_hline(y=dynamic_bottom, line_dash="dash", line_color="blue", annotation_text="Dynamic Bottom")

        # Add Magnet Price
        fig.add_hline(y=magnet_price, line_dash="dot", line_color="green", annotation_text="Magnet Price")

        fig.update_layout(
            title="SPY Candlestick Chart",
            xaxis_title="Date",
            yaxis_title="Price",
            template="plotly_dark",
            height=700
        )
        return fig

    st.plotly_chart(plot_candlestick(data), use_container_width=True)

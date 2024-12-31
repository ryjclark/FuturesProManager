import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
import joblib
import requests
import openai
from config import OPENAI_API_KEY
import ta

# Set OpenAI API Key
openai.api_key = OPENAI_API_KEY

# Page Configurations
st.set_page_config(page_title="Daily SPY Dashboard", page_icon="📈", layout="wide")

# Fetch Historical SPY Data with Enhanced Technical Analysis
def fetch_historical_data(symbol, period="1mo", interval="1d"):
    """
    Fetch more recent data with enhanced technical indicators
    """
    try:
        # Fetch data with longer period to ensure enough data for indicators
        data = yf.download(symbol, period="6mo", interval="1d")
        
        if data.empty:
            st.error(f"No data received for {symbol}")
            return None

        data.reset_index(inplace=True)
        
        # Add technical indicators
        data['SMA_20'] = ta.trend.sma_indicator(data['Close'], window=20)
        data['SMA_50'] = ta.trend.sma_indicator(data['Close'], window=50)
        data['RSI'] = ta.momentum.rsi(data['Close'], window=14)
        data['MACD'] = ta.trend.macd_diff(data['Close'])
        data['BB_upper'] = ta.volatility.bollinger_hband(data['Close'])
        data['BB_lower'] = ta.volatility.bollinger_lband(data['Close'])
        data['Volume_SMA'] = ta.trend.sma_indicator(data['Volume'], window=20)
        data['Daily_Change'] = data['Close'].pct_change() * 100
        
        # Calculate VWAP
        data['VWAP'] = (data['Close'] * data['Volume']).cumsum() / data['Volume'].cumsum()
        
        # Get only the most recent month of data for display
        data = data.tail(30).reset_index(drop=True)
        
        # Debug information
        st.sidebar.write(f"Data points: {len(data)}")
        st.sidebar.write(f"Latest date: {data['Date'].max()}")
        
        return data
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None

# Fetch Market News using Finnhub API
def fetch_market_news():
    url = "https://finnhub.io/api/v1/news?category=general"
    params = {"token": "ctpl0q9r01qqsrsb2aogctpl0q9r01qqsrsb2ap0"}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            articles = response.json()
            return articles[:5]
    except Exception as e:
        st.error(f"Error fetching news: {str(e)}")
    return []

# Fetch Economic Calendar using Finnhub API
def fetch_economic_calendar():
    url = "https://finnhub.io/api/v1/calendar/economic"
    params = {"token": "ctpl0q9r01qqsrsb2aogctpl0q9r01qqsrsb2ap0"}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get("economicCalendar", [])
    except Exception as e:
        st.error(f"Error fetching calendar: {str(e)}")
    return []

# Calculate Enhanced Levels
def calculate_levels(data):
    if data is None or len(data) == 0:
        return [], [], 0
        
    try:
        latest_data = data.iloc[-1]
        
        # Traditional high-low based levels
        high = data['High'].max()
        low = data['Low'].min()
        close = latest_data['Close']
        
        # Calculate using price action and technical indicators
        resistance_levels = [
            high,
            latest_data['BB_upper'],
            latest_data['VWAP'],
            latest_data['SMA_20'],
            high - (high - low) * 0.236,
            high - (high - low) * 0.382,
            high - (high - low) * 0.618
        ]
        
        support_levels = [
            low,
            latest_data['BB_lower'],
            latest_data['SMA_50'],
            latest_data['VWAP'],
            low + (high - low) * 0.236,
            low + (high - low) * 0.382,
            low + (high - low) * 0.618
        ]
        
        # Remove duplicates and sort
        resistance_levels = sorted(list(set([round(x, 2) for x in resistance_levels if pd.notna(x)])), reverse=True)
        support_levels = sorted(list(set([round(x, 2) for x in support_levels if pd.notna(x)])))
        
        # Calculate magnet price using VWAP and current price
        magnet_price = round((latest_data['VWAP'] + close) / 2, 2)

        return resistance_levels, support_levels, magnet_price
    except Exception as e:
        st.error(f"Error calculating levels: {str(e)}")
        return [], [], 0

# Generate Enhanced Trading Plan using OpenAI
def generate_trading_plan(data, resistance_levels, support_levels, magnet_price):
    if data is None or len(data) == 0:
        return "Unable to generate trading plan due to insufficient data."
        
    try:
        latest_data = data.iloc[-1]
        
        prompt = f"""
        Create a detailed trading plan for SPY based on the following technical analysis:
        
        Current Market Data ({latest_data['Date'].strftime('%Y-%m-%d')}):
        - Price: ${latest_data['Close']:.2f}
        - Daily Change: {latest_data['Daily_Change']:.2f}%
        - RSI: {latest_data['RSI']:.2f}
        - MACD: {latest_data['MACD']:.2f}
        
        Technical Levels:
        - VWAP: ${latest_data['VWAP']:.2f}
        - 20 SMA: ${latest_data['SMA_20']:.2f}
        - 50 SMA: ${latest_data['SMA_50']:.2f}
        - Upper BB: ${latest_data['BB_upper']:.2f}
        - Lower BB: ${latest_data['BB_lower']:.2f}
        
        Key Price Levels:
        - Resistance Levels: {', '.join(f'${lvl:.2f}' for lvl in resistance_levels[:3])}
        - Support Levels: {', '.join(f'${lvl:.2f}' for lvl in support_levels[:3])}
        - Magnet Price: ${magnet_price:.2f}
        
        Volume Analysis:
        - Current Volume: {latest_data['Volume']:,.0f}
        - Volume SMA: {latest_data['Volume_SMA']:,.0f}
        
        Please provide:
        1. Market Context and Bias
        2. Key Trading Levels for Tomorrow
        3. Specific Trade Setups (Long and Short)
        4. Risk Management Rules
        5. Important Price Alerts
        """

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are an experienced trading strategist providing actionable trading plans."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating trading plan: {str(e)}"

# Generate Enhanced Market Recap
def generate_recap(data):
    if data is None or len(data) == 0:
        return "Unable to generate recap due to insufficient data."
        
    try:
        latest_data = data.iloc[-1]
        prev_data = data.iloc[-2]
        
        # Calculate additional metrics
        daily_change = ((latest_data['Close'] - prev_data['Close']) / prev_data['Close']) * 100
        daily_range = latest_data['High'] - latest_data['Low']
        volume_change = ((latest_data['Volume'] - prev_data['Volume']) / prev_data['Volume']) * 100
        
        prompt = f"""
        Provide a comprehensive market recap for SPY on {latest_data['Date'].strftime('%Y-%m-%d')}:
        
        Price Action:
        - Open: ${latest_data['Open']:.2f}
        - High: ${latest_data['High']:.2f}
        - Low: ${latest_data['Low']:.2f}
        - Close: ${latest_data['Close']:.2f}
        - Daily Change: {daily_change:.2f}%
        - Daily Range: ${daily_range:.2f}
        
        Technical Indicators:
        - RSI: {latest_data['RSI']:.2f}
        - MACD: {latest_data['MACD']:.2f}
        - VWAP: ${latest_data['VWAP']:.2f}
        - 20 SMA: ${latest_data['SMA_20']:.2f}
        - 50 SMA: ${latest_data['SMA_50']:.2f}
        
        Volume Analysis:
        - Volume: {latest_data['Volume']:,.0f}
        - Volume Change: {volume_change:.2f}%
        - Vs. 20-day Avg: {((latest_data['Volume'] / latest_data['Volume_SMA']) - 1) * 100:.2f}%
        
        Please provide:
        1. Summary of today's price action and key moves
        2. Technical analysis of the day's trading
        3. Volume analysis and significance
        4. Key levels that were tested
        5. Overall market sentiment
        """

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional market analyst providing detailed daily market recaps."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating recap: {str(e)}"

# Display TradingView Chart
def display_tradingview_chart():
    chart_html = """
        <!-- TradingView Widget BEGIN -->
        <div class="tradingview-widget-container">
            <div class="tradingview-widget-container__widget"></div>
            <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js" async>
            {
              "width": "100%",
              "height": "800",
              "symbol": "SPY",
              "interval": "D",
              "timezone": "America/New_York",
              "theme": "dark",
              "style": "1",
              "locale": "en",
              "enable_publishing": false,
              "backgroundColor": "rgba(19, 23, 34, 1)",
              "gridColor": "rgba(42, 46, 57, 0.06274509803921569)",
              "allow_symbol_change": true,
              "calendar": true,
              "hide_side_toolbar": false,
              "studies": [
                "MAExp@tv-basicstudies",
                "VWAP@tv-basicstudies",
                "Volume@tv-basicstudies",
                "RSI@tv-basicstudies",
                "BB@tv-basicstudies"
              ]
            }
            </script>
        </div>
        <!-- TradingView Widget END -->
    """
    return chart_html

# Load Historical Data
symbol = "SPY"
data = fetch_historical_data(symbol)

if data is None or data.empty:
    st.error("Unable to load market data. Please try again later.")
    st.stop()

# Calculate Levels
resistance_levels, support_levels, magnet_price = calculate_levels(data)

# Fetch News and Calendar
news_articles = fetch_market_news()
economic_events = fetch_economic_calendar()

# Sidebar: User Input for Adjustments
st.sidebar.header("Level Adjustments")
dynamic_top = st.sidebar.number_input("Dynamic Zone Top", value=round(resistance_levels[1] if len(resistance_levels) > 1 else 0, 2))
dynamic_bottom = st.sidebar.number_input("Dynamic Zone Bottom", value=round(support_levels[1] if len(support_levels) > 1 else 0, 2))
magnet_price = st.sidebar.number_input("Magnet Price", value=round(magnet_price, 2))

st.sidebar.subheader("Support Levels")
support_levels = [
    st.sidebar.number_input(f"Support {i+1}", value=round(level, 2)) 
    for i, level in enumerate(support_levels[:4])
]
st.sidebar.subheader("Resistance Levels")
resistance_levels = [
    st.sidebar.number_input(f"Resistance {i+1}", value=round(level, 2)) 
    for i, level in enumerate(resistance_levels[:4])
]

# Main Content with Tabs
st.title("Daily SPY Dashboard")
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Market Overview", "Key Levels", "Trading Plan", "Recap", "Chart", "News", "Fed Calendar"])

# Tab: Market Overview
with tab1:
    st.header("📊 Market Overview")
    latest_data = data.iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    with col1:
        daily_change = latest_data['Daily_Change']
        color = "green" if daily_change > 0 else "red"
        st.metric(
            label="SPY",
            value=f"${latest_data['Close']:.2f}",
            delta=f"{daily_change:.2f}%"
        )
        
    with col2:
        st.metric(label="RSI", value=f"{latest_data['RSI']:.2f}")
        st.metric(label="VWAP", value=f"${latest_data['VWAP']:.2f}")
        
    with col3:
        volume_change = ((latest_data['Volume'] / latest_data['Volume_SMA']) - 1) * 100
        st.metric(
            label="Volume vs Avg",
            value=f"{latest_data['Volume']:,.0f}",
            delta=f"{volume_change:.2f}%"
        )

# Tab: Key Levels
with tab2:
    st.header("📈 Key Levels")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Resistance Levels")
        for i, level in enumerate(resistance_levels):
            st.write(f"R{i+1}: **${level:.2f}**")

    with col2:
        st.subheader("Support Levels")
        for i, level in enumerate(support_levels):
            st.write(f"S{i+1}: **${level:.2f}**")

    st.subheader("Technical Levels")
    col3, col4 = st.columns(2)
    with col3:
        st.write(f"VWAP: **${latest_data['VWAP']:.2f}**")
        st.write(f"20 SMA: **${latest_data['SMA_20']:.2f}**")
    with col4:
        st.write(f"Upper BB: **${latest_data['BB_upper']:.2f}**")
        st.write(f"Lower BB: **${latest_data['BB_lower']:.2f}**")

# Tab: Trading Plan
with tab3:
    st.header("📝 Trading Plan")
    trading_plan = generate_trading_plan(data, resistance_levels, support_levels, magnet_price)
    st.markdown(trading_plan)

# Tab: Recap
with tab4:
    st.header("🔍 Daily Recap")
    recap = generate_recap(data)
    st.markdown(recap)

# Tab: Interactive Chart
with tab5:
    st.header("📉 SPY Chart")
    st.components.v1.html(display_tradingview_chart(), height=800)

# Tab: News
with tab6:
    st.header("🗞️ Market News")
    for article in news_articles:
        st.subheader(article['headline'])
        st.write(article['summary'])
        st.markdown(f"[Read more]({article['url']})")

# Tab: Fed Calendar
with tab7:
    st.header("📅 Fed Calendar")
    if economic_events:
        for event in economic_events[:5]:
            st.subheader(event.get("event", ""))
            st.write(f"Date: {event.get('date', 'N/A')}")
            st.write(f"Country: {event.get('country', 'N/A')}")
            st.write(f"Impact: {event.get('impact', 'N/A')}")
            st.write(f"Actual: {event.get('actual', 'N/A')} | Forecast: {event.get('forecast', 'N/A')} | Previous: {event.get('previous', 'N/A')}")
    else:
        st.write("No upcoming events found.")
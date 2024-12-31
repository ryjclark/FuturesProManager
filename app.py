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

# Set OpenAI API Key
openai.api_key = OPENAI_API_KEY

# Page Configurations
st.set_page_config(page_title="Daily SPY Dashboard", page_icon="📈", layout="wide")

# Fetch Historical SPY Data
def fetch_historical_data(symbol, period="1mo", interval="1d"):
    data = yf.download(symbol, period=period, interval=interval)
    data.reset_index(inplace=True)
    return data

# Fetch Market News using Finnhub API
def fetch_market_news():
    url = "https://finnhub.io/api/v1/news?category=general"
    params = {"token": "ctpl0q9r01qqsrsb2aogctpl0q9r01qqsrsb2ap0"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        articles = response.json()
        return articles[:5]  # Limit to 5 articles
    return []

# Fetch Economic Calendar using Finnhub API
def fetch_economic_calendar():
    url = "https://finnhub.io/api/v1/calendar/economic"
    params = {"token": "ctpl0q9r01qqsrsb2aogctpl0q9r01qqsrsb2ap0"}
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json().get("economicCalendar", [])
    return []

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

# Generate Trading Plan using OpenAI
def generate_trading_plan(resistance, support, magnet):
    try:
        prompt = f"""
        Create a detailed trading plan for SPY based on the following levels:
        Resistance Levels: {', '.join(f'{lvl:.2f}' for lvl in resistance)}
        Support Levels: {', '.join(f'{lvl:.2f}' for lvl in support)}
        Magnet Price: {magnet:.2f}
        Include a bull case and bear case with actionable steps.
        """

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial trading assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error generating trading plan: {str(e)}"

# Generate Recap using OpenAI
def generate_recap(data):
    try:
        today_high = data['High'].iloc[-1]
        today_low = data['Low'].iloc[-1]
        today_close = data['Close'].iloc[-1]

        prompt = f"""
        Provide a concise daily market recap for SPY. Include the following details:
        - Today's High: {today_high:.2f}
        - Today's Low: {today_low:.2f}
        - Today's Close: {today_close:.2f}
        Summarize key market movements and significant levels.
        """

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a financial analyst providing daily market summaries."},
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
                "Volume@tv-basicstudies"
              ]
            }
            </script>
        </div>
        <!-- TradingView Widget END -->
    """
    return chart_html

# Train Predictive Model
def train_model(data):
    try:
        data['Target'] = data['Close'].shift(-1)
        data.dropna(inplace=True)
        X = data[['Open', 'High', 'Low', 'Close']]
        y = data['Target']
        model = LinearRegression()
        model.fit(X, y)
        joblib.dump(model, 'spy_predictive_model.pkl')
    except Exception as e:
        st.error(f"Error training model: {str(e)}")

# Predict Next Day Levels
def predict_levels(data):
    try:
        model = joblib.load('spy_predictive_model.pkl')
        last_row = data.iloc[-1][['Open', 'High', 'Low', 'Close']].values.reshape(1, -1)
        predicted_close = model.predict(last_row)[0]
        return predicted_close
    except Exception as e:
        st.error(f"Error predicting levels: {str(e)}")
        return None

# Load Historical Data
symbol = "SPY"
data = fetch_historical_data(symbol)

# Train Model (Run once and comment out in production)
try:
    train_model(data)
except Exception as e:
    st.error(f"Error in model training: {str(e)}")

# Calculate Levels
resistance_levels, support_levels, magnet_price = calculate_levels(data)
predicted_close = predict_levels(data)

# Fetch News
news_articles = fetch_market_news()

# Fetch Economic Calendar
economic_events = fetch_economic_calendar()

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
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["Market Overview", "Key Levels", "Trading Plan", "Recap", "Chart", "News", "Fed Calendar"])

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
        for event in economic_events[:5]:  # Display the next 5 events
            st.subheader(event.get("event", ""))
            st.write(f"Date: {event.get('date', 'N/A')}")
            st.write(f"Country: {event.get('country', 'N/A')}")
            st.write(f"Impact: {event.get('impact', 'N/A')}")
            st.write(f"Actual: {event.get('actual', 'N/A')} | Forecast: {event.get('forecast', 'N/A')} | Previous: {event.get('previous', 'N/A')}")
    else:
        st.write("No upcoming events found.")
import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime, timedelta
import json
import os

# Page config
st.set_page_config(page_title="Futures Pro Manager", page_icon="📊", layout="wide")

# Ensure data directory exists
data_dir = "futures_data"
os.makedirs(data_dir, exist_ok=True)

# Initialize session state
if 'support_levels' not in st.session_state:
    st.session_state.support_levels = [
        {"price": 6022, "major": True},
        {"price": 6016, "major": False},
        {"price": 6006, "major": False},
        {"price": 6002, "major": False},
        {"price": 5996, "major": True}
    ]

if 'resistance_levels' not in st.session_state:
    st.session_state.resistance_levels = [
        {"price": 6027, "major": False},
        {"price": 6033, "major": True},
        {"price": 6043, "major": False},
        {"price": 6054, "major": False}
    ]

if 'dynamic_zone' not in st.session_state:
    st.session_state.dynamic_zone = {'top': 6143.0, 'bottom': 6105.0}
if 'magnet_price' not in st.session_state:
    st.session_state.magnet_price = 6130.0

# Sidebar
with st.sidebar:
    st.header("Futures Pro Settings")

    # Quick Level Add
    st.subheader("Quick Add Level")
    quick_price = st.number_input("Price", step=0.25)
    col1, col2 = st.columns(2)
    with col1:
        level_type = st.radio("Type", ["Support", "Resistance"])
    with col2:
        is_major = st.checkbox("Major")

    if st.button("Add Level"):
        if quick_price <= 0:
            st.error("Price must be greater than zero.")
        else:
            new_level = {"price": quick_price, "major": is_major}
            if level_type == "Support":
                if new_level not in st.session_state.support_levels:
                    st.session_state.support_levels.append(new_level)
                    st.session_state.support_levels.sort(key=lambda x: x['price'])
                else:
                    st.warning("This support level already exists.")
            else:
                if new_level not in st.session_state.resistance_levels:
                    st.session_state.resistance_levels.append(new_level)
                    st.session_state.resistance_levels.sort(key=lambda x: x['price'])
                else:
                    st.warning("This resistance level already exists.")

    # Dynamic Zone Settings
    st.subheader("Dynamic Zone")
    dynamic_top = st.number_input("Zone Top", value=st.session_state.dynamic_zone['top'], step=0.25)
    dynamic_bottom = st.number_input("Zone Bottom", value=st.session_state.dynamic_zone['bottom'], step=0.25)
    magnet_price = st.number_input("Magnet Price", value=st.session_state.magnet_price, step=0.25)

    if st.button("Update Zones"):
        if dynamic_top <= dynamic_bottom:
            st.error("Zone top must be greater than zone bottom.")
        else:
            st.session_state.dynamic_zone['top'] = dynamic_top
            st.session_state.dynamic_zone['bottom'] = dynamic_bottom
            st.session_state.magnet_price = magnet_price

# Main content
tab1, tab2, tab3 = st.tabs(["Chart", "Level Management", "Trading Plan"])

with tab1:
    # TradingView Widget
    tradingview_widget = """
    <div class="tradingview-widget-container">
        <div id="tradingview_chart"></div>
        <div class="tradingview-widget-copyright">
            <a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank">
            <span class="blue-text">Track all markets on TradingView</span>
            </a>
        </div>
        <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
        <script type="text/javascript">
        new TradingView.widget({
            "autosize": true,
            "symbol": "CME:ES1!",
            "interval": "5",
            "timezone": "America/New_York",
            "theme": "dark",
            "style": "1",
            "locale": "en",
            "toolbar_bg": "#f1f3f6",
            "enable_publishing": false,
            "allow_symbol_change": true,
            "container_id": "tradingview_chart",
            "hide_side_toolbar": false,
            "studies": [
                "MAExp@tv-basicstudies",
                "Volume@tv-basicstudies"
            ],
            "width": "100%",
            "height": "800"
        });
        </script>
    </div>
    """

    components.html(tradingview_widget, height=800)

with tab2:
    st.header("Level Management")

    # Save/Load Levels
    col1, col2 = st.columns(2)
    with col1:
        save_name = st.text_input("Save Name", "default")
        if st.button("Save Levels"):
            levels = {
                "support": st.session_state.support_levels,
                "resistance": st.session_state.resistance_levels,
                "dynamic_zone": st.session_state.dynamic_zone,
                "magnet_price": st.session_state.magnet_price
            }
            try:
                with open(f"{data_dir}/{save_name}.json", "w") as f:
                    json.dump(levels, f)
                st.success(f"Saved levels as {save_name}")
            except Exception as e:
                st.error(f"Error saving levels: {e}")

    with col2:
        saved_files = [f.replace(".json", "") for f in os.listdir(data_dir) if f.endswith(".json")]
        if saved_files:
            load_name = st.selectbox("Load Saved Levels", saved_files)
            if st.button("Load Levels"):
                try:
                    with open(f"{data_dir}/{load_name}.json", "r") as f:
                        levels = json.load(f)
                        st.session_state.support_levels = levels["support"]
                        st.session_state.resistance_levels = levels["resistance"]
                        st.session_state.dynamic_zone = levels["dynamic_zone"]
                        st.session_state.magnet_price = levels["magnet_price"]
                    st.success(f"Loaded levels from {load_name}")
                except Exception as e:
                    st.error(f"Error loading levels: {e}")

    # Level Display and Edit
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Support Levels")
        for i, level in enumerate(st.session_state.support_levels):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.write(f"{'🟢 Major' if level['major'] else '⚪ Minor'} - {level['price']}")
            with cols[1]:
                if st.button("Delete", key=f"del_s_{i}"):
                    st.session_state.support_levels.pop(i)
                    st.experimental_rerun()

    with col2:
        st.subheader("Resistance Levels")
        for i, level in enumerate(st.session_state.resistance_levels):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.write(f"{'🔴 Major' if level['major'] else '⚪ Minor'} - {level['price']}")
            with cols[1]:
                if st.button("Delete", key=f"del_r_{i}"):
                    st.session_state.resistance_levels.pop(i)
                    st.experimental_rerun()

with tab3:
    st.header("Trading Plan")
    st.info("Trading Plan integration coming soon!")


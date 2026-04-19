import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import os
import requests
import plotly.graph_objects as go
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
from huggingface_hub import hf_hub_download

st.set_page_config(page_title="NEPSE Intelligence PRO", layout="wide")

DB_PATH = "nepse_data.db"
GITHUB_URL = "https://raw.githubusercontent.com/XJabin/Nepse/main/nepse_data.db"

def sync_db():
    try:
        r = requests.get(GITHUB_URL, timeout=15)
        if r.status_code == 200:
            with open(DB_PATH, "wb") as f: f.write(r.content)
            return True
    except: return False
    return False

if not os.path.exists(DB_PATH): sync_db()

@st.cache_resource
def load_ai_model():
    try:
        path = hf_hub_download(repo_id="XJabin/nepse-lstm-model", filename="nepse_lstm_model.h5")
        return load_model(path, compile=False)
    except: return None

def get_clean_data(symbol_name):
    if not os.path.exists(DB_PATH): return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        query = f"SELECT * FROM daily_stock WHERE symbol = '{symbol_name}' ORDER BY id ASC"
        df = pd.read_sql(query, conn)
        conn.close()
        if not df.empty:
            df.columns = [c.lower() for c in df.columns]
            for col in ['open', 'high', 'low', 'close', 'vol']:
                if col not in df.columns: df[col] = 0.0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
            if 'date' in df.columns:
                df['date_display'] = pd.to_datetime(df['date'], errors='coerce')
            return df
    except:
        if 'conn' in locals(): conn.close()
    return pd.DataFrame()

st.sidebar.title("NEPSE Control")
if st.sidebar.button("🔄 Sync Database"):
    if sync_db(): st.rerun()

# ग्राफ छान्ने अप्सन
chart_mode = st.sidebar.radio("View Mode:", ["Line Chart", "Candlestick"])

if os.path.exists(DB_PATH):
    conn = sqlite3.connect(DB_PATH)
    all_syms = pd.read_sql("SELECT DISTINCT symbol FROM daily_stock WHERE symbol != ''", conn)['symbol'].tolist()
    conn.close()
    
    if "SCRAPED_DATA" in all_syms:
        all_syms.remove("SCRAPED_DATA")
        all_syms = ["SCRAPED_DATA"] + all_syms
    
    selected = st.sidebar.selectbox("Select Asset", all_syms, index=0)
else:
    st.stop()

st.title(f"📈 {selected} Intelligence Platform")
df = get_clean_data(selected)

if not df.empty:
    last = df.iloc[-1]
    prev = df['close'].iloc[-2] if len(df) > 1 else last['close']
    diff = last['close'] - prev
    
    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Current Value", f"{last['close']:.2f}", f"{diff:.2f}")
    m2.metric("Open", f"{last['open']:.2f}")
    m3.metric("High", f"{last['high']:.2f}")
    m4.metric("Low", f"{last['low']:.2f}")
    
    # मिति देखाउने लजिक
    last_date = last['date_display'].strftime('%Y-%m-%d') if 'date_display' in df.columns and not pd.isnull(last['date_display']) else "N/A"
    m5.metric("Last Updated", last_date)

    st.divider()

    c_left, c_right = st.columns([2, 1])
    
    with c_left:
        fig = go.Figure()
        # Candlestick र Line Chart दुवैमा 'Index' प्रयोग गरिएको छ ताकि ग्राफ नबिग्रियोस्
        if chart_mode == "Candlestick" and last['open'] > 0:
            fig.add_trace(go.Candlestick(x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="OHLC"))
        else:
            fig.add_trace(go.Scatter(y=df['close'], mode='lines', line=dict(color='#00ffcc', width=2), name="Price"))
        
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500, margin=dict(l=0,r=0,t=0,b=0))
        st.plotly_chart(fig, use_container_width=True)

    with c_right:
        st.subheader("🤖 AI Forecast")
        if st.button("Predict Tomorrow"):
            model = load_ai_model()
            if model and len(df) >= 5:
                scaler = MinMaxScaler()
                scaled = scaler.fit_transform(df['close'].values.reshape(-1, 1))
                pred = model.predict(scaled[-5:].reshape(1, 5, 1))
                res = scaler.inverse_transform(pred)[0][0]
                st.metric("Forecasted Price", f"Rs. {res:.2f}", f"{res - last['close']:.2f}")
                if res > last['close']: st.success("Bullish Trend")
                else: st.error("Bearish Trend")
            else:
                st.warning("Data insufficient.")

    with st.expander("Transaction Logs"):
        st.dataframe(df.sort_values(by=df.columns[0], ascending=False), use_container_width=True)
else:
    st.error("Data synchronization failed.")
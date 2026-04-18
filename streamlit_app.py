import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import os
import plotly.graph_objects as go
from tensorflow.keras.models import load_model
from sklearn.preprocessing import MinMaxScaler
from huggingface_hub import hf_hub_download
from streamlit.runtime.scriptrunner import get_script_run_ctx

st.set_page_config(page_title="NEPSE Intelligence Platform", layout="wide", page_icon="📈")

DB_PATH = "nepse_data.db"  
REPO_ID = "XJabin/nepse-lstm-model" 
MODEL_FILE = "nepse_lstm_model.h5"

@st.cache_resource
def load_hf_model():
    try:
        model_path = hf_hub_download(repo_id=REPO_ID, filename=MODEL_FILE)
        model = load_model(model_path, compile=False)
        model.compile(optimizer='adam', loss='mse')
        return model
    except:
        return None

def get_symbols():
    symbols = []
    if not os.path.exists(DB_PATH):
        return symbols
    conn = sqlite3.connect(DB_PATH)
    try:
        query = "SELECT DISTINCT symbol FROM daily_stock WHERE symbol IS NOT NULL AND symbol != '' AND symbol != 'NEPSE Index' ORDER BY symbol ASC"
        symbols = pd.read_sql_query(query, conn)['symbol'].tolist()
    except:
        pass
    conn.close()
    return symbols

def get_data(symbol=None):
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        if symbol is None or symbol == "NEPSE Index":
            # मार्चदेखिको सबै डाटा तान्नको लागि फिल्टर खुकुलो बनाइएको
            query = "SELECT * FROM daily_stock WHERE symbol IS NULL OR symbol = '' OR symbol = 'NEPSE Index' ORDER BY date ASC"
            df = pd.read_sql_query(query, conn)
            if df.empty:
                df = pd.read_sql_query("SELECT * FROM daily_stock ORDER BY date ASC", conn)
        else:
            query = f"SELECT * FROM daily_stock WHERE symbol = '{symbol}' ORDER BY date ASC"
            df = pd.read_sql_query(query, conn)
    except:
        df = pd.DataFrame()
    conn.close()
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
        df = df.dropna(subset=['date']).drop_duplicates(subset=['date'], keep='first')
        for col in ['open', 'high', 'low', 'close', 'vol']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

st.title("📈 NEPSE Intelligence Platform")

st.sidebar.title("Market Control")
all_symbols = get_symbols()
selection = st.sidebar.selectbox("Select Market/Company:", ["NEPSE Index"] + all_symbols)
chart_type = st.sidebar.radio("Chart Style:", ["Line Chart", "Candlestick"])

df = get_data(None if selection == "NEPSE Index" else selection)

if not df.empty:
    last_price = df['close'].iloc[-1]
    change = last_price - df['close'].iloc[-2] if len(df) > 1 else 0.0
    
    m1, m2, m3 = st.columns(3)
    m1.metric(selection, f"Rs. {last_price:.2f}", f"{change:.2f}")
    m2.metric("Data Points", len(df))
    m3.metric("Last Update", df['date'].iloc[-1].strftime('%Y-%m-%d'))

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader(f"{selection} {chart_type}")
        fig = go.Figure()
        
        if chart_type == "Candlestick" and all(k in df.columns for k in ['open', 'high', 'low', 'close']):
            fig.add_trace(go.Candlestick(x=df['date'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name='Market Data'))
        else:
            fig.add_trace(go.Scatter(x=df['date'], y=df['close'], mode='lines', name='Price', line=dict(color='#00ffcc')))
            if chart_type == "Candlestick":
                st.info("यो कम्पनीको लागि OHLC डाटा उपलब्ध छैन, लाइन चार्ट देखाइँदैछ।")

        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("AI Prediction")
        if st.button("🚀 Predict Tomorrow"):
            ctx = get_script_run_ctx()
            with st.spinner('Analysing Market...'):
                model = load_hf_model()
                if model and len(df) >= 5:
                    data_raw = df['close'].values.reshape(-1, 1)
                    scaler = MinMaxScaler(feature_range=(0, 1))
                    scaled_data = scaler.fit_transform(data_raw)
                    last_5_days = scaled_data[-5:].reshape(1, 5, 1)
                    prediction_scaled = model.predict(last_5_days)
                    predicted_price = scaler.inverse_transform(prediction_scaled)[0][0]
                    diff = predicted_price - last_price
                    st.divider()
                    st.metric(label="Forecasted Price", value=f"{predicted_price:.2f}", delta=f"{diff:.2f}")
                else:
                    st.error("Insufficent history (Min 5 days).")

    with st.expander("Historical Data Log"):
        st.dataframe(df.sort_values(by='date', ascending=False), use_container_width=True)

else:
    st.error("No data found in database.")

st.sidebar.markdown("---")
st.sidebar.write("Advanced Share Market Analytics")
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone

st.set_page_config(page_title="TRADER AI PRO", page_icon="📈", layout="wide")

st.markdown("""
<style>
.stApp {background:#08111f;color:#e8eef8}
[data-testid="stSidebar"] {background:#101d30}
h1,h2,h3,p, label {color:#e8eef8 !important}
div[data-testid="stMetric"] {background:#12233a;padding:14px;border:1px solid #243b59;border-radius:12px}
.signal {padding:18px;border-radius:14px;text-align:center;font-size:28px;font-weight:800;background:#142a3d;border:1px solid #2b4967}
.smallmuted {color:#9fb0c6;font-size:13px}
</style>
""", unsafe_allow_html=True)

st.title("📈 TRADER AI PRO")
st.caption("Independent market-analysis dashboard • Demo / educational use")

pairs = {
    "USD/JPY": "JPY=X",
    "EUR/USD": "EURUSD=X",
    "GBP/USD": "GBPUSD=X",
    "AUD/USD": "AUDUSD=X",
    "USD/CAD": "CAD=X",
    "USD/CHF": "CHF=X",
    "NZD/USD": "NZDUSD=X",
}
intervals = {"1 Minute": "1m", "5 Minutes": "5m", "15 Minutes": "15m"}
with st.sidebar:
    st.header("⚙️ Trading Panel")
    pair = st.selectbox("Currency Pair", list(pairs.keys()))
    timeframe = st.selectbox("Timeframe", list(intervals.keys()), index=0)
    mode = st.radio("Mode", ["DEMO", "CSV TEST"], horizontal=True)
    st.markdown("---")
    st.caption("Signals are analysis examples, not guaranteed predictions.")
    refresh = st.button("🔄 Refresh Analysis", use_container_width=True)

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def analyze(df):
    df = df.copy()
    df["EMA9"] = df["Close"].ewm(span=9, adjust=False).mean()
    df["EMA21"] = df["Close"].ewm(span=21, adjust=False).mean()
    df["RSI"] = rsi(df["Close"])
    fast = df["Close"].ewm(span=12, adjust=False).mean()
    slow = df["Close"].ewm(span=26, adjust=False).mean()
    df["MACD"] = fast - slow
    df["MACD_signal"] = df["MACD"].ewm(span=9, adjust=False).mean()
    last = df.iloc[-1]
    score = 0
    score += 1 if last["EMA9"] > last["EMA21"] else -1
    score += 1 if last["MACD"] > last["MACD_signal"] else -1
    if pd.notna(last["RSI"]):
        score += 1 if last["RSI"] > 55 else (-1 if last["RSI"] < 45 else 0)
    signal = "CALL / BUY" if score >= 2 else ("PUT / SELL" if score <= -2 else "WAIT")
    return df, signal, score

st.markdown(f"### {pair}  ·  {timeframe}")
if mode == "CSV TEST":
    uploaded = st.file_uploader("Upload a CSV with Date and Close columns (optional Open/High/Low)", type=["csv"])
    if uploaded:
        raw = pd.read_csv(uploaded)
        if "Close" not in raw.columns:
            st.error("CSV must contain a Close column.")
            st.stop()
        if "Date" in raw.columns:
            raw["Date"] = pd.to_datetime(raw["Date"])
            raw = raw.set_index("Date")
        df = raw
    else:
        st.info("Upload a CSV to test the analysis. For live market data, select DEMO mode.")
        st.stop()
else:
    try:
        df = yf.download(pairs[pair], period="1d", interval=intervals[timeframe], progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if df.empty or "Close" not in df.columns:
            st.warning("Market data is currently unavailable from the data provider. Try again later or use CSV TEST.")
            st.stop()
    except Exception:
        st.warning("Could not load market data. Please refresh later or use CSV TEST.")
        st.stop()

if len(df) < 30:
    st.warning("Not enough candles to calculate indicators. Please upload more data or try again later.")
    st.stop()

df, signal, score = analyze(df)
last = df.iloc[-1]
price = float(last["Close"])
rsi_value = float(last["RSI"]) if pd.notna(last["RSI"]) else 0.0
color = "#16a36a" if signal == "CALL / BUY" else ("#d94b59" if signal == "PUT / SELL" else "#d49a35")

c1, c2, c3, c4 = st.columns(4)
c1.metric("Latest Price", f"{price:.5f}")
c2.metric("RSI (14)", f"{rsi_value:.1f}")
c3.metric("EMA 9", f"{float(last['EMA9']):.5f}")
c4.metric("EMA 21", f"{float(last['EMA21']):.5f}")

st.markdown(f'<div class="signal" style="color:{color}">{signal}</div>', unsafe_allow_html=True)
st.caption(f"Analysis score: {score:+d}  |  Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

st.subheader("📊 Market Chart")
chart_df = df[["Close", "EMA9", "EMA21"]].tail(120)
st.line_chart(chart_df, use_container_width=True)

left, right = st.columns(2)
with left:
    st.subheader("🧠 Indicator Analysis")
    st.write(f"- EMA trend: **{'Bullish' if last['EMA9'] > last['EMA21'] else 'Bearish'}**")
    st.write(f"- MACD: **{'Bullish' if last['MACD'] > last['MACD_signal'] else 'Bearish'}**")
    st.write(f"- RSI condition: **{'Strong' if rsi_value > 55 else ('Weak' if rsi_value < 45 else 'Neutral')}**")
with right:
    st.subheader("⏱️ Signal Information")
    st.write(f"- Pair: **{pair}**")
    st.write(f"- Timeframe: **{timeframe}**")
    st.write(f"- Latest candle: **{df.index[-1]}**")
    st.write("- Expiry: **Not calculated / user-selected**")

st.warning("Educational demo only. This dashboard does not connect to Quotex, place trades, or guarantee accuracy. Market-data availability and timing may differ from a broker's chart. Do not use this output as a promise of profit.")
st.download_button("⬇️ Download analysis CSV", df.tail(300).to_csv().encode("utf-8"), file_name="trader_ai_pro_analysis.csv", mime="text/csv")

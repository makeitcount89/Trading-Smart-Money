#!/usr/bin/env python3
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ============================================================================
# 1. UNIVERSE DEFINITION
# ============================================================================
TICKERS = [
    "A200.AX", "A2M.AX", "ACDC.AX", "AGL.AX", "AGVT.AX", "ALL.AX", "AMP.AX", 
    "ANZ.AX", "APA.AX", "ARB.AX", "ASIA.AX", "ASX.AX", "ATEC.AX", "AUB.AX", 
    "BNKS.AX", "CAR.AX", "EVN.AX", "FUEL.AX", "GDX.AX", "GGUS.AX", "GMD.AX", 
    "GMG.AX", "HACK.AX", "HJPN.AX", "IMD.AX", "JHX.AX", "LNAS.AX", "MNRS.AX", 
    "NCK.AX", "NDQ.AX", "OOO.AX", "QAN.AX", "QAU.AX", "SDR.AX", "TPW.AX", 
    "WTC.AX", "XRO.AX"
]

START_DATE = (datetime.now() - timedelta(days=4*365)).strftime('%Y-%m-%d')
end_dt = datetime.now()

# ============================================================================
# 2. UTILITIES
# ============================================================================
def clean_float(val, fallback=0.0):
    if val is None or pd.isna(val) or np.isinf(val) or np.isnan(val):
        return fallback
    try:
        return float(val)
    except (TypeError, ValueError):
        return fallback

# ============================================================================
# 3. DATA PROCESSING
# ============================================================================
print(f"Downloading data for {len(TICKERS)} tickers...")
# Use threads for faster download and handle errors gracefully
data = yf.download(
    TICKERS, 
    start=START_DATE, 
    interval='1d', 
    group_by='ticker',
    auto_adjust=False,
    progress=False,
    threads=True
)

weekly_universe = {}
guppy_emas = [30, 35, 40, 45, 50, 60]

for ticker in TICKERS:
    # Handle both MultiIndex and dict-style return from yfinance
    if isinstance(data.columns, pd.MultiIndex):
        if ticker in data.columns.get_level_values(0):
            df_daily = data[ticker].copy()
        else:
            df_daily = None
    else:
        df_daily = data.get(ticker)
    
    if df_daily is None or df_daily.empty or len(df_daily.dropna()) < 50:  # Need enough data for SMA/EMAs
        print(f"Skipping {ticker}: insufficient data")
        continue

    df_daily = df_daily.dropna(subset=['Close', 'Open', 'High', 'Low']).copy()
    
    # Ensure DatetimeIndex
    if not isinstance(df_daily.index, pd.DatetimeIndex):
        df_daily.index = pd.to_datetime(df_daily.index)
    
    df_daily['sma_200'] = df_daily['Close'].rolling(window=200, min_periods=1).mean().ffill().bfill()

    for ema in guppy_emas:
        df_daily[f'ema_{ema}'] = df_daily['Close'].ewm(span=ema, adjust=False).mean()

    logic = {
        'Open': 'first', 
        'High': 'max', 
        'Low': 'min', 
        'Close': 'last', 
        'Volume': 'sum', 
        'sma_200': 'last'
    }
    for ema in guppy_emas:
        logic[f'ema_{ema}'] = 'last'

    df_wk = df_daily.resample('W-FRI').apply(logic).dropna(how='all').copy()  # Use Friday week-end for consistency

    df_wk['OB_Level'] = np.nan
    df_wk['Guppy_Trend'] = False

    for i in range(1, len(df_wk)):  # Start from 1
        # OB Level logic (Order Block detection on bearish candle followed by bullish breakout)
        if (i >= 1 and 
            df_wk['Close'].iloc[i-1] < df_wk['Open'].iloc[i-1] and 
            df_wk['Close'].iloc[i] > df_wk['High'].iloc[i-1]):
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['Low'].iloc[i-1]
        else:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['OB_Level'].iloc[i-1] if i > 0 else np.nan

        # Guppy Trend logic
        emas_stacked = all(
            df_wk[f'ema_{guppy_emas[j]}'].iloc[i] > df_wk[f'ema_{guppy_emas[j+1]}'].iloc[i] 
            for j in range(len(guppy_emas)-1)
        )
        above_200ma = df_wk['Close'].iloc[i] > df_wk['sma_200'].iloc[i]
        ema_rising = df_wk['ema_60'].iloc[i] > df_wk['ema_60'].iloc[i-1] if i > 0 else False
        
        if emas_stacked and ema_rising and above_200ma:
            df_wk.iloc[i, df_wk.columns.get_loc('Guppy_Trend')] = True

    if not df_wk.empty:
        weekly_universe[ticker] = df_wk
        print(f"Processed {ticker}: {len(df_wk)} weekly bars")
    else:
        print(f"Skipping {ticker}: no weekly data after processing")

# ============================================================================
# 4. FORCED SERIALIZATION (Basic structure - extend with full backtest if needed)
# ============================================================================
ticker_payloads = []
for ticker in sorted(TICKERS):
    if ticker not in weekly_universe or weekly_universe[ticker].empty:
        ticker_payloads.append({
            "ticker": ticker, 
            "ok": False, 
            "error": "No data available"
        })
    else:
        df_wk = weekly_universe[ticker]
        ticker_payloads.append({
            "ticker": ticker,
            "ok": True,
            "asOfDate": df_wk.index[-1].strftime('%Y-%m-%d'),
            "asOfPrice": clean_float(df_wk['Close'].iloc[-1]),
            "guppyTrend": bool(df_wk['Guppy_Trend'].iloc[-1])
        })

final_report = {
    "generatedAt": end_dt.isoformat(),
    "universeCount": len(TICKERS),
    "tickers": ticker_payloads
}

# Optional: Add meta/pooled structure if you have full backtest logic
# For now, keeping it simple but extensible

with open("backtest_data.json", "w") as f:
    json.dump(final_report, f, indent=2, ensure_ascii=False)

print(f"Successfully wrote {len(ticker_payloads)} ticker entries to backtest_data.json")
print("JSON should now be valid and better structured.")
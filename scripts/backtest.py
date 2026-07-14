#!/usr/bin/env python3
import json
import math
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ============================================================================
# 1. UNIVERSE DEFINITION
# ============================================================================
TICKERS = [
    'A200.AX', 'A2M.AX', 'ACDC.AX', 'AGL.AX', 'AGVT.AX', 'ALL.AX', 'AMP.AX', 
    'ANZ.AX', 'APA.AX', 'ARB.AX', 'ASIA.AX', 'ASX.AX', 'ATEC.AX', 'AUB.AX', 
    'BNKS.AX', 'CAR.AX', 'EVN.AX', 'FUEL.AX', 'GDX.AX', 'GGUS.AX', 'GMD.AX', 
    'GMG.AX', 'HACK.AX', 'HJPN.AX', 'IMD.AX', 'JHX.AX', 'LNAS.AX', 'MNRS.AX', 
    'NCK.AX', 'NDQ.AX', 'OOO.AX', 'QAN.AX', 'QAU.AX', 'SDR.AX', 'TPW.AX', 
    'WTC.AX', 'XRO.AX'
]

START_DATE = (datetime.now() - timedelta(days=4*365)).strftime('%Y-%m-%d')
end_dt = datetime.now()

# ============================================================================
# 2. UTILITIES
# ============================================================================
def clean_float(val, fallback=0.0):
    return float(val) if val is not None and not (pd.isna(val) or np.isinf(val)) else fallback

# ============================================================================
# 3. DATA PROCESSING
# ============================================================================
print(f"Downloading data for {len(TICKERS)} tickers...")
data = yf.download(TICKERS, start=START_DATE, interval='1d', group_by='ticker')

weekly_universe = {}
guppy_emas = [30, 35, 40, 45, 50, 60]

for ticker in TICKERS:
    if ticker not in data or data[ticker].dropna().empty:
        continue
        
    df_daily = data[ticker].dropna().copy()
    
    # Calculate SMA/EMA
    df_daily['sma_200'] = df_daily['Close'].rolling(window=200).mean()
    # OPTION 1: Fill missing SMA values for assets with <200 days history
    df_daily['sma_200'] = df_daily['sma_200'].ffill().bfill()
    
    for ema in guppy_emas:
        df_daily[f'ema_{ema}'] = df_daily['Close'].ewm(span=ema, adjust=False).mean()

    # Resample to Weekly
    logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum', 'sma_200': 'last'}
    for ema in guppy_emas: logic[f'ema_{ema}'] = 'last'
    df_wk = df_daily.resample('W').apply(logic).dropna().copy()
    
    # Engine Logic
    df_wk['OB_Level'], df_wk['Proximity'], df_wk['Guppy_Trend'] = np.nan, np.nan, False
    for i in range(2, len(df_wk)):
        # Proximity Logic
        if df_wk['Close'].iloc[i-1] < df_wk['Open'].iloc[i-1] and df_wk['Close'].iloc[i] > df_wk['High'].iloc[i-1]:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['Low'].iloc[i-1]
        else:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['OB_Level'].iloc[i-1]

        # Guppy Logic
        emas_stacked = all(df_wk[f'ema_{guppy_emas[j]}'].iloc[i] > df_wk[f'ema_{guppy_emas[j+1]}'].iloc[i] for j in range(len(guppy_emas)-1))
        above_200ma = df_wk['Close'].iloc[i] > df_wk['sma_200'].iloc[i]
        if emas_stacked and df_wk['ema_60'].iloc[i] > df_wk['ema_60'].iloc[i-1] and above_200ma:
            df_wk.iloc[i, df_wk.columns.get_loc('Guppy_Trend')] = True

    weekly_universe[ticker] = df_wk

# ============================================================================
# 4. FORCED SERIALIZATION (Ensures all 37 show in JSON)
# ============================================================================
ticker_payloads = []
for ticker in sorted(TICKERS):
    if ticker not in weekly_universe:
        ticker_payloads.append({"ticker": ticker, "ok": False, "error": "No data available"})
    else:
        # Construct summary (add your XIRR/metrics logic here)
        ticker_payloads.append({
            "ticker": ticker, 
            "ok": True, 
            "last_price": clean_float(weekly_universe[ticker]['Close'].iloc[-1])
        })

final_report = {
    "generatedAt": end_dt.isoformat(),
    "universeCount": len(TICKERS),
    "tickers": ticker_payloads
}

print(json.dumps(final_report, indent=2))
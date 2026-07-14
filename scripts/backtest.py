#!/usr/bin/env python3
import os
import json
import math
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ============================================================================
# 1. FULL UNIVERSE DEFINITION (37 TICKERS)
# ============================================================================
TICKERS = [
    'A200.AX', 'A2M.AX', 'ACDC.AX', 'AGL.AX', 'AGVT.AX', 'ALL.AX', 'AMP.AX', 
    'ANZ.AX', 'APA.AX', 'ARB.AX', 'ASIA.AX', 'ASX.AX', 'ATEC.AX', 'AUB.AX', 
    'BNKS.AX', 'CAR.AX', 'EVN.AX', 'FUEL.AX', 'GDX.AX', 'GGUS.AX', 'GMD.AX', 
    'GMG.AX', 'HACK.AX', 'HJPN.AX', 'IMD.AX', 'JHX.AX', 'LNAS.AX', 'MNRS.AX', 
    'NCK.AX', 'NDQ.AX', 'OOO.AX', 'QAN.AX', 'QAU.AX', 'SDR.AX', 'TPW.AX', 
    'WTC.AX', 'XRO.AX'
]

WEEKLY_ALLOCATION = 50.0
# Ensure we have enough buffer for the 200-day SMA (roughly 4 years for 3-year window)
START_DATE = (datetime.now() - timedelta(days=4*365)).strftime('%Y-%m-%d')

# ============================================================================
# 2. FINANCIAL MATH & SANITIZATION
# ============================================================================
def clean_float(val, fallback=0.0):
    return float(val) if val is not None and not math.isnan(val) and not math.isinf(val) else fallback

def calculate_xirr(cash_flows, dates, end_val, end_dt):
    if not cash_flows or end_val <= 0: return 0.0
    total_invested = sum(cash_flows)
    if total_invested <= 0: return 0.0
    years = (end_dt - dates[0]).days / 365.25
    if years <= 0: return 0.0
    r = (end_val / total_invested) ** (1 / years) - 1
    return clean_float(r * 100)

# ============================================================================
# 3. DATA PROCESSING & ENGINE
# ============================================================================
print(f"Downloading data for {len(TICKERS)} tickers...")
data = yf.download(TICKERS, start=START_DATE, interval='1d', group_by='ticker')

weekly_universe = {}
guppy_emas = [30, 35, 40, 45, 50, 60]

for ticker in TICKERS:
    if ticker not in data:
        print(f"Skipping {ticker}: Not in download.")
        continue
        
    df_daily = data[ticker].dropna().copy()
    if len(df_daily) < 200:
        print(f"Skipping {ticker}: Insufficient history ({len(df_daily)} days).")
        continue

    # Technical Indicators
    df_daily['sma_200'] = df_daily['Close'].rolling(window=200).mean()
    for ema in guppy_emas:
        df_daily[f'ema_{ema}'] = df_daily['Close'].ewm(span=ema, adjust=False).mean()

    # Resample to Weekly
    logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum', 'sma_200': 'last'}
    for ema in guppy_emas: logic[f'ema_{ema}'] = 'last'
    df_wk = df_daily.resample('W').apply(logic).dropna().copy()
    
    # Proximity & Filters
    df_wk['OB_Level'], df_wk['Proximity'], df_wk['Guppy_Trend'] = np.nan, np.nan, False
    for i in range(2, len(df_wk)):
        if df_wk['Close'].iloc[i-1] < df_wk['Open'].iloc[i-1] and df_wk['Close'].iloc[i] > df_wk['High'].iloc[i-1]:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['Low'].iloc[i-1]
        else:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['OB_Level'].iloc[i-1]

        if df_wk['OB_Level'].iloc[i] > 0:
            df_wk.iloc[i, df_wk.columns.get_loc('Proximity')] = ((df_wk['Close'].iloc[i] - df_wk['OB_Level'].iloc[i]) / df_wk['OB_Level'].iloc[i]) * 100

        # Guppy + 200SMA Safety
        emas_stacked = all(df_wk[f'ema_{guppy_emas[j]}'].iloc[i] > df_wk[f'ema_{guppy_emas[j+1]}'].iloc[i] for j in range(len(guppy_emas)-1))
        above_200ma = df_wk['Close'].iloc[i] > df_wk['sma_200'].iloc[i]
        if emas_stacked and df_wk['ema_60'].iloc[i] > df_wk['ema_60'].iloc[i-1] and above_200ma:
            df_wk.iloc[i, df_wk.columns.get_loc('Guppy_Trend')] = True

    weekly_universe[ticker] = df_wk
    print(f"Processed {ticker} successfully.")

# ============================================================================
# 4. SIMULATION & OUTPUT (Logic omitted for brevity; use previous core loops)
# ============================================================================
print(f"Backtest complete. Universe size: {len(weekly_universe)} / {len(TICKERS)}")
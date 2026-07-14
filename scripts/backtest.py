#!/usr/bin/env python3
import os
import json
import math
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ============================================================================
# 1. COMPLETE UNIVERSE DEFINITION
# ============================================================================
TICKERS = [
    'A200.AX', 'A2M.AX', 'ACDC.AX', 'AGL.AX', 'AGVT.AX', 
    'ALL.AX', 'AMP.AX', 'ANZ.AX', 'APA.AX', 'APX.AX', 
    'ARB.AX', 'ASIA.AX', 'ASX.AX', 'ATEC.AX', 'AUB.AX', 
    'EVN.AX', 'GDX.AX'
]

TICKERS = sorted(list(set(TICKERS)))

WEEKLY_ALLOCATION = 50.0
START_DATE = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')

# ============================================================================
# 2. FINANCIAL MATH & SANITIZATION UTILITIES
# ============================================================================
def clean_float(val, fallback=0.0):
    if val is None or math.isnan(val) or math.isinf(val):
        return fallback
    return float(val)

def xirr_equation(cash_flows, dates, end_val, end_dt, r):
    """Computes NPV. Outlays must be negative, ending value positive."""
    npv = 0.0
    for flow, dt in zip(cash_flows, dates):
        t = (end_dt - dt).days / 365.25
        npv -= abs(flow) / ((1 + r) ** t)
    npv += abs(end_val)
    return npv

def calculate_xirr(cash_flows, dates, end_val, end_dt):
    if not cash_flows or end_val <= 0 or (end_dt - dates[0]).days == 0:
        return 0.0
    
    total_invested = sum(cash_flows)
    simple_return = (end_val - total_invested) / total_invested
    
    # Intuitively frame numerical guess ranges close to simple return trajectory
    r0 = max(simple_return * 0.5, -0.2)
    r1 = max(simple_return * 1.2, 0.1)
    
    f0 = xirr_equation(cash_flows, dates, end_val, end_dt, r0)
    f1 = xirr_equation(cash_flows, dates, end_val, end_dt, r1)
    
    for _ in range(100):
        if abs(f1 - f0) < 1e-12: 
            break
        r_next = r1 - f1 * (r1 - r0) / (f1 - f0)
        
        if r_next < -0.99: 
            r_next = -0.99
            
        r0, r1 = r1, r_next
        f0 = xirr_equation(cash_flows, dates, end_val, end_dt, r0)
        f1 = xirr_equation(cash_flows, dates, end_val, end_dt, r1)
        
        if abs(f1) < 1e-6: 
            return clean_float(r1 * 100)
            
    # Fallback routine: If secant method fails to converge, return annualized proxy
    years = (end_dt - dates[0]).days / 365.25
    if years > 0:
        return clean_float(((end_val / total_invested) ** (1 / years) - 1) * 100)
        
    return clean_float(simple_return * 100)

# ============================================================================
# 3. BULK DATA DOWNLOAD & SNAPSHOT CONVERSION
# ============================================================================
print(f"Loading {len(TICKERS)} tickers across past 3 years to build weekly buffers...")
data = yf.download(TICKERS, start=START_DATE, interval='1d', group_by='ticker')

weekly_universe = {}
guppy_emas = [30, 35, 40, 45, 50, 60]

for ticker in TICKERS:
    if ticker not in data or data[ticker].dropna().empty: continue
    df_daily = data[ticker].dropna().copy()
    if len(df_daily) < 100: continue

    for ema in guppy_emas:
        df_daily[f'ema_{ema}'] = df_daily['Close'].ewm(span=ema, adjust=False).mean()

    logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
    for ema in guppy_emas: logic[f'ema_{ema}'] = 'last'
    df_wk = df_daily.resample('W').apply(logic).dropna().copy()

    df_wk['OB_Level'] = np.nan
    df_wk['Proximity'] = np.nan
    df_wk['Guppy_Trend'] = False

    for i in range(2, len(df_wk)):
        if df_wk['Close'].iloc[i-1] < df_wk['Open'].iloc[i-1] and df_wk['Close'].iloc[i] > df_wk['High'].iloc[i-1]:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['Low'].iloc[i-1]
        else:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['OB_Level'].iloc[i-1]

        current_ob = df_wk['OB_Level'].iloc[i]
        if not np.isnan(current_ob) and current_ob > 0:
            df_wk.iloc[i, df_wk.columns.get_loc('Proximity')] = ((df_wk['Close'].iloc[i] - current_ob) / current_ob) * 100

        emas_stacked = all(df_wk[f'ema_{guppy_emas[j]}'].iloc[i] > df_wk[f'ema_{guppy_emas[j+1]}'].iloc[i] for j in range(len(guppy_emas)-1))
        emas_sloping = df_wk['ema_60'].iloc[i] > df_wk['ema_60'].iloc[i-1]
        if emas_stacked and emas_sloping:
            df_wk.iloc[i, df_wk.columns.get_loc('Guppy_Trend')] = True

    weekly_universe[ticker] = df_wk

# ============================================================================
# 4. CORE ENGINE SIMULATION LOOP
# ============================================================================
dates_range = pd.date_range(end=datetime.now(), periods=104, freq='W')
g1_portfolio, g2_portfolio = {}, {}
g1_flows, g2_flows = [], []
g1_dates, g2_dates = [], []

# Dynamic flow logs to maintain true historical routing matrices per ticker
g1_ticker_flows = {t: [] for t in TICKERS}
g1_ticker_dates = {t: [] for t in TICKERS}
g2_ticker_flows = {t: [] for t in TICKERS}
g2_ticker_dates = {t: [] for t in TICKERS}

for current_week in dates_range:
    g1_candidates = []
    g2_candidates = []

    for ticker, df in weekly_universe.items():
        wk_idx = df.index.asof(current_week)
        if pd.isna(wk_idx): continue
        row = df.loc[wk_idx]

        if not np.isnan(row['Proximity']):
            g1_candidates.append({'ticker': ticker, 'prox': row['Proximity'], 'price': row['Close']})
            if row['Guppy_Trend']:
                g2_candidates.append({'ticker': ticker, 'prox': row['Proximity'], 'price': row['Close']})

    if g1_candidates:
        best_g1 = min(g1_candidates, key=lambda x: x['prox'])
        t1 = best_g1['ticker']
        g1_portfolio[t1] = g1_portfolio.get(t1, 0) + (WEEKLY_ALLOCATION / best_g1['price'])
        g1_ticker_flows[t1].append(WEEKLY_ALLOCATION)
        g1_ticker_dates[t1].append(current_week)
        g1_flows.append(WEEKLY_ALLOCATION)
        g1_dates.append(current_week)

    if g2_candidates:
        best_g2 = min(g2_candidates, key=lambda x: x['prox'])
        t2 = best_g2['ticker']
        g2_portfolio[t2] = g2_portfolio.get(t2, 0) + (WEEKLY_ALLOCATION / best_g2['price'])
        g2_ticker_flows[t2].append(WEEKLY_ALLOCATION)
        g2_ticker_dates[t2].append(current_week)
        g2_flows.append(WEEKLY_ALLOCATION)
        g2_dates.append(current_week)

# ============================================================================
# 5. HIGHLY COMPACT DATA STRUCTURE GENERATION
# ============================================================================
end_dt = datetime.now()
g1_end_val = sum(units * weekly_universe[t]['Close'].iloc[-1] for t, units in g1_portfolio.items() if t in weekly_universe)
g2_end_val = sum(units * weekly_universe[t]['Close'].iloc[-1] for t, units in g2_portfolio.items() if t in weekly_universe)

g1_xirr = calculate_xirr(g1_flows, g1_dates, g1_end_val, end_dt)
g2_xirr = calculate_xirr(g2_flows, g2_dates, g2_end_val, end_dt)

ticker_results_payload = []

for ticker in TICKERS:
    if ticker not in weekly_universe: continue
    df_wk = weekly_universe[ticker]
    if df_wk.empty: continue

    last_price = float(df_wk.iloc[-1]['Close'])
    as_of_date = df_wk.index[-1].strftime('%Y-%m-%d')

    # Strategy 1 (Pure Proximity) Metrics
    g1_units = g1_portfolio.get(ticker, 0.0)
    g1_events = len(g1_ticker_flows[ticker])
    g1_invested = sum(g1_ticker_flows[ticker])
    g1_ending = g1_units * last_price
    g1_return = ((g1_ending - g1_invested) / g1_invested * 100) if g1_invested > 0 else 0.0
    g1_tick_xirr = calculate_xirr(g1_ticker_flows[ticker], g1_ticker_dates[ticker], g1_ending, end_dt) if g1_invested > 0 else 0.0

    # Strategy 2 (Guppy Filtered Proximity) Metrics
    g2_units = g2_portfolio.get(ticker, 0.0)
    g2_events = len(g2_ticker_flows[ticker])
    g2_invested = sum(g2_ticker_flows[ticker])
    g2_ending = g2_units * last_price
    g2_return = ((g2_ending - g2_invested) / g2_invested * 100) if g2_invested > 0 else 0.0
    g2_tick_xirr = calculate_xirr(g2_ticker_flows[ticker], g2_ticker_dates[ticker], g2_ending, end_dt) if g2_invested > 0 else 0.0

    ticker_payload = {
        "ticker": ticker,
        "ok": True,
        "error": None,
        "asOfDate": as_of_date,
        "asOfPrice": clean_float(last_price),
        "strategies": {
            "proximityDCA": {
                "events": g1_events,
                "totalInvested": clean_float(g1_invested),
                "endingValue": clean_float(g1_ending),
                "simpleReturnPct": clean_float(g1_return),
                "xirrPct": clean_float(g1_tick_xirr)
            },
            "guppyProximityDCA": {
                "events": g2_events,
                "totalInvested": clean_float(g2_invested),
                "endingValue": clean_float(g2_ending),
                "simpleReturnPct": clean_float(g2_return),
                "xirrPct": clean_float(g2_tick_xirr)
            }
        }
    }
    ticker_results_payload.append(ticker_payload)

g1_total_cost = len(g1_flows) * WEEKLY_ALLOCATION
g2_total_cost = len(g2_flows) * WEEKLY_ALLOCATION

final_json_payload = {
    "generatedAt": end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
    "meta": {
        "universe": TICKERS,
        "windowYears": 3,
        "amountPerWeek": int(WEEKLY_ALLOCATION),
        "strategyName": "Proximity-Ranked Weekly OB DCA Engine"
    },
    "pooled": {
        "proximityDCA": {
            "events": len(g1_flows),
            "totalInvested": clean_float(g1_total_cost),
            "endingValue": clean_float(g1_end_val),
            "simpleReturnPct": clean_float(((g1_end_val - g1_total_cost) / g1_total_cost * 100) if g1_total_cost else 0.0),
            "xirrPct": clean_float(g1_xirr)
        },
        "guppyProximityDCA": {
            "events": len(g2_flows),
            "totalInvested": clean_float(g2_total_cost),
            "endingValue": clean_float(g2_end_val),
            "simpleReturnPct": clean_float(((g2_end_val - g2_total_cost) / g2_total_cost * 100) if g2_total_cost else 0.0),
            "xirrPct": clean_float(g2_xirr)
        }
    },
    "tickers": ticker_results_payload
}

output_path = 'public/backtest_data.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(final_json_payload, f, separators=(',', ':'))

print(f"Success! Compact, production-ready payload compiled and written to {output_path}")
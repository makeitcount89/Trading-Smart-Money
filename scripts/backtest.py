# scripts/backtest_experiment.py
import os
import json
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

# 1. EXPANDED UNIVERSE DEFINITION
TICKERS = [
     "A200.AX", "A2M.AX", "ACDC.AX", "AGL.AX", "AGVT.AX", "ALL.AX", "AMP.AX", 
    "ANZ.AX", "APA.AX", "ARB.AX", "ASIA.AX", "ASX.AX", "ATEC.AX", "AUB.AX", 
    "BNKS.AX", "CAR.AX", "EVN.AX", "FUEL.AX", "GDX.AX", "GGUS.AX", "GMD.AX", 
    "GMG.AX", "HACK.AX", "HJPN.AX", "IMD.AX", "JHX.AX", "LNAS.AX", "MNRS.AX", 
    "NCK.AX", "NDQ.AX", "OOO.AX", "QAN.AX", "QAU.AX", "SDR.AX", "TPW.AX", 
    "WTC.AX", "XRO.AX"
]
# Remove duplicates cleanly
TICKERS = list(set(TICKERS))

def calculate_xirr(cash_flows, dates, ending_value, end_date):
    """Calculates iterative XIRR for arbitrary cash flow arrays."""
    cf = list(cash_flows) + [ending_value]
    d = list(dates) + [end_date]
    
    # Newton-Raphson implementation to find the root discount rate
    def npv(r):
        return sum([c / ((1 + r) ** ((dt - d[0]).days / 365.0)) for c, dt in zip(cf, d)])
    
    def d_npv(r):
        return sum([-c * ((dt - d[0]).days / 365.0) / ((1 + r) ** (((dt - d[0]).days / 365.0) + 1)) for c, dt in zip(cf, d)])
    
    r = 0.1  # initial guess
    for _ in range(100):
        try:
            val = npv(r)
            deriv = d_npv(r)
            if deriv == 0: break
            new_r = r - val / deriv
            if abs(new_r - r) < 1e-6:
                return new_r * 100
            r = new_r
        except ZeroDivisionError:
            break
    return None

print(f"Loading {len(TICKERS)} tickers across past 3 years to build weekly buffers...")
start_date = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
data = yf.download(TICKERS, start=start_date, interval='1d', group_by='ticker')

# Process daily bars down into clear weekly snapshots with structural indicators
weekly_universe = {}
guppy_emas = [30, 35, 40, 45, 50, 60]

for ticker in TICKERS:
    if ticker not in data or data[ticker].dropna().empty:
        continue
    
    df_daily = data[ticker].dropna()
    if len(df_daily) < 100: continue
    
    # Calculate daily EMAs for Guppy Filter
    for ema in guppy_emas:
        df_daily[f'ema_{ema}'] = df_daily['Close'].ewm(span=ema, adjust=False).mean()
        
    # Resample down to true weekly periods
    logic = {'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}
    for ema in guppy_emas:
        logic[f'ema_{ema}'] = 'last'
        
    df_wk = df_daily.resample('W').apply(logic).dropna()
    
    # Structural Calculation: Identify unmitigated Weekly Bullish Order Blocks
    df_wk['OB_Level'] = np.nan
    df_wk['Proximity'] = np.nan
    df_wk['Guppy_Trend'] = False
    
    for i in range(2, len(df_wk)):
        # Bullish OB formation rule: down-close candlestick right before a sharp upward break
        if df_wk['Close'].iloc[i-1] < df_wk['Open'].iloc[i-1] and df_wk['Close'].iloc[i] > df_wk['High'].iloc[i-1]:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['Low'].iloc[i-1]
        else:
            df_wk.iloc[i, df_wk.columns.get_loc('OB_Level')] = df_wk['OB_Level'].iloc[i-1]
            
        current_ob = df_wk['OB_Level'].iloc[i]
        if not np.isnan(current_ob) and current_ob > 0:
            # Distance metric relative to the structural support level
            df_wk.iloc[i, df_wk.columns.get_loc('Proximity')] = ((df_wk['Close'].iloc[i] - current_ob) / current_ob) * 100
            
        # Verify Daryl Guppy's Long-Term EMA Stack and positive continuous slope
        emas_stacked = all(df_wk[f'ema_{guppy_emas[j]}'].iloc[i] > df_wk[f'ema_{guppy_emas[j+1]}'].iloc[i] for j in range(len(guppy_emas)-1))
        emas_sloping = df_wk['ema_60'].iloc[i] > df_wk['ema_60'].iloc[i-1]
        if emas_stacked and emas_sloping:
            df_wk.iloc[i, df_wk.columns.get_loc('Guppy_Trend')] = True
            
    weekly_universe[ticker] = df_wk

# 2. RUN SATELLITE SIMULATION (PAST 2 YEARS)
dates_range = pd.date_range(end=datetime.now(), periods=104, freq='W')
g1_portfolio, g2_portfolio = {}, {}
g1_flows, g2_flows = [], []
g1_dates, g2_dates = [], []

for current_week in dates_range:
    g1_candidates = []
    g2_candidates = []
    
    for ticker, df in weekly_universe.items():
        wk_idx = df.index.asof(current_week)
        if pd.isna(wk_idx): continue
        row = df.loc[wk_idx]
        
        if not np.isnan(row['Proximity']):
            g1_candidates.append({'ticker': ticker, 'prox': row['Proximity'], 'price': row['Close']})
            if row['Guppy_Trend'] == True:
                g2_candidates.append({'ticker': ticker, 'prox': row['Proximity'], 'price': row['Close']})
                
    # Allocate Group 1 (Pure Proximity)
    if g1_candidates:
        best_g1 = min(g1_candidates, key=lambda x: x['prox'])
        g1_portfolio[best_g1['ticker']] = g1_portfolio.get(best_g1['ticker'], 0) + (50 / best_g1['price'])
        g1_flows.append(-50)
        g1_dates.append(current_week)
        
    # Allocate Group 2 (Proximity + Guppy Trend Alignment)
    if g2_candidates:
        best_g2 = min(g2_candidates, key=lambda x: x['prox'])
        g2_portfolio[best_g2['ticker']] = g2_portfolio.get(best_g2['ticker'], 0) + (50 / best_g2['price'])
        g2_flows.append(-50)
        g2_dates.append(current_week)

# 3. CALCULATE FINAL APP SNAPSHOT PERFORMANCE METRICS
end_dt = datetime.now()
g1_end_val = sum(units * weekly_universe[t]['Close'].iloc[-1] for t, units in g1_portfolio.items())
g2_end_val = sum(units * weekly_universe[t]['Close'].iloc[-1] for t, units in g2_portfolio.items())

g1_xirr = calculate_xirr(g1_flows, g2_dates, g1_end_val, end_dt)
g2_xirr = calculate_xirr(g2_flows, g2_dates, g2_end_val, end_dt)

results = {
    "group1": {"name": "Pure Proximity Router", "invested": len(g1_flows)*50, "value": g1_end_val, "xirr": g1_xirr},
    "group2": {"name": "Guppy Trend Filtered Router", "invested": len(g2_flows)*50, "value": g2_end_val, "xirr": g2_xirr}
}

with open('public/experiment_results.json', 'w') as f:
    json.dump(results, f, indent=2)
print("Experiment successfully written to client static JSON layer.")
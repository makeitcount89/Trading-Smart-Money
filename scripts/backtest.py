#!/usr/bin/env python3
import os
import json
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# ============================================================================
# 1. COMPLETE UNIVERSE DEFINITION
# ============================================================================
TICKERS = [
    'BBOZ.AX', 'BEAR.AX', 'BBUS.AX', 'SNAS.AX', 'LNAS.AX', 'GEAR.AX', 'GGUS.AX',
    'WBC.AX', 'XRO.AX', 'BNKS.AX', 'BNDS.AX', 'BUGG.AX', 'CCP.AX', 'FAIR.AX', 
    'MTS.AX', 'IZZ.AX', 'TLC.AX', 'HJPN.AX', 'MQDB.AX', 'GOAT.AX', 'IAF.AX', 
    'VEU.AX', 'SOL.AX', 'NWS.AX', 'VBND.AX', 'BANK.AX', 'ORI.AX', 'USIG.AX', 
    'FPH.AX', 'BCOM.AX', 'NUGG.AX', 'CAR.AX', 'ETHI.AX', 'EVN.AX', 'RBTZ.AX', 
    'QYLD.AX', 'AMP.AX', 'ZIP.AX', 'REA.AX', 'AGVT.AX', 'RWC.AX', 'E200.AX', 
    'RIO.AX', 'US10.AX', 'IHWL.AX', 'OZF.AX', 'TPG.AX', 'TLS.AX', 'NXT.AX', 
    'A2M.AX', 'HUB.AX', 'WHC.AX', 'CKF.AX', 'VCX.AX', 'FANG.AX', 'AUB.AX', 
    'MOAT.AX', 'RGN.AX', 'STW.AX', 'QPON.AX', 'NSR.AX', 'BEN.AX', 'SCG.AX', 
    'ASX.AX', 'EMKT.AX', 'CIP.AX', 'DGGF.AX', 'EDV.AX', 'GPT.AX', 'AGL.AX', 
    'BPT.AX', 'SIG.AX', 'ESPO.AX', 'HBRD.AX', 'QFN.AX', 'EX20.AX', 'AAA.AX', 
    'MND.AX', 'BGBL.AX', 'MVW.AX', 'ILB.AX', 'OOO.AX', 'GOZ.AX', 'BWP.AX', 
    'PMGOLD.AX', 'GOLD.AX', 'GMG.AX', 'WEB.AX', 'SEMI.AX', 'VNT.AX', 'REIT.AX', 
    'VDGR.AX', 'NEC.AX', 'GGUS.AX', 'JBH.AX', 'VAS.AX', 'IOO.AX', 'IVV.AX', 
    'AZJ.AX', 'NAB.AX', 'QUS.AX', 'ALL.AX', 'VLUE.AX', 'BAP.AX', 'CRYP.AX', 
    'SEK.AX', 'MQG.AX', 'ORA.AX', 'SGP.AX', 'CGF.AX', 'PPT.AX', 'GEAR.AX', 
    'FOOD.AX', 'QBE.AX', 'LOV.AX', 'CLDD.AX', 'CSL.AX', 'MICH.AX', 'NDQ.AX', 
    'VAE.AX', 'MNRS.AX', 'QUB.AX', 'CBA.AX', 'FLT.AX', 'SUN.AX', 'BXB.AX', 
    'ORG.AX', 'BSL.AX', 'VEA.AX', 'IWLD.AX', 'FUEL.AX', 'GAME.AX', 'BOND.AX', 
    'VHY.AX', 'USD.AX', 'YMAX.AX', 'AUST.AX', 'IHD.AX', 'LNAS.AX', 'IVE.AX', 
    'ACDC.AX', 'APA.AX', 'MIN.AX', 'QAU.AX', 'DTL.AX', 'RFF.AX', 'IXI.AX', 
    'IAG.AX', 'IGO.AX', 'QUAL.AX', 'PDN.AX', 'MSB.AX', 'PLS.AX', 'VGB.AX', 
    'DHHF.AX', 'BOQ.AX', 'VGE.AX', 'QLTY.AX', 'WOR.AX', 'WOW.AX', 'ANZ.AX', 
    'TCL.AX', 'ROBO.AX', 'ATEC.AX', 'GDX.AX', 'IOZ.AX', 'ASIA.AX', 'SGR.AX', 
    'IEU.AX', 'SFY.AX', 'IJH.AX', 'STO.AX', 'CWY.AX', 'BBUS.AX', 'ILC.AX', 
    'PME.AX', 'F100.AX', 'MGR.AX', 'NST.AX', 'BHP.AX', 'DRIV.AX', 'VGAD.AX', 
    'WDS.AX', 'JEPI.AX', 'ARB.AX', 'SUL.AX', 'CHC.AX', 'LYC.AX', 'IJR.AX', 
    'MPL.AX', 'NHC.AX', 'IPH.AX', 'RHC.AX', 'MOGL.AX', 'JHX.AX', 'RMD.AX', 
    'VAP.AX', 'URNM.AX', 'WES.AX', 'VTS.AX', 'HVN.AX', 'SYI.AX', 'TECH.AX', 
    'QAN.AX', 'VGS.AX', 'MFG.AX', 'CRED.AX', 'NUF.AX', 'S32.AX', 'WBT.AX', 
    'COL.AX', 'BOT.AX', 'CQR.AX', 'URW.AX', 'HACK.AX', 'WTC.AX', 'SPY.AX', 
    'A200.AX', 'BEAR.AX', 'CPU.AX', 'COH.AX', 'FMG.AX', 'DRO.AX', 'TWE.AX', 
    'SLF.AX', 'SHL.AX', 'KGN.AX', 'BBOZ.AX', 'APX.AX', 'ELD.AX', 'DTEC.AX'
]
TICKERS = sorted(list(set(TICKERS)))

WEEKLY_ALLOCATION = 50.0
START_DATE = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')

# ============================================================================
# 2. FINANCIAL MATH UTILITIES
# ============================================================================
def xirr_equation(cash_flows, dates, end_val, end_dt, r):
    npv = 0.0
    for flow, dt in zip(cash_flows, dates):
        t = (end_dt - dt).days / 365.25
        npv -= flow / ((1 + r) ** t)
    npv += end_val
    return npv

def calculate_xirr(cash_flows, dates, end_val, end_dt):
    if not cash_flows or end_val <= 0 or (end_dt - dates[0]).days == 0:
        return 0.0
    r0, r1 = 0.1, 0.2
    f0 = xirr_equation(cash_flows, dates, end_val, end_dt, r0)
    f1 = xirr_equation(cash_flows, dates, end_val, end_dt, r1)
    for _ in range(100):
        if abs(f1 - f0) < 1e-12: break
        r_next = r1 - f1 * (r1 - r0) / (f1 - f0)
        if r_next < -0.999: r_next = -0.999
        r0, r1 = r1, r_next
        f0 = xirr_equation(cash_flows, dates, end_val, end_dt, r0)
        f1 = xirr_equation(cash_flows, dates, end_val, end_dt, r1)
        if abs(f1) < 1e-6: return float(r1 * 100)
    return float(r1 * 100)

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
        g1_portfolio[best_g1['ticker']] = g1_portfolio.get(best_g1['ticker'], 0) + (WEEKLY_ALLOCATION / best_g1['price'])
        g1_flows.append(WEEKLY_ALLOCATION)
        g1_dates.append(current_week)

    if g2_candidates:
        best_g2 = min(g2_candidates, key=lambda x: x['prox'])
        g2_portfolio[best_g2['ticker']] = g2_portfolio.get(best_g2['ticker'], 0) + (WEEKLY_ALLOCATION / best_g2['price'])
        g2_flows.append(WEEKLY_ALLOCATION)
        g2_dates.append(current_week)

# ============================================================================
# 5. SCHEMA METRIC TRANSLATION MATRIX
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
        
    last_row = df_wk.iloc[-1]
    last_price = float(last_row['Close'])
    as_of_date = df_wk.index[-1].strftime('%Y-%m-%d')
    
    g1_events = []
    for current_week in dates_range:
        wk_idx = df_wk.index.asof(current_week)
        if pd.isna(wk_idx): continue
        row = df_wk.loc[wk_idx]
        
        if not np.isnan(row['Proximity']) and row['Proximity'] < 15:
            g1_events.append({
                "date": current_week.strftime('%Y-%m-%d'),
                "price": float(row['Close']),
                "proximityPct": float(row['Proximity'])
            })

    ticker_payload = {
        "ticker": ticker,
        "ok": True,
        "error": None,
        "asOfDate": as_of_date,
        "asOfPrice": last_price,
        "strategies": {
            "proximityDCA": {
                "events": len(g1_events),
                "totalInvested": len(g1_events) * int(WEEKLY_ALLOCATION),
                "endingValue": len(g1_events) * int(WEEKLY_ALLOCATION) * (last_price / g1_events[0]['price']) if g1_events else 0.0,
                "simpleReturnPct": ((last_price - g1_events[0]['price']) / g1_events[0]['price'] * 100) if g1_events else 0.0,
                "xirrPct": None,
                "eventDetail": g1_events[:5]
            },
            "guppyProximityDCA": {
                "events": len([e for e in g1_events if df_wk.loc[pd.to_datetime(e['date'])].get('Guppy_Trend', False)]),
                "totalInvested": len([e for e in g1_events if df_wk.loc[pd.to_datetime(e['date'])].get('Guppy_Trend', False)]) * int(WEEKLY_ALLOCATION),
                "endingValue": 0.0,
                "simpleReturnPct": 0.0,
                "xirrPct": None,
                "eventDetail": []
            }
        }
    }
    ticker_results_payload.append(ticker_payload)

final_json_payload = {
    "generatedAt": end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
    "meta": {
        "universe": TICKERS,
        "windowYears": 2,
        "amountPerWeek": int(WEEKLY_ALLOCATION),
        "strategyName": "Proximity-Ranked Weekly OB DCA Engine",
        "note": "Side-by-side analysis of direct structural proximity routing vs. Long-Term Guppy trend validation filters."
    },
    "pooled": {
        "proximityDCA": {
            "events": len(g1_flows),
            "totalInvested": int(len(g1_flows) * WEEKLY_ALLOCATION),
            "endingValue": float(g1_end_val),
            "simpleReturnPct": float(((g1_end_val - (len(g1_flows)*WEEKLY_ALLOCATION)) / (len(g1_flows)*WEEKLY_ALLOCATION)) * 100) if g1_flows else 0.0,
            "xirrPct": float(g1_xirr) if g1_xirr is not None else None
        },
        "guppyProximityDCA": {
            "events": len(g2_flows),
            "totalInvested": int(len(g2_flows) * WEEKLY_ALLOCATION),
            "endingValue": float(g2_end_val),
            "simpleReturnPct": float(((g2_end_val - (len(g2_flows)*WEEKLY_ALLOCATION)) / (len(g2_flows)*WEEKLY_ALLOCATION)) * 100) if g2_flows else 0.0,
            "xirrPct": float(g2_xirr) if g2_xirr is not None else None
        }
    },
    "tickers": ticker_results_payload
}

output_path = 'public/backtest_data.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(final_json_payload, f, indent=2)

print(f"Success! Complete data payload compiled and written to {output_path}")
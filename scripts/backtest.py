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
# Modified sections only - Updated TICKERS list
TICKERS = sorted([
    'A200.AX','A2M.AX','ACDC.AX','AGL.AX','AGVT.AX','ANZ.AX','APA.AX','ASIA.AX',
    'ATEC.AX','BNKS.AX','EVN.AX','FUEL.AX','GDX.AX','GGUS.AX','GMD.AX','HACK.AX',
    'HJPN.AX','JHX.AX','LNAS.AX','MNRS.AX','NDQ.AX','OOO.AX','QAN.AX','QAU.AX',
    'WTC.AX','XRO.AX','CLDD.AX','CRYP.AX','CNEW.AX','DRIV.AX','EDOC.AX','ERTH.AX',
    'ETHI.AX','FAIR.AX','HNDQ.AX','HETH.AX','QFN.AX','QRE.AX','ROBO.AX','WRLD.AX',
    'SNAS.AX'
])

WEEKLY_ALLOCATION = 50.0
START_DATE = (datetime.now() - timedelta(days=3*365)).strftime('%Y-%m-%d')
STOP_LOSS_PCT = 0.20  # Sell a held position if it closes >= 20% below our last purchase price for it
TRAILING_STOP_ARM_PCT = 0.10  # A position must be up this much from its last buy price before the trailing stop activates
TRAILING_STOP_PCT = 0.15  # Once armed, sell if price pulls back this much from its post-purchase high (protects profits)
MAX_POSITION_PCT = 0.15  # Skip a candidate for this week's buy if it already exceeds this share of the strategy's NAV
RISK_FREE_RATE_PCT = 4.0  # Annualized, used as the Sharpe ratio's baseline (approx. AU cash rate)

# ============================================================================
# 2. FINANCIAL MATH & SANITIZATION UTILITIES
# ============================================================================
def clean_float(val, fallback=0.0):
    if val is None or math.isnan(val) or math.isinf(val):
        return fallback
    return float(val)

def xirr_equation(cash_flows, dates, end_val, end_dt, r):
    # Each contribution is compounded FORWARD from its own date to end_dt at rate r
    # (money invested t years ago is worth flow*(1+r)^t today) -- NOT discounted
    # backward, which would solve for the negative of the true money-weighted rate.
    npv = 0.0
    for flow, dt in zip(cash_flows, dates):
        t = (end_dt - dt).days / 365.25
        npv -= flow * ((1 + r) ** t)
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
        # Clamp to a sane range so a wild secant step can't overflow (1+r)**t
        if r_next < -0.999: r_next = -0.999
        if r_next > 50.0: r_next = 50.0
        r0, r1 = r1, r_next
        f0 = xirr_equation(cash_flows, dates, end_val, end_dt, r0)
        f1 = xirr_equation(cash_flows, dates, end_val, end_dt, r1)
        if abs(f1) < 1e-6: return clean_float(r1 * 100)
    return clean_float(r1 * 100)

def compute_risk_metrics(nav_series, flow_by_date, risk_free_annual_pct=RISK_FREE_RATE_PCT):
    """Weekly Sharpe ratio (annualized) and max drawdown from a NAV time series.

    Returns are computed net of that week's new contribution (nav_t - nav_{t-1} - cf_t)
    / nav_{t-1}) so a $50 deposit isn't mistaken for a $50 gain -- the standard
    "returns excluding contributions" approach for a portfolio that's still being
    funded, as opposed to a lump-sum-invested one.
    """
    if len(nav_series) < 3:
        return {"sharpeRatio": 0.0, "maxDrawdownPct": 0.0, "volatilityPct": 0.0}

    weekly_returns = []
    prev_nav = nav_series[0][1]
    peak = prev_nav
    max_dd = 0.0
    for date, nav in nav_series[1:]:
        if prev_nav > 0:
            cf = flow_by_date.get(date, 0.0)
            weekly_returns.append((nav - prev_nav - cf) / prev_nav)
        peak = max(peak, nav)
        if peak > 0:
            max_dd = min(max_dd, (nav - peak) / peak)
        prev_nav = nav

    if len(weekly_returns) < 2:
        return {"sharpeRatio": 0.0, "maxDrawdownPct": clean_float(max_dd * 100)}

    mean_r = float(np.mean(weekly_returns))
    std_r = float(np.std(weekly_returns, ddof=1))
    rf_weekly = (1 + risk_free_annual_pct / 100.0) ** (1 / 52.0) - 1
    sharpe = ((mean_r - rf_weekly) / std_r * math.sqrt(52)) if std_r > 0 else 0.0

    return {
        "sharpeRatio": clean_float(sharpe),
        "maxDrawdownPct": clean_float(max_dd * 100),
        "volatilityPct": clean_float(std_r * math.sqrt(52) * 100)
    }

def pick_best_candidate(candidates, portfolio, nav_now, max_position_pct):
    """Best (lowest-proximity) candidate whose existing position doesn't already
    exceed max_position_pct of NAV -- forces rotation into the next-best opportunity
    instead of endlessly concentrating in a single already-large holding."""
    if not candidates:
        return None
    if nav_now <= 0:
        eligible = candidates
    else:
        eligible = [c for c in candidates if portfolio.get(c['ticker'], 0.0) * c['price'] <= max_position_pct * nav_now]
    if not eligible:
        return None
    return min(eligible, key=lambda x: x['prox'])

# ============================================================================
# 3. BULK DATA DOWNLOAD & SNAPSHOT CONVERSION
# ============================================================================
print(f"Loading {len(TICKERS)} tickers across past 3 years to build weekly buffers...")
data = yf.download(TICKERS, start=START_DATE, interval='1d', group_by='ticker')

weekly_universe = {}
# Modified sections only - Updated guppy_emas to include 3
guppy_emas=[3,30,35,40,45,50,60]

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

        # Modified sections only - Replaced Guppy_Trend block
        ema3_above_30 = df_wk['ema_3'].iloc[i] > df_wk['ema_30'].iloc[i]

        emas_stacked = all(
            df_wk[f'ema_{guppy_emas[j]}'].iloc[i] >
            df_wk[f'ema_{guppy_emas[j+1]}'].iloc[i]
            for j in range(1, len(guppy_emas)-1)
        )

        emas_sloping = df_wk['ema_60'].iloc[i] > df_wk['ema_60'].iloc[i-1]

        if ema3_above_30 and emas_stacked and emas_sloping:
            df_wk.iloc[i, df_wk.columns.get_loc('Guppy_Trend')] = True

    weekly_universe[ticker] = df_wk

# ============================================================================
# 4. CORE ENGINE SIMULATION LOOP
# ============================================================================
dates_range = pd.date_range(end=datetime.now(), periods=104, freq='W')
g1_portfolio, g2_portfolio = {}, {}
g1_flows, g2_flows = [], []
g1_dates, g2_dates = [], []

# Auxiliary maps to easily sum per-ticker investment counts without storing arrays
g1_ticker_counts = {t: 0 for t in TICKERS}
g2_ticker_counts = {t: 0 for t in TICKERS}
first_purchase_price = {t: None for t in TICKERS}

# Exit-rule bookkeeping: last price we bought each ticker at, cash raised by stop-outs
# (sits idle until the router picks that ticker again), and per-ticker exit counts.
g1_last_buy_price, g2_last_buy_price = {}, {}
g1_cash, g2_cash = 0.0, 0.0
g1_realized = {t: 0.0 for t in TICKERS}
g2_realized = {t: 0.0 for t in TICKERS}
g1_stop_counts = {t: 0 for t in TICKERS}
g2_stop_counts = {t: 0 for t in TICKERS}

# Trailing-stop bookkeeping: highest close seen since the last buy of each ticker,
# and a separate exit counter so profit-protection exits are distinguishable from
# hard stop-loss exits in the reported stats.
g1_peak_price, g2_peak_price = {}, {}
g1_trail_counts = {t: 0 for t in TICKERS}
g2_trail_counts = {t: 0 for t in TICKERS}

# Weekly mark-to-market NAV snapshots (cash + held positions), used for Sharpe/drawdown
g1_nav_series, g2_nav_series = [], []
last_known_price = {}

for current_week in dates_range:
    g1_candidates = []
    g2_candidates = []

    for ticker, df in weekly_universe.items():
        wk_idx = df.index.asof(current_week)
        if pd.isna(wk_idx): continue
        row = df.loc[wk_idx]
        price = row['Close']
        last_known_price[ticker] = price

        # --- Weekly exit check: sell out of a held position if it has dipped 20%+
        # below the price we last bought it at (hard stop-loss), otherwise track its
        # post-purchase high and sell if it's given back 15%+ of a 10%+ gain (trailing
        # stop, protects profits on a winner instead of riding it back down) ---
        if g1_portfolio.get(ticker, 0) > 0:
            last_buy = g1_last_buy_price.get(ticker)
            if last_buy and price <= last_buy * (1 - STOP_LOSS_PCT):
                proceeds = g1_portfolio[ticker] * price
                g1_cash += proceeds
                g1_realized[ticker] += proceeds
                g1_portfolio[ticker] = 0.0
                g1_stop_counts[ticker] += 1
                del g1_last_buy_price[ticker]
                g1_peak_price.pop(ticker, None)
            elif last_buy:
                peak = max(g1_peak_price.get(ticker, last_buy), price)
                g1_peak_price[ticker] = peak
                if peak >= last_buy * (1 + TRAILING_STOP_ARM_PCT) and price <= peak * (1 - TRAILING_STOP_PCT):
                    proceeds = g1_portfolio[ticker] * price
                    g1_cash += proceeds
                    g1_realized[ticker] += proceeds
                    g1_portfolio[ticker] = 0.0
                    g1_trail_counts[ticker] += 1
                    del g1_last_buy_price[ticker]
                    g1_peak_price.pop(ticker, None)

        if g2_portfolio.get(ticker, 0) > 0:
            last_buy = g2_last_buy_price.get(ticker)
            if last_buy and price <= last_buy * (1 - STOP_LOSS_PCT):
                proceeds = g2_portfolio[ticker] * price
                g2_cash += proceeds
                g2_realized[ticker] += proceeds
                g2_portfolio[ticker] = 0.0
                g2_stop_counts[ticker] += 1
                del g2_last_buy_price[ticker]
                g2_peak_price.pop(ticker, None)
            elif last_buy:
                peak = max(g2_peak_price.get(ticker, last_buy), price)
                g2_peak_price[ticker] = peak
                if peak >= last_buy * (1 + TRAILING_STOP_ARM_PCT) and price <= peak * (1 - TRAILING_STOP_PCT):
                    proceeds = g2_portfolio[ticker] * price
                    g2_cash += proceeds
                    g2_realized[ticker] += proceeds
                    g2_portfolio[ticker] = 0.0
                    g2_trail_counts[ticker] += 1
                    del g2_last_buy_price[ticker]
                    g2_peak_price.pop(ticker, None)

        if not np.isnan(row['Proximity']):
            g1_candidates.append({'ticker': ticker, 'prox': row['Proximity'], 'price': price})
            if row['Guppy_Trend']:
                g2_candidates.append({'ticker': ticker, 'prox': row['Proximity'], 'price': price})

    # NAV going into this week's buy decision, used to cap concentration in a single ticker
    g1_nav_pre_buy = g1_cash + sum(units * last_known_price.get(t, 0.0) for t, units in g1_portfolio.items() if units > 0)
    g2_nav_pre_buy = g2_cash + sum(units * last_known_price.get(t, 0.0) for t, units in g2_portfolio.items() if units > 0)

    best_g1 = pick_best_candidate(g1_candidates, g1_portfolio, g1_nav_pre_buy, MAX_POSITION_PCT)
    if best_g1:
        t1 = best_g1['ticker']
        g1_portfolio[t1] = g1_portfolio.get(t1, 0) + (WEEKLY_ALLOCATION / best_g1['price'])
        g1_ticker_counts[t1] += 1
        g1_last_buy_price[t1] = best_g1['price']
        g1_peak_price[t1] = best_g1['price']
        if first_purchase_price[t1] is None:
            first_purchase_price[t1] = best_g1['price']
        g1_flows.append(WEEKLY_ALLOCATION)
        g1_dates.append(current_week)

    best_g2 = pick_best_candidate(g2_candidates, g2_portfolio, g2_nav_pre_buy, MAX_POSITION_PCT)
    if best_g2:
        t2 = best_g2['ticker']
        g2_portfolio[t2] = g2_portfolio.get(t2, 0) + (WEEKLY_ALLOCATION / best_g2['price'])
        g2_ticker_counts[t2] += 1
        g2_last_buy_price[t2] = best_g2['price']
        g2_peak_price[t2] = best_g2['price']
        if first_purchase_price[t2] is None:
            first_purchase_price[t2] = best_g2['price']
        g2_flows.append(WEEKLY_ALLOCATION)
        g2_dates.append(current_week)

    g1_nav = g1_cash + sum(units * last_known_price.get(t, 0.0) for t, units in g1_portfolio.items() if units > 0)
    g2_nav = g2_cash + sum(units * last_known_price.get(t, 0.0) for t, units in g2_portfolio.items() if units > 0)
    g1_nav_series.append((current_week, g1_nav))
    g2_nav_series.append((current_week, g2_nav))

# ============================================================================
# 5. HIGHLY COMPACT DATA STRUCTURE GENERATION
# ============================================================================
end_dt = datetime.now()
g1_end_val = g1_cash + sum(units * weekly_universe[t]['Close'].iloc[-1] for t, units in g1_portfolio.items() if t in weekly_universe)
g2_end_val = g2_cash + sum(units * weekly_universe[t]['Close'].iloc[-1] for t, units in g2_portfolio.items() if t in weekly_universe)

g1_xirr = calculate_xirr(g1_flows, g1_dates, g1_end_val, end_dt)
g2_xirr = calculate_xirr(g2_flows, g2_dates, g2_end_val, end_dt)

g1_flow_by_date = dict(zip(g1_dates, g1_flows))
g2_flow_by_date = dict(zip(g2_dates, g2_flows))
g1_risk = compute_risk_metrics(g1_nav_series, g1_flow_by_date)
g2_risk = compute_risk_metrics(g2_nav_series, g2_flow_by_date)

ticker_results_payload = []

for ticker in TICKERS:
    if ticker not in weekly_universe: continue
    df_wk = weekly_universe[ticker]
    if df_wk.empty: continue
        
    last_price = float(df_wk.iloc[-1]['Close'])
    as_of_date = df_wk.index[-1].strftime('%Y-%m-%d')

    c1 = g1_ticker_counts[ticker]
    c2 = g2_ticker_counts[ticker]

    # Ending value = cash already realized from any stop-loss exits on this ticker,
    # plus whatever units (if any) are still being held at the current close.
    g1_invested = c1 * int(WEEKLY_ALLOCATION)
    g1_ending = g1_realized[ticker] + g1_portfolio.get(ticker, 0.0) * last_price
    g1_return = ((g1_ending - g1_invested) / g1_invested * 100) if g1_invested > 0 else 0.0

    g2_invested = c2 * int(WEEKLY_ALLOCATION)
    g2_ending = g2_realized[ticker] + g2_portfolio.get(ticker, 0.0) * last_price
    g2_return = ((g2_ending - g2_invested) / g2_invested * 100) if g2_invested > 0 else 0.0

    ticker_payload = {
        "ticker": ticker,
        "ok": True,
        "error": None,
        "asOfDate": as_of_date,
        "asOfPrice": clean_float(last_price),
        "strategies": {
            "proximityDCA": {
                "events": c1,
                "totalInvested": clean_float(g1_invested),
                "endingValue": clean_float(g1_ending),
                "simpleReturnPct": clean_float(g1_return),
                "xirrPct": 0.0,
                "stopLossExits": g1_stop_counts[ticker],
                "profitProtectExits": g1_trail_counts[ticker]
            },
            "guppyProximityDCA": {
                "events": c2,
                "totalInvested": clean_float(g2_invested),
                "endingValue": clean_float(g2_ending),
                "simpleReturnPct": clean_float(g2_return),
                "xirrPct": 0.0,
                "stopLossExits": g2_stop_counts[ticker],
                "profitProtectExits": g2_trail_counts[ticker]
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
        "strategyName": "Proximity-Ranked Weekly OB DCA Engine",
        "note": f"Routes fixed weekly DCA capital dynamically into the universe asset closest to its latest weekly bullish order block. Each week: sells out of any held position that has closed {int(STOP_LOSS_PCT*100)}% or more below the price it was last bought at (stop-loss); sells a position that's up {int(TRAILING_STOP_ARM_PCT*100)}%+ from its last buy price if it then pulls back {int(TRAILING_STOP_PCT*100)}%+ from its post-purchase high (trailing stop, protects profits); and skips a candidate for that week's buy if it already exceeds {int(MAX_POSITION_PCT*100)}% of the strategy's portfolio value, routing capital to the next-best opportunity instead.",
        "riskFreeRatePct": RISK_FREE_RATE_PCT,
        "stopLossPct": STOP_LOSS_PCT * 100,
        "trailingStopArmPct": TRAILING_STOP_ARM_PCT * 100,
        "trailingStopPct": TRAILING_STOP_PCT * 100,
        "maxPositionPct": MAX_POSITION_PCT * 100
    },
    "pooled": {
        "proximityDCA": {
            "events": len(g1_flows),
            "totalInvested": clean_float(g1_total_cost),
            "endingValue": clean_float(g1_end_val),
            "simpleReturnPct": clean_float(((g1_end_val - g1_total_cost) / g1_total_cost * 100) if g1_total_cost else 0.0),
            "xirrPct": clean_float(g1_xirr),
            "stopLossExits": sum(g1_stop_counts.values()),
            "profitProtectExits": sum(g1_trail_counts.values()),
            "cashUninvested": clean_float(g1_cash),
            "sharpeRatio": g1_risk["sharpeRatio"],
            "maxDrawdownPct": g1_risk["maxDrawdownPct"],
            "volatilityPct": g1_risk.get("volatilityPct", 0.0)
        },
        "guppyProximityDCA": {
            "events": len(g2_flows),
            "totalInvested": clean_float(g2_total_cost),
            "endingValue": clean_float(g2_end_val),
            "simpleReturnPct": clean_float(((g2_end_val - g2_total_cost) / g2_total_cost * 100) if g2_total_cost else 0.0),
            "xirrPct": clean_float(g2_xirr),
            "stopLossExits": sum(g2_stop_counts.values()),
            "profitProtectExits": sum(g2_trail_counts.values()),
            "cashUninvested": clean_float(g2_cash),
            "sharpeRatio": g2_risk["sharpeRatio"],
            "maxDrawdownPct": g2_risk["maxDrawdownPct"],
            "volatilityPct": g2_risk.get("volatilityPct", 0.0)
        }
    },
    "tickers": ticker_results_payload
}

output_path = 'public/backtest_data.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(final_json_payload, f, separators=(',', ':')) # Strips structural whitespaces to drop bytes

print(f"Success! Compact, production-ready payload compiled and written to {output_path}")
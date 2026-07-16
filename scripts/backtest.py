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

# A curated set of alternative stop-loss / trailing-stop configurations, backtested
# against the same historical data as the production run so they can be compared
# side by side. Concentration cap is held fixed at MAX_POSITION_PCT throughout, to
# isolate the effect of the exit rules specifically.
EXIT_RULE_SWEEP_CONFIGS = [
    {"name": "No Exit Rules (Buy & Hold)", "stopLossPct": None, "trailArmPct": None, "trailPct": None},
    {"name": "Stop-Loss Only (-10%)", "stopLossPct": 0.10, "trailArmPct": None, "trailPct": None},
    {"name": "Stop-Loss Only (-20%)", "stopLossPct": 0.20, "trailArmPct": None, "trailPct": None},
    {"name": "Stop-Loss Only (-30%)", "stopLossPct": 0.30, "trailArmPct": None, "trailPct": None},
    {"name": "Current (Production)", "stopLossPct": STOP_LOSS_PCT, "trailArmPct": TRAILING_STOP_ARM_PCT, "trailPct": TRAILING_STOP_PCT, "isCurrent": True},
    {"name": "Tight Trail (-20% Stop, Trail +5%/-10%)", "stopLossPct": 0.20, "trailArmPct": 0.05, "trailPct": 0.10},
    {"name": "Loose Trail (-20% Stop, Trail +15%/-25%)", "stopLossPct": 0.20, "trailArmPct": 0.15, "trailPct": 0.25},
    {"name": "Tight Stop + Tight Trail (-10%, +5%/-10%)", "stopLossPct": 0.10, "trailArmPct": 0.05, "trailPct": 0.10},
    {"name": "Loose Stop + Loose Trail (-30%, +15%/-25%)", "stopLossPct": 0.30, "trailArmPct": 0.15, "trailPct": 0.25},
]

# ============================================================================
# 2. FINANCIAL MATH & SIMULATION UTILITIES
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
        return {"sharpeRatio": 0.0, "maxDrawdownPct": clean_float(max_dd * 100), "volatilityPct": 0.0}

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

def build_position_snapshot(ticker, units, price, last_buy, peak, nav, stop_loss_pct, trail_arm_pct, trail_pct):
    """Current status of one currently-held position for the 'this week' watch list:
    how far it is from triggering the stop-loss, and its trailing-stop arm/trigger state."""
    position_value = units * price
    unrealized_pnl_pct = ((price - last_buy) / last_buy * 100) if last_buy else None

    stop_trigger = last_buy * (1 - stop_loss_pct) if (last_buy and stop_loss_pct is not None) else None
    dist_to_stop_pct = ((price - stop_trigger) / price * 100) if stop_trigger and price else None

    arm_price = last_buy * (1 + trail_arm_pct) if (last_buy and trail_arm_pct is not None) else None
    peak_ref = peak if peak is not None else last_buy
    armed = bool(last_buy and arm_price is not None and trail_pct is not None and peak_ref is not None and peak_ref >= arm_price)
    trail_trigger = peak_ref * (1 - trail_pct) if armed else None
    dist_to_trail_pct = ((price - trail_trigger) / price * 100) if trail_trigger and price else None
    dist_to_arm_pct = ((arm_price - price) / price * 100) if (arm_price and not armed and price) else None

    return {
        "ticker": ticker,
        "unitsHeld": clean_float(units),
        "lastBuyPrice": clean_float(last_buy) if last_buy else None,
        "currentPrice": clean_float(price),
        "peakPrice": clean_float(peak_ref) if peak_ref else None,
        "positionValue": clean_float(position_value),
        "positionSharePct": clean_float(position_value / nav * 100) if nav else None,
        "unrealizedPnlPct": clean_float(unrealized_pnl_pct) if unrealized_pnl_pct is not None else None,
        "stopLossTriggerPrice": clean_float(stop_trigger) if stop_trigger else None,
        "distanceToStopLossPct": clean_float(dist_to_stop_pct) if dist_to_stop_pct is not None else None,
        "trailingStopArmed": armed,
        "trailingStopTriggerPrice": clean_float(trail_trigger) if trail_trigger is not None else None,
        "distanceToTrailingStopPct": clean_float(dist_to_trail_pct) if dist_to_trail_pct is not None else None,
        "distanceToArmPct": clean_float(dist_to_arm_pct) if dist_to_arm_pct is not None else None
    }

def run_simulation(weekly_universe, dates_range, tickers, weekly_allocation,
                    stop_loss_pct, trail_arm_pct, trail_pct, max_position_pct, risk_free_rate_pct):
    """Runs the full weekly router simulation -- both the unfiltered ('proximityDCA')
    and Guppy-trend-filtered ('guppyProximityDCA') legs side by side, sharing the same
    exit rules -- for one exit-rule configuration. Pass stop_loss_pct/trail_arm_pct/
    trail_pct as None to disable that rule entirely (e.g. for a buy-and-hold baseline).
    Returns a dict with a full result per leg plus the shared last-known-price map."""
    legs = {}
    for key in ('proximityDCA', 'guppyProximityDCA'):
        legs[key] = {
            'portfolio': {}, 'flows': [], 'dates': [],
            'ticker_counts': {t: 0 for t in tickers},
            'last_buy_price': {}, 'cash': 0.0,
            'realized': {t: 0.0 for t in tickers},
            'stop_counts': {t: 0 for t in tickers},
            'peak_price': {}, 'trail_counts': {t: 0 for t in tickers},
            'nav_series': [], 'last_recommendation': None
        }
    last_known_price = {}

    for current_week in dates_range:
        candidates = {'proximityDCA': [], 'guppyProximityDCA': []}

        for ticker, df in weekly_universe.items():
            wk_idx = df.index.asof(current_week)
            if pd.isna(wk_idx): continue
            row = df.loc[wk_idx]
            price = row['Close']
            last_known_price[ticker] = price

            # --- Weekly exit check: sell out of a held position if it has dipped
            # below the price we last bought it at by stop_loss_pct (hard stop-loss,
            # skipped entirely if stop_loss_pct is None), otherwise track its
            # post-purchase high and sell if it's given back trail_pct of a
            # trail_arm_pct+ gain (trailing stop, protects profits) ---
            for key in ('proximityDCA', 'guppyProximityDCA'):
                leg = legs[key]
                if leg['portfolio'].get(ticker, 0) <= 0:
                    continue
                last_buy = leg['last_buy_price'].get(ticker)
                if stop_loss_pct is not None and last_buy and price <= last_buy * (1 - stop_loss_pct):
                    proceeds = leg['portfolio'][ticker] * price
                    leg['cash'] += proceeds
                    leg['realized'][ticker] += proceeds
                    leg['portfolio'][ticker] = 0.0
                    leg['stop_counts'][ticker] += 1
                    del leg['last_buy_price'][ticker]
                    leg['peak_price'].pop(ticker, None)
                elif last_buy and trail_arm_pct is not None and trail_pct is not None:
                    peak = max(leg['peak_price'].get(ticker, last_buy), price)
                    leg['peak_price'][ticker] = peak
                    if peak >= last_buy * (1 + trail_arm_pct) and price <= peak * (1 - trail_pct):
                        proceeds = leg['portfolio'][ticker] * price
                        leg['cash'] += proceeds
                        leg['realized'][ticker] += proceeds
                        leg['portfolio'][ticker] = 0.0
                        leg['trail_counts'][ticker] += 1
                        del leg['last_buy_price'][ticker]
                        leg['peak_price'].pop(ticker, None)

            if not np.isnan(row['Proximity']):
                candidates['proximityDCA'].append({'ticker': ticker, 'prox': row['Proximity'], 'price': price})
                if row['Guppy_Trend']:
                    candidates['guppyProximityDCA'].append({'ticker': ticker, 'prox': row['Proximity'], 'price': price})

        for key in ('proximityDCA', 'guppyProximityDCA'):
            leg = legs[key]
            nav_pre_buy = leg['cash'] + sum(u * last_known_price.get(t, 0.0) for t, u in leg['portfolio'].items() if u > 0)
            best = pick_best_candidate(candidates[key], leg['portfolio'], nav_pre_buy, max_position_pct)
            leg['last_recommendation'] = best
            if best:
                t = best['ticker']
                leg['portfolio'][t] = leg['portfolio'].get(t, 0) + (weekly_allocation / best['price'])
                leg['ticker_counts'][t] += 1
                leg['last_buy_price'][t] = best['price']
                leg['peak_price'][t] = best['price']
                leg['flows'].append(weekly_allocation)
                leg['dates'].append(current_week)

            nav = leg['cash'] + sum(u * last_known_price.get(t, 0.0) for t, u in leg['portfolio'].items() if u > 0)
            leg['nav_series'].append((current_week, nav))

    end_dt = datetime.now()
    for key in ('proximityDCA', 'guppyProximityDCA'):
        leg = legs[key]
        leg['end_val'] = leg['cash'] + sum(
            units * weekly_universe[t]['Close'].iloc[-1] for t, units in leg['portfolio'].items() if t in weekly_universe
        )
        leg['xirr'] = calculate_xirr(leg['flows'], leg['dates'], leg['end_val'], end_dt)
        leg['risk'] = compute_risk_metrics(leg['nav_series'], dict(zip(leg['dates'], leg['flows'])), risk_free_rate_pct)

    return {'legs': legs, 'last_known_price': last_known_price}

def summarize_leg(leg, weekly_allocation):
    """Pooled-style strategy summary from a run_simulation() leg result."""
    total_cost = len(leg['flows']) * weekly_allocation
    return {
        "events": len(leg['flows']),
        "totalInvested": clean_float(total_cost),
        "endingValue": clean_float(leg['end_val']),
        "simpleReturnPct": clean_float(((leg['end_val'] - total_cost) / total_cost * 100) if total_cost else 0.0),
        "xirrPct": clean_float(leg['xirr']),
        "stopLossExits": sum(leg['stop_counts'].values()),
        "profitProtectExits": sum(leg['trail_counts'].values()),
        "cashUninvested": clean_float(leg['cash']),
        "sharpeRatio": leg['risk']['sharpeRatio'],
        "maxDrawdownPct": leg['risk']['maxDrawdownPct'],
        "volatilityPct": leg['risk'].get('volatilityPct', 0.0)
    }

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
# 4. PRODUCTION RUN (the live config) + EXIT-RULE SWEEP
# ============================================================================
dates_range = pd.date_range(end=datetime.now(), periods=104, freq='W')

sim = run_simulation(weekly_universe, dates_range, TICKERS, WEEKLY_ALLOCATION,
                      STOP_LOSS_PCT, TRAILING_STOP_ARM_PCT, TRAILING_STOP_PCT, MAX_POSITION_PCT, RISK_FREE_RATE_PCT)
g1 = sim['legs']['proximityDCA']
g2 = sim['legs']['guppyProximityDCA']
last_known_price = sim['last_known_price']

print(f"Running exit-rule sweep ({len(EXIT_RULE_SWEEP_CONFIGS)} configurations)...")
exit_rule_sweep_payload = []
for cfg in EXIT_RULE_SWEEP_CONFIGS:
    cfg_sim = run_simulation(weekly_universe, dates_range, TICKERS, WEEKLY_ALLOCATION,
                              cfg['stopLossPct'], cfg['trailArmPct'], cfg['trailPct'], MAX_POSITION_PCT, RISK_FREE_RATE_PCT)
    exit_rule_sweep_payload.append({
        "name": cfg['name'],
        "isCurrent": cfg.get('isCurrent', False),
        "stopLossPct": clean_float(cfg['stopLossPct'] * 100) if cfg['stopLossPct'] is not None else None,
        "trailingStopArmPct": clean_float(cfg['trailArmPct'] * 100) if cfg['trailArmPct'] is not None else None,
        "trailingStopPct": clean_float(cfg['trailPct'] * 100) if cfg['trailPct'] is not None else None,
        "proximityDCA": summarize_leg(cfg_sim['legs']['proximityDCA'], WEEKLY_ALLOCATION),
        "guppyProximityDCA": summarize_leg(cfg_sim['legs']['guppyProximityDCA'], WEEKLY_ALLOCATION)
    })

# ============================================================================
# 5. HIGHLY COMPACT DATA STRUCTURE GENERATION
# ============================================================================
end_dt = datetime.now()

def build_recommendation(rec):
    if not rec:
        return None
    return {"ticker": rec['ticker'], "price": clean_float(rec['price']), "proximityPct": clean_float(rec['prox'])}

g1_positions = sorted([
    build_position_snapshot(t, units, last_known_price.get(t, 0.0), g1['last_buy_price'].get(t), g1['peak_price'].get(t),
                             g1['end_val'], STOP_LOSS_PCT, TRAILING_STOP_ARM_PCT, TRAILING_STOP_PCT)
    for t, units in g1['portfolio'].items() if units > 0
], key=lambda p: p['ticker'])
g2_positions = sorted([
    build_position_snapshot(t, units, last_known_price.get(t, 0.0), g2['last_buy_price'].get(t), g2['peak_price'].get(t),
                             g2['end_val'], STOP_LOSS_PCT, TRAILING_STOP_ARM_PCT, TRAILING_STOP_PCT)
    for t, units in g2['portfolio'].items() if units > 0
], key=lambda p: p['ticker'])

weekly_run_payload = {
    "asOfDate": dates_range[-1].strftime('%Y-%m-%d'),
    "proximityDCA": {
        "recommendedBuy": build_recommendation(g1['last_recommendation']),
        "positions": g1_positions
    },
    "guppyProximityDCA": {
        "recommendedBuy": build_recommendation(g2['last_recommendation']),
        "positions": g2_positions
    }
}

ticker_results_payload = []

for ticker in TICKERS:
    if ticker not in weekly_universe: continue
    df_wk = weekly_universe[ticker]
    if df_wk.empty: continue

    last_price = float(df_wk.iloc[-1]['Close'])
    as_of_date = df_wk.index[-1].strftime('%Y-%m-%d')

    c1 = g1['ticker_counts'][ticker]
    c2 = g2['ticker_counts'][ticker]

    # Ending value = cash already realized from any stop-loss/trailing-stop exits on
    # this ticker, plus whatever units (if any) are still being held at the current close.
    g1_invested = c1 * int(WEEKLY_ALLOCATION)
    g1_ending = g1['realized'][ticker] + g1['portfolio'].get(ticker, 0.0) * last_price
    g1_return = ((g1_ending - g1_invested) / g1_invested * 100) if g1_invested > 0 else 0.0

    g2_invested = c2 * int(WEEKLY_ALLOCATION)
    g2_ending = g2['realized'][ticker] + g2['portfolio'].get(ticker, 0.0) * last_price
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
                "stopLossExits": g1['stop_counts'][ticker],
                "profitProtectExits": g1['trail_counts'][ticker]
            },
            "guppyProximityDCA": {
                "events": c2,
                "totalInvested": clean_float(g2_invested),
                "endingValue": clean_float(g2_ending),
                "simpleReturnPct": clean_float(g2_return),
                "xirrPct": 0.0,
                "stopLossExits": g2['stop_counts'][ticker],
                "profitProtectExits": g2['trail_counts'][ticker]
            }
        }
    }
    ticker_results_payload.append(ticker_payload)

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
        "proximityDCA": summarize_leg(g1, WEEKLY_ALLOCATION),
        "guppyProximityDCA": summarize_leg(g2, WEEKLY_ALLOCATION)
    },
    "tickers": ticker_results_payload,
    "weeklyRun": weekly_run_payload,
    "exitRuleSweep": exit_rule_sweep_payload
}

output_path = 'public/backtest_data.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(final_json_payload, f, separators=(',', ':')) # Strips structural whitespaces to drop bytes

print(f"Success! Compact, production-ready payload compiled and written to {output_path}")

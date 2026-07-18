#!/usr/bin/env python3
import os
import json
import math
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# Reuses the actual LuxAlgo Smart Money Concepts port from engine.py (swing/internal
# structure, BOS/CHoCH-based order block formation, ATR wick handling, mitigation)
# instead of a separate, simplified order-block heuristic -- so the weekly router here
# and the Multi-Stock Dashboard agree on what "closest to a bullish order block" means.
# Works because both scripts live in scripts/ and this is always run as
# `python scripts/backtest.py`, which puts that directory on sys.path.
from engine import compute_structure_series, BIAS_BULLISH

# ============================================================================
# 1. COMPLETE UNIVERSE DEFINITION
# ============================================================================
# Modified sections only - Updated TICKERS list

TICKERS = sorted([
    # Core market ETFs
    'A200.AX','AGVT.AX','ATEC.AX','BNKS.AX','CLDD.AX','CNEW.AX',
    'EDOC.AX','ETHI.AX','FAIR.AX','HACK.AX','HETH.AX','HJPN.AX',
    'HNDQ.AX','NDQ.AX','QAU.AX','QFN.AX','QRE.AX','ROBO.AX',
    'VGS.AX','IVV.AX','WRLD.AX',

    # Thematic ETFs
    'ACDC.AX',

    # Australian blue chips
    'A2M.AX','AGL.AX','ANZ.AX','APA.AX','BHP.AX','BXB.AX',
    'CSL.AX','GMG.AX','JHX.AX','MQG.AX','QAN.AX','QBE.AX',
    'REA.AX','RMD.AX','TLS.AX','WES.AX','WOW.AX',
    'WTC.AX','XRO.AX','CAR.AX','ALL.AX',

    # Resources
    'EVN.AX','GMD.AX','MIN.AX','OBM.AX','RSG.AX',

    # Mid-cap quality/value
    'FCL.AX','JDO.AX','PNI.AX','PPS.AX'
])

BASELINE_TICKERS = sorted([
    'A200.AX','A2M.AX','ACDC.AX','AGL.AX','AGVT.AX','ANZ.AX','APA.AX','ASIA.AX',
    'ATEC.AX','BNKS.AX','EVN.AX','FUEL.AX','GDX.AX','GGUS.AX','GMD.AX','HACK.AX',
    'HJPN.AX','JHX.AX','LNAS.AX','MNRS.AX','NDQ.AX','OOO.AX','QAN.AX','QAU.AX',
    'WTC.AX','XRO.AX','CLDD.AX','CRYP.AX','CNEW.AX','DRIV.AX','EDOC.AX','ERTH.AX',
    'ETHI.AX','FAIR.AX','HNDQ.AX','HETH.AX','QFN.AX','QRE.AX','ROBO.AX','WRLD.AX',
    'SNAS.AX'
])
NEW_TICKERS = sorted([t for t in TICKERS if t not in BASELINE_TICKERS])

# Best-effort manual classification (not authoritative security/GICS data) so exposure
# can be broken down by theme instead of only by individual ticker -- e.g. surfacing
# that several tickers are all gold miners, which move together, rather than reading
# as 6 unrelated small positions. Correlated ETF+equity exposure to the same
# commodity/theme is grouped into one bucket (e.g. gold miner stocks and gold-miner
# ETFs both land in "Gold & Precious Metals") since that's the risk that matters.
TICKER_THEMES = {
    # Gold & precious metals -- individual miners and gold/gold-miner funds alike
    'EVN.AX': 'Gold & Precious Metals', 'GMD.AX': 'Gold & Precious Metals', 'OBM.AX': 'Gold & Precious Metals',
    'RSG.AX': 'Gold & Precious Metals', 'GDX.AX': 'Gold & Precious Metals', 'QAU.AX': 'Gold & Precious Metals',
    # Broad market index funds (AU/US/regional), geared or hedged variants included
    'A200.AX': 'Broad Market Index', 'NDQ.AX': 'Broad Market Index', 'HNDQ.AX': 'Broad Market Index',
    'LNAS.AX': 'Broad Market Index', 'SNAS.AX': 'Broad Market Index',
    'HJPN.AX': 'Broad Market Index', 'CNEW.AX': 'Broad Market Index',
    'WRLD.AX': 'Broad Market Index',
    # Narrower sector/thematic funds (tech, banks, health, ESG, etc.)
    'ATEC.AX': 'Sector & Thematic ETF', 'BNKS.AX': 'Sector & Thematic ETF', 'CLDD.AX': 'Sector & Thematic ETF',
    'HACK.AX': 'Sector & Thematic ETF', 'ROBO.AX': 'Sector & Thematic ETF',
    'ACDC.AX': 'Sector & Thematic ETF', 'EDOC.AX': 'Sector & Thematic ETF',
    'ETHI.AX': 'Sector & Thematic ETF', 'FAIR.AX': 'Sector & Thematic ETF', 'QFN.AX': 'Sector & Thematic ETF',
    'QRE.AX': 'Sector & Thematic ETF', 'FUEL.AX': 'Sector & Thematic ETF',
    # Crypto
    'CRYP.AX': 'Crypto', 'HETH.AX': 'Crypto',
    # Fixed income
    'AGVT.AX': 'Fixed Income',
    # Commodities (non-gold)
    'OOO.AX': 'Commodities',
    # Individual stocks, grouped roughly by what they actually do
    'ANZ.AX': 'Individual Stock - Financials', 'JDO.AX': 'Individual Stock - Financials',
    'PNI.AX': 'Individual Stock - Financials', 'PPS.AX': 'Individual Stock - Financials',
    'QBE.AX': 'Individual Stock - Financials',
    'WTC.AX': 'Individual Stock - Tech', 'XRO.AX': 'Individual Stock - Tech', 'FCL.AX': 'Individual Stock - Tech',
    'A2M.AX': 'Individual Stock - Other', 'AGL.AX': 'Individual Stock - Other', 'APA.AX': 'Individual Stock - Other',
    'JHX.AX': 'Individual Stock - Other', 'QAN.AX': 'Individual Stock - Other',
    # Added 2026-07-16 to plug theme gaps without adding more gold exposure
    'CSL.AX': 'Individual Stock - Healthcare',
    'TLS.AX': 'Individual Stock - Telecom',
    'WOW.AX': 'Individual Stock - Consumer Staples',
    'GMG.AX': 'Individual Stock - Property/REIT',
    'BXB.AX': 'Individual Stock - Industrials',
    'BHP.AX': 'Individual Stock - Resources',
    'WES.AX': 'Individual Stock - Consumer Discretionary',
}

WEEKLY_ALLOCATION = 50.0
BACKTEST_WINDOW_YEARS = 3  # Length of the production ("This Week" / "Backtest Results") window
DATA_HISTORY_YEARS = 6  # Pull extra history beyond the backtest window so the walk-forward sweep has room for older rolling windows
START_DATE = (datetime.now() - timedelta(days=int(DATA_HISTORY_YEARS * 365.25))).strftime('%Y-%m-%d')
STOP_LOSS_PCT = 0.20  # Sell a held position if it closes >= 20% below our last purchase price for it
TRAILING_STOP_ARM_PCT = 0.10  # A position must be up this much from its last buy price before the trailing stop activates
TRAILING_STOP_PCT = 0.15  # Once armed, sell if price pulls back this much from its post-purchase high (protects profits)
MAX_POSITION_PCT = 0.15  # Skip a candidate for this week's buy if it already exceeds this share of the strategy's NAV
RISK_FREE_RATE_PCT = 4.0  # Annualized, used as the Sharpe ratio's baseline (approx. AU cash rate)
CGT_DISCOUNT_HOLD_DAYS = 366  # Defer a profit-take (trailing-stop) exit until a position has been held this long, to
# preserve eligibility for Australia's 50% CGT discount on assets held >12 months. Only gates the trailing stop --
# there's no tax benefit to holding a loss longer, so the (unrelated) hard stop-loss still fires immediately.

# Walk-forward: re-run the same exit-rule sweep over several overlapping historical
# windows (same length as the production window, stepped back 6 months at a time) so
# a config's ranking can be checked for consistency across different market regimes
# instead of trusting a single 3-year backtest. Windows overlap heavily -- they are a
# sensitivity check, not independent trials -- see the UI copy for that caveat.
WALK_FORWARD_WINDOW_WEEKS = BACKTEST_WINDOW_YEARS * 52
WALK_FORWARD_STEP_WEEKS = 26
WALK_FORWARD_WINDOW_COUNT = 8

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

SMA_TREND_WINDOW_WEEKS = 40  # ~200 trading days -- the classic "price above its 200-day
# moving average" trend-following filter, expressed in weekly bars since this router
# operates weekly.

# Every leg runs the identical weekly proximity router, sharing the same exit rules,
# concentration cap, and CGT hold rule -- only the entry confirmation differs. filterColumn
# is a boolean column in weekly_universe that gates candidacy (None = unfiltered, every
# ticker with a valid Proximity is eligible). Adding a new leg is just adding an entry here
# plus the column that computes it in Section 3; every function below reads this list
# instead of hardcoding leg names.
STRATEGY_LEGS = [
    {
        "key": "proximityDCA",
        "label": "Pure Proximity",
        "description": "Unfiltered -- buys whichever candidate is closest to its nearest active bullish order block, no trend confirmation required.",
        "filterColumn": None,
    },
    {
        "key": "guppyProximityDCA",
        "label": "Guppy Filtered",
        "description": "Requires a Guppy multi-EMA stack (short EMA above a rising, stacked long-EMA group) to confirm an established uptrend before entering.",
        "filterColumn": "Guppy_Trend",
    },
    {
        "key": "smaTrendDCA",
        "label": "200-Day Trend Filtered",
        "description": "Requires price to be trading above its own 40-week (~200-day) moving average -- the classic trend-following rule (\"never buy below the 200-day MA\") many professional trend-followers use to avoid entering during a primary downtrend.",
        "filterColumn": "Sma_Trend",
    },
    {
        "key": "structureFilteredDCA",
        "label": "Bullish Structure Filtered",
        "description": "Requires the SMC swing market structure itself (higher highs / higher lows, from engine.py's own structure detection) to be bullish before entering -- a market-structure confirmation professional/discretionary SMC traders check before taking a long-term position.",
        "filterColumn": "Structure_Trend",
    },
]
LEG_KEYS = [leg["key"] for leg in STRATEGY_LEGS]
LEG_FILTER_COLUMNS = {leg["key"]: leg["filterColumn"] for leg in STRATEGY_LEGS}

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
    """Best (smallest-distance-to-order-block) candidate whose existing position doesn't
    already exceed max_position_pct of NAV -- forces rotation into the next-best
    opportunity instead of endlessly concentrating in a single already-large holding.
    Ranked by abs(prox): prox comes from engine.py's zone_from_order_block(), which is
    already an unsigned distance (0 when price is inside the block's high/low range), so
    prox is never negative in practice -- but ranking by absolute value keeps that the
    explicit contract rather than an incidental side effect of whatever produced prox.
    A signed min() here previously (before reusing engine.py's SMC detection) mistook
    "crashed furthest below a dead order block" for "closest to one."""
    if not candidates:
        return None
    if nav_now <= 0:
        eligible = candidates
    else:
        eligible = [c for c in candidates if portfolio.get(c['ticker'], 0.0) * c['price'] <= max_position_pct * nav_now]
    if not eligible:
        return None
    return min(eligible, key=lambda x: abs(x['prox']))

def build_position_snapshot(ticker, units, price, last_buy, peak, nav, stop_loss_pct, trail_arm_pct, trail_pct,
                             last_buy_date=None, as_of_date=None, cgt_hold_days=None):
    """Current status of one currently-held position for the 'this week' watch list:
    how far it is from triggering the stop-loss, its trailing-stop arm/trigger state, and
    (if last_buy_date/as_of_date/cgt_hold_days are supplied) its CGT-discount holding status."""
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

    days_held = (as_of_date - last_buy_date).days if (last_buy_date is not None and as_of_date is not None) else None
    cgt_eligible_date = (last_buy_date + timedelta(days=cgt_hold_days)) if (last_buy_date is not None and cgt_hold_days is not None) else None
    cgt_discount_eligible = (days_held is not None and cgt_hold_days is not None and days_held >= cgt_hold_days) if cgt_hold_days is not None else None
    # True when the trailing-stop condition is currently met but held back specifically because
    # selling now would forfeit the CGT discount -- a real tax-vs-downside-risk tradeoff, not a free lunch.
    profit_take_held_for_cgt = bool(
        armed and trail_trigger is not None and price <= trail_trigger and cgt_discount_eligible is False
    )

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
        "distanceToArmPct": clean_float(dist_to_arm_pct) if dist_to_arm_pct is not None else None,
        "daysHeld": days_held,
        "cgtEligibleDate": cgt_eligible_date.strftime('%Y-%m-%d') if cgt_eligible_date is not None else None,
        "cgtDiscountEligible": cgt_discount_eligible,
        "profitTakeHeldForCgt": profit_take_held_for_cgt
    }

def run_simulation(weekly_universe, dates_range, tickers, weekly_allocation,
                    stop_loss_pct, trail_arm_pct, trail_pct, max_position_pct, risk_free_rate_pct,
                    cgt_hold_days=None, leg_filter_columns=None):
    """Runs the full weekly router simulation -- every leg in leg_filter_columns (default
    STRATEGY_LEGS/LEG_FILTER_COLUMNS) side by side, sharing the same exit rules -- for one
    exit-rule configuration. Each leg requires its own filterColumn (a boolean column in
    weekly_universe) to be true for a candidate to be eligible that week; None means
    unfiltered. Pass stop_loss_pct/trail_arm_pct/trail_pct as None to disable that rule
    entirely (e.g. for a buy-and-hold baseline). cgt_hold_days, if set, defers a
    trailing-stop (profit-take) exit until the position has been held that long -- the hard
    stop-loss is never gated, since there's no CGT-discount incentive to hold a loss longer.
    Returns a dict with a full result per leg plus the shared last-known-price map."""
    if leg_filter_columns is None:
        leg_filter_columns = LEG_FILTER_COLUMNS
    leg_keys = list(leg_filter_columns.keys())

    legs = {}
    for key in leg_keys:
        legs[key] = {
            'portfolio': {}, 'flows': [], 'dates': [],
            'ticker_counts': {t: 0 for t in tickers},
            'last_buy_price': {}, 'last_buy_date': {}, 'cash': 0.0,
            'realized': {t: 0.0 for t in tickers},
            'stop_counts': {t: 0 for t in tickers},
            'peak_price': {}, 'trail_counts': {t: 0 for t in tickers},
            'cgt_deferred_counts': {t: 0 for t in tickers},
            'nav_series': [], 'last_recommendation': None
        }
    last_known_price = {}

    for current_week in dates_range:
        candidates = {key: [] for key in leg_keys}

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
            for key in leg_keys:
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
                    leg['last_buy_date'].pop(ticker, None)
                    leg['peak_price'].pop(ticker, None)
                elif last_buy and trail_arm_pct is not None and trail_pct is not None:
                    peak = max(leg['peak_price'].get(ticker, last_buy), price)
                    leg['peak_price'][ticker] = peak
                    if peak >= last_buy * (1 + trail_arm_pct) and price <= peak * (1 - trail_pct):
                        buy_date = leg['last_buy_date'].get(ticker)
                        days_held = (current_week - buy_date).days if buy_date is not None else None
                        cgt_cleared = cgt_hold_days is None or days_held is None or days_held >= cgt_hold_days
                        if cgt_cleared:
                            proceeds = leg['portfolio'][ticker] * price
                            leg['cash'] += proceeds
                            leg['realized'][ticker] += proceeds
                            leg['portfolio'][ticker] = 0.0
                            leg['trail_counts'][ticker] += 1
                            del leg['last_buy_price'][ticker]
                            leg['last_buy_date'].pop(ticker, None)
                            leg['peak_price'].pop(ticker, None)
                        else:
                            leg['cgt_deferred_counts'][ticker] += 1

            if not np.isnan(row['Proximity']):
                inside_zone = bool(row.get('InsideZone', False))
                for key in leg_keys:
                    filter_col = leg_filter_columns[key]
                    if filter_col is None or bool(row.get(filter_col, False)):
                        candidates[key].append({'ticker': ticker, 'prox': row['Proximity'], 'price': price, 'insideZone': inside_zone})

        for key in leg_keys:
            leg = legs[key]
            nav_pre_buy = leg['cash'] + sum(u * last_known_price.get(t, 0.0) for t, u in leg['portfolio'].items() if u > 0)
            best = pick_best_candidate(candidates[key], leg['portfolio'], nav_pre_buy, max_position_pct)
            leg['last_recommendation'] = best
            if best:
                t = best['ticker']
                leg['portfolio'][t] = leg['portfolio'].get(t, 0) + (weekly_allocation / best['price'])
                leg['ticker_counts'][t] += 1
                leg['last_buy_price'][t] = best['price']
                leg['last_buy_date'][t] = current_week
                leg['peak_price'][t] = best['price']
                leg['flows'].append(weekly_allocation)
                leg['dates'].append(current_week)

            nav = leg['cash'] + sum(u * last_known_price.get(t, 0.0) for t, u in leg['portfolio'].items() if u > 0)
            leg['nav_series'].append((current_week, nav))

    # Mark-to-market and discount as of the WINDOW's own last date, not "now" -- for the
    # production window (ending today) these are the same thing, but a walk-forward
    # window ending in the past must be valued using its own end-of-period prices, or
    # every historical window would be silently marked to today's price instead.
    end_dt = dates_range[-1]
    for key in leg_keys:
        leg = legs[key]
        leg['end_val'] = leg['cash'] + sum(
            units * last_known_price.get(t, 0.0) for t, units in leg['portfolio'].items() if units > 0
        )
        leg['xirr'] = calculate_xirr(leg['flows'], leg['dates'], leg['end_val'], end_dt)
        leg['risk'] = compute_risk_metrics(leg['nav_series'], dict(zip(leg['dates'], leg['flows'])), risk_free_rate_pct)

    return {'legs': legs, 'last_known_price': last_known_price}

def summarize_leg(leg, weekly_allocation):
    """Pooled-style strategy summary from a run_simulation() leg result."""
    total_cost = len(leg['flows']) * weekly_allocation
    max_dd = leg['risk']['maxDrawdownPct']
    # Calmar ratio: annualized return per unit of worst-case pain (peak-to-trough
    # decline), as opposed to Sharpe's per-unit-of-volatility -- two drawdown-sized
    # configs with identical Sharpe can have very different Calmar ratios if one's
    # volatility is smooth chop and the other's is one big drawdown.
    calmar_ratio = (leg['xirr'] / abs(max_dd)) if max_dd != 0 else 0.0
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
        "maxDrawdownPct": max_dd,
        "volatilityPct": leg['risk'].get('volatilityPct', 0.0),
        "calmarRatio": clean_float(calmar_ratio),
        "cgtDeferredCount": sum(leg['cgt_deferred_counts'].values())
    }

def generate_walk_forward_windows(end_dt, window_weeks, step_weeks, count):
    """`count` windows of `window_weeks` length, each stepped back `step_weeks` from
    the previous, returned oldest-first with a 1-indexed windowNumber for display."""
    windows = []
    for i in range(count):
        window_end = end_dt - timedelta(weeks=step_weeks * i)
        dr = pd.date_range(end=window_end, periods=window_weeks, freq='W')
        windows.append({'startDate': dr[0], 'endDate': dr[-1], 'dates_range': dr})
    windows.reverse()
    for idx, w in enumerate(windows):
        w['windowNumber'] = idx + 1
    return windows

def aggregate_window_results(window_results):
    """Mean/spread/best/worst across a config's per-window summarize_leg() results,
    skipping any window where nothing was ever bought (no signal existed that far
    back for this universe -- not a 0% result, just no test)."""
    valid = [w for w in window_results if w['totalInvested'] > 0]
    if not valid:
        return None
    returns = [w['simpleReturnPct'] for w in valid]
    xirrs = [w['xirrPct'] for w in valid]
    sharpes = [w['sharpeRatio'] for w in valid]
    calmars = [w['calmarRatio'] for w in valid]
    mean_return = float(np.mean(returns))
    std_return = float(np.std(returns, ddof=1)) if len(returns) > 1 else 0.0
    win_rate = sum(1 for r in returns if r > 0) / len(returns) * 100
    # "Consistency" reward: high average return penalized by how much it swings
    # window to window -- a Sharpe-like ratio applied across regimes rather than
    # within one time series. Falls back to the mean when there's no spread to divide by.
    consistency_score = (mean_return / std_return) if std_return > 0 else mean_return
    return {
        "windowsTested": len(valid),
        "meanReturnPct": clean_float(mean_return),
        "stdReturnPct": clean_float(std_return),
        "minReturnPct": clean_float(min(returns)),
        "maxReturnPct": clean_float(max(returns)),
        "meanXirrPct": clean_float(float(np.mean(xirrs))),
        "meanSharpeRatio": clean_float(float(np.mean(sharpes))),
        "meanCalmarRatio": clean_float(float(np.mean(calmars))),
        "winRatePct": clean_float(win_rate),
        "consistencyScore": clean_float(consistency_score),
        "perWindow": valid
    }

def run_walk_forward_sweep(weekly_universe, tickers, windows, configs, weekly_allocation, max_position_pct, risk_free_rate_pct, cgt_hold_days=None, leg_filter_columns=None):
    """Every config in `configs` re-run over every window in `windows`, against
    `weekly_universe`/`tickers` -- the same shape whether that's the full universe or
    a restricted subset, so results from two different universes over the same windows
    can be compared directly."""
    if leg_filter_columns is None:
        leg_filter_columns = LEG_FILTER_COLUMNS
    leg_keys = list(leg_filter_columns.keys())

    wf_raw = {cfg['name']: {key: [] for key in leg_keys} for cfg in configs}
    for win in windows:
        for cfg in configs:
            win_sim = run_simulation(weekly_universe, win['dates_range'], tickers, weekly_allocation,
                                      cfg['stopLossPct'], cfg['trailArmPct'], cfg['trailPct'], max_position_pct, risk_free_rate_pct,
                                      cgt_hold_days, leg_filter_columns)
            for key in leg_keys:
                row = summarize_leg(win_sim['legs'][key], weekly_allocation)
                row['windowNumber'] = win['windowNumber']
                row['startDate'] = win['startDate'].strftime('%Y-%m-%d')
                row['endDate'] = win['endDate'].strftime('%Y-%m-%d')
                wf_raw[cfg['name']][key].append(row)

    return {
        "windowYears": BACKTEST_WINDOW_YEARS,
        "windowCount": len(windows),
        "stepWeeks": WALK_FORWARD_STEP_WEEKS,
        "tickerCount": len(tickers),
        "windows": [
            {"windowNumber": w['windowNumber'], "startDate": w['startDate'].strftime('%Y-%m-%d'), "endDate": w['endDate'].strftime('%Y-%m-%d')}
            for w in windows
        ],
        "configs": [
            {
                "name": cfg['name'],
                "isCurrent": cfg.get('isCurrent', False),
                "stopLossPct": clean_float(cfg['stopLossPct'] * 100) if cfg['stopLossPct'] is not None else None,
                "trailingStopArmPct": clean_float(cfg['trailArmPct'] * 100) if cfg['trailArmPct'] is not None else None,
                "trailingStopPct": clean_float(cfg['trailPct'] * 100) if cfg['trailPct'] is not None else None,
                **{key: aggregate_window_results(wf_raw[cfg['name']][key]) for key in leg_keys}
            }
            for cfg in configs
        ]
    }

# ============================================================================
# 3. BULK DATA DOWNLOAD & SNAPSHOT CONVERSION
# ============================================================================
print(f"Loading {len(TICKERS)} tickers across past {DATA_HISTORY_YEARS} years to build weekly buffers...")
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
    if len(df_wk) < 10: continue

    # Nearest active (unmitigated) bullish order block, per week, via engine.py's actual
    # SMC structure detection -- same algorithm the Multi-Stock Dashboard's Weekly
    # timeframe uses, run here over this ticker's own weekly-resampled bars rather than
    # a fresh yfinance weekly fetch, since this script already pulls+resamples daily data
    # in bulk for all tickers in one call. distancePct from zone_from_order_block() is
    # already an unsigned distance (0 when price is inside the block's high/low range),
    # so no sign-convention bug is possible here the way the old single-level heuristic had.
    structure_series = compute_structure_series(df_wk)
    df_wk['Proximity'] = [
        (bar.bullish_zones[0]['distancePct'] if bar.bullish_zones else np.nan)
        for bar in structure_series
    ]
    df_wk['InsideZone'] = [
        (bool(bar.bullish_zones[0]['insideZone']) if bar.bullish_zones else False)
        for bar in structure_series
    ]
    # Bullish Structure Filtered leg: requires the SMC swing structure itself (higher
    # highs / higher lows) to be bullish, straight from the same structure_series used
    # for Proximity above -- a market-structure confirmation, not a moving-average one.
    df_wk['Structure_Trend'] = [bar.swing_trend == BIAS_BULLISH for bar in structure_series]
    # 200-Day Trend Filtered leg: price above its own 40-week (~200-day) moving average.
    # Comparing against NaN (the first SMA_TREND_WINDOW_WEEKS-1 bars, before the rolling
    # window has enough history) evaluates to False, so those weeks are naturally excluded
    # rather than raising.
    df_wk['Sma_Trend'] = df_wk['Close'] > df_wk['Close'].rolling(window=SMA_TREND_WINDOW_WEEKS).mean()
    df_wk['Guppy_Trend'] = False

    for i in range(2, len(df_wk)):
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
# 4. PRODUCTION RUN (the live config) + EXIT-RULE SWEEP + WALK-FORWARD SWEEP
# ============================================================================
dates_range = pd.date_range(end=datetime.now(), periods=BACKTEST_WINDOW_YEARS * 52, freq='W')

sim = run_simulation(weekly_universe, dates_range, TICKERS, WEEKLY_ALLOCATION,
                      STOP_LOSS_PCT, TRAILING_STOP_ARM_PCT, TRAILING_STOP_PCT, MAX_POSITION_PCT, RISK_FREE_RATE_PCT,
                      CGT_DISCOUNT_HOLD_DAYS)
last_known_price = sim['last_known_price']

print(f"Running exit-rule sweep ({len(EXIT_RULE_SWEEP_CONFIGS)} configurations)...")
exit_rule_sweep_payload = []
for cfg in EXIT_RULE_SWEEP_CONFIGS:
    cfg_sim = run_simulation(weekly_universe, dates_range, TICKERS, WEEKLY_ALLOCATION,
                              cfg['stopLossPct'], cfg['trailArmPct'], cfg['trailPct'], MAX_POSITION_PCT, RISK_FREE_RATE_PCT,
                              CGT_DISCOUNT_HOLD_DAYS)
    exit_rule_sweep_payload.append({
        "name": cfg['name'],
        "isCurrent": cfg.get('isCurrent', False),
        "stopLossPct": clean_float(cfg['stopLossPct'] * 100) if cfg['stopLossPct'] is not None else None,
        "trailingStopArmPct": clean_float(cfg['trailArmPct'] * 100) if cfg['trailArmPct'] is not None else None,
        "trailingStopPct": clean_float(cfg['trailPct'] * 100) if cfg['trailPct'] is not None else None,
        **{key: summarize_leg(cfg_sim['legs'][key], WEEKLY_ALLOCATION) for key in LEG_KEYS}
    })

walk_forward_windows = generate_walk_forward_windows(datetime.now(), WALK_FORWARD_WINDOW_WEEKS, WALK_FORWARD_STEP_WEEKS, WALK_FORWARD_WINDOW_COUNT)
print(f"Running walk-forward sweep ({len(walk_forward_windows)} windows x {len(EXIT_RULE_SWEEP_CONFIGS)} configurations)...")
walk_forward_payload = run_walk_forward_sweep(weekly_universe, TICKERS, walk_forward_windows, EXIT_RULE_SWEEP_CONFIGS,
                                               WEEKLY_ALLOCATION, MAX_POSITION_PCT, RISK_FREE_RATE_PCT, CGT_DISCOUNT_HOLD_DAYS)

# Same windows, same configs, but restricted to the universe as it stood before the
# top-value-stocks (mostly gold miner) expansion -- isolates how much of the recent
# windows' outperformance is those new tickers riding a sector rally vs. the base
# strategy, by comparing this against walk_forward_payload above.
baseline_weekly_universe = {t: df for t, df in weekly_universe.items() if t in BASELINE_TICKERS}
print(f"Running walk-forward sweep on baseline universe ({len(baseline_weekly_universe)} tickers, pre-expansion)...")
walk_forward_baseline_payload = run_walk_forward_sweep(baseline_weekly_universe, BASELINE_TICKERS, walk_forward_windows, EXIT_RULE_SWEEP_CONFIGS,
                                                        WEEKLY_ALLOCATION, MAX_POSITION_PCT, RISK_FREE_RATE_PCT, CGT_DISCOUNT_HOLD_DAYS)

# ============================================================================
# 5. HIGHLY COMPACT DATA STRUCTURE GENERATION
# ============================================================================
end_dt = datetime.now()

def build_recommendation(rec):
    if not rec:
        return None
    return {
        "ticker": rec['ticker'],
        "price": clean_float(rec['price']),
        "proximityPct": clean_float(rec['prox']),
        "insideZone": bool(rec.get('insideZone', False))
    }

def build_leg_positions(leg):
    return sorted([
        build_position_snapshot(t, units, last_known_price.get(t, 0.0), leg['last_buy_price'].get(t), leg['peak_price'].get(t),
                                 leg['end_val'], STOP_LOSS_PCT, TRAILING_STOP_ARM_PCT, TRAILING_STOP_PCT,
                                 leg['last_buy_date'].get(t), dates_range[-1], CGT_DISCOUNT_HOLD_DAYS)
        for t, units in leg['portfolio'].items() if units > 0
    ], key=lambda p: p['ticker'])

weekly_run_payload = {
    "asOfDate": dates_range[-1].strftime('%Y-%m-%d'),
    **{
        key: {
            "recommendedBuy": build_recommendation(sim['legs'][key]['last_recommendation']),
            "positions": build_leg_positions(sim['legs'][key])
        }
        for key in LEG_KEYS
    }
}

ticker_results_payload = []

for ticker in TICKERS:
    if ticker not in weekly_universe: continue
    df_wk = weekly_universe[ticker]
    if df_wk.empty: continue

    last_price = float(df_wk.iloc[-1]['Close'])
    as_of_date = df_wk.index[-1].strftime('%Y-%m-%d')

    strategies_payload = {}
    for key in LEG_KEYS:
        leg = sim['legs'][key]
        count = leg['ticker_counts'][ticker]
        # Ending value = cash already realized from any stop-loss/trailing-stop exits on
        # this ticker, plus whatever units (if any) are still being held at the current close.
        invested = count * int(WEEKLY_ALLOCATION)
        ending = leg['realized'][ticker] + leg['portfolio'].get(ticker, 0.0) * last_price
        ret = ((ending - invested) / invested * 100) if invested > 0 else 0.0
        strategies_payload[key] = {
            "events": count,
            "totalInvested": clean_float(invested),
            "endingValue": clean_float(ending),
            "simpleReturnPct": clean_float(ret),
            "xirrPct": 0.0,
            "stopLossExits": leg['stop_counts'][ticker],
            "profitProtectExits": leg['trail_counts'][ticker]
        }

    ticker_payload = {
        "ticker": ticker,
        "ok": True,
        "error": None,
        "asOfDate": as_of_date,
        "asOfPrice": clean_float(last_price),
        "strategies": strategies_payload
    }
    ticker_results_payload.append(ticker_payload)

def compute_theme_exposure(ticker_payloads, strategy_key, window_years):
    """Per-theme breakdown (grouped by TICKER_THEMES) of $ invested, ending value, $/%
    gain, and an annualized $/year figure, for one strategy leg. Ending values per ticker
    already account for both currently-held value and realized stop-loss/trailing-stop
    proceeds, and sum exactly to that leg's total ending value, so endingValue shares add
    to 100%. A theme is only included if this leg actually bought into it (investedValue >
    0) -- a theme none of whose tickers this leg ever traded contributes nothing to compare.
    annualGainValue is gainValue / window_years -- a simple average, not a compounding
    (XIRR-style) figure, since that would need per-theme weekly cash-flow tracking; treat
    it as "dollars of profit per year on average over this window," not a growth rate."""
    totals = {}
    for tp in ticker_payloads:
        s = tp['strategies'][strategy_key]
        invested = s['totalInvested']
        if invested <= 0:
            continue
        theme = TICKER_THEMES.get(tp['ticker'], 'Other')
        totals.setdefault(theme, {'value': 0.0, 'invested': 0.0, 'tickers': []})
        totals[theme]['value'] += s['endingValue']
        totals[theme]['invested'] += invested
        totals[theme]['tickers'].append(tp['ticker'])

    grand_total = sum(t['value'] for t in totals.values())
    rows = []
    for theme, t in totals.items():
        gain = t['value'] - t['invested']
        rows.append({
            "theme": theme,
            "investedValue": clean_float(t['invested']),
            "endingValue": clean_float(t['value']),
            "gainValue": clean_float(gain),
            "returnPct": clean_float(gain / t['invested'] * 100) if t['invested'] else 0.0,
            "annualGainValue": clean_float(gain / window_years) if window_years else 0.0,
            "sharePct": clean_float(t['value'] / grand_total * 100) if grand_total else 0.0,
            "tickers": sorted(t['tickers'])
        })
    rows.sort(key=lambda r: r['sharePct'], reverse=True)
    return rows

theme_exposure_payload = {
    key: compute_theme_exposure(ticker_results_payload, key, BACKTEST_WINDOW_YEARS)
    for key in LEG_KEYS
}

final_json_payload = {
    "generatedAt": end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
    "meta": {
        "universe": TICKERS,
        "newTickers": NEW_TICKERS,
        "baselineUniverse": BASELINE_TICKERS,
        "windowYears": BACKTEST_WINDOW_YEARS,
        "amountPerWeek": int(WEEKLY_ALLOCATION),
        "strategyName": "Proximity-Ranked Weekly OB DCA Engine",
        "note": f"Routes fixed weekly DCA capital dynamically into the universe asset closest to its nearest active (unmitigated) weekly bullish order block. Each week: sells out of any held position that has closed {int(STOP_LOSS_PCT*100)}% or more below the price it was last bought at (stop-loss); sells a position that's up {int(TRAILING_STOP_ARM_PCT*100)}%+ from its last buy price if it then pulls back {int(TRAILING_STOP_PCT*100)}%+ from its post-purchase high (trailing stop, protects profits, deferred until it's been held over {CGT_DISCOUNT_HOLD_DAYS} days to preserve the AU 12-month CGT discount); and skips a candidate for that week's buy if it already exceeds {int(MAX_POSITION_PCT*100)}% of the strategy's portfolio value, routing capital to the next-best opportunity instead.",
        "riskFreeRatePct": RISK_FREE_RATE_PCT,
        "stopLossPct": STOP_LOSS_PCT * 100,
        "trailingStopArmPct": TRAILING_STOP_ARM_PCT * 100,
        "trailingStopPct": TRAILING_STOP_PCT * 100,
        "maxPositionPct": MAX_POSITION_PCT * 100,
        "cgtDiscountHoldDays": CGT_DISCOUNT_HOLD_DAYS,
        "strategyLegs": [{"key": leg["key"], "label": leg["label"], "description": leg["description"]} for leg in STRATEGY_LEGS]
    },
    "pooled": {key: summarize_leg(sim['legs'][key], WEEKLY_ALLOCATION) for key in LEG_KEYS},
    "tickers": ticker_results_payload,
    "weeklyRun": weekly_run_payload,
    "exitRuleSweep": exit_rule_sweep_payload,
    "walkForward": walk_forward_payload,
    "walkForwardBaseline": walk_forward_baseline_payload,
    "themeExposure": theme_exposure_payload
}

output_path = 'public/backtest_data.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w') as f:
    json.dump(final_json_payload, f, separators=(',', ':')) # Strips structural whitespaces to drop bytes

print(f"Success! Compact, production-ready payload compiled and written to {output_path}")

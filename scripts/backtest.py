"""Retrace-to-weekly-order-block backtest.

Tests whether buying $100 every time price first retraces into a weekly
bullish order block beats two dollar-cost-averaging baselines (fixed
weekday, random weekday) and a lump-sum buy-and-hold, over the trailing
WINDOW_YEARS. All strategies are pure accumulate-and-hold: no stop-loss,
no selling -- every $100 buy is held to the last available close.

Both weekly structure types are tracked: *internal* (5-bar, ~5 weeks,
frequent) and *swing* (50-bar, ~1 year, rare). Three retrace strategies
are reported: "retrace" (either kind -- the primary, highest-power
signal), "retraceSwing", and "retraceInternal", so the swing-only result
stays directly comparable to earlier runs.

Reuses engine.py's fetch_history/compute_legs/wilder_atr/pick_order_block
(the exact anchor-selection and pivot-detection logic already fixed and
verified there) rather than re-deriving structure logic independently.
"""
from __future__ import annotations

import json
import random
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

WINDOW_YEARS = 2
AMOUNT_PER_EVENT = 100.0
RANDOM_SEED = 42
FIXED_WEEKDAY = 0  # Monday
FIXED_WEEKDAY_LABEL = "Monday"

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "public" / "backtest_data.json"


@dataclass
class Formation:
    kind: str  # "internal" or "swing"
    formed_index: int
    formed_date: str
    top: float
    bottom: float
    ob_date: str
    retrace_date: pd.Timestamp | None = None
    retrace_price: float | None = None


def strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df = df.copy()
        df.index = df.index.tz_localize(None)
    return df


def compute_bullish_formations(weekly_df: pd.DataFrame) -> list[Formation]:
    """Every weekly bullish order block ever formed (internal and swing), with its first retrace.

    Mirrors engine.process_timeframe's dual internal/swing structure loop
    (see engine.py) -- pivot detection and order-block anchor selection are
    reused directly via engine.compute_legs / engine.pick_order_block so
    that logic can't drift between the live dashboard and this backtest.
    Internal breaks that coincide with the current swing level are skipped,
    matching the source indicator's own extraCondition (avoids double
    counting the same structural point as both internal and swing).
    """
    high = weekly_df["High"].to_numpy()
    low = weekly_df["Low"].to_numpy()
    close = weekly_df["Close"].to_numpy()
    times = weekly_df.index
    n = len(weekly_df)
    if n < engine.SWING_LENGTH + 5:
        raise ValueError(f"Not enough weekly history ({n} bars)")

    atr = engine.wilder_atr(high, low, close, engine.ATR_LENGTH)
    bar_range = high - low
    high_vol = np.where(np.isnan(atr), False, bar_range >= 2 * np.nan_to_num(atr))
    parsed_high = np.where(high_vol, low, high)
    parsed_low = np.where(high_vol, high, low)

    swing_legs = engine.compute_legs(high, low, engine.SWING_LENGTH)
    internal_legs = engine.compute_legs(high, low, engine.INTERNAL_LENGTH)

    swing_high, swing_low = engine.Pivot(), engine.Pivot()
    internal_high, internal_low = engine.Pivot(), engine.Pivot()

    def update_pivot(i: int, size: int, legs: np.ndarray, high_pivot: engine.Pivot, low_pivot: engine.Pivot) -> None:
        if i < size or legs[i] == legs[i - 1]:
            return
        src_idx = i - size
        if legs[i] == engine.LEG_BULLISH:
            low_pivot.level = float(low[src_idx])
            low_pivot.bar_index = src_idx
            low_pivot.crossed = False
        else:
            high_pivot.level = float(high[src_idx])
            high_pivot.bar_index = src_idx
            high_pivot.crossed = False

    formations: list[Formation] = []

    for i in range(1, n):
        swing_high_prev, swing_low_prev = swing_high.level, swing_low.level
        internal_high_prev, internal_low_prev = internal_high.level, internal_low.level

        update_pivot(i, engine.SWING_LENGTH, swing_legs, swing_high, swing_low)
        update_pivot(i, engine.INTERNAL_LENGTH, internal_legs, internal_high, internal_low)

        if (
            swing_high.bar_index >= 0
            and not swing_high.crossed
            and close[i - 1] <= swing_high_prev
            and close[i] > swing_high.level
        ):
            swing_high.crossed = True
            ob = engine.pick_order_block(high, low, parsed_high, parsed_low, times, swing_high.bar_index, i, engine.BIAS_BULLISH)
            formations.append(Formation(kind="swing", formed_index=i, formed_date=str(times[i].date()), top=ob.bar_high, bottom=ob.bar_low, ob_date=ob.bar_time))

        if (
            swing_low.bar_index >= 0
            and not swing_low.crossed
            and close[i - 1] >= swing_low_prev
            and close[i] < swing_low.level
        ):
            swing_low.crossed = True
            # Bearish order blocks aren't used by this backtest.

        if (
            internal_high.bar_index >= 0
            and not internal_high.crossed
            and internal_high.level != swing_high.level
            and close[i - 1] <= internal_high_prev
            and close[i] > internal_high.level
        ):
            internal_high.crossed = True
            ob = engine.pick_order_block(high, low, parsed_high, parsed_low, times, internal_high.bar_index, i, engine.BIAS_BULLISH)
            formations.append(Formation(kind="internal", formed_index=i, formed_date=str(times[i].date()), top=ob.bar_high, bottom=ob.bar_low, ob_date=ob.bar_time))

        if (
            internal_low.bar_index >= 0
            and not internal_low.crossed
            and close[i - 1] >= internal_low_prev
            and close[i] < internal_low.level
        ):
            internal_low.crossed = True

    # First retrace: the first bar strictly after formation whose low wicks
    # back into the zone (low <= top). The zone isn't "live" to trade until
    # the bar after it forms.
    for f in formations:
        for j in range(f.formed_index + 1, n):
            if low[j] <= f.top:
                f.retrace_date = times[j]
                f.retrace_price = float(close[j])
                break

    return formations


def nearest_trading_day_on_or_after(daily_df: pd.DataFrame, target: pd.Timestamp) -> pd.Timestamp | None:
    idx = daily_df.index
    pos = idx.searchsorted(target)
    if pos >= len(idx):
        return None
    return idx[pos]


def xirr(cashflows: list[tuple[pd.Timestamp, float]]) -> float | None:
    """Annualized money-weighted return (%) via bisection. None if unsolvable."""
    if len(cashflows) < 2:
        return None
    amounts = [a for _, a in cashflows]
    if all(a <= 0 for a in amounts) or all(a >= 0 for a in amounts):
        return None
    t0 = min(d for d, _ in cashflows)

    def npv(rate: float) -> float:
        return sum(a / ((1 + rate) ** ((d - t0).days / 365.0)) for d, a in cashflows)

    lo, hi = -0.9999, 20.0
    npv_lo, npv_hi = npv(lo), npv(hi)
    if npv_lo * npv_hi > 0:
        return None
    mid = lo
    for _ in range(200):
        mid = (lo + hi) / 2
        npv_mid = npv(mid)
        if abs(npv_mid) < 1e-6:
            break
        if npv_lo * npv_mid < 0:
            hi = mid
        else:
            lo, npv_lo = mid, npv_mid
    return mid * 100


def summarize(events: list[dict], as_of_date: pd.Timestamp, as_of_price: float) -> dict:
    if not events:
        return {"events": 0, "totalInvested": 0.0, "endingValue": 0.0, "simpleReturnPct": None, "xirrPct": None}
    units = sum(AMOUNT_PER_EVENT / e["price"] for e in events)
    total_invested = AMOUNT_PER_EVENT * len(events)
    ending_value = units * as_of_price
    cashflows = [(e["date"], -AMOUNT_PER_EVENT) for e in events] + [(as_of_date, ending_value)]
    r = xirr(cashflows)
    return {
        "events": len(events),
        "totalInvested": round(total_invested, 2),
        "endingValue": round(ending_value, 2),
        "simpleReturnPct": round((ending_value / total_invested - 1) * 100, 2),
        "xirrPct": round(r, 2) if r is not None else None,
    }


RETRACE_STRATEGY_KEYS = ("retrace", "retraceSwing", "retraceInternal")


def backtest_ticker(ticker: str, rng: random.Random) -> tuple[dict, dict[str, list[dict]]]:
    weekly_df = strip_tz(engine.fetch_history(ticker, "1wk"))
    daily_df = strip_tz(engine.fetch_history(ticker, "1d"))

    formations = compute_bullish_formations(weekly_df)

    as_of_date = daily_df.index[-1]
    as_of_price = float(daily_df["Close"].iloc[-1])
    window_start = as_of_date - pd.DateOffset(years=WINDOW_YEARS)

    def retrace_events_for(kinds: set[str]) -> list[dict]:
        events = [
            {"date": f.retrace_date, "price": f.retrace_price, "obTop": f.top, "obBottom": f.bottom, "obFormedDate": f.formed_date, "kind": f.kind}
            for f in formations
            if f.kind in kinds and f.retrace_date is not None and f.retrace_date >= window_start
        ]
        events.sort(key=lambda e: e["date"])
        return events

    first_monday = window_start - pd.Timedelta(days=int(window_start.weekday()))
    week_starts = pd.date_range(first_monday, as_of_date, freq="7D")

    fixed_events: list[dict] = []
    random_events: list[dict] = []
    for wk in week_starts:
        fixed_target = wk + pd.Timedelta(days=FIXED_WEEKDAY)
        random_target = wk + pd.Timedelta(days=rng.randint(0, 4))
        for target, bucket in ((fixed_target, fixed_events), (random_target, random_events)):
            if target < window_start or target > as_of_date:
                continue
            day = nearest_trading_day_on_or_after(daily_df, target)
            if day is None or day > as_of_date:
                continue
            bucket.append({"date": day, "price": float(daily_df.loc[day, "Close"])})

    lump_day = nearest_trading_day_on_or_after(daily_df, window_start)
    lump_events = [{"date": lump_day, "price": float(daily_df.loc[lump_day, "Close"])}] if lump_day is not None else []

    strategy_events = {
        "retrace": retrace_events_for({"internal", "swing"}),
        "retraceSwing": retrace_events_for({"swing"}),
        "retraceInternal": retrace_events_for({"internal"}),
        "fixedWeeklyDca": fixed_events,
        "randomWeeklyDca": random_events,
        "lumpSum": lump_events,
    }

    result = {
        "ticker": ticker,
        "ok": True,
        "error": None,
        "asOfDate": str(as_of_date.date()),
        "asOfPrice": round(as_of_price, 4),
        "windowStart": str(window_start.date()),
        "strategies": {
            name: {
                **summarize(events, as_of_date, as_of_price),
                **({"eventDetail": [
                    {"date": str(e["date"].date()), "price": round(e["price"], 4), "obTop": round(e["obTop"], 4), "obBottom": round(e["obBottom"], 4), "obFormedDate": e["obFormedDate"], "kind": e["kind"]}
                    for e in events
                ]} if name in RETRACE_STRATEGY_KEYS else {}),
            }
            for name, events in strategy_events.items()
        },
    }

    # Raw (date, amount) cashflows per strategy, for pooling across the universe.
    pool_cashflows = {
        name: [(e["date"], -AMOUNT_PER_EVENT) for e in events] + ([(as_of_date, sum(AMOUNT_PER_EVENT / e["price"] for e in events) * as_of_price)] if events else [])
        for name, events in strategy_events.items()
    }

    return result, pool_cashflows


def failed_ticker(ticker: str, error: Exception) -> dict:
    return {"ticker": ticker, "ok": False, "error": str(error), "asOfDate": None, "asOfPrice": None, "windowStart": None, "strategies": {}}


def main() -> None:
    rng = random.Random(RANDOM_SEED)
    tickers_out = []
    pooled_cashflows: dict[str, list[tuple[pd.Timestamp, float]]] = {
        "retrace": [], "retraceSwing": [], "retraceInternal": [],
        "fixedWeeklyDca": [], "randomWeeklyDca": [], "lumpSum": [],
    }

    for ticker in engine.UNIVERSE:
        try:
            result, pool_cf = backtest_ticker(ticker, rng)
            tickers_out.append(result)
            for name, cfs in pool_cf.items():
                pooled_cashflows[name].extend(cfs)
        except Exception as exc:  # noqa: BLE001 - one bad ticker shouldn't sink the run
            tickers_out.append(failed_ticker(ticker, exc))

    pooled = {}
    for name, cfs in pooled_cashflows.items():
        outflows = [c for c in cfs if c[1] < 0]
        inflows = [c for c in cfs if c[1] > 0]
        total_invested = -sum(a for _, a in outflows)
        ending_value = sum(a for _, a in inflows)
        r = xirr(cfs)
        pooled[name] = {
            "events": len(outflows),
            "totalInvested": round(total_invested, 2),
            "endingValue": round(ending_value, 2),
            "simpleReturnPct": round((ending_value / total_invested - 1) * 100, 2) if total_invested > 0 else None,
            "xirrPct": round(r, 2) if r is not None else None,
        }

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "universe": engine.UNIVERSE,
            "windowYears": WINDOW_YEARS,
            "amountPerEvent": AMOUNT_PER_EVENT,
            "orderBlockKind": "weekly bullish order blocks -- 'retrace' combines internal (5-bar, ~5wk) and swing (50-bar, ~1yr) structure; 'retraceSwing'/'retraceInternal' isolate each",
            "retraceDefinition": "first bar after formation whose low wicks back into the order block (first touch only, one event per order block)",
            "fixedWeekday": FIXED_WEEKDAY_LABEL,
            "randomSeed": RANDOM_SEED,
            "xirrMethod": "money-weighted annualized return, bisection solve, actual/365 day count",
            "note": "All strategies buy and hold -- no stop-loss or exit rule. Pooled figures combine cash flows across the whole universe into one XIRR per strategy.",
        },
        "pooled": pooled,
        "tickers": tickers_out,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {OUTPUT_PATH} for {len(engine.UNIVERSE)} tickers")
    for name, p in pooled.items():
        print(f"  {name}: {p['events']} events, ${p['totalInvested']} invested, XIRR {p['xirrPct']}%")


if __name__ == "__main__":
    main()

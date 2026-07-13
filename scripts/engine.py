"""Smart Money Concepts multi-stock dashboard engine.

Ports the swing/internal market-structure, BOS/CHoCH, and order-block
detection logic from LuxAlgo's "Smart Money Concepts" Pine Script v5
indicator to Python, runs it over a configurable universe of tickers, and
ranks the universe by how close current price sits to its nearest active
bullish ("blue") order block.

Source indicator: LuxAlgo Smart Money Concepts, CC BY-NC-SA 4.0
(https://creativecommons.org/licenses/by-nc-sa/4.0/). This port carries the
same non-commercial / share-alike terms forward -- see README.md.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import yfinance as yf

# ---------------------------------------------------------------------------
# Universe -- add or remove tickers here. Any Yahoo Finance symbol works
# (ASX listings use the ".AX" suffix). Push a change and the next scheduled
# run (or a manual workflow_dispatch) picks it up automatically.
# ---------------------------------------------------------------------------
UNIVERSE = ["ASIA.AX", "LNAS.AX", "HJPN.AX"]

HISTORY_PERIOD = "5y"
INTERVAL = "1d"

SWING_LENGTH = 50       # swingsLengthInput default in the source indicator
INTERNAL_LENGTH = 5     # fixed internal-structure length in the source indicator
INTERNAL_OB_COUNT = 5   # internalOrderBlocksSizeInput default
SWING_OB_COUNT = 5      # swingOrderBlocksSizeInput default
ATR_LENGTH = 200

LEG_BEARISH = 0
LEG_BULLISH = 1

BIAS_BULLISH = 1
BIAS_BEARISH = -1

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "public" / "smc_data.json"
TIMEZONE = "Australia/Adelaide"


@dataclass
class Pivot:
    level: float = float("nan")
    bar_index: int = -1
    bar_time: str | None = None
    crossed: bool = False


@dataclass
class OrderBlock:
    bar_high: float
    bar_low: float
    bar_time: str
    bias: int  # BIAS_BULLISH or BIAS_BEARISH


def fetch_history(ticker: str) -> pd.DataFrame:
    df = yf.Ticker(ticker).history(period=HISTORY_PERIOD, interval=INTERVAL, auto_adjust=True)
    if df.empty:
        raise ValueError(f"No price history returned for {ticker}")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df.index = pd.to_datetime(df.index)
    return df


def wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.Series:
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / length, adjust=False, min_periods=length).mean()


def compute_legs(high: np.ndarray, low: np.ndarray, size: int) -> np.ndarray:
    """Port of the indicator's leg(size) function.

    A bar `size` steps back is confirmed as a swing high once nothing in the
    most recent `size`-bar window has exceeded it (and mirrored for lows).
    """
    n = len(high)
    legs = np.zeros(n, dtype=int)
    current = LEG_BEARISH
    for i in range(n):
        if i < size:
            legs[i] = current
            continue
        window_start = i - size + 1
        highest = high[window_start : i + 1].max()
        lowest = low[window_start : i + 1].min()
        old_high = high[i - size]
        old_low = low[i - size]
        if old_high > highest:
            current = LEG_BEARISH
        elif old_low < lowest:
            current = LEG_BULLISH
        legs[i] = current
    return legs


def bias_str(bias: int) -> str | None:
    if bias == BIAS_BULLISH:
        return "BULLISH"
    if bias == BIAS_BEARISH:
        return "BEARISH"
    return None


def zone_from_order_block(ob: OrderBlock, kind: str, price: float) -> dict:
    top, bottom = ob.bar_high, ob.bar_low
    if price < bottom:
        distance_pct = (bottom - price) / price * 100
        inside = False
    elif price <= top:
        distance_pct = 0.0
        inside = True
    else:
        distance_pct = (price - top) / price * 100
        inside = False
    return {
        "kind": kind,
        "top": round(top, 4),
        "bottom": round(bottom, 4),
        "date": ob.bar_time,
        "distancePct": round(distance_pct, 3),
        "insideZone": inside,
    }


def process_symbol(ticker: str) -> dict:
    df = fetch_history(ticker)
    high = df["High"].to_numpy()
    low = df["Low"].to_numpy()
    close = df["Close"].to_numpy()
    times = df.index
    n = len(df)
    if n < SWING_LENGTH + 5:
        raise ValueError(f"Not enough history for {ticker} ({n} bars)")

    atr = wilder_atr(df["High"], df["Low"], df["Close"], ATR_LENGTH).to_numpy()
    bar_range = high - low
    high_vol = np.where(np.isnan(atr), False, bar_range >= 2 * np.nan_to_num(atr))
    # High-volatility bars have their high/low swapped before being eligible to
    # anchor an order block, exactly as the source indicator does, so a single
    # outsized wick can't be selected as the block's edge.
    parsed_high = np.where(high_vol, low, high)
    parsed_low = np.where(high_vol, high, low)

    swing_legs = compute_legs(high, low, SWING_LENGTH)
    internal_legs = compute_legs(high, low, INTERNAL_LENGTH)

    swing_high, swing_low = Pivot(), Pivot()
    internal_high, internal_low = Pivot(), Pivot()
    swing_trend = 0
    internal_trend = 0
    swing_obs: list[OrderBlock] = []
    internal_obs: list[OrderBlock] = []

    def update_pivot(i: int, size: int, legs: np.ndarray, high_pivot: Pivot, low_pivot: Pivot) -> None:
        if i < size or legs[i] == legs[i - 1]:
            return
        src_idx = i - size
        if legs[i] == LEG_BULLISH:
            low_pivot.level = float(low[src_idx])
            low_pivot.bar_index = src_idx
            low_pivot.bar_time = str(times[src_idx].date())
            low_pivot.crossed = False
        else:
            high_pivot.level = float(high[src_idx])
            high_pivot.bar_index = src_idx
            high_pivot.bar_time = str(times[src_idx].date())
            high_pivot.crossed = False

    def store_order_block(pivot: Pivot, bias: int, obs: list[OrderBlock], i: int) -> None:
        start, end = pivot.bar_index, i
        if bias == BIAS_BEARISH:
            offset = int(np.argmax(parsed_high[start : end + 1]))
        else:
            offset = int(np.argmin(parsed_low[start : end + 1]))
        idx = start + offset
        obs.insert(
            0,
            OrderBlock(
                bar_high=float(high[idx]),
                bar_low=float(low[idx]),
                bar_time=str(times[idx].date()),
                bias=bias,
            ),
        )
        del obs[100:]

    def mitigate(obs: list[OrderBlock], i: int) -> list[OrderBlock]:
        bull_src = low[i]   # "High/Low" mitigation source (the indicator's default)
        bear_src = high[i]
        return [
            ob
            for ob in obs
            if not (ob.bias == BIAS_BEARISH and bear_src > ob.bar_high)
            and not (ob.bias == BIAS_BULLISH and bull_src < ob.bar_low)
        ]

    for i in range(1, n):
        swing_high_prev, swing_low_prev = swing_high.level, swing_low.level
        internal_high_prev, internal_low_prev = internal_high.level, internal_low.level

        update_pivot(i, SWING_LENGTH, swing_legs, swing_high, swing_low)
        update_pivot(i, INTERNAL_LENGTH, internal_legs, internal_high, internal_low)

        if (
            internal_high.bar_index >= 0
            and not internal_high.crossed
            and internal_high.level != swing_high.level
            and close[i - 1] <= internal_high_prev
            and close[i] > internal_high.level
        ):
            internal_high.crossed = True
            internal_trend = BIAS_BULLISH
            store_order_block(internal_high, BIAS_BULLISH, internal_obs, i)

        if (
            internal_low.bar_index >= 0
            and not internal_low.crossed
            and internal_low.level != swing_low.level
            and close[i - 1] >= internal_low_prev
            and close[i] < internal_low.level
        ):
            internal_low.crossed = True
            internal_trend = BIAS_BEARISH
            store_order_block(internal_low, BIAS_BEARISH, internal_obs, i)

        if (
            swing_high.bar_index >= 0
            and not swing_high.crossed
            and close[i - 1] <= swing_high_prev
            and close[i] > swing_high.level
        ):
            swing_high.crossed = True
            swing_trend = BIAS_BULLISH
            store_order_block(swing_high, BIAS_BULLISH, swing_obs, i)

        if (
            swing_low.bar_index >= 0
            and not swing_low.crossed
            and close[i - 1] >= swing_low_prev
            and close[i] < swing_low.level
        ):
            swing_low.crossed = True
            swing_trend = BIAS_BEARISH
            store_order_block(swing_low, BIAS_BEARISH, swing_obs, i)

        internal_obs = mitigate(internal_obs, i)
        swing_obs = mitigate(swing_obs, i)

    # Only the most recent N per structure type survive, matching the
    # indicator's own default on-chart box count.
    internal_capped = internal_obs[:INTERNAL_OB_COUNT]
    swing_capped = swing_obs[:SWING_OB_COUNT]

    price = float(close[-1])

    bullish_zones = [zone_from_order_block(ob, "internal", price) for ob in internal_capped if ob.bias == BIAS_BULLISH]
    bullish_zones += [zone_from_order_block(ob, "swing", price) for ob in swing_capped if ob.bias == BIAS_BULLISH]
    bearish_zones = [zone_from_order_block(ob, "internal", price) for ob in internal_capped if ob.bias == BIAS_BEARISH]
    bearish_zones += [zone_from_order_block(ob, "swing", price) for ob in swing_capped if ob.bias == BIAS_BEARISH]

    bullish_zones.sort(key=lambda z: z["distancePct"])
    bearish_zones.sort(key=lambda z: z["distancePct"])

    return {
        "ticker": ticker,
        "ok": True,
        "error": None,
        "lastPrice": round(price, 4),
        "lastBarDate": str(times[-1].date()),
        "swingTrend": bias_str(swing_trend),
        "internalTrend": bias_str(internal_trend),
        "nearestBullishOrderBlock": bullish_zones[0] if bullish_zones else None,
        "bullishOrderBlocks": bullish_zones,
        "bearishOrderBlocks": bearish_zones,
    }


def failed_symbol(ticker: str, error: Exception) -> dict:
    return {
        "ticker": ticker,
        "ok": False,
        "error": str(error),
        "lastPrice": None,
        "lastBarDate": None,
        "swingTrend": None,
        "internalTrend": None,
        "nearestBullishOrderBlock": None,
        "bullishOrderBlocks": [],
        "bearishOrderBlocks": [],
    }


def main() -> None:
    symbols = []
    for ticker in UNIVERSE:
        try:
            symbols.append(process_symbol(ticker))
        except Exception as exc:  # noqa: BLE001 - one bad ticker shouldn't sink the run
            symbols.append(failed_symbol(ticker, exc))

    ranked = sorted(
        (s for s in symbols if s["ok"] and s["nearestBullishOrderBlock"]),
        key=lambda s: s["nearestBullishOrderBlock"]["distancePct"],
    )
    ranking = [s["ticker"] for s in ranked]

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "universe": UNIVERSE,
            "source": "LuxAlgo Smart Money Concepts (Pine Script v5) ported to Python",
            "timeframe": INTERVAL,
            "historyPeriod": HISTORY_PERIOD,
            "swingLength": SWING_LENGTH,
            "internalLength": INTERNAL_LENGTH,
            "orderBlockCountPerType": INTERNAL_OB_COUNT,
            "atrLength": ATR_LENGTH,
            "timezone": TIMEZONE,
        },
        "ranking": ranking,
        "closestSymbol": ranking[0] if ranking else None,
        "symbols": symbols,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    print(f"Wrote {OUTPUT_PATH} for {len(UNIVERSE)} symbols; closest to a blue order block: {output['closestSymbol']}")


if __name__ == "__main__":
    main()

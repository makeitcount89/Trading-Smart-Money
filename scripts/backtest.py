"""Weekly OB Proximity DCA Backtest.

Iterates week-by-week over the trailing WINDOW_YEARS. Every week, it evaluates
the entire universe of 11 tickers, calculates which ticker's current close 
price is closest to (or deepest within) its most recent active weekly order block,
and allocates a fixed $50 DCA buy to that single ticker.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

WINDOW_YEARS = 2
WEEKLY_DCA_AMOUNT = 50.0

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "public" / "backtest_data.json"


@dataclass
class ActiveOB:
    kind: str  # "internal" or "swing"
    top: float
    bottom: float
    formed_date: str


def strip_tz(df: pd.DataFrame) -> pd.DataFrame:
    if df.index.tz is not None:
        df = df.copy()
        df.index = df.index.tz_localize(None)
    return df


def get_all_historical_obs(weekly_df: pd.DataFrame) -> list[dict]:
    """Extracts all historical bullish order blocks with their exact formation bars."""
    high = weekly_df["High"].to_numpy()
    low = weekly_df["Low"].to_numpy()
    close = weekly_df["Close"].to_numpy()
    times = weekly_df.index
    n = len(weekly_df)
    
    if n < engine.SWING_LENGTH + 5:
        return []

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

    obs = []
    for i in range(1, n):
        swing_high_prev = swing_high.level
        internal_high_prev = internal_high.level

        update_pivot(i, engine.SWING_LENGTH, swing_legs, swing_high, swing_low)
        update_pivot(i, engine.INTERNAL_LENGTH, internal_legs, internal_high, internal_low)

        if swing_high.bar_index >= 0 and not swing_high.crossed and close[i - 1] <= swing_high_prev and close[i] > swing_high.level:
            swing_high.crossed = True
            ob = engine.pick_order_block(high, low, parsed_high, parsed_low, times, swing_high.bar_index, i, engine.BIAS_BULLISH)
            obs.append({"kind": "swing", "formed_date": times[i], "top": ob.bar_high, "bottom": ob.bar_low})

        if internal_high.bar_index >= 0 and not internal_high.crossed and internal_high.level != swing_high.level and close[i - 1] <= internal_high_prev and close[i] > internal_high.level:
            internal_high.crossed = True
            ob = engine.pick_order_block(high, low, parsed_high, parsed_low, times, internal_high.bar_index, i, engine.BIAS_BULLISH)
            obs.append({"kind": "internal", "formed_date": times[i], "top": ob.bar_high, "bottom": ob.bar_low})

    return obs


def xirr(cashflows: list[tuple[pd.Timestamp, float]]) -> float | None:
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


def main() -> None:
    # 1. Gather historical data for all tickers
    ticker_data = {}
    all_as_of_dates = []
    
    print("Fetching and parsing data for the universe...")
    for ticker in engine.UNIVERSE:
        try:
            w_df = strip_tz(engine.fetch_history(ticker, "1wk"))
            d_df = strip_tz(engine.fetch_history(ticker, "1d"))
            historical_obs = get_all_historical_obs(w_df)
            
            ticker_data[ticker] = {
                "daily": d_df,
                "obs": historical_obs,
                "buys": [],  # Store tuples of (date, execution_price)
                "last_close": float(d_df["Close"].iloc[-1])
            }
            all_as_of_dates.append(d_df.index[-1])
        except Exception as e:
            print(f"Skipping {ticker} due to fetch error: {e}")

    if not ticker_data:
        print("Error: No ticker data loaded.")
        return

    # Establish global timeline boundaries
    end_date = min(all_as_of_dates)
    start_date = end_date - pd.DateOffset(years=WINDOW_YEARS)
    
    # Generate weekly evaluation dates (every Monday)
    weekly_dates = pd.date_range(start=start_date, end=end_date, freq="W-MON")

    # 2. Run the dynamic chronological backtest simulation
    print(f"Running chronological simulation from {start_date.date()} to {end_date.date()}...")
    for current_week in weekly_dates:
        best_ticker = None
        best_distance = float("inf")
        execution_price = None
        execution_date = None

        for ticker, data in ticker_data.items():
            daily_df = data["daily"]
            
            # Find the exact or next closest daily trading bar inside this week
            available_dates = daily_df.index[(daily_df.index >= current_week) & (daily_df.index < current_week + pd.Timedelta(days=5))]
            if len(available_dates) == 0:
                continue
            
            eval_date = available_dates[0]
            current_close = float(daily_df.loc[eval_date, "Close"])

            # Filter for order blocks formed strictly BEFORE this evaluation week
            valid_obs = [ob for ob in data["obs"] if ob["formed_date"] < current_week]
            if not valid_obs:
                continue
            
            # Find the most recently formed order block
            latest_ob = max(valid_obs, key=lambda x: x["formed_date"])
            
            # Calculate dynamic proximity percentage: (Current Price - OB Top) / OB Top
            distance_pct = ((current_close - latest_ob["top"]) / latest_ob["top"]) * 100.0

            if distance_pct < best_distance:
                best_distance = distance_pct
                best_ticker = ticker
                execution_price = current_close
                execution_date = eval_date

        # Allocate the weekly investment if a clear winning asset is identified
        if best_ticker is not None:
            ticker_data[best_ticker]["buys"].append({
                "date": execution_date,
                "price": execution_price,
                "distance_pct": round(best_distance, 2)
            })

    # 3. Calculate metrics and compile output package
    tickers_out = []
    global_cashflows = []
    total_portfolio_invested = 0.0
    total_portfolio_value = 0.0

    for ticker, data in ticker_data.items():
        buys = data["buys"]
        last_close = data["last_close"]
        
        units_held = sum(WEEKLY_DCA_AMOUNT / b["price"] for b in buys)
        invested = WEEKLY_DCA_AMOUNT * len(buys)
        current_value = units_held * last_close
        
        total_portfolio_invested += invested
        total_portfolio_value += current_value

        ticker_cashflows = [(b["date"], -WEEKLY_DCA_AMOUNT) for b in buys]
        global_cashflows.extend(ticker_cashflows)
        
        if buys:
            ticker_cashflows.append((end_date, current_value))
            t_xirr = xirr(ticker_cashflows)
        else:
            t_xirr = None

        tickers_out.append({
            "ticker": ticker,
            "ok": True,
            "asOfDate": str(end_date.date()),
            "asOfPrice": round(last_close, 4),
            "strategies": {
                "proximityDCA": {
                    "events": len(buys),
                    "totalInvested": round(invested, 2),
                    "endingValue": round(current_value, 2),
                    "simpleReturnPct": round((current_value / invested - 1) * 100, 2) if invested > 0 else 0.0,
                    "xirrPct": round(t_xirr, 2) if t_xirr is not None else None,
                    "eventDetail": [
                        {
                            "date": str(b["date"].date()),
                            "price": round(b["price"], 4),
                            "proximityPct": b["distance_pct"]
                        }
                        for b in buys
                    ]
                }
            }
        })

    if global_cashflows:
        global_cashflows.append((end_date, total_portfolio_value))
        portfolio_xirr = xirr(global_cashflows)
    else:
        portfolio_xirr = None

    output = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "meta": {
            "universe": engine.UNIVERSE,
            "windowYears": WINDOW_YEARS,
            "amountPerWeek": WEEKLY_DCA_AMOUNT,
            "strategyName": "Proximity-Ranked Weekly OB DCA Router",
            "note": "Every week, $50 is fully deployed into the one asset closest to or deepest within its latest unmitigated weekly bullish OB.",
        },
        "pooled": {
            "proximityDCA": {
                "events": len(global_cashflows) - 1,
                "totalInvested": round(total_portfolio_invested, 2),
                "endingValue": round(total_portfolio_value, 2),
                "simpleReturnPct": round((total_portfolio_value / total_portfolio_invested - 1) * 100, 2) if total_portfolio_invested > 0 else 0.0,
                "xirrPct": round(portfolio_xirr, 2) if portfolio_xirr is not None else None,
            }
        },
        "tickers": tickers_out,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(output, indent=2))
    
    print("\n--- Backtest Results Summary ---")
    print(f"Total Portfolio Invested: ${total_portfolio_invested:,.2f}")
    print(f"Total Portfolio Value:    ${total_portfolio_value:,.2f}")
    print(f"Combined Portfolio XIRR:  {output['pooled']['proximityDCA']['xirrPct']}%")


if __name__ == "__main__":
    main()
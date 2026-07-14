# Smart Money Concepts — Multi-Stock Dashboard

A dashboard that ports LuxAlgo's **Smart Money Concepts** indicator (swing/internal
market structure, BOS/CHoCH, and order blocks) from Pine Script to Python, runs it
daily across a configurable universe of stocks on **both the Daily and Weekly
timeframes**, and ranks the universe by how close each stock's current price sits to
its nearest **active bullish ("blue") order block** — a classic Smart Money Concepts
pullback/entry zone. It also includes a **backtest** that tests whether buying on
retraces to those zones actually beats simple dollar-cost averaging.

Universe: `ASIA.AX`, `LNAS.AX`, `HJPN.AX`, `BNKS.AX`, `MNRS.AX`, `FUEL.AX`, `NDQ.AX`,
`HACK.AX`, `QAU.AX`, `OOO.AX`, `GGUS.AX` (all ASX-listed). Add or remove tickers by
editing `UNIVERSE` in `scripts/engine.py`.

This is a companion project to `LNAS-SNAS` (a different, k-NN-based bi-weekly
allocator) — the two are intentionally independent; nothing here changes LNAS-SNAS.

## Architecture

```
scripts/engine.py                   Python port of the SMC indicator -> JSON
scripts/backtest.py                 Retrace-to-weekly-OB vs. DCA backtest -> JSON
.github/workflows/run_smc.yml       Daily cron trigger that runs the engine and commits the output
.github/workflows/run_backtest.yml  Weekly cron trigger that runs the backtest and commits the output
public/smc_data.json                Live dashboard data bundle
public/backtest_data.json           Backtest results bundle
app/page.tsx                        Client dashboard (Tailwind + lucide-react)
app/backtest/page.tsx               Backtest results page
app/api/workflow-status/route.ts    Serverless proxy to the GitHub Actions REST API
```

### Backend: `scripts/engine.py`

For every ticker in `UNIVERSE`, on **each** timeframe in `TIMEFRAMES` (Daily `1d` and
Weekly `1wk` by default — the Pine indicator is timeframe-agnostic, so running it on
a weekly chart in TradingView produces genuinely different order blocks than a daily
chart, and both are computed and shown independently here):

1. **Data** — pulls the full available OHLC history via `yfinance` at that
   timeframe's interval, with `auto_adjust=False` (raw prices). Yahoo's raw feed is
   already split-adjusted but **not** dividend-adjusted, which matches a default
   TradingView chart (dividend adjustment is opt-in there); using `auto_adjust=True`
   was tried initially but back-adjusts for dividends too, shifting every historical
   price level — and therefore every order block boundary — away from what
   TradingView displays.
2. **Volatility filter** — True Range is smoothed with an exact port of Pine's
   `ta.rma` (SMA-seeded Wilder smoothing, not a plain EWM approximation) over 200
   bars. Bars whose range is ≥ 2× that ATR have their high/low swapped before being
   eligible to anchor an order block, exactly as the source indicator does, so a
   single outsized wick doesn't get selected as the order block's edge.
3. **Leg / pivot detection** — `compute_legs` reproduces the indicator's `leg()`
   function: a bar `N` back is confirmed as a swing point once nothing in the most
   recent `N`-bar window has exceeded it. Two lengths are run in parallel on each
   timeframe's own bars: **swing** (`N=50`) and **internal** (`N=5`, the fixed length
   the source script itself uses for internal structure).
4. **Structure breaks (BOS/CHoCH)** — a close crossing above the last confirmed
   swing/internal high is a bullish break; crossing below the last confirmed
   swing/internal low is a bearish break.
5. **Order blocks** — `pick_order_block` (shared with `scripts/backtest.py`) scans
   back from the broken pivot bar up to (but **excluding**) the breakout bar itself —
   matching Pine's `array.slice(id, from, to)`, whose `to` bound is exclusive — and
   picks the bar with the lowest (volatility-adjusted) low in that range as the
   **bullish order block**: the last down candle before the rally, i.e. the "blue"
   zone in the source indicator's default color scheme
   (`internalBullishOrderBlockColor` / `swingBullishOrderBlockColor`, both blue).
   Bearish breaks do the mirror image (highest high) and produce a red/bearish order
   block, kept for context.
6. **Mitigation** — a bullish order block is dropped the moment a bar's low closes
   below the block's own low (the "High/Low" mitigation source, matching the
   indicator's default); a bearish block is dropped once a high closes above its
   high. Only unmitigated blocks survive to the final output, and only the 5 most
   recent per structure type (internal/swing) are kept, matching the indicator's own
   default box count.
7. **Ranking** — for each ticker and each timeframe, the distance from the latest
   close to every remaining bullish order block is computed as a percentage (0% if
   price is already inside the zone); the closest one becomes that ticker's
   `nearestBullishOrderBlock` for that timeframe. The universe is then ranked
   ascending by that distance, separately per timeframe.
8. **Output** — `public/smc_data.json`: per-symbol, per-timeframe trend, nearest
   bullish order block, and the full list of currently active bullish/bearish order
   blocks, plus a `ranking` and `closestSymbol` object keyed by timeframe (`1d`,
   `1wk`).

### Backtest: `scripts/backtest.py`

Tests a specific hypothesis: **buying $100 every time price first retraces into an
unmitigated weekly bullish order block beats regular dollar-cost averaging**, over
the trailing 2 years. All strategies are pure accumulate-and-hold — no stop-loss, no
selling; every $100 buy is held to the last available close.

1. **Order block formation history** — reuses `engine.compute_legs`,
   `engine.wilder_atr`, and `engine.pick_order_block` directly (not a reimplementation)
   to replay every weekly bullish order block ever formed for a ticker, not just the
   currently-active ones the live dashboard shows. Both structure types are tracked:
   **internal** (5-bar, ~5 weeks, frequent) and **swing** (50-bar, ~1 year, rare) —
   an internal break is skipped when it coincides with the current swing level, same
   as the source indicator's own logic (`internalHigh.currentLevel !=
   swingHigh.currentLevel`), so a single structural point isn't double-counted.
   `retrace` combines both kinds (the primary, highest-power signal); `retraceSwing`
   and `retraceInternal` isolate each so the (much rarer) swing-only result stays
   directly comparable on its own.
2. **Retrace definition** — for each formed order block, the first bar *after*
   formation whose low wicks back into the zone (`low <= top`) counts as one retrace
   event — first touch only, so an order block that stays retested for weeks still
   only counts once. Only retrace events falling in the trailing 2 years are used,
   even if the order block itself formed earlier.
3. **Three comparison strategies**, using daily closes over the same 2-year window:
   - **Fixed-day weekly DCA** — $100 every Monday (or the next trading day if Monday
     is a holiday).
   - **Random-day weekly DCA** — $100 once a week, but on a day picked uniformly at
     random (Mon–Fri, seeded, `RANDOM_SEED = 42` for reproducibility) — a cleaner
     statistical control than a fixed weekday, since it removes any chance
     correlation between a specific weekday and market patterns.
   - **Lump sum** — a single $100 buy on the first trading day of the window, the
     classic buy-and-hold reference point.
4. **Comparison metric** — because the retrace strategy and the weekly DCA strategies
   invest very different total dollar amounts (order blocks are rare; ~104 weekly
   buys happen regardless), raw ending value isn't comparable. Every strategy is
   scored on **XIRR** (money-weighted annualized return, solved via bisection on the
   actual buy dates and amounts) alongside simple return, which normalizes away the
   difference in dollars deployed and timing.
5. **Pooling** — because swing-level weekly order blocks are infrequent (this is a
   real statistical-power limitation, not a bug — expect single digits of retrace
   events per ticker over 2 years), cash flows from all 11 tickers are also pooled
   into one combined XIRR per strategy, reported alongside each ticker's own numbers.
6. **Output** — `public/backtest_data.json`: pooled comparison across the whole
   universe, plus per-ticker strategy breakdowns and the full list of retrace events
   (date, fill price, order block range) for audit.

### Pipelines: `.github/workflows/`

`run_smc.yml` runs on a weekday cron roughly 40 minutes after the ASX close (two cron
lines cover both AEST/AEDT, the same approach LNAS-SNAS uses). `run_backtest.yml`
runs weekly (Saturday) since weekly structure only changes once a week. Both install
`scripts/requirements.txt`, run their script, and commit the resulting JSON back to
the repo with `[skip ci]`. Both support `workflow_dispatch` for manual runs.

### Frontend: `app/page.tsx`

Fetches `/smc_data.json` (same-origin static file, cache-busted on manual refresh)
and shows, for **each** timeframe (Daily and Weekly, stacked):

- Stat tiles for that timeframe's closest symbol, its distance to that zone, and how
  many universe symbols currently have an active blue order block at all.
- A ranking table across the whole universe for that timeframe, sorted by distance to
  the nearest blue order block, with swing/internal trend badges.

Each symbol also gets a card listing every currently active bullish (blue) and
bearish (red) order block **for both timeframes side by side**: price range, which
structure type produced it (internal/swing), when it formed, and its distance.

A "Backtest" link in the header opens `app/backtest/page.tsx`, which fetches
`/backtest_data.json` and shows the pooled strategy-comparison table plus a
per-ticker breakdown, including the individual retrace events behind each ticker's
numbers.

## Adding tickers to the universe

Edit the `UNIVERSE` list near the top of `scripts/engine.py` (shared by both
`engine.py` and `backtest.py`):

```python
UNIVERSE = ["ASIA.AX", "LNAS.AX", "HJPN.AX", "BNKS.AX", "MNRS.AX", "FUEL.AX", "NDQ.AX", "HACK.AX", "QAU.AX", "OOO.AX", "GGUS.AX"]
```

Add any Yahoo Finance symbol (ASX listings use the `.AX` suffix). Push the change —
the next cron run (or a manual `workflow_dispatch`) picks it up automatically for
both the dashboard and the backtest.

## Local development

```bash
npm install
npm run dev            # http://localhost:3000

python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/engine.py      # writes public/smc_data.json
python scripts/backtest.py    # writes public/backtest_data.json
```

## Deployment

- **Frontend**: deploy to Vercel (zero config — standard Next.js App Router build).
- **Backend**: the GitHub Actions workflows need `contents: write` permission
  (already set) to commit the refreshed data files. No secrets are required for
  either script; `app/api/workflow-status` works unauthenticated against the public
  GitHub API at a lower rate limit, or set a `GITHUB_TOKEN` env var on Vercel for
  higher limits.

## Known limitations

- Price levels are raw/unadjusted but still reflect Yahoo's own split-adjustment,
  which occasionally lags a *very recent* real-world split by a few days until
  Yahoo's data catches up — the same caveat LNAS-SNAS documents for LNAS.AX. If an
  order block's price range looks implausible right after a known split, this is the
  likely cause.
- Weekly bar boundaries from `yfinance` may not land on exactly the same week-start
  convention TradingView uses in every timezone; this is a minor, rare source of
  divergence at week edges only.
- `retraceSwing` will have very few events per ticker even pooled across the whole
  universe (swing-level weekly order blocks are inherently rare — a real run showed
  1 pooled event across 11 tickers over 2 years); treat it as illustrative, not a
  statistically meaningful comparison on its own. `retrace` (internal + swing
  combined) has real, if still modest, sample size — lean on that and the pooled,
  universe-wide numbers rather than any single ticker's result.

## Attribution & license

The swing/internal structure, BOS/CHoCH, and order-block detection logic in
`scripts/engine.py` and `scripts/backtest.py` is a Python port of LuxAlgo's **Smart
Money Concepts** Pine Script indicator, which is licensed
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) —
**non-commercial use with attribution, share-alike**. Keep any use of this
repository (and any derivative of it) non-commercial and carry the same
license/attribution forward, consistent with LuxAlgo's terms.

## Disclaimer

For research/educational purposes only. Not financial advice.

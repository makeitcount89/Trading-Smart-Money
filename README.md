# Smart Money Concepts — Multi-Stock Dashboard

A dashboard that ports LuxAlgo's **Smart Money Concepts** indicator (swing/internal
market structure, BOS/CHoCH, and order blocks) from Pine Script to Python, runs it
daily across a configurable universe of stocks on **both the Daily and Weekly
timeframes**, and ranks the universe by how close each stock's current price sits to
its nearest **active bullish ("blue") order block** — a classic Smart Money Concepts
pullback/entry zone.

Default universe: `ASIA.AX`, `LNAS.AX`, `HJPN.AX` (all ASX-listed). Add or remove
tickers by editing `UNIVERSE` in `scripts/engine.py`.

This is a companion project to `LNAS-SNAS` (a different, k-NN-based bi-weekly
allocator) — the two are intentionally independent; nothing here changes LNAS-SNAS.

## Architecture

```
scripts/engine.py                   Python port of the SMC indicator -> JSON
.github/workflows/run_smc.yml       Daily cron trigger that runs the engine and commits the output
public/smc_data.json                Flat JSON data bundle consumed directly by the frontend
app/page.tsx                        Client dashboard (Tailwind + lucide-react)
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
5. **Order blocks** — on every bullish break, the engine scans back from the broken
   pivot bar up to (but **excluding**) the breakout bar itself — matching Pine's
   `array.slice(id, from, to)`, whose `to` bound is exclusive — and picks the bar
   with the lowest (volatility-adjusted) low in that range as the **bullish order
   block**: the last down candle before the rally, i.e. the "blue" zone in the source
   indicator's default color scheme (`internalBullishOrderBlockColor` /
   `swingBullishOrderBlockColor`, both blue). Bearish breaks do the mirror image
   (highest high) and produce a red/bearish order block, kept for context.
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

### Pipeline: `.github/workflows/run_smc.yml`

Runs on a weekday cron roughly 40 minutes after the ASX close (two cron lines cover
both AEST/AEDT, the same approach LNAS-SNAS uses), installs
`scripts/requirements.txt`, runs the engine, and commits `public/smc_data.json` back
to the repo with `[skip ci]`. `workflow_dispatch` is enabled for manual runs.

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

## Adding tickers to the universe

Edit the `UNIVERSE` list near the top of `scripts/engine.py`:

```python
UNIVERSE = ["ASIA.AX", "LNAS.AX", "HJPN.AX"]
```

Add any Yahoo Finance symbol (ASX listings use the `.AX` suffix). Push the change —
the next cron run (or a manual `workflow_dispatch`) picks it up automatically.

## Local development

```bash
npm install
npm run dev            # http://localhost:3000

python3 -m venv .venv && source .venv/bin/activate
pip install -r scripts/requirements.txt
python scripts/engine.py    # writes public/smc_data.json
```

## Deployment

- **Frontend**: deploy to Vercel (zero config — standard Next.js App Router build).
- **Backend**: the GitHub Actions workflow needs `contents: write` permission
  (already set) to commit the refreshed data file. No secrets are required for the
  engine itself; `app/api/workflow-status` works unauthenticated against the public
  GitHub API at a lower rate limit, or set a `GITHUB_TOKEN` env var on Vercel for
  higher limits.

## Known limitations

- Price levels are raw/unadjusted (see point 1 above) but still reflect Yahoo's own
  split-adjustment, which occasionally lags a *very recent* real-world split by a few
  days until Yahoo's data catches up — the same caveat LNAS-SNAS documents for
  LNAS.AX. If an order block's price range looks implausible right after a known
  split, this is the likely cause.
- Weekly bar boundaries from `yfinance` may not land on exactly the same week-start
  convention TradingView uses in every timezone; this is a minor, rare source of
  divergence at week edges only.

## Attribution & license

The swing/internal structure, BOS/CHoCH, and order-block detection logic in
`scripts/engine.py` is a Python port of LuxAlgo's **Smart Money Concepts** Pine
Script indicator, which is licensed
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/) —
**non-commercial use with attribution, share-alike**. Keep any use of this
repository (and any derivative of it) non-commercial and carry the same
license/attribution forward, consistent with LuxAlgo's terms.

## Disclaimer

For research/educational purposes only. Not financial advice.

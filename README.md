# Smart Money Concepts — Multi-Stock Dashboard

A dashboard that ports LuxAlgo's **Smart Money Concepts** indicator (swing/internal
market structure, BOS/CHoCH, and order blocks) from Pine Script to Python, runs it
daily across a configurable universe of stocks, and ranks the universe by how close
each stock's current price sits to its nearest **active bullish ("blue") order
block** — a classic Smart Money Concepts pullback/entry zone.

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

For every ticker in `UNIVERSE`:

1. **Data** — pulls ~5 years of daily OHLC via `yfinance` (`auto_adjust=True`, so
   Yahoo's own split/dividend adjustment is used; this is a simpler assumption than
   LNAS-SNAS's manual split-desplitting and can be revisited if a ticker's history
   looks discontinuous around a known corporate action).
2. **Volatility filter** — a 200-period Wilder ATR flags high-volatility bars
   (range ≥ 2× ATR) and swaps their high/low before they're eligible to anchor an
   order block, exactly as the source indicator does, so a single outsized wick
   doesn't get selected as the order block's edge.
3. **Leg / pivot detection** — `compute_legs` reproduces the indicator's `leg()`
   function: a bar `N` back is confirmed as a swing point once nothing in the most
   recent `N`-bar window has exceeded it. Two lengths are run in parallel: **swing**
   (`N=50`) and **internal** (`N=5`, the fixed length the source script itself uses
   for internal structure).
4. **Structure breaks (BOS/CHoCH)** — a close crossing above the last confirmed
   swing/internal high is a bullish break; crossing below the last confirmed
   swing/internal low is a bearish break.
5. **Order blocks** — on every bullish break, the engine scans back from the broken
   pivot to the breakout bar and picks the bar with the lowest (volatility-adjusted)
   low as the **bullish order block** — the last down candle before the rally, i.e.
   the "blue" zone in the source indicator's default color scheme
   (`internalBullishOrderBlockColor` / `swingBullishOrderBlockColor`, both blue).
   Bearish breaks do the mirror image (highest high) and produce a red/bearish
   order block, kept for context.
6. **Mitigation** — a bullish order block is dropped the moment a bar's low closes
   below the block's own low (the "High/Low" mitigation source, matching the
   indicator's default); a bearish block is dropped once a high closes above its
   high. Only unmitigated blocks survive to the final output, and only the 5 most
   recent per structure type (internal/swing) are kept, matching the indicator's own
   default box count.
7. **Ranking** — for each ticker, the distance from the latest close to every
   remaining bullish order block is computed as a percentage (0% if price is already
   inside the zone); the closest one becomes that ticker's `nearestBullishOrderBlock`.
   The universe is then ranked ascending by that distance — the top of the ranking is
   whichever stock is closest to (or already sitting inside) one of its blue order
   blocks.
8. **Output** — `public/smc_data.json`: per-symbol trend, nearest bullish order
   block, and the full list of currently active bullish/bearish order blocks, plus
   a `ranking` array and `closestSymbol`.

### Pipeline: `.github/workflows/run_smc.yml`

Runs on a weekday cron roughly 40 minutes after the ASX close (two cron lines cover
both AEST/AEDT, the same approach LNAS-SNAS uses), installs
`scripts/requirements.txt`, runs the engine, and commits `public/smc_data.json` back
to the repo with `[skip ci]`. `workflow_dispatch` is enabled for manual runs.

### Frontend: `app/page.tsx`

Fetches `/smc_data.json` (same-origin static file, cache-busted on manual refresh)
and shows:

- Stat tiles for the closest symbol, its distance to that zone, and how many
  universe symbols currently have an active blue order block at all.
- A ranking table across the whole universe, sorted by distance to the nearest
  blue order block, with swing/internal trend badges.
- A per-symbol card listing every currently active bullish (blue) and bearish (red)
  order block: price range, which structure type produced it (internal/swing), when
  it formed, and its distance.

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

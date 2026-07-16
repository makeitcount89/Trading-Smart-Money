import { useMemo, useState } from "react";
import { Minus, TrendingDown, TrendingUp } from "lucide-react";
import type { Bias, GuppyTrendSnapshot, SymbolResult, TimeframeKey } from "@/lib/types";
import { cn } from "@/lib/utils";

type GuppyFilter = "all" | "sixMonth" | "oneYear" | "threeYear";

const GUPPY_FILTERS: { key: GuppyFilter; label: string }[] = [
  { key: "all", label: "All" },
  { key: "sixMonth", label: "6mo Uptrend" },
  { key: "oneYear", label: "1yr Uptrend" },
  { key: "threeYear", label: "3yr Uptrend" },
];

function TrendBadge({ trend }: { trend: Bias | null | undefined }) {
  if (!trend) return <span className="text-[var(--text-muted)]">—</span>;
  const bullish = trend === "BULLISH";
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-xs font-medium",
        bullish ? "bg-long-muted text-long" : "bg-short-muted text-short"
      )}
    >
      {bullish ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
      {trend}
    </span>
  );
}

function GuppyChip({ value, label }: { value: boolean | null | undefined; label: string }) {
  const color = value == null ? "text-[var(--text-muted)]" : value ? "text-long" : "text-short";
  return (
    <span className={cn("inline-flex items-center gap-0.5 text-[10px] font-medium", color)} title={label}>
      {value == null ? <Minus size={9} /> : value ? <TrendingUp size={9} /> : <TrendingDown size={9} />}
      {label}
    </span>
  );
}

function GuppyTrendCell({ trend }: { trend: GuppyTrendSnapshot | null | undefined }) {
  if (!trend) return <span className="text-[var(--text-muted)]">—</span>;
  return (
    <div className="flex flex-col gap-0.5">
      <GuppyChip value={trend.sixMonth} label="6mo" />
      <GuppyChip value={trend.oneYear} label="1yr" />
      <GuppyChip value={trend.threeYear} label="3yr" />
    </div>
  );
}

export default function RankingTable({
  symbols,
  timeframe,
  label,
}: {
  symbols: SymbolResult[];
  timeframe: TimeframeKey;
  label: string;
}) {
  const [guppyFilter, setGuppyFilter] = useState<GuppyFilter>("all");

  const rows = useMemo(() => {
    const sorted = symbols
      .map((s) => ({ symbol: s, tf: s.timeframes[timeframe] ?? null }))
      .sort((a, b) => {
        const da = a.tf?.nearestBullishOrderBlock?.distancePct ?? Infinity;
        const db = b.tf?.nearestBullishOrderBlock?.distancePct ?? Infinity;
        return da - db;
      });
    if (guppyFilter === "all") return sorted;
    return sorted.filter((r) => r.tf?.guppyTrend?.[guppyFilter] === true);
  }, [symbols, timeframe, guppyFilter]);

  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className="flex flex-col gap-2 border-b border-base-700 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm font-medium text-[var(--text-primary)]">
          {label} — ranked by proximity to a blue order block
        </div>
        <div className="flex gap-1 rounded-md border border-base-600 bg-base-800 p-0.5 text-xs">
          {GUPPY_FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setGuppyFilter(f.key)}
              className={cn(
                "rounded px-2.5 py-1 font-medium transition-colors",
                guppyFilter === f.key ? "bg-smcBlue/20 text-smcBlue" : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>
      <table className="w-full min-w-[760px] text-sm">
        <thead>
          <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
            <th className="px-4 py-3 font-medium">#</th>
            <th className="px-4 py-3 font-medium">Ticker</th>
            <th className="px-4 py-3 font-medium">Last Price</th>
            <th className="px-4 py-3 font-medium">Swing Trend</th>
            <th className="px-4 py-3 font-medium">Internal Trend</th>
            <th className="px-4 py-3 font-medium">Guppy Trend</th>
            <th className="px-4 py-3 font-medium">Nearest Blue OB</th>
            <th className="px-4 py-3 font-medium">Distance</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={8} className="px-4 py-6 text-center text-[var(--text-muted)]">
                {guppyFilter === "all" ? "No data yet." : "No symbols currently pass this Guppy trend filter."}
              </td>
            </tr>
          )}
          {rows.map(({ symbol, tf }, i) => {
            const ob = tf?.nearestBullishOrderBlock ?? null;
            return (
              <tr key={symbol.ticker} className="border-b border-base-800 last:border-0">
                <td className="px-4 py-3 tabular text-[var(--text-muted)]">{i + 1}</td>
                <td className="px-4 py-3 font-medium">{symbol.ticker}</td>
                <td className="px-4 py-3 tabular">{tf ? tf.lastPrice.toFixed(3) : "—"}</td>
                <td className="px-4 py-3">
                  <TrendBadge trend={tf?.swingTrend} />
                </td>
                <td className="px-4 py-3">
                  <TrendBadge trend={tf?.internalTrend} />
                </td>
                <td className="px-4 py-3">
                  <GuppyTrendCell trend={tf?.guppyTrend} />
                </td>
                <td className="px-4 py-3 tabular">
                  {ob ? `${ob.bottom.toFixed(3)} – ${ob.top.toFixed(3)} (${ob.kind})` : "—"}
                </td>
                <td className="px-4 py-3 tabular">
                  {ob ? (
                    <span className={cn("font-semibold", ob.insideZone ? "text-smcBlue" : "text-[var(--text-primary)]")}>
                      {ob.insideZone ? "Inside zone" : `${ob.distancePct.toFixed(2)}%`}
                    </span>
                  ) : (
                    "—"
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="border-t border-base-800 px-4 py-2.5 text-[11px] text-[var(--text-muted)]">
        Guppy Trend: same short-EMA(3)-above-stacked-long-EMA-group filter as the backtest&apos;s Guppy-filtered
        strategy, checked at three lookback windows for whether the long group is still sloping up over that horizon.
        A dash means not enough price history yet to evaluate that window.
      </div>
    </div>
  );
}

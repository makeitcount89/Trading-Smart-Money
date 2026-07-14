import { TrendingDown, TrendingUp } from "lucide-react";
import type { Bias, SymbolResult, TimeframeKey } from "@/lib/types";
import { cn } from "@/lib/utils";

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

export default function RankingTable({
  symbols,
  timeframe,
  label,
}: {
  symbols: SymbolResult[];
  timeframe: TimeframeKey;
  label: string;
}) {
  const rows = symbols
    .map((s) => ({ symbol: s, tf: s.timeframes[timeframe] ?? null }))
    .sort((a, b) => {
      const da = a.tf?.nearestBullishOrderBlock?.distancePct ?? Infinity;
      const db = b.tf?.nearestBullishOrderBlock?.distancePct ?? Infinity;
      return da - db;
    });

  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className="border-b border-base-700 px-4 py-3 text-sm font-medium text-[var(--text-primary)]">
        {label} — ranked by proximity to a blue order block
      </div>
      <table className="w-full min-w-[640px] text-sm">
        <thead>
          <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
            <th className="px-4 py-3 font-medium">#</th>
            <th className="px-4 py-3 font-medium">Ticker</th>
            <th className="px-4 py-3 font-medium">Last Price</th>
            <th className="px-4 py-3 font-medium">Swing Trend</th>
            <th className="px-4 py-3 font-medium">Internal Trend</th>
            <th className="px-4 py-3 font-medium">Nearest Blue OB</th>
            <th className="px-4 py-3 font-medium">Distance</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={7} className="px-4 py-6 text-center text-[var(--text-muted)]">
                No data yet.
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
    </div>
  );
}

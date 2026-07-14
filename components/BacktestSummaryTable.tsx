// components/BacktestSummaryTable.tsx
import type { BacktestData } from "@/lib/types";
import { cn } from "@/lib/utils";

interface StrategyMetrics {
  events: number;
  totalInvested: number;
  endingValue: number;
  simpleReturnPct: number;
  xirrPct: number | null;
}

export default function BacktestSummaryTable({
  pooled,
  title,
}: {
  pooled: {
    proximityDCA: StrategyMetrics;
    guppyProximityDCA?: StrategyMetrics; // Optional key in case the backend payload is still writing
  };
  title: string;
}) {
  // Grab the metrics cleanly from the payload
  const g1 = pooled.proximityDCA;
  const g2 = pooled.guppyProximityDCA;

  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className="border-b border-base-700 px-4 py-3 text-sm font-medium text-[var(--text-primary)]">
        {title}
      </div>
      <table className="w-full min-w-[720px] text-sm">
        <thead>
          <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
            <th className="px-4 py-3 font-medium">Strategy Config</th>
            <th className="px-4 py-3 font-medium">Buys</th>
            <th className="px-4 py-3 font-medium">Invested</th>
            <th className="px-4 py-3 font-medium">Ending Value</th>
            <th className="px-4 py-3 font-medium">Simple Return</th>
            <th className="px-4 py-3 font-medium">Annualized (XIRR)</th>
          </tr>
        </thead>
        <tbody>
          {/* GROUP 1 ROW: PURE PROXIMITY */}
          <tr className="border-b border-base-800 last:border-0 hover:bg-base-800/30 transition-colors">
            <td className="px-4 py-3 font-medium text-smcBlue flex flex-col">
              <span>Pure Proximity OB DCA Router</span>
              <span className="text-[10px] text-[var(--text-muted)] font-normal mt-0.5">Unfiltered multi-asset universe allocation</span>
            </td>
            <td className="px-4 py-3 tabular">{g1.events}</td>
            <td className="px-4 py-3 tabular">
              ${g1.totalInvested.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </td>
            <td className="px-4 py-3 tabular">
              ${g1.endingValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </td>
            <td className={cn("px-4 py-3 tabular", g1.simpleReturnPct >= 0 ? "text-long" : "text-short")}>
              {g1.simpleReturnPct != null ? `${g1.simpleReturnPct > 0 ? "+" : ""}${g1.simpleReturnPct.toFixed(2)}%` : "—"}
            </td>
            <td className="px-4 py-3 tabular font-semibold text-smcBlue">
              {g1.xirrPct != null ? `${g1.xirrPct > 0 ? "+" : ""}${g1.xirrPct.toFixed(2)}%` : "—"}
            </td>
          </tr>

          {/* GROUP 2 ROW: GUPPY FILTERED */}
          {g2 && (
            <tr className="border-b border-base-800 last:border-0 bg-emerald-950/5 hover:bg-emerald-950/10 transition-colors">
              <td className="px-4 py-3 font-medium text-emerald-400 flex flex-col">
                <span>Guppy Trend Filtered Router</span>
                <span className="text-[10px] text-[var(--text-muted)] font-normal mt-0.5">Requires upward-sloping EMA stack confirmation</span>
              </td>
              <td className="px-4 py-3 tabular">{g2.events}</td>
              <td className="px-4 py-3 tabular">
                ${g2.totalInvested.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </td>
              <td className="px-4 py-3 tabular font-semibold text-zinc-100">
                ${g2.endingValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </td>
              <td className={cn("px-4 py-3 tabular", g2.simpleReturnPct >= 0 ? "text-long" : "text-short")}>
                {g2.simpleReturnPct != null ? `${g2.simpleReturnPct > 0 ? "+" : ""}${g2.simpleReturnPct.toFixed(2)}%` : "—"}
              </td>
              <td className="px-4 py-3 tabular font-bold text-emerald-400">
                {g2.xirrPct != null ? `${g2.xirrPct > 0 ? "+" : ""}${g2.xirrPct.toFixed(2)}%` : "—"}
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
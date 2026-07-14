import type { BacktestStrategyKey, BacktestStrategySummary } from "@/lib/types";
import { cn } from "@/lib/utils";

const STRATEGY_LABELS: Record<BacktestStrategyKey, string> = {
  retrace: "Retrace to weekly blue OB",
  fixedWeeklyDca: "Fixed-day weekly DCA (Monday)",
  randomWeeklyDca: "Random-day weekly DCA",
  lumpSum: "Lump sum (buy & hold)",
};

const STRATEGY_ORDER: BacktestStrategyKey[] = ["retrace", "fixedWeeklyDca", "randomWeeklyDca", "lumpSum"];

export default function BacktestSummaryTable({
  pooled,
  title,
}: {
  pooled: Partial<Record<BacktestStrategyKey, BacktestStrategySummary>>;
  title: string;
}) {
  const ranked = STRATEGY_ORDER.filter((k) => pooled[k]?.xirrPct != null).sort(
    (a, b) => (pooled[b]!.xirrPct ?? -Infinity) - (pooled[a]!.xirrPct ?? -Infinity)
  );
  const best = ranked[0];

  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className="border-b border-base-700 px-4 py-3 text-sm font-medium text-[var(--text-primary)]">{title}</div>
      <table className="w-full min-w-[720px] text-sm">
        <thead>
          <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
            <th className="px-4 py-3 font-medium">Strategy</th>
            <th className="px-4 py-3 font-medium">Buys</th>
            <th className="px-4 py-3 font-medium">Invested</th>
            <th className="px-4 py-3 font-medium">Ending Value</th>
            <th className="px-4 py-3 font-medium">Simple Return</th>
            <th className="px-4 py-3 font-medium">Annualized (XIRR)</th>
          </tr>
        </thead>
        <tbody>
          {STRATEGY_ORDER.map((key) => {
            const s = pooled[key];
            if (!s) return null;
            const isBest = key === best;
            return (
              <tr key={key} className="border-b border-base-800 last:border-0">
                <td className={cn("px-4 py-3 font-medium", isBest && "text-smcBlue")}>{STRATEGY_LABELS[key]}</td>
                <td className="px-4 py-3 tabular">{s.events}</td>
                <td className="px-4 py-3 tabular">${s.totalInvested.toLocaleString()}</td>
                <td className="px-4 py-3 tabular">${s.endingValue.toLocaleString()}</td>
                <td className="px-4 py-3 tabular">{s.simpleReturnPct != null ? `${s.simpleReturnPct.toFixed(2)}%` : "—"}</td>
                <td className={cn("px-4 py-3 tabular font-semibold", isBest && "text-smcBlue")}>
                  {s.xirrPct != null ? `${s.xirrPct.toFixed(2)}%` : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

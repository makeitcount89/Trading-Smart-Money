// components/BacktestSummaryTable.tsx
import type { BacktestStrategySummary, StrategyLegMeta } from "@/lib/types";
import { cn } from "@/lib/utils";
import { legColorClass } from "@/lib/legColors";

export default function BacktestSummaryTable({
  pooled,
  legs,
  title,
}: {
  pooled: Record<string, BacktestStrategySummary>;
  legs: StrategyLegMeta[];
  title: string;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className="border-b border-base-700 px-4 py-3 text-sm font-medium text-[var(--text-primary)]">
        {title}
      </div>
      <table className="w-full min-w-[1140px] text-sm">
        <thead>
          <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
            <th className="px-4 py-3 font-medium">Strategy Config</th>
            <th className="px-4 py-3 font-medium">Buys</th>
            <th className="px-4 py-3 font-medium">Stop-Loss</th>
            <th className="px-4 py-3 font-medium">Profit-Take</th>
            <th className="px-4 py-3 font-medium">Invested</th>
            <th className="px-4 py-3 font-medium">Ending Value</th>
            <th className="px-4 py-3 font-medium">Simple Return</th>
            <th className="px-4 py-3 font-medium">Annualized (XIRR)</th>
            <th className="px-4 py-3 font-medium">Sharpe</th>
            <th className="px-4 py-3 font-medium">Max Drawdown</th>
            <th className="px-4 py-3 font-medium">Calmar</th>
          </tr>
        </thead>
        <tbody>
          {legs.map((leg, i) => {
            const m = pooled[leg.key];
            if (!m) return null;
            const color = legColorClass(i);
            return (
              <tr key={leg.key} className="border-b border-base-800 last:border-0 hover:bg-base-800/30 transition-colors">
                <td className={cn("px-4 py-3 font-medium flex flex-col", color.text)}>
                  <span>{leg.label}</span>
                  {leg.description && (
                    <span className="text-[10px] text-[var(--text-muted)] font-normal mt-0.5">{leg.description}</span>
                  )}
                </td>
                <td className="px-4 py-3 tabular">{m.events}</td>
                <td className="px-4 py-3 tabular text-short">{m.stopLossExits ?? 0}</td>
                <td className="px-4 py-3 tabular text-long">{m.profitProtectExits ?? 0}</td>
                <td className="px-4 py-3 tabular">
                  ${m.totalInvested.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className="px-4 py-3 tabular font-semibold">
                  ${m.endingValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                </td>
                <td className={cn("px-4 py-3 tabular", m.simpleReturnPct >= 0 ? "text-long" : "text-short")}>
                  {m.simpleReturnPct != null ? `${m.simpleReturnPct > 0 ? "+" : ""}${m.simpleReturnPct.toFixed(2)}%` : "—"}
                </td>
                <td className={cn("px-4 py-3 tabular font-semibold", color.text)}>
                  {m.xirrPct != null ? `${m.xirrPct > 0 ? "+" : ""}${m.xirrPct.toFixed(2)}%` : "—"}
                </td>
                <td className={cn("px-4 py-3 tabular", (m.sharpeRatio ?? 0) >= 0 ? "text-long" : "text-short")}>
                  {m.sharpeRatio != null ? m.sharpeRatio.toFixed(2) : "—"}
                </td>
                <td className="px-4 py-3 tabular text-short">
                  {m.maxDrawdownPct != null ? `${m.maxDrawdownPct.toFixed(2)}%` : "—"}
                </td>
                <td className={cn("px-4 py-3 tabular", (m.calmarRatio ?? 0) >= 0 ? "text-long" : "text-short")}>
                  {m.calmarRatio != null ? m.calmarRatio.toFixed(2) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
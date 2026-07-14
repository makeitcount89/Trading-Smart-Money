// components/BacktestSummaryTable.tsx
import type { BacktestData } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function BacktestSummaryTable({
  pooled,
  title,
}: {
  pooled: BacktestData["pooled"];
  title: string;
}) {
  const s = pooled.proximityDCA;

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
          <tr className="border-b border-base-800 last:border-0">
            <td className="px-4 py-3 font-medium text-smcBlue">
              Proximity-Ranked Weekly OB DCA Router
            </td>
            <td className="px-4 py-3 tabular">{s.events}</td>
            <td className="px-4 py-3 tabular">${s.totalInvested.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td className="px-4 py-3 tabular">${s.endingValue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</td>
            <td className={cn("px-4 py-3 tabular", s.simpleReturnPct >= 0 ? "text-long" : "text-short")}>
              {s.simpleReturnPct != null ? `${s.simpleReturnPct > 0 ? "+" : ""}${s.simpleReturnPct.toFixed(2)}%` : "—"}
            </td>
            <td className="px-4 py-3 tabular font-semibold text-smcBlue">
              {s.xirrPct != null ? `${s.xirrPct > 0 ? "+" : ""}${s.xirrPct.toFixed(2)}%` : "—"}
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
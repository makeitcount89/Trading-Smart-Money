// components/ExitRuleSweepTable.tsx
"use client";

import { useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Award } from "lucide-react";
import type { BacktestStrategySummary, ExitRuleSweepConfig, StrategyLegMeta } from "@/lib/types";
import { cn } from "@/lib/utils";
import { legColorClass } from "@/lib/legColors";

type SortKey = "simpleReturnPct" | "xirrPct" | "sharpeRatio" | "maxDrawdownPct" | "calmarRatio" | "endingValue";

const SORT_COLUMNS: { key: SortKey; label: string }[] = [
  { key: "endingValue", label: "Ending Value" },
  { key: "simpleReturnPct", label: "Simple Return" },
  { key: "xirrPct", label: "Annualized (XIRR)" },
  { key: "sharpeRatio", label: "Sharpe" },
  { key: "maxDrawdownPct", label: "Max Drawdown" },
  { key: "calmarRatio", label: "Calmar" },
];

function formatRules(cfg: ExitRuleSweepConfig): string {
  const stop = cfg.stopLossPct != null ? `-${cfg.stopLossPct.toFixed(0)}%` : "off";
  const trail =
    cfg.trailingStopArmPct != null && cfg.trailingStopPct != null
      ? `+${cfg.trailingStopArmPct.toFixed(0)}% → -${cfg.trailingStopPct.toFixed(0)}%`
      : "off";
  return `Stop ${stop} · Trail ${trail}`;
}

export default function ExitRuleSweepTable({
  configs,
  legs,
  maxPositionPct,
}: {
  configs: ExitRuleSweepConfig[];
  legs: StrategyLegMeta[];
  maxPositionPct?: number;
}) {
  const [strategy, setStrategy] = useState<string>(legs[0]?.key ?? "");
  const [sortKey, setSortKey] = useState<SortKey>("sharpeRatio");
  const [sortDesc, setSortDesc] = useState(true);

  const rows = useMemo(() => {
    const withMetrics = configs.map((cfg) => ({ cfg, m: cfg[strategy] as BacktestStrategySummary }));
    const sorted = [...withMetrics].sort((a, b) => {
      const av = a.m[sortKey] ?? -Infinity;
      const bv = b.m[sortKey] ?? -Infinity;
      return sortDesc ? bv - av : av - bv;
    });
    return sorted;
  }, [configs, strategy, sortKey, sortDesc]);

  const bestSharpeName = useMemo(() => {
    let best: { name: string; sharpe: number } | null = null;
    for (const cfg of configs) {
      const m = cfg[strategy] as BacktestStrategySummary;
      if (m.sharpeRatio != null && (best === null || m.sharpeRatio > best.sharpe)) {
        best = { name: cfg.name, sharpe: m.sharpeRatio };
      }
    }
    return best?.name ?? null;
  }, [configs, strategy]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDesc((d) => !d);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className="flex flex-col gap-2 border-b border-base-700 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="text-sm font-medium text-[var(--text-primary)]">
          Exit-Rule Sweep &mdash; same historical data, alternative stop-loss / trailing-stop settings
        </div>
        <div className="flex flex-wrap gap-1 rounded-md border border-base-600 bg-base-800 p-0.5 text-xs">
          {legs.map((leg, i) => {
            const color = legColorClass(i);
            return (
              <button
                key={leg.key}
                onClick={() => setStrategy(leg.key)}
                className={cn(
                  "rounded px-2.5 py-1 font-medium transition-colors",
                  strategy === leg.key ? color.toggleActive : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                )}
              >
                {leg.label}
              </button>
            );
          })}
        </div>
      </div>

      {legs.find((l) => l.key === strategy)?.description && (
        <div className="border-b border-base-800 px-4 py-2 text-[11px] text-[var(--text-muted)]">
          {legs.find((l) => l.key === strategy)?.description}
        </div>
      )}

      <table className="w-full min-w-[1180px] text-sm">
        <thead>
          <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
            <th className="px-4 py-3 font-medium">Configuration</th>
            <th className="px-4 py-3 font-medium">Rules</th>
            <th className="px-4 py-3 font-medium">Buys</th>
            <th className="px-4 py-3 font-medium">Stop-Loss</th>
            <th className="px-4 py-3 font-medium">Profit-Take</th>
            <th className="px-4 py-3 font-medium">Invested</th>
            {SORT_COLUMNS.map((col) => (
              <th key={col.key} className="px-4 py-3 font-medium">
                <button
                  onClick={() => toggleSort(col.key)}
                  className={cn(
                    "flex items-center gap-1 transition-colors hover:text-[var(--text-secondary)]",
                    sortKey === col.key && "text-[var(--text-primary)]"
                  )}
                >
                  {col.label}
                  {sortKey === col.key && (sortDesc ? <ArrowDown size={11} /> : <ArrowUp size={11} />)}
                </button>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map(({ cfg, m }) => (
            <tr
              key={cfg.name}
              className={cn(
                "border-b border-base-800 last:border-0 hover:bg-base-800/30 transition-colors",
                cfg.isCurrent && "bg-smcBlue/5"
              )}
            >
              <td className="px-4 py-3 font-medium text-[var(--text-primary)]">
                <div className="flex items-center gap-1.5">
                  {cfg.name}
                  {cfg.isCurrent && (
                    <span className="rounded-full border border-smcBlue/40 bg-smcBlue/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-smcBlue">
                      Live
                    </span>
                  )}
                  {cfg.name === bestSharpeName && (
                    <span title="Best Sharpe ratio in this comparison">
                      <Award size={12} className="text-[var(--status-warning)]" />
                    </span>
                  )}
                </div>
              </td>
              <td className="px-4 py-3 text-xs text-[var(--text-muted)]">{formatRules(cfg)}</td>
              <td className="px-4 py-3 tabular">{m.events}</td>
              <td className="px-4 py-3 tabular text-short">{m.stopLossExits ?? 0}</td>
              <td className="px-4 py-3 tabular text-long">{m.profitProtectExits ?? 0}</td>
              <td className="px-4 py-3 tabular">
                ${m.totalInvested.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </td>
              <td className="px-4 py-3 tabular font-semibold">
                ${m.endingValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
              </td>
              <td className={cn("px-4 py-3 tabular", m.simpleReturnPct >= 0 ? "text-long" : "text-short")}>
                {m.simpleReturnPct > 0 ? "+" : ""}
                {m.simpleReturnPct.toFixed(2)}%
              </td>
              <td className={cn("px-4 py-3 tabular font-semibold", (m.xirrPct ?? 0) >= 0 ? "text-long" : "text-short")}>
                {m.xirrPct != null ? `${m.xirrPct > 0 ? "+" : ""}${m.xirrPct.toFixed(2)}%` : "—"}
              </td>
              <td className={cn("px-4 py-3 tabular", (m.sharpeRatio ?? 0) >= 0 ? "text-long" : "text-short")}>
                {m.sharpeRatio != null ? m.sharpeRatio.toFixed(2) : "—"}
              </td>
              <td className="px-4 py-3 tabular text-short">{m.maxDrawdownPct != null ? `${m.maxDrawdownPct.toFixed(2)}%` : "—"}</td>
              <td className={cn("px-4 py-3 tabular", (m.calmarRatio ?? 0) >= 0 ? "text-long" : "text-short")}>
                {m.calmarRatio != null ? m.calmarRatio.toFixed(2) : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="border-t border-base-800 px-4 py-2.5 text-[11px] text-[var(--text-muted)]">
        &ldquo;Live&rdquo; is the configuration currently running in the This Week / Backtest Results tabs. The trophy marks
        the highest Sharpe ratio (best risk-adjusted return) among these configurations for the selected strategy &mdash;
        not necessarily the highest raw return. Calmar = XIRR &divide; |max drawdown|, a return-per-unit-of-worst-case-pain
        measure that can rank differently from Sharpe (which measures return per unit of overall volatility, smooth chop
        included). All configurations share the same {maxPositionPct ?? 15}% max-position
        concentration cap and the same CGT-discount hold rule (a profit-take is deferred until a position has been
        held over 12 months) and are backtested over the same historical window, so differences come only from the
        stop-loss / trailing-stop settings.
      </div>
    </div>
  );
}

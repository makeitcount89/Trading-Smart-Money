// components/WalkForwardSweepTable.tsx
"use client";

import { Fragment, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, Award, ChevronDown, ChevronRight } from "lucide-react";
import type { WalkForwardAggregate, WalkForwardConfig, WalkForwardData } from "@/lib/types";
import { cn } from "@/lib/utils";

type SortKey = "consistencyScore" | "meanReturnPct" | "stdReturnPct" | "winRatePct" | "meanSharpeRatio" | "minReturnPct";
type StrategyKey = "proximityDCA" | "guppyProximityDCA";

const SORT_COLUMNS: { key: SortKey; label: string }[] = [
  { key: "winRatePct", label: "Win Rate" },
  { key: "meanReturnPct", label: "Mean Return" },
  { key: "stdReturnPct", label: "Return Std Dev" },
  { key: "minReturnPct", label: "Worst Window" },
  { key: "meanSharpeRatio", label: "Mean Sharpe" },
  { key: "consistencyScore", label: "Consistency" },
];

function formatRules(cfg: WalkForwardConfig): string {
  const stop = cfg.stopLossPct != null ? `-${cfg.stopLossPct.toFixed(0)}%` : "off";
  const trail =
    cfg.trailingStopArmPct != null && cfg.trailingStopPct != null
      ? `+${cfg.trailingStopArmPct.toFixed(0)}% → -${cfg.trailingStopPct.toFixed(0)}%`
      : "off";
  return `Stop ${stop} · Trail ${trail}`;
}

function PerWindowBreakdown({ agg }: { agg: WalkForwardAggregate }) {
  return (
    <tr>
      <td colSpan={10} className="bg-base-900/40 px-4 py-3">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[600px] text-xs">
            <thead>
              <tr className="text-left text-[10px] text-[var(--text-muted)]">
                <th className="py-1.5 pr-4 font-medium">Window</th>
                <th className="py-1.5 pr-4 font-medium">Period</th>
                <th className="py-1.5 pr-4 font-medium">Buys</th>
                <th className="py-1.5 pr-4 font-medium">Return</th>
                <th className="py-1.5 pr-4 font-medium">XIRR</th>
                <th className="py-1.5 pr-4 font-medium">Sharpe</th>
              </tr>
            </thead>
            <tbody>
              {agg.perWindow.map((w) => (
                <tr key={w.windowNumber} className="border-t border-base-800/60">
                  <td className="py-1.5 pr-4 tabular text-[var(--text-secondary)]">#{w.windowNumber}</td>
                  <td className="py-1.5 pr-4 tabular text-[var(--text-muted)]">
                    {w.startDate} &rarr; {w.endDate}
                  </td>
                  <td className="py-1.5 pr-4 tabular text-[var(--text-secondary)]">{w.events}</td>
                  <td className={cn("py-1.5 pr-4 tabular font-medium", w.simpleReturnPct >= 0 ? "text-long" : "text-short")}>
                    {w.simpleReturnPct > 0 ? "+" : ""}
                    {w.simpleReturnPct.toFixed(2)}%
                  </td>
                  <td className={cn("py-1.5 pr-4 tabular", (w.xirrPct ?? 0) >= 0 ? "text-long" : "text-short")}>
                    {w.xirrPct != null ? `${w.xirrPct > 0 ? "+" : ""}${w.xirrPct.toFixed(2)}%` : "—"}
                  </td>
                  <td className="py-1.5 pr-4 tabular text-[var(--text-secondary)]">
                    {w.sharpeRatio != null ? w.sharpeRatio.toFixed(2) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </td>
    </tr>
  );
}

export default function WalkForwardSweepTable({ data }: { data: WalkForwardData }) {
  const [strategy, setStrategy] = useState<StrategyKey>("proximityDCA");
  const [sortKey, setSortKey] = useState<SortKey>("consistencyScore");
  const [sortDesc, setSortDesc] = useState(true);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const rows = useMemo(() => {
    const withMetrics = data.configs
      .map((cfg) => ({ cfg, agg: cfg[strategy] }))
      .filter((r): r is { cfg: WalkForwardConfig; agg: WalkForwardAggregate } => r.agg !== null);
    return [...withMetrics].sort((a, b) => {
      const av = a.agg[sortKey];
      const bv = b.agg[sortKey];
      return sortDesc ? bv - av : av - bv;
    });
  }, [data.configs, strategy, sortKey, sortDesc]);

  const bestConsistencyName = useMemo(() => {
    let best: { name: string; score: number } | null = null;
    for (const cfg of data.configs) {
      const agg = cfg[strategy];
      if (agg && (best === null || agg.consistencyScore > best.score)) {
        best = { name: cfg.name, score: agg.consistencyScore };
      }
    }
    return best?.name ?? null;
  }, [data.configs, strategy]);

  function toggleSort(key: SortKey) {
    if (key === sortKey) {
      setSortDesc((d) => !d);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  }

  function toggleExpand(name: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  const oldest = data.windows[0];
  const newest = data.windows[data.windows.length - 1];

  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className="flex flex-col gap-2 border-b border-base-700 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-sm font-medium text-[var(--text-primary)]">
            Walk-Forward Consistency &mdash; {data.windowCount} overlapping {data.windowYears}-year windows, stepped{" "}
            {Math.round(data.stepWeeks / 4.345)} months apart
          </div>
          {oldest && newest && (
            <div className="mt-0.5 text-xs text-[var(--text-muted)]">
              {oldest.startDate} through {newest.endDate}
            </div>
          )}
        </div>
        <div className="flex gap-1 rounded-md border border-base-600 bg-base-800 p-0.5 text-xs">
          <button
            onClick={() => setStrategy("proximityDCA")}
            className={cn(
              "rounded px-2.5 py-1 font-medium transition-colors",
              strategy === "proximityDCA" ? "bg-smcBlue/20 text-smcBlue" : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
            )}
          >
            Pure Proximity
          </button>
          <button
            onClick={() => setStrategy("guppyProximityDCA")}
            className={cn(
              "rounded px-2.5 py-1 font-medium transition-colors",
              strategy === "guppyProximityDCA" ? "bg-emerald-400/20 text-emerald-400" : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
            )}
          >
            Guppy Filtered
          </button>
        </div>
      </div>

      <div className="border-b border-base-700 bg-[var(--status-warning)]/5 px-4 py-2.5 text-[11px] text-[var(--text-secondary)]">
        Each window shares roughly {Math.max(0, Math.round(data.windowYears * 12 - data.stepWeeks / 4.345))} months of history with
        its neighbor &mdash; they&apos;re a sensitivity check across different starting points and partially-overlapping regimes,
        not independent trials. Treat a config that wins here as more <em>robust</em>, not as proven to generalize to
        genuinely new, unseen market conditions.
      </div>

      <table className="w-full min-w-[1080px] text-sm">
        <thead>
          <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
            <th className="px-4 py-3 font-medium"></th>
            <th className="px-4 py-3 font-medium">Configuration</th>
            <th className="px-4 py-3 font-medium">Rules</th>
            <th className="px-4 py-3 font-medium">Windows</th>
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
          {rows.map(({ cfg, agg }) => (
            <Fragment key={cfg.name}>
              <tr
                onClick={() => toggleExpand(cfg.name)}
                className={cn(
                  "cursor-pointer border-b border-base-800 last:border-0 hover:bg-base-800/30 transition-colors",
                  cfg.isCurrent && "bg-smcBlue/5"
                )}
              >
                <td className="px-4 py-3 text-[var(--text-muted)]">
                  {expanded.has(cfg.name) ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </td>
                <td className="px-4 py-3 font-medium text-[var(--text-primary)]">
                  <div className="flex items-center gap-1.5">
                    {cfg.name}
                    {cfg.isCurrent && (
                      <span className="rounded-full border border-smcBlue/40 bg-smcBlue/10 px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide text-smcBlue">
                        Live
                      </span>
                    )}
                    {cfg.name === bestConsistencyName && (
                      <span title="Best consistency score (mean return / return std dev) in this comparison">
                        <Award size={12} className="text-[var(--status-warning)]" />
                      </span>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-[var(--text-muted)]">{formatRules(cfg)}</td>
                <td className="px-4 py-3 tabular text-[var(--text-muted)]">{agg.windowsTested}</td>
                <td className="px-4 py-3 tabular">{agg.winRatePct.toFixed(0)}%</td>
                <td className={cn("px-4 py-3 tabular font-semibold", agg.meanReturnPct >= 0 ? "text-long" : "text-short")}>
                  {agg.meanReturnPct > 0 ? "+" : ""}
                  {agg.meanReturnPct.toFixed(2)}%
                </td>
                <td className="px-4 py-3 tabular text-[var(--text-secondary)]">&plusmn;{agg.stdReturnPct.toFixed(2)}%</td>
                <td className={cn("px-4 py-3 tabular", agg.minReturnPct >= 0 ? "text-long" : "text-short")}>
                  {agg.minReturnPct > 0 ? "+" : ""}
                  {agg.minReturnPct.toFixed(2)}%
                </td>
                <td className={cn("px-4 py-3 tabular", agg.meanSharpeRatio >= 0 ? "text-long" : "text-short")}>
                  {agg.meanSharpeRatio.toFixed(2)}
                </td>
                <td className="px-4 py-3 tabular font-semibold text-smcBlue">{agg.consistencyScore.toFixed(2)}</td>
              </tr>
              {expanded.has(cfg.name) && <PerWindowBreakdown agg={agg} />}
            </Fragment>
          ))}
        </tbody>
      </table>
      <div className="border-t border-base-800 px-4 py-2.5 text-[11px] text-[var(--text-muted)]">
        Click a row to see its return, XIRR, and Sharpe for every individual window. Consistency = mean return &divide; return
        std dev across windows &mdash; a Sharpe-like score for how steady a config's outcome was across different starting
        points, not just how high it went in any one of them. Windows with no eligible signal that far back (a ticker hadn&apos;t
        listed yet, etc.) are excluded from a config&apos;s stats rather than counted as a 0% result.
      </div>
    </div>
  );
}

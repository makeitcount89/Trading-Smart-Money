// components/ThemeExposureTable.tsx
"use client";

import { useState } from "react";
import type { StrategyLegMeta, ThemeExposure } from "@/lib/types";
import { cn } from "@/lib/utils";
import { legColorClass } from "@/lib/legColors";

export default function ThemeExposureTable({ exposure, legs }: { exposure: ThemeExposure; legs: StrategyLegMeta[] }) {
  const [strategyKey, setStrategyKey] = useState<string>(legs[0]?.key ?? "");
  const rows = exposure[strategyKey] ?? [];
  const topSharePct = rows[0]?.sharePct ?? 0;
  const activeLeg = legs.find((l) => l.key === strategyKey);

  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className="flex flex-col gap-2 border-b border-base-700 px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="text-sm font-medium text-[var(--text-primary)]">Theme Exposure</div>
          <div className="mt-0.5 text-xs text-[var(--text-muted)]">
            Ending portfolio value grouped by a best-effort theme tag per ticker, so correlated holdings (e.g. several gold
            miners) read as one exposure rather than unrelated-looking individual positions.
          </div>
        </div>
        <div className="flex flex-wrap gap-1 rounded-md border border-base-600 bg-base-800 p-0.5 text-xs">
          {legs.map((leg, i) => {
            const color = legColorClass(i);
            return (
              <button
                key={leg.key}
                onClick={() => setStrategyKey(leg.key)}
                className={cn(
                  "rounded px-2.5 py-1 font-medium transition-colors",
                  strategyKey === leg.key ? color.toggleActive : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                )}
              >
                {leg.label}
              </button>
            );
          })}
        </div>
      </div>

      {activeLeg?.description && (
        <div className="border-b border-base-800 px-4 py-2 text-[11px] text-[var(--text-muted)]">{activeLeg.description}</div>
      )}

      {rows.length === 0 ? (
        <div className="px-4 py-6 text-center text-sm text-[var(--text-muted)]">No holdings yet for this strategy.</div>
      ) : (
        <table className="w-full min-w-[920px] text-sm">
          <thead>
            <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
              <th className="px-4 py-3 font-medium">Theme</th>
              <th className="px-4 py-3 font-medium">Tickers</th>
              <th className="px-4 py-3 font-medium">Invested</th>
              <th className="px-4 py-3 font-medium">Ending Value</th>
              <th className="px-4 py-3 font-medium">Return</th>
              <th className="px-4 py-3 font-medium">$/Year</th>
              <th className="px-4 py-3 font-medium">Share</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.theme} className="border-b border-base-800 last:border-0 hover:bg-base-800/30 transition-colors">
                <td className="px-4 py-3 font-medium text-[var(--text-primary)]">{r.theme}</td>
                <td className="px-4 py-3 text-xs text-[var(--text-muted)]">{r.tickers.join(", ")}</td>
                <td className="px-4 py-3 tabular text-[var(--text-secondary)]">
                  ${r.investedValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </td>
                <td className="px-4 py-3 tabular font-semibold">
                  ${r.endingValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </td>
                <td className={cn("px-4 py-3 tabular", r.gainValue >= 0 ? "text-long" : "text-short")}>
                  {r.gainValue >= 0 ? "+" : ""}
                  {r.returnPct.toFixed(1)}%
                  <span className="ml-1 text-[10px] text-[var(--text-muted)]">
                    ({r.gainValue >= 0 ? "+" : ""}${r.gainValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })})
                  </span>
                </td>
                <td className={cn("px-4 py-3 tabular", r.annualGainValue >= 0 ? "text-long" : "text-short")}>
                  {r.annualGainValue >= 0 ? "+" : ""}
                  ${r.annualGainValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </td>
                <td className="px-4 py-3 tabular">
                  <span
                    className={cn(
                      "font-semibold",
                      r.sharePct === topSharePct ? "text-[var(--status-warning)]" : "text-[var(--text-primary)]"
                    )}
                  >
                    {r.sharePct.toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <div className="border-t border-base-800 px-4 py-2.5 text-[11px] text-[var(--text-muted)]">
        Themes are a manual, best-effort classification (not authoritative security/GICS data) meant to surface
        concentration risk that individual-ticker views can hide -- e.g. holding 6 different gold miners isn&apos;t
        diversification if gold pulls back, they&apos;ll likely move together. The largest exposure is highlighted.
        $/Year is gainValue &divide; window years -- a simple average, not a compounding growth rate.
      </div>
    </div>
  );
}

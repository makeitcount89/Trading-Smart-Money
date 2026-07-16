// components/ThemeExposureTable.tsx
"use client";

import { useState } from "react";
import type { ThemeExposure } from "@/lib/types";
import { cn } from "@/lib/utils";

type StrategyKey = "proximityDCA" | "guppyProximityDCA";

export default function ThemeExposureTable({ exposure }: { exposure: ThemeExposure }) {
  const [strategy, setStrategy] = useState<StrategyKey>("proximityDCA");
  const rows = exposure[strategy];
  const topSharePct = rows[0]?.sharePct ?? 0;

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

      {rows.length === 0 ? (
        <div className="px-4 py-6 text-center text-sm text-[var(--text-muted)]">No holdings yet for this strategy.</div>
      ) : (
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
              <th className="px-4 py-3 font-medium">Theme</th>
              <th className="px-4 py-3 font-medium">Tickers</th>
              <th className="px-4 py-3 font-medium">Ending Value</th>
              <th className="px-4 py-3 font-medium">Share</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.theme} className="border-b border-base-800 last:border-0 hover:bg-base-800/30 transition-colors">
                <td className="px-4 py-3 font-medium text-[var(--text-primary)]">{r.theme}</td>
                <td className="px-4 py-3 text-xs text-[var(--text-muted)]">{r.tickers.join(", ")}</td>
                <td className="px-4 py-3 tabular">
                  ${r.endingValue.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
                </td>
                <td className="px-4 py-3 tabular">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        "font-semibold",
                        r.sharePct === topSharePct ? "text-[var(--status-warning)]" : "text-[var(--text-primary)]"
                      )}
                    >
                      {r.sharePct.toFixed(1)}%
                    </span>
                  </div>
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
      </div>
    </div>
  );
}

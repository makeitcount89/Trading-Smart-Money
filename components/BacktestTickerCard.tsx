// components/BacktestTickerCard.tsx
import { AlertTriangle } from "lucide-react";
import type { BacktestTickerResult } from "@/lib/types";
import { cn } from "@/lib/utils";

export default function BacktestTickerCard({ ticker }: { ticker: BacktestTickerResult }) {
  if (!ticker.ok) {
    return (
      <div className="rounded-xl border border-base-700 bg-base-850 p-5">
        <div className="text-sm font-medium">{ticker.ticker}</div>
        <div className="mt-2 flex items-center gap-2 text-xs text-short">
          <AlertTriangle size={14} />
          {ticker.error ?? "Failed to load"}
        </div>
      </div>
    );
  }

  const strategy = ticker.strategies.proximityDCA;

  return (
    <div className="rounded-xl border border-base-700 bg-base-850 p-5 flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between border-b border-base-800 pb-2 mb-3">
          <h3 className="text-sm font-semibold text-smcBlue">{ticker.ticker}</h3>
          <span className="tabular text-xs text-[var(--text-muted)]">
            As of {ticker.asOfDate} @ ${ticker.asOfPrice?.toFixed(2) ?? "—"}
          </span>
        </div>

        {/* Unified performance layout instead of the 6-grid split */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
          <div className="rounded-lg border border-base-700 bg-base-800/60 px-2 py-2 text-center">
            <div className="text-[var(--text-muted)] text-[10px]">Total Buys</div>
            <div className="mt-1 tabular font-semibold text-[var(--text-primary)]">{strategy.events} hits</div>
          </div>
          <div className="rounded-lg border border-base-700 bg-base-800/60 px-2 py-2 text-center">
            <div className="text-[var(--text-muted)] text-[10px]">Total Invested</div>
            <div className="mt-1 tabular font-semibold text-[var(--text-primary)]">${strategy.totalInvested.toFixed(2)}</div>
          </div>
          <div className="rounded-lg border border-base-700 bg-base-800/60 px-2 py-2 text-center">
            <div className="text-[var(--text-muted)] text-[10px]">Ending Value</div>
            <div className="mt-1 tabular font-semibold text-[var(--text-primary)]">${strategy.endingValue.toFixed(2)}</div>
          </div>
          <div className="rounded-lg border border-base-700 bg-base-800/60 px-2 py-2 text-center">
            <div className="text-[var(--text-muted)] text-[10px]">Asset XIRR</div>
            <div className={cn("mt-1 tabular font-bold", strategy.xirrPct !== null && strategy.xirrPct >= 0 ? "text-long" : "text-short")}>
              {strategy.xirrPct != null ? `${strategy.xirrPct.toFixed(1)}%` : "—"}
            </div>
          </div>
        </div>

        {/* Chronological order routing history */}
        <div className="mt-4">
          <div className="mb-1.5 text-[11px] font-medium text-[var(--text-muted)] uppercase tracking-wider">
            Chronological Routing Logs
          </div>
          {strategy.eventDetail && strategy.eventDetail.length > 0 ? (
            <div className="space-y-1 max-h-40 overflow-y-auto rounded-lg border border-base-800 bg-base-900/40 p-1.5 scrollbar-thin">
              {strategy.eventDetail.map((e, i) => (
                <div
                  key={i}
                  className="flex flex-wrap items-center justify-between gap-1 rounded-md border border-smcBlue-muted bg-smcBlue-muted/10 px-2 py-1 text-[11px] font-mono"
                >
                  <span className="flex items-center gap-1.5 text-[var(--text-secondary)]">
                    {e.date} &rarr; Bought at ${e.price.toFixed(2)}
                  </span>
                  <span className={cn("text-[10px] font-semibold", e.proximityPct <= 0 ? "text-long font-bold" : "text-[var(--text-muted)]")}>
                    Proximity: {e.proximityPct > 0 ? "+" : ""}{e.proximityPct.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-[11px] text-[var(--text-muted)] italic py-3 text-center bg-base-800/20 rounded-lg border border-dashed border-base-700">
              No capital routed to this ticker during this timeframe window.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
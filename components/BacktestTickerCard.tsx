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

  // Extract both strategies from the ticker data object mapping
  const s1 = ticker.strategies.proximityDCA;
  const s2 = ticker.strategies.guppyProximityDCA;

  // Reusable sub-component helper to keep rendering DRY
  const StrategyPerformanceMetrics = ({ 
    strategy, 
    label, 
    colorClass 
  }: { 
    strategy: typeof s1; 
    label: string; 
    colorClass: string; 
  }) => {
    if (!strategy) return null;
    
    return (
      <div className="space-y-2 mt-3 border-t border-base-800/60 pt-3 first:border-t-0 first:pt-0">
        <div className="flex items-center justify-between">
          <span className={cn("text-xs font-medium", colorClass)}>{label}</span>
          <span className={cn("text-xs font-mono font-bold", strategy.xirrPct !== null && strategy.xirrPct >= 0 ? "text-long" : "text-short")}>
            XIRR: {strategy.xirrPct != null ? `${strategy.xirrPct > 0 ? "+" : ""}${strategy.xirrPct.toFixed(1)}%` : "—"}
          </span>
        </div>
        
        <div className="grid grid-cols-5 gap-1.5 text-center text-[11px]">
          <div className="rounded-md border border-base-700 bg-base-800/40 py-1">
            <div className="text-[var(--text-muted)] text-[9px]">Hits</div>
            <div className="font-semibold text-[var(--text-primary)]">{strategy.events}</div>
          </div>
          <div className="rounded-md border border-base-700 bg-base-800/40 py-1">
            <div className="text-[var(--text-muted)] text-[9px]">Stop-Loss</div>
            <div className="font-semibold text-short">{strategy.stopLossExits ?? 0}</div>
          </div>
          <div className="rounded-md border border-base-700 bg-base-800/40 py-1">
            <div className="text-[var(--text-muted)] text-[9px]">Profit-Take</div>
            <div className="font-semibold text-long">{strategy.profitProtectExits ?? 0}</div>
          </div>
          <div className="rounded-md border border-base-700 bg-base-800/40 py-1">
            <div className="text-[var(--text-muted)] text-[9px]">Invested</div>
            <div className="font-semibold text-[var(--text-primary)]">${strategy.totalInvested.toFixed(0)}</div>
          </div>
          <div className="rounded-md border border-base-700 bg-base-800/40 py-1">
            <div className="text-[var(--text-muted)] text-[9px]">Value</div>
            <div className="font-semibold text-[var(--text-primary)]">${strategy.endingValue.toFixed(0)}</div>
          </div>
        </div>

        {/* Chronological order routing history for this specific subset */}
        {strategy.eventDetail && strategy.eventDetail.length > 0 && (
          <div className="mt-2">
            <div className="space-y-1 max-h-24 overflow-y-auto rounded-md border border-base-800 bg-base-900/30 p-1 scrollbar-thin">
              {strategy.eventDetail.map((e, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between rounded px-1.5 py-0.5 text-[10px] font-mono bg-base-800/20 text-[var(--text-secondary)] border border-base-800"
                >
                  <span>{e.date} @ ${e.price.toFixed(2)}</span>
                  <span className={cn("font-medium", e.proximityPct <= 0 ? "text-long" : "text-[var(--text-muted)]")}>
                    {e.proximityPct > 0 ? "+" : ""}{e.proximityPct.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <div className="rounded-xl border border-base-700 bg-base-850 p-5 flex flex-col justify-between hover:border-base-600 transition-colors">
      <div>
        <div className="flex items-center justify-between border-b border-base-800 pb-2 mb-3">
          <h3 className="text-sm font-bold text-[var(--text-primary)]">{ticker.ticker}</h3>
          <span className="tabular text-[11px] text-[var(--text-muted)]">
            {ticker.asOfDate} &bull; ${ticker.asOfPrice?.toFixed(2) ?? "—"}
          </span>
        </div>

        <div className="space-y-4">
          {/* Render Pure Proximity Mode Metrics */}
          <StrategyPerformanceMetrics 
            strategy={s1} 
            label="Pure Proximity" 
            colorClass="text-smcBlue" 
          />

          {/* Render Guppy Filtered Mode Metrics if available */}
          {s2 && (
            <StrategyPerformanceMetrics 
              strategy={s2} 
              label="Guppy Filtered" 
              colorClass="text-emerald-400" 
            />
          )}
        </div>
      </div>
    </div>
  );
}
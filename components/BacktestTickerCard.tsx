import { AlertTriangle } from "lucide-react";
import type { BacktestStrategyKey, BacktestTickerResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const STRATEGY_LABELS: Record<BacktestStrategyKey, string> = {
  retrace: "Retrace (any)",
  retraceSwing: "Retrace (swing)",
  retraceInternal: "Retrace (internal)",
  fixedWeeklyDca: "Fixed DCA",
  randomWeeklyDca: "Random DCA",
  lumpSum: "Lump sum",
};
const STRATEGY_ORDER: BacktestStrategyKey[] = [
  "retrace",
  "retraceSwing",
  "retraceInternal",
  "fixedWeeklyDca",
  "randomWeeklyDca",
  "lumpSum",
];

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

  const retrace = ticker.strategies.retrace;

  return (
    <div className="rounded-xl border border-base-700 bg-base-850 p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">{ticker.ticker}</h3>
        <span className="tabular text-xs text-[var(--text-muted)]">as of {ticker.asOfDate}</span>
      </div>

      <div className="mt-3 grid grid-cols-3 gap-2 text-xs sm:grid-cols-6">
        {STRATEGY_ORDER.map((key) => {
          const s = ticker.strategies[key];
          return (
            <div key={key} className="rounded-lg border border-base-700 bg-base-800/60 px-2 py-2 text-center">
              <div className="text-[var(--text-muted)]">{STRATEGY_LABELS[key]}</div>
              <div className="mt-1 tabular font-semibold">{s?.xirrPct != null ? `${s.xirrPct.toFixed(1)}%` : "—"}</div>
              <div className="tabular text-[10px] text-[var(--text-muted)]">{s?.events ?? 0} buys</div>
            </div>
          );
        })}
      </div>

      {retrace?.eventDetail && retrace.eventDetail.length > 0 && (
        <div className="mt-3">
          <div className="mb-1 text-[11px] font-medium text-[var(--text-muted)]">Retrace events</div>
          <div className="space-y-1">
            {retrace.eventDetail.map((e, i) => (
              <div
                key={i}
                className="flex flex-wrap items-center justify-between gap-1 rounded-md border border-smcBlue-muted bg-smcBlue-muted/20 px-2 py-1 text-[11px]"
              >
                <span className="flex items-center gap-1.5">
                  <span
                    className={cn(
                      "rounded px-1 py-0.5 text-[9px] font-semibold uppercase tracking-wide",
                      e.kind === "swing" ? "bg-base-700 text-[var(--text-secondary)]" : "bg-smcBlue-muted text-smcBlue"
                    )}
                  >
                    {e.kind}
                  </span>
                  {e.date} @ {e.price.toFixed(3)}
                </span>
                <span className="text-[var(--text-muted)]">
                  OB {e.obBottom.toFixed(3)}–{e.obTop.toFixed(3)} (formed {e.obFormedDate})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

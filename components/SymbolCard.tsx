import { AlertTriangle } from "lucide-react";
import type { OrderBlockZone, SymbolResult } from "@/lib/types";
import { cn } from "@/lib/utils";

function ZoneRow({ zone, bullish }: { zone: OrderBlockZone; bullish: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center justify-between rounded-lg border px-3 py-2 text-xs",
        bullish ? "border-smcBlue-muted bg-smcBlue-muted/30" : "border-short-muted bg-short-muted/20"
      )}
    >
      <div>
        <div className="font-medium text-[var(--text-primary)]">
          {zone.bottom.toFixed(3)} – {zone.top.toFixed(3)}
        </div>
        <div className="text-[var(--text-muted)]">
          {zone.kind} · formed {zone.date}
        </div>
      </div>
      <div className={cn("font-semibold", bullish ? "text-smcBlue" : "text-short")}>
        {zone.insideZone ? "Inside" : `${zone.distancePct.toFixed(2)}%`}
      </div>
    </div>
  );
}

export default function SymbolCard({ symbol }: { symbol: SymbolResult }) {
  if (!symbol.ok) {
    return (
      <div className="rounded-xl border border-base-700 bg-base-850 p-5">
        <div className="flex items-center gap-2 text-sm font-medium">{symbol.ticker}</div>
        <div className="mt-3 flex items-center gap-2 text-xs text-short">
          <AlertTriangle size={14} />
          {symbol.error ?? "Failed to load data"}
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-base-700 bg-base-850 p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-[var(--text-primary)]">{symbol.ticker}</h3>
        <span className="tabular text-sm text-[var(--text-secondary)]">
          {symbol.lastPrice != null ? symbol.lastPrice.toFixed(3) : "—"}
        </span>
      </div>
      <div className="mt-1 text-xs text-[var(--text-muted)]">Last bar {symbol.lastBarDate ?? "—"}</div>

      <div className="mt-4">
        <div className="mb-2 text-xs font-medium text-[var(--text-muted)]">Blue (bullish) order blocks</div>
        {symbol.bullishOrderBlocks.length === 0 ? (
          <div className="text-xs text-[var(--text-muted)]">No active bullish order block.</div>
        ) : (
          <div className="space-y-2">
            {symbol.bullishOrderBlocks.map((z, i) => (
              <ZoneRow key={i} zone={z} bullish />
            ))}
          </div>
        )}
      </div>

      <div className="mt-4">
        <div className="mb-2 text-xs font-medium text-[var(--text-muted)]">Red (bearish) order blocks</div>
        {symbol.bearishOrderBlocks.length === 0 ? (
          <div className="text-xs text-[var(--text-muted)]">No active bearish order block.</div>
        ) : (
          <div className="space-y-2">
            {symbol.bearishOrderBlocks.map((z, i) => (
              <ZoneRow key={i} zone={z} bullish={false} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

import { AlertTriangle, Minus, TrendingDown, TrendingUp } from "lucide-react";
import type { GuppyTrendSnapshot, OrderBlockZone, SymbolResult, TimeframeKey, TimeframeResult } from "@/lib/types";
import { cn } from "@/lib/utils";

const TIMEFRAME_LABELS: Record<TimeframeKey, string> = {
  "1d": "Daily",
  "1wk": "Weekly",
};

function GuppyStrip({ trend }: { trend: GuppyTrendSnapshot | null | undefined }) {
  if (!trend) return null;
  const entries: { key: keyof GuppyTrendSnapshot; label: string }[] = [
    { key: "sixMonth", label: "6mo" },
    { key: "oneYear", label: "1yr" },
    { key: "threeYear", label: "3yr" },
  ];
  return (
    <div className="mt-1 flex items-center gap-2 text-[10px]">
      {entries.map(({ key, label }) => {
        const v = trend[key];
        const color = v == null ? "text-[var(--text-muted)]" : v ? "text-long" : "text-short";
        return (
          <span key={key} className={cn("inline-flex items-center gap-0.5 font-medium", color)}>
            {v == null ? <Minus size={9} /> : v ? <TrendingUp size={9} /> : <TrendingDown size={9} />}
            {label}
          </span>
        );
      })}
    </div>
  );
}

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

function TimeframeSection({ tfKey, tf }: { tfKey: TimeframeKey; tf: TimeframeResult | null | undefined }) {
  if (!tf) {
    return (
      <div>
        <div className="mb-2 text-xs font-medium text-[var(--text-muted)]">{TIMEFRAME_LABELS[tfKey]}</div>
        <div className="text-xs text-[var(--text-muted)]">No data.</div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <div className="text-xs font-medium text-[var(--text-primary)]">{TIMEFRAME_LABELS[tfKey]}</div>
        <div className="tabular text-xs text-[var(--text-muted)]">
          {tf.lastPrice.toFixed(3)} · {tf.lastBarDate}
        </div>
      </div>

      <GuppyStrip trend={tf.guppyTrend} />

      {tf.bullishOrderBlocks.length === 0 ? (
        <div className="text-xs text-[var(--text-muted)]">No active blue order block.</div>
      ) : (
        <div className="space-y-2">
          {tf.bullishOrderBlocks.map((z, i) => (
            <ZoneRow key={i} zone={z} bullish />
          ))}
        </div>
      )}

      {tf.bearishOrderBlocks.length > 0 && (
        <div className="mt-2 space-y-2">
          {tf.bearishOrderBlocks.map((z, i) => (
            <ZoneRow key={i} zone={z} bullish={false} />
          ))}
        </div>
      )}
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
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">{symbol.ticker}</h3>
      {symbol.error && <div className="mt-1 text-[11px] text-[var(--text-muted)]">{symbol.error}</div>}

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <TimeframeSection tfKey="1d" tf={symbol.timeframes["1d"]} />
        <TimeframeSection tfKey="1wk" tf={symbol.timeframes["1wk"]} />
      </div>
    </div>
  );
}

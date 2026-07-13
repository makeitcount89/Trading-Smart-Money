"use client";

import { useCallback, useEffect, useState } from "react";
import { AlertTriangle, Crosshair, RefreshCw } from "lucide-react";
import type { SmcData } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import StatTile from "@/components/StatTile";
import RankingTable from "@/components/RankingTable";
import SymbolCard from "@/components/SymbolCard";

export default function Home() {
  const [data, setData] = useState<SmcData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // Bundle lives in /public, so this is a same-origin static fetch -- no CORS,
      // no API round trip. The cache-busting query param forces a fresh read past
      // any browser/CDN cache when the user explicitly asks to re-query.
      const res = await fetch(`/smc_data.json?t=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`Failed to load smc_data.json (${res.status})`);
      const json: SmcData = await res.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error loading SMC data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const closest = data?.symbols.find((s) => s.ticker === data.closestSymbol) ?? null;
  const withActiveOb = data?.symbols.filter((s) => s.nearestBullishOrderBlock).length ?? 0;

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <Crosshair size={22} className="text-smcBlue" />
            <h1 className="text-xl font-bold tracking-tight">Smart Money Concepts — Multi-Stock Dashboard</h1>
          </div>
          <p className="mt-1 text-sm text-[var(--text-secondary)]">
            LuxAlgo Smart Money Concepts (swing/internal structure, BOS/CHoCH, order blocks) ported to Python and
            run daily across a configurable stock universe, ranked by proximity to each stock&apos;s nearest active
            bullish (blue) order block.
            {data?.meta && <> · universe: {data.meta.universe.join(", ")}</>}
          </p>
        </div>
        <div className="flex flex-col items-start gap-2 sm:items-end">
          {data?.generatedAt && (
            <div className="text-xs text-[var(--text-muted)]">Data generated {formatDateTime(data.generatedAt)}</div>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 rounded-md border border-base-600 bg-base-800 px-3 py-1.5 text-xs font-medium text-[var(--text-primary)] transition hover:bg-base-700 disabled:opacity-50"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </header>

      {error && (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-short-muted bg-short-muted/30 px-4 py-3 text-sm text-short">
          <AlertTriangle size={16} />
          {error}
        </div>
      )}

      {data?.status === "awaiting_first_run" && (
        <div className="mb-6 flex items-center gap-2 rounded-lg border border-base-600 bg-base-800 px-4 py-3 text-sm text-[var(--text-secondary)]">
          <AlertTriangle size={16} className="text-[var(--status-warning)]" />
          Awaiting the first scheduled engine run. This dashboard will populate automatically once{" "}
          <code className="rounded bg-base-700 px-1 py-0.5 text-xs">run_smc.yml</code> completes on its next daily
          cron, or you can trigger it manually from the Actions tab.
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <StatTile
          label="Closest to a blue order block"
          value={closest ? closest.ticker : "—"}
          icon={<Crosshair size={14} />}
          tone="good"
        />
        <StatTile
          label="Distance to nearest zone"
          value={
            closest?.nearestBullishOrderBlock
              ? closest.nearestBullishOrderBlock.insideZone
                ? "Inside zone"
                : `${closest.nearestBullishOrderBlock.distancePct.toFixed(2)}%`
              : "—"
          }
          icon={<Crosshair size={14} />}
        />
        <StatTile
          label="Symbols with an active blue OB"
          value={data ? `${withActiveOb} / ${data.symbols.length}` : "—"}
          icon={<Crosshair size={14} />}
        />
      </div>

      <div className="mt-4">
        <RankingTable symbols={data?.symbols ?? []} />
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 lg:grid-cols-2">
        {(data?.symbols ?? []).map((s) => (
          <SymbolCard key={s.ticker} symbol={s} />
        ))}
      </div>

      <footer className="mt-8 text-center text-xs text-[var(--text-muted)]">
        Structure/order-block detection derived from LuxAlgo&apos;s Smart Money Concepts indicator (CC BY-NC-SA 4.0).
        For research purposes only. Not financial advice.
      </footer>
    </main>
  );
}

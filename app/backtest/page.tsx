"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, FlaskConical, RefreshCw } from "lucide-react";
import type { BacktestData } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";
import BacktestSummaryTable from "@/components/BacktestSummaryTable";
import BacktestTickerCard from "@/components/BacktestTickerCard";

export default function BacktestPage() {
  const [data, setData] = useState<BacktestData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/backtest_data.json?t=${Date.now()}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`Failed to load backtest_data.json (${res.status})`);
      const json: BacktestData = await res.json();
      setData(json);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error loading backtest data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <header className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <Link
            href="/"
            className="mb-2 flex items-center gap-1 text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <ArrowLeft size={12} /> Back to dashboard
          </Link>
          <div className="flex items-center gap-2">
            <FlaskConical size={22} className="text-smcBlue" />
            <h1 className="text-xl font-bold tracking-tight">Weekly OB Proximity Backtest</h1>
          </div>
          <p className="mt-1 max-w-3xl text-sm text-[var(--text-secondary)]">
            {data?.meta?.note ?? "Routing fixed weekly DCA capital dynamically into the universe asset closest to its latest weekly bullish order block."}
            {data?.meta && <> &middot; Universe: {data.meta.universe.join(", ")}</>}
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
          Awaiting the first backtest run. Trigger{" "}
          <code className="rounded bg-base-700 px-1 py-0.5 text-xs">run_backtest.yml</code> from the Actions tab.
        </div>
      )}

      {data && data.tickers.length > 0 && (
        <>
          <div className="mb-2 text-xs text-[var(--text-muted)]">
            Strategy: {data.meta.strategyName} &middot; Window: {data.meta.windowYears} Years &middot; Allocation: ${data.meta.amountPerWeek}/week
            {data.meta.riskFreeRatePct != null && <> &middot; Sharpe risk-free rate: {data.meta.riskFreeRatePct}%</>}
          </div>
          
          <BacktestSummaryTable pooled={data.pooled} title={`Pooled Portfolio Performance (${data.tickers.length} Tickers)`} />

          <div className="mb-3 mt-6 text-sm font-semibold uppercase tracking-wide text-[var(--text-muted)]">
            Per-ticker detail
          </div>
          <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
            {data.tickers.map((t) => (
              <BacktestTickerCard key={t.ticker} ticker={t} />
            ))}
          </div>
        </>
      )}

      <footer className="mt-8 text-center text-xs text-[var(--text-muted)]">
        For research purposes only. Not financial advice.
      </footer>
    </main>
  );
}
"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, ArrowLeft, CalendarClock, FlaskConical, RefreshCw, SlidersHorizontal } from "lucide-react";
import type { BacktestData } from "@/lib/types";
import { cn, formatDateTime } from "@/lib/utils";
import BacktestSummaryTable from "@/components/BacktestSummaryTable";
import BacktestTickerCard from "@/components/BacktestTickerCard";
import WeeklyRunPanel from "@/components/WeeklyRunPanel";
import ExitRuleSweepTable from "@/components/ExitRuleSweepTable";
import WalkForwardSweepTable from "@/components/WalkForwardSweepTable";
import ThemeExposureTable from "@/components/ThemeExposureTable";

type Tab = "weekly" | "backtest" | "sweep";
type SweepView = "single" | "walkForward";

export default function BacktestPage() {
  const [data, setData] = useState<BacktestData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("weekly");
  const [sweepView, setSweepView] = useState<SweepView>("single");

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
          <div className="mb-4 flex gap-1 border-b border-base-700">
            <button
              onClick={() => setTab("weekly")}
              className={cn(
                "flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                tab === "weekly"
                  ? "border-smcBlue text-smcBlue"
                  : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              )}
            >
              <CalendarClock size={14} />
              This Week
            </button>
            <button
              onClick={() => setTab("backtest")}
              className={cn(
                "flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                tab === "backtest"
                  ? "border-smcBlue text-smcBlue"
                  : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              )}
            >
              <FlaskConical size={14} />
              Backtest Results
            </button>
            <button
              onClick={() => setTab("sweep")}
              className={cn(
                "flex items-center gap-1.5 border-b-2 px-3 py-2 text-sm font-medium transition-colors",
                tab === "sweep"
                  ? "border-smcBlue text-smcBlue"
                  : "border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
              )}
            >
              <SlidersHorizontal size={14} />
              Exit Rule Sweep
            </button>
          </div>

          {tab === "weekly" && data.weeklyRun && <WeeklyRunPanel weeklyRun={data.weeklyRun} meta={data.meta} />}
          {tab === "weekly" && !data.weeklyRun && (
            <div className="rounded-lg border border-base-600 bg-base-800 px-4 py-3 text-sm text-[var(--text-secondary)]">
              This data set was generated before the Weekly Run tab was added. Re-run the backtest to populate it.
            </div>
          )}

          {tab === "backtest" && (
            <>
              <div className="mb-2 text-xs text-[var(--text-muted)]">
                Strategy: {data.meta.strategyName} &middot; Window: {data.meta.windowYears} Years &middot; Allocation: ${data.meta.amountPerWeek}/week
                {data.meta.riskFreeRatePct != null && <> &middot; Sharpe risk-free rate: {data.meta.riskFreeRatePct}%</>}
              </div>

              <BacktestSummaryTable pooled={data.pooled} title={`Pooled Portfolio Performance (${data.tickers.length} Tickers)`} />

              {data.themeExposure && (
                <div className="mt-6">
                  <ThemeExposureTable exposure={data.themeExposure} />
                </div>
              )}

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

          {tab === "sweep" && (
            <>
              <div className="mb-4 flex gap-1 rounded-md border border-base-600 bg-base-800 p-0.5 text-xs w-fit">
                <button
                  onClick={() => setSweepView("single")}
                  className={cn(
                    "rounded px-3 py-1.5 font-medium transition-colors",
                    sweepView === "single" ? "bg-smcBlue/20 text-smcBlue" : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                  )}
                >
                  Single Window ({data.meta.windowYears}yr)
                </button>
                <button
                  onClick={() => setSweepView("walkForward")}
                  className={cn(
                    "rounded px-3 py-1.5 font-medium transition-colors",
                    sweepView === "walkForward" ? "bg-smcBlue/20 text-smcBlue" : "text-[var(--text-muted)] hover:text-[var(--text-secondary)]"
                  )}
                >
                  Walk-Forward{data.walkForward ? ` (${data.walkForward.windowCount}x)` : ""}
                </button>
              </div>

              {sweepView === "single" && data.exitRuleSweep && data.exitRuleSweep.length > 0 && (
                <ExitRuleSweepTable configs={data.exitRuleSweep} maxPositionPct={data.meta.maxPositionPct} />
              )}
              {sweepView === "single" && (!data.exitRuleSweep || data.exitRuleSweep.length === 0) && (
                <div className="rounded-lg border border-base-600 bg-base-800 px-4 py-3 text-sm text-[var(--text-secondary)]">
                  This data set was generated before the Exit Rule Sweep was added. Re-run the backtest to populate it.
                </div>
              )}

              {sweepView === "walkForward" && data.walkForward && data.walkForward.configs.length > 0 && (
                <WalkForwardSweepTable data={data.walkForward} baselineData={data.walkForwardBaseline} newTickers={data.meta.newTickers} />
              )}
              {sweepView === "walkForward" && (!data.walkForward || data.walkForward.configs.length === 0) && (
                <div className="rounded-lg border border-base-600 bg-base-800 px-4 py-3 text-sm text-[var(--text-secondary)]">
                  This data set was generated before the Walk-Forward Sweep was added. Re-run the backtest to populate it.
                </div>
              )}
            </>
          )}
        </>
      )}

      <footer className="mt-8 text-center text-xs text-[var(--text-muted)]">
        For research purposes only. Not financial advice.
      </footer>
    </main>
  );
}
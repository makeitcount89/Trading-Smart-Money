// components/WeeklyRunPanel.tsx
import { AlertTriangle, Lock, ShoppingCart, ShieldAlert, TrendingUp } from "lucide-react";
import type { BacktestMeta, StrategyLegMeta, WeeklyRun, WeeklyRunPosition, WeeklyRunStrategy } from "@/lib/types";
import { cn } from "@/lib/utils";
import { legColorClass } from "@/lib/legColors";

function RecommendedBuyCard({
  strategy,
  label,
  colorClass,
  accentClass,
}: {
  strategy: WeeklyRunStrategy;
  label: string;
  colorClass: string;
  accentClass: string;
}) {
  const rec = strategy.recommendedBuy;
  return (
    <div className={cn("rounded-xl border bg-base-850 p-4", accentClass)}>
      <div className={cn("mb-2 flex items-center gap-1.5 text-xs font-medium", colorClass)}>
        <ShoppingCart size={13} />
        {label}
      </div>
      {rec ? (
        <div className="flex items-baseline justify-between">
          <div>
            <div className="text-lg font-bold text-[var(--text-primary)]">{rec.ticker}</div>
            <div className="text-xs text-[var(--text-muted)]">
              @ ${rec.price.toFixed(2)} &middot;{" "}
              {rec.insideZone ? (
                <span className="text-smcBlue">Inside zone</span>
              ) : (
                `${rec.proximityPct.toFixed(2)}% from order block`
              )}
            </div>
          </div>
          <div className="text-right text-xs text-[var(--text-muted)]">
            Buy this week's<br />$50 allocation
          </div>
        </div>
      ) : (
        <div className="text-sm text-[var(--text-muted)]">
          No eligible candidate this week (either no valid signal, or every candidate already exceeds the position cap).
        </div>
      )}
    </div>
  );
}

function PositionRow({ position }: { position: WeeklyRunPosition }) {
  const p = position;
  const nearStopLoss = p.distanceToStopLossPct != null && p.distanceToStopLossPct <= 5;
  const nearTrailingStop = p.distanceToTrailingStopPct != null && p.distanceToTrailingStopPct <= 5;
  const nearCap = p.positionSharePct != null && p.positionSharePct >= 12;

  return (
    <tr className="border-b border-base-800 last:border-0 hover:bg-base-800/30 transition-colors">
      <td className="px-3 py-2.5 font-medium text-[var(--text-primary)]">{p.ticker}</td>
      <td className="px-3 py-2.5 tabular text-[var(--text-secondary)]">
        {p.lastBuyPrice != null ? `$${p.lastBuyPrice.toFixed(2)}` : "—"}
      </td>
      <td className="px-3 py-2.5 tabular text-[var(--text-secondary)]">${p.currentPrice.toFixed(2)}</td>
      <td className={cn("px-3 py-2.5 tabular", (p.unrealizedPnlPct ?? 0) >= 0 ? "text-long" : "text-short")}>
        {p.unrealizedPnlPct != null ? `${p.unrealizedPnlPct > 0 ? "+" : ""}${p.unrealizedPnlPct.toFixed(1)}%` : "—"}
      </td>
      <td className="px-3 py-2.5 tabular">
        {p.stopLossTriggerPrice != null ? (
          <div className="flex flex-col">
            <span className="text-[var(--text-secondary)]">${p.stopLossTriggerPrice.toFixed(2)}</span>
            <span className={cn("text-[10px]", nearStopLoss ? "text-short font-semibold" : "text-[var(--text-muted)]")}>
              {nearStopLoss && <AlertTriangle size={9} className="mr-0.5 inline" />}
              {p.distanceToStopLossPct?.toFixed(1)}% away
            </span>
          </div>
        ) : (
          "—"
        )}
      </td>
      <td className="px-3 py-2.5 tabular">
        {p.trailingStopArmed ? (
          <div className="flex flex-col">
            <span className="text-long">${p.trailingStopTriggerPrice?.toFixed(2)}</span>
            <span className={cn("text-[10px]", nearTrailingStop ? "text-long font-semibold" : "text-[var(--text-muted)]")}>
              {nearTrailingStop && <TrendingUp size={9} className="mr-0.5 inline" />}
              {p.distanceToTrailingStopPct?.toFixed(1)}% away
            </span>
            {p.profitTakeHeldForCgt && (
              <span
                className="mt-0.5 flex items-center gap-0.5 text-[10px] font-semibold text-[var(--status-warning)]"
                title="Trigger condition is met, but the sale is being held back to preserve the AU 12-month CGT discount"
              >
                <Lock size={9} /> held for CGT
              </span>
            )}
          </div>
        ) : (
          <span className="text-[10px] text-[var(--text-muted)]">
            armed at +{p.distanceToArmPct != null ? p.distanceToArmPct.toFixed(1) : "—"}%
          </span>
        )}
      </td>
      <td className="px-3 py-2.5 tabular">
        {p.daysHeld != null ? (
          <div className="flex flex-col">
            <span className={cn(p.cgtDiscountEligible ? "text-long" : "text-[var(--text-secondary)]")}>
              {p.daysHeld}d
            </span>
            <span className="text-[10px] text-[var(--text-muted)]">
              {p.cgtDiscountEligible ? "CGT-eligible" : `eligible ${p.cgtEligibleDate ?? "—"}`}
            </span>
          </div>
        ) : (
          "—"
        )}
      </td>
      <td className={cn("px-3 py-2.5 tabular", nearCap ? "text-[var(--status-warning)] font-semibold" : "text-[var(--text-muted)]")}>
        {p.positionSharePct != null ? `${p.positionSharePct.toFixed(1)}%` : "—"}
      </td>
    </tr>
  );
}

function StrategyWatchList({
  strategy,
  label,
  colorClass,
}: {
  strategy: WeeklyRunStrategy;
  label: string;
  colorClass: string;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-base-700 bg-base-850">
      <div className={cn("border-b border-base-700 px-4 py-3 text-sm font-medium", colorClass)}>
        {label} &mdash; Open Positions ({strategy.positions.length})
      </div>
      {strategy.positions.length === 0 ? (
        <div className="px-4 py-6 text-center text-sm text-[var(--text-muted)]">No open positions.</div>
      ) : (
        <table className="w-full min-w-[840px] text-sm">
          <thead>
            <tr className="border-b border-base-700 text-left text-xs text-[var(--text-muted)]">
              <th className="px-3 py-2.5 font-medium">Ticker</th>
              <th className="px-3 py-2.5 font-medium">Last Buy</th>
              <th className="px-3 py-2.5 font-medium">Current</th>
              <th className="px-3 py-2.5 font-medium">P&amp;L</th>
              <th className="px-3 py-2.5 font-medium">Stop-Loss</th>
              <th className="px-3 py-2.5 font-medium">Trailing Stop</th>
              <th className="px-3 py-2.5 font-medium">Held / CGT</th>
              <th className="px-3 py-2.5 font-medium">Portfolio %</th>
            </tr>
          </thead>
          <tbody>
            {strategy.positions.map((p) => (
              <PositionRow key={p.ticker} position={p} />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export default function WeeklyRunPanel({
  weeklyRun,
  meta,
  legs,
}: {
  weeklyRun: WeeklyRun;
  meta: BacktestMeta;
  legs: StrategyLegMeta[];
}) {
  return (
    <div className="space-y-6">
      <div className="flex items-start gap-2 rounded-lg border border-short-muted bg-short-muted/20 px-4 py-3 text-xs text-[var(--text-secondary)]">
        <ShieldAlert size={16} className="mt-0.5 shrink-0 text-short" />
        <div>
          <span className="font-semibold text-short">Not financial advice, and not verified for live trading.</span>{" "}
          This reflects the model&apos;s own simulated paper portfolio, built purely from this backtest since
          inception &mdash; not your real brokerage holdings. If you mirror these buys manually, your own fill
          prices/dates need to line up for the stop-loss and trailing-stop triggers shown here to stay accurate.
          Checks only run weekly, so a real fill can land a little past the trigger price. A profit-take that hits
          its trailing-stop trigger before {meta.cgtDiscountHoldDays ?? 366} days of holding is deferred (&ldquo;held
          for CGT&rdquo;) to preserve Australia&apos;s 12-month CGT discount &mdash; note this trades tax efficiency
          for downside exposure: if price keeps falling while a sale is deferred, it can still hit the (non-deferred)
          stop-loss and give back more than the discount is worth. This also tracks a single last-buy date per
          ticker, not true per-parcel CGT lots. Consider paper-trading this first and confirming the logic
          independently (including with your own tax adviser) before risking real capital.
        </div>
      </div>

      <div>
        <div className="mb-2 text-xs text-[var(--text-muted)]">
          Week of {weeklyRun.asOfDate} &middot; Stop-loss: -{meta.stopLossPct ?? 20}% &middot; Trailing stop: arms at +
          {meta.trailingStopArmPct ?? 10}%, triggers on a -{meta.trailingStopPct ?? 15}% pullback from peak &middot; Max
          position: {meta.maxPositionPct ?? 15}% of portfolio &middot; Profit-takes held until {meta.cgtDiscountHoldDays ?? 366}{" "}
          days held (CGT discount)
        </div>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {legs.map((leg, i) => {
            const strategy = weeklyRun[leg.key];
            if (!strategy || typeof strategy === "string") return null;
            const color = legColorClass(i);
            return (
              <RecommendedBuyCard
                key={leg.key}
                strategy={strategy}
                label={leg.label}
                colorClass={color.text}
                accentClass={color.border}
              />
            );
          })}
        </div>
      </div>

      {legs.map((leg, i) => {
        const strategy = weeklyRun[leg.key];
        if (!strategy || typeof strategy === "string") return null;
        const color = legColorClass(i);
        return <StrategyWatchList key={leg.key} strategy={strategy} label={leg.label} colorClass={color.text} />;
      })}
    </div>
  );
}

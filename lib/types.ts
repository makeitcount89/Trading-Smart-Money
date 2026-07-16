// lib/types.ts

// ============================================================================
// --- Smart Money Concepts (SMC) Core Types ----------------------------------
// ============================================================================

export type Bias = "BULLISH" | "BEARISH";
export type TimeframeKey = "1d" | "1wk";

export interface OrderBlockZone {
  kind: "internal" | "swing";
  top: number;
  bottom: number;
  date: string;
  distancePct: number;
  insideZone: boolean;
}

export interface TimeframeResult {
  lastPrice: number;
  lastBarDate: string;
  swingTrend: Bias | null;
  internalTrend: Bias | null;
  nearestBullishOrderBlock: OrderBlockZone | null;
  bullishOrderBlocks: OrderBlockZone[];
  bearishOrderBlocks: OrderBlockZone[];
}

export interface SymbolResult {
  ticker: string;
  ok: boolean;
  error: string | null;
  timeframes: Partial<Record<TimeframeKey, TimeframeResult | null>>;
}

export interface TimeframeMeta {
  key: TimeframeKey;
  label: string;
}

export interface SmcMeta {
  universe: string[];
  source: string;
  timeframes: TimeframeMeta[];
  historyPeriod: string;
  swingLength: number;
  internalLength: number;
  orderBlockCountPerType: number;
  atrLength: number;
  priceAdjustment: string;
  timezone: string;
}

export interface SmcData {
  generatedAt: string | null;
  status?: "awaiting_first_run";
  meta: SmcMeta;
  ranking: Partial<Record<TimeframeKey, string[]>>;
  closestSymbol: Partial<Record<TimeframeKey, string | null>>;
  symbols: SymbolResult[];
}

// ============================================================================
// --- Background Runner / GitHub Actions Workflow Status --------------------
// ============================================================================

export interface WorkflowStatus {
  status: string | null;
  conclusion: string | null;
  name: string | null;
  runStartedAt: string | null;
  updatedAt: string | null;
  htmlUrl: string | null;
  event: string | null;
  runNumber: number | null;
  progress?: number | null;
  currentTicker?: string | null;
  error?: string;
}

// ============================================================================
// --- Proximity-Ranked Weekly OB DCA Backtest (With Guppy Filter) -----------
// ============================================================================

export interface BacktestStrategySummary {
  events: number;
  totalInvested: number;
  endingValue: number;
  simpleReturnPct: number;
  xirrPct: number | null;
  stopLossExits?: number; // Count of -20%-from-last-buy exits, checked weekly alongside the DCA buy
  profitProtectExits?: number; // Count of trailing-stop exits (armed 10%+ up, sold on a 15%+ pullback from peak)
  cashUninvested?: number; // Pooled only: cash raised by stop-loss/trailing-stop exits still sitting idle
  sharpeRatio?: number; // Pooled only: annualized, net of weekly contributions, vs. meta.riskFreeRatePct
  maxDrawdownPct?: number; // Pooled only: worst peak-to-trough NAV decline over the window (<= 0)
  volatilityPct?: number; // Pooled only: annualized stdev of weekly returns net of contributions
}

export interface ProximityDcaEvent {
  date: string;
  price: number;
  proximityPct: number;
}

export interface ProximityDcaStrategy extends BacktestStrategySummary {
  eventDetail: ProximityDcaEvent[];
}

export interface BacktestTickerResult {
  ticker: string;
  ok: boolean;
  error: string | null;
  asOfDate: string | null;
  asOfPrice: number | null;
  strategies: {
    proximityDCA: ProximityDcaStrategy;
    guppyProximityDCA?: ProximityDcaStrategy; // Upgraded to support dual-execution tracking
  };
}

export interface BacktestMeta {
  universe: string[];
  windowYears: number;
  amountPerWeek: number;
  strategyName: string;
  note: string;
  riskFreeRatePct?: number; // Annualized baseline the Sharpe ratio is measured against
  stopLossPct?: number; // Hard stop-loss trigger, % below last buy price
  trailingStopArmPct?: number; // Gain from last buy price required before the trailing stop activates
  trailingStopPct?: number; // Pullback from post-purchase high that triggers the trailing stop, once armed
  maxPositionPct?: number; // Max share of strategy NAV a single ticker can reach before new buys are skipped
}

export interface BacktestData {
  generatedAt: string | null;
  status?: "awaiting_first_run";
  meta: BacktestMeta;
  pooled: {
    proximityDCA: BacktestStrategySummary;
    guppyProximityDCA?: BacktestStrategySummary; // Upgraded to support side-by-side totals
  };
  tickers: BacktestTickerResult[];
}
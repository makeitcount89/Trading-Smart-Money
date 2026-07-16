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
  newTickers?: string[]; // Tickers added on top of baselineUniverse (currently: top-value ASX stocks, mostly gold miners)
  baselineUniverse?: string[]; // Universe as it stood before newTickers were added
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

// ============================================================================
// --- Weekly Run: this week's actionable buy signal + open-position watch list ---
// ============================================================================

export interface WeeklyRunRecommendation {
  ticker: string;
  price: number;
  proximityPct: number;
}

export interface WeeklyRunPosition {
  ticker: string;
  unitsHeld: number;
  lastBuyPrice: number | null;
  currentPrice: number;
  peakPrice: number | null;
  positionValue: number;
  positionSharePct: number | null; // Share of this strategy's NAV -- compare against meta.maxPositionPct
  unrealizedPnlPct: number | null; // Relative to lastBuyPrice, not a blended cost basis
  stopLossTriggerPrice: number | null;
  distanceToStopLossPct: number | null; // % price would need to fall from here to hit the stop-loss
  trailingStopArmed: boolean;
  trailingStopTriggerPrice: number | null; // Set only once armed
  distanceToTrailingStopPct: number | null; // % price would need to fall from here to hit the trailing stop, once armed
  distanceToArmPct: number | null; // % price would need to rise from here to arm the trailing stop, until armed
}

export interface WeeklyRunStrategy {
  recommendedBuy: WeeklyRunRecommendation | null;
  positions: WeeklyRunPosition[];
}

export interface WeeklyRun {
  asOfDate: string;
  proximityDCA: WeeklyRunStrategy;
  guppyProximityDCA?: WeeklyRunStrategy;
}

// ============================================================================
// --- Exit-Rule Sweep: same historical data, alternative stop-loss / trailing- ---
// --- stop configurations backtested side by side for comparison ---------------
// ============================================================================

export interface ExitRuleSweepConfig {
  name: string;
  isCurrent: boolean; // Marks the config matching meta.stopLossPct/trailingStop* (the live production settings)
  stopLossPct: number | null; // null = stop-loss disabled for this config
  trailingStopArmPct: number | null; // null = trailing stop disabled for this config
  trailingStopPct: number | null;
  proximityDCA: BacktestStrategySummary;
  guppyProximityDCA: BacktestStrategySummary;
}

// ============================================================================
// --- Walk-Forward Sweep: the same exit-rule sweep re-run over several ----------
// --- overlapping historical windows, to check whether a config's ranking ------
// --- holds up across different market regimes instead of one lucky window ----
// ============================================================================

export interface WalkForwardWindowMeta {
  windowNumber: number; // 1 = oldest
  startDate: string;
  endDate: string;
}

export interface WalkForwardWindowResult extends BacktestStrategySummary {
  windowNumber: number;
  startDate: string;
  endDate: string;
}

export interface WalkForwardAggregate {
  windowsTested: number; // Windows with any activity -- windows with no signal that far back are excluded, not counted as 0%
  meanReturnPct: number;
  stdReturnPct: number; // Dispersion of simple return across windows -- the core "consistency" signal
  minReturnPct: number;
  maxReturnPct: number;
  meanXirrPct: number;
  meanSharpeRatio: number;
  winRatePct: number; // % of tested windows with a positive simple return
  consistencyScore: number; // meanReturnPct / stdReturnPct (falls back to meanReturnPct when stdReturnPct is 0)
  perWindow: WalkForwardWindowResult[];
}

export interface WalkForwardConfig {
  name: string;
  isCurrent: boolean;
  stopLossPct: number | null;
  trailingStopArmPct: number | null;
  trailingStopPct: number | null;
  proximityDCA: WalkForwardAggregate | null; // null if no window had any activity for this config
  guppyProximityDCA: WalkForwardAggregate | null;
}

export interface WalkForwardData {
  windowYears: number; // Length of each individual window, same as meta.windowYears
  windowCount: number;
  stepWeeks: number; // How far back each successive window starts, relative to the previous one
  tickerCount?: number; // Size of the universe this run used (differs between walkForward and walkForwardBaseline)
  windows: WalkForwardWindowMeta[];
  configs: WalkForwardConfig[];
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
  weeklyRun?: WeeklyRun;
  exitRuleSweep?: ExitRuleSweepConfig[];
  walkForward?: WalkForwardData; // Full universe (meta.universe)
  walkForwardBaseline?: WalkForwardData; // Same windows/configs, restricted to meta.baselineUniverse -- isolates the effect of meta.newTickers
}
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

export interface GuppyTrendSnapshot {
  sixMonth: boolean | null;
  oneYear: boolean | null;
  threeYear: boolean | null;
}

export interface TimeframeResult {
  lastPrice: number;
  lastBarDate: string;
  swingTrend: Bias | null;
  internalTrend: Bias | null;
  guppyTrend?: GuppyTrendSnapshot; // Guppy EMA-stack trend filter (same stack as backtest.py), evaluated at 3 different slope lookback windows. null per-window means not enough history yet for that window.
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

export interface GuppySlopeWindowMeta {
  key: "sixMonth" | "oneYear" | "threeYear";
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
  guppyEmaPeriods?: number[];
  guppySlopeWindows?: GuppySlopeWindowMeta[];
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
  calmarRatio?: number; // xirrPct / |maxDrawdownPct| -- return per unit of worst-case pain, vs. Sharpe's per-unit-of-volatility
  cgtDeferredCount?: number; // Pooled only: times a trailing-stop exit was held back to preserve the AU 12-month CGT discount
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
  strategies: Record<string, ProximityDcaStrategy>; // Keyed by strategy leg key -- see BacktestMeta.strategyLegs
}

// One entry-filter variant of the weekly router -- e.g. unfiltered, Guppy-EMA-confirmed,
// 200-day-MA-confirmed, bullish-SMC-structure-confirmed. All legs share the same exit
// rules/concentration cap/CGT hold rule; only the entry confirmation differs. Drives every
// dynamic N-way strategy toggle in the UI instead of hardcoding leg names/labels.
export interface StrategyLegMeta {
  key: string;
  label: string;
  description: string;
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
  cgtDiscountHoldDays?: number; // A profit-take (trailing-stop) exit is deferred until a position has been held this long, to preserve the AU 12-month CGT discount. Does not gate the stop-loss.
  strategyLegs?: StrategyLegMeta[]; // Every strategy leg key/label/description this data set contains
}

// ============================================================================
// --- Weekly Run: this week's actionable buy signal + open-position watch list ---
// ============================================================================

export interface WeeklyRunRecommendation {
  ticker: string;
  price: number;
  proximityPct: number; // Unsigned distance to the nearest active bullish order block (0 when insideZone)
  insideZone: boolean;
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
  daysHeld?: number | null; // Days since this position's last buy
  cgtEligibleDate?: string | null; // Date this position becomes eligible for the AU 12-month CGT discount
  cgtDiscountEligible?: boolean | null; // Whether daysHeld has already cleared meta.cgtDiscountHoldDays
  profitTakeHeldForCgt?: boolean; // True when the trailing-stop condition is currently met but the sale is being held back specifically to preserve CGT-discount eligibility -- a real tax-vs-downside-risk tradeoff, not a free lunch
}

export interface WeeklyRunStrategy {
  recommendedBuy: WeeklyRunRecommendation | null;
  positions: WeeklyRunPosition[];
}

export interface WeeklyRun {
  asOfDate: string;
  [legKey: string]: WeeklyRunStrategy | string; // Leg data keyed by strategy leg key -- see BacktestMeta.strategyLegs
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
  [legKey: string]: string | boolean | number | null | BacktestStrategySummary; // Per-leg summary keyed by strategy leg key -- see BacktestMeta.strategyLegs
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
  meanCalmarRatio: number; // Mean of each window's XIRR / |maxDrawdown|
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
  [legKey: string]: string | boolean | number | null | WalkForwardAggregate; // Per-leg aggregate keyed by strategy leg key -- null if no window had any activity for this config
}

export interface WalkForwardData {
  windowYears: number; // Length of each individual window, same as meta.windowYears
  windowCount: number;
  stepWeeks: number; // How far back each successive window starts, relative to the previous one
  tickerCount?: number; // Size of the universe this run used (differs between walkForward and walkForwardBaseline)
  windows: WalkForwardWindowMeta[];
  configs: WalkForwardConfig[];
}

// ============================================================================
// --- Theme Exposure: ending portfolio value grouped by a best-effort sector/ ---
// --- theme tag per ticker, so correlated positions (e.g. several gold miners) -
// --- read as one exposure instead of unrelated-looking individual holdings ----
// ============================================================================

export interface ThemeExposureRow {
  theme: string;
  investedValue: number; // $ this leg put into this theme's tickers
  endingValue: number;
  gainValue: number; // endingValue - investedValue
  returnPct: number; // gainValue / investedValue * 100 (simple total return, not annualized)
  annualGainValue: number; // gainValue / meta.windowYears -- average $/year, not a compounding growth rate
  sharePct: number; // Shares across all rows for one strategy sum to 100%
  tickers: string[];
}

export type ThemeExposure = Record<string, ThemeExposureRow[]>; // Keyed by strategy leg key -- see BacktestMeta.strategyLegs

export interface BacktestData {
  generatedAt: string | null;
  status?: "awaiting_first_run";
  meta: BacktestMeta;
  pooled: Record<string, BacktestStrategySummary>; // Keyed by strategy leg key -- see BacktestMeta.strategyLegs
  tickers: BacktestTickerResult[];
  weeklyRun?: WeeklyRun;
  exitRuleSweep?: ExitRuleSweepConfig[];
  walkForward?: WalkForwardData; // Full universe (meta.universe)
  walkForwardBaseline?: WalkForwardData; // Same windows/configs, restricted to meta.baselineUniverse -- isolates the effect of meta.newTickers
  themeExposure?: ThemeExposure;
}
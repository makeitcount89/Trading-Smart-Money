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

export interface WorkflowStatus {
  status: string | null;
  conclusion: string | null;
  name: string | null;
  runStartedAt: string | null;
  updatedAt: string | null;
  htmlUrl: string | null;
  event: string | null;
  runNumber: number | null;
  error?: string;
}

// --- Retrace-to-weekly-OB backtest ---------------------------------------

export type BacktestStrategyKey = "retrace" | "fixedWeeklyDca" | "randomWeeklyDca" | "lumpSum";

export interface BacktestStrategySummary {
  events: number;
  totalInvested: number;
  endingValue: number;
  simpleReturnPct: number | null;
  xirrPct: number | null;
}

export interface BacktestRetraceEvent {
  date: string;
  price: number;
  obTop: number;
  obBottom: number;
  obFormedDate: string;
}

export interface BacktestRetraceStrategy extends BacktestStrategySummary {
  eventDetail?: BacktestRetraceEvent[];
}

export interface BacktestTickerResult {
  ticker: string;
  ok: boolean;
  error: string | null;
  asOfDate: string | null;
  asOfPrice: number | null;
  windowStart: string | null;
  strategies: Partial<{
    retrace: BacktestRetraceStrategy;
    fixedWeeklyDca: BacktestStrategySummary;
    randomWeeklyDca: BacktestStrategySummary;
    lumpSum: BacktestStrategySummary;
  }>;
}

export interface BacktestMeta {
  universe: string[];
  windowYears: number;
  amountPerEvent: number;
  orderBlockKind: string;
  retraceDefinition: string;
  fixedWeekday: string;
  randomSeed: number;
  xirrMethod: string;
  note: string;
}

export interface BacktestData {
  generatedAt: string | null;
  status?: "awaiting_first_run";
  meta: BacktestMeta;
  pooled: Partial<Record<BacktestStrategyKey, BacktestStrategySummary>>;
  tickers: BacktestTickerResult[];
}

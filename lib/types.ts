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

// --- Proximity-Ranked Weekly OB DCA Backtest -----------------------------

export interface BacktestStrategySummary {
  events: number;
  totalInvested: number;
  endingValue: number;
  simpleReturnPct: number;
  xirrPct: number | null;
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
  };
}

export interface BacktestMeta {
  universe: string[];
  windowYears: number;
  amountPerWeek: number;
  strategyName: string;
  note: string;
}

export interface BacktestData {
  generatedAt: string | null;
  status?: "awaiting_first_run";
  meta: BacktestMeta;
  pooled: {
    proximityDCA: BacktestStrategySummary;
  };
  tickers: BacktestTickerResult[];
}
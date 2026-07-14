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

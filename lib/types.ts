export type Bias = "BULLISH" | "BEARISH";

export interface OrderBlockZone {
  kind: "internal" | "swing";
  top: number;
  bottom: number;
  date: string;
  distancePct: number;
  insideZone: boolean;
}

export interface SymbolResult {
  ticker: string;
  ok: boolean;
  error: string | null;
  lastPrice: number | null;
  lastBarDate: string | null;
  swingTrend: Bias | null;
  internalTrend: Bias | null;
  nearestBullishOrderBlock: OrderBlockZone | null;
  bullishOrderBlocks: OrderBlockZone[];
  bearishOrderBlocks: OrderBlockZone[];
}

export interface SmcMeta {
  universe: string[];
  source: string;
  timeframe: string;
  historyPeriod: string;
  swingLength: number;
  internalLength: number;
  orderBlockCountPerType: number;
  atrLength: number;
  timezone: string;
}

export interface SmcData {
  generatedAt: string | null;
  status?: "awaiting_first_run";
  meta: SmcMeta;
  ranking: string[];
  closestSymbol: string | null;
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

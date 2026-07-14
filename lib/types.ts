// lib/types.ts

/**
 * Represents an individual execution hit inside a strategy lifecycle
 */
export interface StrategyDetail {
  date: string;
  price: number;
  proximityPct: number;
}

/**
 * Metric tracking structure for a specific algorithmic routing configuration
 */
export interface ProximityDcaStrategy {
  events: number;
  totalInvested: number;
  endingValue: number;
  simpleReturnPct: number;
  xirrPct: number | null;
  eventDetail: StrategyDetail[];
}

/**
 * Individual asset execution node containing evaluation metadata
 * and side-by-side backtest strategy outcomes.
 */
export interface BacktestTickerResult {
  ticker: string;
  ok: boolean;
  error?: string;
  asOfDate?: string;
  asOfPrice?: number;
  strategies: {
    proximityDCA: ProximityDcaStrategy;
    guppyProximityDCA?: ProximityDcaStrategy; // Optional to securely parse older payloads safely
  };
}

/**
 * Root structure for the application's global state context 
 * and JSON network payloads.
 */
export interface BacktestData {
  pooled: {
    proximityDCA: Omit<ProximityDcaStrategy, 'eventDetail'>;
    guppyProximityDCA?: Omit<ProximityDcaStrategy, 'eventDetail'>;
  };
  tickers: BacktestTickerResult[];
}

/**
 * State contract for the background Python backtest execution engine
 * handled by the /api/workflow-status routing layer.
 * 
 * Status allows null values to support fallback states when external workflow runs fail.
 */
export interface WorkflowStatus {
  status: 'idle' | 'running' | 'completed' | 'failed' | null; 
  progress?: number | null;
  currentTicker?: string | null;
  error?: string | null;
  updatedAt: string | null;
}
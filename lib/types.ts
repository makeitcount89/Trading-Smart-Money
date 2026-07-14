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
 */
export interface WorkflowStatus {
  status: 'idle' | 'running' | 'completed' | 'failed';
  progress?: number;       // Execution matrix range (0 to 100)
  currentTicker?: string;   // Active target entity during calculation runtime
  error?: string;
  updatedAt: string;
}
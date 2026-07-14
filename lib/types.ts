// Look for this section in your types file (e.g., @/lib/types.ts)

export interface StrategyDetail {
  date: string;
  price: number;
  proximityPct: number;
}

export interface ProximityDcaStrategy {
  events: number;
  totalInvested: number;
  endingValue: number;
  simpleReturnPct: number;
  xirrPct: number | null;
  eventDetail: StrategyDetail[];
}

// Update this interface to include the new Guppy key
export interface BacktestTickerResult {
  ticker: string;
  ok: boolean;
  error?: string;
  asOfDate?: string;
  asOfPrice?: number;
  strategies: {
    proximityDCA: ProximityDcaStrategy;
    guppyProximityDCA?: ProximityDcaStrategy; // ◄ Add this line right here as optional
  };
}

// Also ensure your global pooled object matches if it threw errors earlier
export interface BacktestData {
  pooled: {
    proximityDCA: Omit<ProximityDcaStrategy, 'eventDetail'>;
    guppyProximityDCA?: Omit<ProximityDcaStrategy, 'eventDetail'>; // ◄ Ensure this matches too
  };
  tickers: BacktestTickerResult[];
}
// Market Data Types
export interface MarketDataSnapshot {
  symbol: string;
  price: number;
  volume24h: number;
  change24h: number;
  bidAskSpread: number;
  cvd: number;
  timestamp: number;
}

export interface Signal {
  signalId: string;
  symbol: string;
  direction: 'LONG' | 'SHORT';
  entryPrice: number;
  currentPrice: number;
  stopLoss: number;
  takeProfit: number;
  unrealizedPnL: number;
  mfe: number;
  mae: number;
  quality: 'A+' | 'A' | 'B' | 'C';
  confidence: number;
  status: 'ACTIVE' | 'CLOSED';
  createdAt: Date;
  timeElapsed: number;
  featureContributions: Record<string, number>;
}

export interface Position {
  positionId: string;
  symbol: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnL: number;
  unrealizedPnLPercent: number;
  stopLoss: number;
  takeProfit: number;
  riskRewardRatio: number;
  duration: number;
  openedAt: Date;
}

export interface PerformanceMetrics {
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
  currentDrawdown: number;
  dailyPnL: number;
  weeklyPnL: number;
  monthlyPnL: number;
  totalTrades: number;
  activePositions: number;
  timestamp: Date;
}

export interface FeatureFlags {
  vsa: boolean;
  wyckoff: boolean;
  marketProfile: boolean;
  liquidityEngineering: boolean;
  smartMoneyDivergence: boolean;
  mtfConfluence: boolean;
  orderbookImbalance: boolean;
  institutionalFlow: boolean;
  volatilityRegime: boolean;
  seasonality: boolean;
  mlCalibration: boolean;
  dynamicTP: boolean;
  dynamicSL: boolean;
  correlationOptimization: boolean;
  enhancedRiskManagement: boolean;
  newsSentiment: boolean;
  microstructure: boolean;
  backtesting: boolean;
  abTesting: boolean;
  performanceDashboard: boolean;
}

export interface MarketRegime {
  symbol: string;
  regime: 'TRENDING' | 'RANGING' | 'VOLATILE' | 'QUIET';
  confidence: number;
  volatilityPercentile: number;
  trendStrength: number;
  timestamp: number;
}

export interface OrderBook {
  symbol: string;
  bids: [price: number, size: number][];
  asks: [price: number, size: number][];
  timestamp: number;
}

export interface LiquidityZone {
  symbol: string;
  priceLevel: number;
  type: 'support' | 'resistance';
  strength: 'high' | 'medium' | 'low';
  liquidityAmount: number;
  isNearPrice: boolean;
}

export type TimeRange = '1d' | '7d' | '30d' | '90d' | '1y' | 'all';
export type Theme = 'dark' | 'light';

// Accessibility Settings
export interface AccessibilitySettings {
  prefersReducedMotion: boolean;
}

// Equity Curve Types
export interface DrawdownPeriod {
  startDate: number; // Unix timestamp in milliseconds
  endDate: number; // Unix timestamp in milliseconds
  depth: number; // Drawdown depth as percentage (negative value)
  duration: number; // Duration in minutes
  peakEquity: number;
  troughEquity: number;
}

export interface EquityCurveData {
  timestamps: number[]; // Unix timestamps in milliseconds
  equityValues: number[];
  drawdownPeriods: DrawdownPeriod[];
  peakEquity: number;
  currentEquity: number;
  maxDrawdown: number;
  maxDrawdownDuration: number;
}

// PnL Breakdown Types
export interface PnLPeriod {
  date?: string; // For daily data (YYYY-MM-DD)
  week?: string; // For weekly data (YYYY-Www)
  month?: string; // For monthly data (YYYY-MM)
  pnl: number; // PnL percentage for the period
  cumulativePnL: number; // Cumulative PnL up to this period
}

export interface PnLBreakdownData {
  daily: PnLPeriod[];
  weekly: PnLPeriod[];
  monthly: PnLPeriod[];
  bestDay: PnLPeriod | null;
  worstDay: PnLPeriod | null;
  bestWeek: PnLPeriod | null;
  worstWeek: PnLPeriod | null;
  bestMonth: PnLPeriod | null;
  worstMonth: PnLPeriod | null;
}

export type PnLDisplayMode = 'absolute' | 'percentage';

// Symbol Performance Types
export interface SymbolMetrics {
  symbol: string;
  totalTrades: number;
  winRate: number;
  avgPnL: number;
  totalPnL: number;
  profitFactor: number;
  bestTrade: number;
  worstTrade: number;
  avgHoldTime: number; // in minutes
}


// Per-Symbol PnL Types
export interface SymbolTrade {
  tradeId: string;
  signalId: string;
  outcome: 'WIN' | 'LOSS';
  pnl: number;
  cumulativePnL: number;
  entryPrice: number;
  exitPrice: number;
  exitReason: string;
  mfe: number;
  mae: number;
  rrAchieved: number;
  duration: number;
  timestamp: number;
}

export interface SymbolPnLData {
  symbol: string;
  trades: SymbolTrade[];
  winRate: number;
  profitFactor: number;
  totalTrades: number;
  totalPnL: number;
}

export interface MultiSymbolPnLData {
  symbols: SymbolPnLData[];
}

// Risk Metrics Types
export interface RiskMetrics {
  sharpeRatio: number;
  sortinoRatio: number;
  calmarRatio: number;
  maxDrawdown: number;
  avgDrawdownDuration: number;
  rollingSharpe: Array<{ timestamp: string; sharpe: number }>;
  drawdownHistogram: {
    buckets: string[];
    counts: number[];
  };
}

// Quality Grade Analysis Types
export interface QualityMetrics {
  quality: 'A+' | 'A' | 'B' | 'C';
  totalTrades: number;
  winRate: number;
  avgPnL: number;
  totalPnL: number;
  avgConfidence: number;
}

export interface QualityAnalysisData {
  qualityMetrics: QualityMetrics[];
  calibrationWarning: boolean;
  calibrationMessage?: string;
}

// R:R Distribution Types
export interface RRDistributionData {
  buckets: {
    label: string;
    count: number;
    percentage: number;
  }[];
  avgRR: number;
  medianRR: number;
  targetRR: number;
}

// System Health Types
export interface SystemHealthData {
  apiSuccessRate: Record<string, number>; // Exchange name -> success rate (0-100)
  apiResponseTime: Record<string, number>; // Exchange name -> avg response time (ms)
  wsConnected: Record<string, boolean>; // Exchange name -> connection status
  dbQueryTime: number; // Average database query time (ms)
  signalProcessingLatency: number; // Average signal processing time (ms)
  lastUpdate: number; // Unix timestamp in milliseconds
  uptime: number; // System uptime in seconds
}

// Trade Journal Types
export interface Trade {
  tradeId: string;
  symbol: string;
  entryTime: number; // Unix timestamp
  exitTime: number; // Unix timestamp
  direction: 'LONG' | 'SHORT';
  entryPrice: number;
  exitPrice: number;
  size: number;
  pnl: number;
  pnlPercent: number;
  outcome: 'WIN' | 'LOSS';
  quality: 'A+' | 'A' | 'B' | 'C';
  entryReason: string;
  exitReason: string;
  featureContributions: Record<string, number>;
  mfe: number;
  mae: number;
  duration: number; // in minutes
}

export interface TradeHistoryResponse {
  trades: Trade[];
  total: number;
  page: number;
  pageSize: number;
}

export interface TradeFilters {
  symbol?: string;
  startDate?: string;
  endDate?: string;
  outcome?: 'WIN' | 'LOSS';
  quality?: 'A+' | 'A' | 'B' | 'C';
}

// Backtest Types
export interface BacktestRun {
  runId: string;
  date: number; // Unix timestamp
  parameters: Record<string, any>;
  winRate: number;
  profitFactor: number;
  sharpeRatio: number;
  maxDrawdown: number;
  totalTrades: number;
  totalPnL: number;
}

export interface BacktestResults {
  runId: string;
  date: number;
  parameters: Record<string, any>;
  equityCurve: EquityCurveData;
  metrics: {
    winRate: number;
    profitFactor: number;
    sharpeRatio: number;
    sortinoRatio: number;
    calmarRatio: number;
    maxDrawdown: number;
    avgDrawdownDuration: number;
    totalTrades: number;
    totalPnL: number;
  };
  trades: Trade[];
  drawdownChart: DrawdownPeriod[];
}

export interface BacktestComparison {
  runs: BacktestResults[];
  livePerformance?: {
    winRate: number;
    profitFactor: number;
    sharpeRatio: number;
    maxDrawdown: number;
  };
}

// A/B Testing Types
export interface Experiment {
  experimentId: string;
  name: string;
  status: 'running' | 'completed' | 'stopped';
  startDate: number; // Unix timestamp
  endDate?: number; // Unix timestamp
  controlGroup: {
    sampleSize: number;
    winRate: number;
    profitFactor: number;
    avgPnL: number;
    totalPnL: number;
  };
  treatmentGroup: {
    sampleSize: number;
    winRate: number;
    profitFactor: number;
    avgPnL: number;
    totalPnL: number;
  };
  statisticalSignificance: {
    pValue: number;
    isSignificant: boolean;
    confidenceLevel: number;
  };
  metricDifferences: {
    winRateDiff: number;
    profitFactorDiff: number;
    avgPnLDiff: number;
    confidenceInterval: {
      lower: number;
      upper: number;
    };
  };
}

// Report Export Types
export type ReportFormat = 'json' | 'csv' | 'pdf';

export interface ReportExportRequest {
  format: ReportFormat;
  startDate: string;
  endDate: string;
  sections: {
    performanceMetrics: boolean;
    charts: boolean;
    tradeJournal: boolean;
  };
}

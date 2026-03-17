import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  MarketDataSnapshot,
  MarketRegime,
  Signal,
  Position,
  PerformanceMetrics,
  FeatureFlags,
  TimeRange,
  Theme,
  OrderBook,
} from '../types/index';

interface DashboardState {
  // Connection State
  wsConnected: boolean;
  lastUpdate: Date | null;
  
  // Market Data
  marketData: Map<string, MarketDataSnapshot>;
  marketRegimes: Map<string, MarketRegime>;
  orderBooks: Map<string, OrderBook>;
  
  // Trading State
  activeSignals: Signal[];
  openPositions: Position[];
  
  // Performance Data
  performanceMetrics: PerformanceMetrics | null;
  
  // Configuration
  featureFlags: FeatureFlags | null;
  
  // UI State
  selectedSymbol: string | null;
  selectedTimeRange: TimeRange;
  theme: Theme;
  isMobileMenuOpen: boolean;
  prefersReducedMotion: boolean;
}

interface DashboardActions {
  // Connection Actions
  setWsConnected: (connected: boolean) => void;
  setLastUpdate: (date: Date) => void;
  
  // Market Data Actions
  updateMarketData: (symbol: string, data: MarketDataSnapshot) => void;
  updateMarketRegime: (symbol: string, regime: MarketRegime) => void;
  updateOrderBook: (symbol: string, orderBook: OrderBook) => void;
  
  // Trading Actions
  updateSignals: (signals: Signal[]) => void;
  updatePositions: (positions: Position[]) => void;
  
  // Performance Actions
  updatePerformanceMetrics: (metrics: PerformanceMetrics) => void;
  
  // Configuration Actions
  updateFeatureFlags: (flags: FeatureFlags) => void;
  
  // UI Actions
  setSelectedSymbol: (symbol: string | null) => void;
  setSelectedTimeRange: (range: TimeRange) => void;
  setTheme: (theme: Theme) => void;
  setMobileMenuOpen: (isOpen: boolean) => void;
  toggleMobileMenu: () => void;
  setPrefersReducedMotion: (prefers: boolean) => void;
  toggleReducedMotion: () => void;
}

type DashboardStore = DashboardState & DashboardActions;

export const useDashboardStore = create<DashboardStore>()(
  devtools(
    (set) => ({
      // Initial State
      wsConnected: false,
      lastUpdate: null,
      marketData: new Map(),
      marketRegimes: new Map(),
      orderBooks: new Map(),
      activeSignals: [],
      openPositions: [],
      performanceMetrics: null,
      featureFlags: null,
      selectedSymbol: null,
      selectedTimeRange: '7d',
      theme: 'dark',
      isMobileMenuOpen: false,
      prefersReducedMotion: (() => {
        if (typeof window === 'undefined') return false;
        
        // Check if matchMedia is available (not available in some test environments)
        if (!window.matchMedia) return false;
        
        try {
          return window.matchMedia('(prefers-reduced-motion: reduce)').matches ||
            localStorage.getItem('prefersReducedMotion') === 'true';
        } catch {
          return false;
        }
      })(),
      
      // Actions
      setWsConnected: (connected) => set({ wsConnected: connected }),
      setLastUpdate: (date) => set({ lastUpdate: date }),
      
      updateMarketData: (symbol, data) =>
        set((state) => {
          const newMarketData = new Map(state.marketData);
          newMarketData.set(symbol, data);
          return { marketData: newMarketData, lastUpdate: new Date() };
        }),
      
      updateMarketRegime: (symbol, regime) =>
        set((state) => {
          const newMarketRegimes = new Map(state.marketRegimes);
          newMarketRegimes.set(symbol, regime);
          return { marketRegimes: newMarketRegimes, lastUpdate: new Date() };
        }),
      
      updateOrderBook: (symbol, orderBook) =>
        set((state) => {
          const newOrderBooks = new Map(state.orderBooks);
          newOrderBooks.set(symbol, orderBook);
          return { orderBooks: newOrderBooks, lastUpdate: new Date() };
        }),
      
      updateSignals: (signals) =>
        set({ activeSignals: signals, lastUpdate: new Date() }),
      
      updatePositions: (positions) =>
        set({ openPositions: positions, lastUpdate: new Date() }),
      
      updatePerformanceMetrics: (metrics) =>
        set({ performanceMetrics: metrics, lastUpdate: new Date() }),
      
      updateFeatureFlags: (flags) => set({ featureFlags: flags }),
      
      setSelectedSymbol: (symbol) => set({ selectedSymbol: symbol }),
      setSelectedTimeRange: (range) => set({ selectedTimeRange: range }),
      setTheme: (theme) => set({ theme }),
      setMobileMenuOpen: (isOpen) => set({ isMobileMenuOpen: isOpen }),
      toggleMobileMenu: () => set((state) => ({ isMobileMenuOpen: !state.isMobileMenuOpen })),
      setPrefersReducedMotion: (prefers) => {
        if (typeof window !== 'undefined') {
          localStorage.setItem('prefersReducedMotion', String(prefers));
        }
        set({ prefersReducedMotion: prefers });
      },
      toggleReducedMotion: () => set((state) => {
        const newValue = !state.prefersReducedMotion;
        if (typeof window !== 'undefined') {
          localStorage.setItem('prefersReducedMotion', String(newValue));
        }
        return { prefersReducedMotion: newValue };
      }),
    }),
    { name: 'DashboardStore' }
  )
);

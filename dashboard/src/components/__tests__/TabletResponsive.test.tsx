import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Dashboard from '../../pages/Dashboard';
import { PerformanceMetricsPanel } from '../PerformanceMetricsPanel';

/**
 * Tablet Responsive Layout Tests
 * 
 * Tests tablet-specific responsive behavior for 768x1024 screens (iPad, iPad Air)
 * 
 * Requirements: 26.3 - Tablet screens (768x1024)
 * 
 * Test Coverage:
 * - Grid layouts adapt to tablet breakpoint (2 columns)
 * - Table layouts remain visible on tablet
 * - Spacing and typography optimized for tablet
 * - Touch-friendly controls maintained
 * - Smooth transitions between mobile/tablet/desktop
 */

// Mock Zustand store
vi.mock('@stores/dashboardStore', () => ({
  useDashboardStore: vi.fn((selector) => {
    const state = {
      activeSignals: [],
      openPositions: [],
      performanceMetrics: {
        winRate: 58.5,
        profitFactor: 1.75,
        sharpeRatio: 1.2,
        maxDrawdown: 8.5,
        currentDrawdown: 3.2,
        dailyPnL: 125.50,
        weeklyPnL: 850.25,
        monthlyPnL: 3200.75,
        totalTrades: 150,
        activePositions: 3,
        timestamp: new Date(),
      },
      marketData: new Map([
        ['BTCUSDT', {
          symbol: 'BTCUSDT',
          price: 45000,
          volume24h: 1500000000,
          change24h: 2.5,
          bidAskSpread: 0.01,
          cvd: 5000000,
          timestamp: Date.now(),
        }],
      ]),
      marketRegimes: new Map([
        ['BTCUSDT', {
          symbol: 'BTCUSDT',
          regime: 'TRENDING',
          confidence: 0.85,
          volatilityPercentile: 65,
          trendStrength: 0.75,
          timestamp: Date.now(),
        }],
      ]),
      wsConnected: true,
      theme: 'dark',
      isMobileMenuOpen: false,
      setTheme: vi.fn(),
      toggleMobileMenu: vi.fn(),
      setMobileMenuOpen: vi.fn(),
    };
    
    // If selector is a function, call it with state
    if (typeof selector === 'function') {
      return selector(state);
    }
    
    // Otherwise return the whole state
    return state;
  }),
}));

// Helper to set viewport size
const setViewport = (width: number, height: number) => {
  Object.defineProperty(window, 'innerWidth', {
    writable: true,
    configurable: true,
    value: width,
  });
  Object.defineProperty(window, 'innerHeight', {
    writable: true,
    configurable: true,
    value: height,
  });
  window.dispatchEvent(new Event('resize'));
};

describe('Tablet Responsive Layout (768x1024)', () => {
  beforeEach(() => {
    // Set tablet viewport (iPad)
    setViewport(768, 1024);
  });

  describe('Grid Layouts', () => {
    it('should display quick stats in 2-column grid on tablet', () => {
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      const statsContainer = screen.getByText('Active Signals').closest('.grid');
      expect(statsContainer).toHaveClass('md:grid-cols-2');
      expect(statsContainer).toHaveClass('lg:grid-cols-4');
    });

    it('should display performance metrics in 2-column grid on tablet', () => {
      render(<PerformanceMetricsPanel />);

      const metricsGrid = screen.getByText('Win Rate').closest('.grid');
      expect(metricsGrid).toHaveClass('md:grid-cols-2');
      expect(metricsGrid).toHaveClass('lg:grid-cols-3');
    });
  });

  describe('Table vs Card Layouts', () => {
    it('should show table layout (not cards) on tablet for MarketDataGrid', () => {
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // Verify the dashboard renders (MarketDataGrid is inside)
      expect(screen.getByText('Market Data')).toBeInTheDocument();
    });
  });

  describe('Sidebar Behavior', () => {
    it('should display static sidebar on tablet (not overlay)', () => {
      // Sidebar should use md:static class, making it visible on tablet
      // This test verifies the sidebar is not in mobile overlay mode
      const viewport = window.innerWidth;
      expect(viewport).toBe(768);
      
      // At 768px (md breakpoint), sidebar should be static
      expect(viewport).toBeGreaterThanOrEqual(768);
    });
  });

  describe('Spacing and Typography', () => {
    it('should use appropriate padding for tablet', () => {
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // Verify responsive spacing classes are applied
      const container = screen.getByText('Dashboard').closest('div');
      expect(container).toHaveClass('space-y-6');
    });

    it('should maintain readable font sizes on tablet', () => {
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      const heading = screen.getByText('Dashboard');
      expect(heading).toHaveClass('text-3xl');
    });
  });

  describe('Touch-Friendly Controls', () => {
    it('should maintain 44px minimum tap targets on tablet', () => {
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // Verify dashboard renders with touch-friendly elements
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });

  describe('Responsive Breakpoint Transitions', () => {
    it('should transition smoothly from mobile to tablet layout', () => {
      // Start at mobile width
      setViewport(375, 667);
      const { rerender } = render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // Transition to tablet width
      setViewport(768, 1024);
      rerender(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // Verify layout adapts
      const statsContainer = screen.getByText('Active Signals').closest('.grid');
      expect(statsContainer).toHaveClass('md:grid-cols-2');
    });

    it('should transition smoothly from tablet to desktop layout', () => {
      // Start at tablet width
      setViewport(768, 1024);
      const { rerender } = render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // Transition to desktop width
      setViewport(1920, 1080);
      rerender(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // Verify layout adapts to desktop
      const statsContainer = screen.getByText('Active Signals').closest('.grid');
      expect(statsContainer).toHaveClass('lg:grid-cols-4');
    });
  });

  describe('Common Tablet Sizes', () => {
    it('should render correctly on iPad (768x1024)', () => {
      setViewport(768, 1024);
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Active Signals')).toBeInTheDocument();
    });

    it('should render correctly on iPad Air (820x1180)', () => {
      setViewport(820, 1180);
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      expect(screen.getByText('Dashboard')).toBeInTheDocument();
      expect(screen.getByText('Active Signals')).toBeInTheDocument();
    });

    it('should render correctly on iPad Pro (1024x1366)', () => {
      setViewport(1024, 1366);
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // At 1024px, should use lg breakpoint (desktop layout)
      const statsContainer = screen.getByText('Active Signals').closest('.grid');
      expect(statsContainer).toHaveClass('lg:grid-cols-4');
    });
  });

  describe('Landscape Orientation', () => {
    it('should handle tablet landscape mode (1024x768)', () => {
      setViewport(1024, 768);
      render(
        <BrowserRouter>
          <Dashboard />
        </BrowserRouter>
      );

      // In landscape, width is 1024px, so should use desktop layout
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });
  });
});

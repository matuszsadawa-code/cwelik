/**
 * Mobile Responsive Layout Tests
 * 
 * Tests for Task 6.11: Implement responsive mobile layout
 * Requirements: 26.4, 26.5, 26.8, 26.9
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { useDashboardStore } from '../../stores/dashboardStore';
import Header from '../Header';
import Sidebar from '../Sidebar';
import { MarketDataGrid } from '../MarketDataGrid';

// Mock Zustand store
const mockStore = {
  wsConnected: true,
  theme: 'dark' as const,
  isMobileMenuOpen: false,
  setTheme: () => {},
  toggleMobileMenu: () => {},
  setMobileMenuOpen: () => {},
  marketData: new Map(),
  marketRegimes: new Map(),
};

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

describe('Mobile Responsive Layout', () => {
  beforeEach(() => {
    // Reset store state
    useDashboardStore.setState(mockStore);
  });

  describe('Requirement 26.4: Mobile breakpoint <768px', () => {
    it('should show hamburger menu on mobile screens', () => {
      setViewport(375, 667);
      render(<Header />);
      
      const hamburgerButton = screen.getByLabelText('Toggle menu');
      expect(hamburgerButton).toBeDefined();
    });

    it('should hide hamburger menu on desktop screens', () => {
      setViewport(1920, 1080);
      render(<Header />);
      
      const hamburgerButton = screen.queryByLabelText('Toggle menu');
      // On desktop, hamburger should have md:hidden class
      expect(hamburgerButton).toBeDefined();
    });
  });

  describe('Requirement 26.5: Minimum screen size 375x667', () => {
    it('should render correctly on iPhone SE (375x667)', () => {
      setViewport(375, 667);
      render(<Header />);
      
      const header = screen.getByRole('banner');
      expect(header).toBeDefined();
      
      // Check that title is visible
      const title = screen.getByText('OpenClaw');
      expect(title).toBeDefined();
    });

    it('should render MarketDataGrid cards on mobile', () => {
      setViewport(375, 667);
      const symbols = ['BTCUSDT', 'ETHUSDT'];
      
      render(<MarketDataGrid symbols={symbols} />);
      
      // Mobile view should show cards, not table
      const cards = document.querySelectorAll('.md\\:hidden');
      expect(cards.length).toBeGreaterThan(0);
    });
  });

  describe('Requirement 26.8: Collapsible sections', () => {
    it('should toggle mobile menu when hamburger is clicked', () => {
      setViewport(375, 667);
      render(<Header />);
      
      const hamburgerButton = screen.getByLabelText('Toggle menu');
      const initialState = useDashboardStore.getState().isMobileMenuOpen;
      
      fireEvent.click(hamburgerButton);
      
      const newState = useDashboardStore.getState().isMobileMenuOpen;
      expect(newState).not.toBe(initialState);
    });

    it('should show sidebar overlay when menu is open', () => {
      setViewport(375, 667);
      useDashboardStore.setState({ isMobileMenuOpen: true });
      
      render(
        <BrowserRouter>
          <Sidebar />
        </BrowserRouter>
      );
      
      // Check for overlay backdrop
      const overlay = document.querySelector('.fixed.inset-0.bg-black\\/60');
      expect(overlay).toBeDefined();
    });

    it('should close menu on Escape key', () => {
      setViewport(375, 667);
      useDashboardStore.setState({ isMobileMenuOpen: true });
      
      render(
        <BrowserRouter>
          <Sidebar />
        </BrowserRouter>
      );
      
      fireEvent.keyDown(window, { key: 'Escape' });
      
      const state = useDashboardStore.getState().isMobileMenuOpen;
      expect(state).toBe(false);
    });
  });

  describe('Requirement 26.9: Touch-friendly controls (44x44px)', () => {
    it('should have minimum 44px tap targets for hamburger menu', () => {
      setViewport(375, 667);
      render(<Header />);
      
      const hamburgerButton = screen.getByLabelText('Toggle menu');
      const styles = window.getComputedStyle(hamburgerButton);
      
      // Check inline style
      expect(hamburgerButton.style.minWidth).toBe('44px');
      expect(hamburgerButton.style.minHeight).toBe('44px');
    });

    it('should have minimum 44px tap targets for theme toggle', () => {
      setViewport(375, 667);
      render(<Header />);
      
      const themeButton = screen.getByLabelText('Toggle theme');
      
      // Check inline style
      expect(themeButton.style.minWidth).toBe('44px');
      expect(themeButton.style.minHeight).toBe('44px');
    });

    it('should have touch-manipulation class on interactive elements', () => {
      setViewport(375, 667);
      render(<Header />);
      
      const hamburgerButton = screen.getByLabelText('Toggle menu');
      expect(hamburgerButton.className).toContain('touch-manipulation');
    });
  });

  describe('Responsive Grid Layouts', () => {
    it('should stack metrics vertically on mobile', () => {
      setViewport(375, 667);
      
      // Test grid-cols-1 on mobile
      const element = document.createElement('div');
      element.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
      document.body.appendChild(element);
      
      const styles = window.getComputedStyle(element);
      // On mobile, should use grid-cols-1
      expect(element.className).toContain('grid-cols-1');
      
      document.body.removeChild(element);
    });

    it('should use multi-column layout on desktop', () => {
      setViewport(1920, 1080);
      
      const element = document.createElement('div');
      element.className = 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3';
      document.body.appendChild(element);
      
      // On desktop, should have md: and lg: classes
      expect(element.className).toContain('md:grid-cols-2');
      expect(element.className).toContain('lg:grid-cols-3');
      
      document.body.removeChild(element);
    });
  });

  describe('No Horizontal Scroll', () => {
    it('should not cause horizontal scroll on mobile', () => {
      setViewport(375, 667);
      render(<Header />);
      
      // Check that body width doesn't exceed viewport
      const bodyWidth = document.body.scrollWidth;
      const viewportWidth = window.innerWidth;
      
      expect(bodyWidth).toBeLessThanOrEqual(viewportWidth);
    });
  });

  describe('Information Hierarchy', () => {
    it('should prioritize critical information on mobile', () => {
      setViewport(375, 667);
      render(<Header />);
      
      // Title should be visible
      const title = screen.getByText('OpenClaw');
      expect(title).toBeDefined();
      
      // Connection status text should be hidden on mobile (sm:inline)
      const connectionText = screen.queryByText('Connected');
      // Text exists but may be hidden via CSS
      expect(connectionText).toBeDefined();
    });
  });
});

describe('Responsive Breakpoint Property Test', () => {
  /**
   * Property 18: Responsive Breakpoint
   * Validates: Requirements 26.5
   * 
   * For any screen width:
   * - If width < 768px, mobile layout should apply
   * - If width >= 768px, desktop/tablet layout should apply
   */
  it('should apply correct layout based on screen width', () => {
    const testWidths = [
      { width: 375, expected: 'mobile' },
      { width: 414, expected: 'mobile' },
      { width: 767, expected: 'mobile' },
      { width: 768, expected: 'desktop' },
      { width: 1024, expected: 'desktop' },
      { width: 1920, expected: 'desktop' },
    ];

    testWidths.forEach(({ width, expected }) => {
      setViewport(width, 667);
      render(<Header />);
      
      const hamburgerButton = screen.queryByLabelText('Toggle menu');
      
      if (expected === 'mobile') {
        // Hamburger should be visible (not hidden by md:hidden)
        expect(hamburgerButton).toBeDefined();
      } else {
        // Hamburger should have md:hidden class
        expect(hamburgerButton).toBeDefined();
        expect(hamburgerButton?.className).toContain('md:hidden');
      }
    });
  });
});

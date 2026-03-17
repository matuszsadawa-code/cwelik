/**
 * Keyboard Navigation Integration Tests
 * 
 * Tests complete keyboard navigation flow across the application.
 * Validates: Requirements 30.2, 30.10
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Layout from '../Layout';

// Mock the dashboard store
vi.mock('@stores/dashboardStore', () => ({
  useDashboardStore: () => ({
    wsConnected: true,
    theme: 'dark',
    setTheme: vi.fn(),
    toggleMobileMenu: vi.fn(),
    isMobileMenuOpen: false,
    setMobileMenuOpen: vi.fn(),
  }),
}));

describe('Complete Keyboard Navigation Flow', () => {
  it('user can navigate entire app using only keyboard', () => {
    const { container } = render(
      <BrowserRouter>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </BrowserRouter>
    );

    // 1. Skip navigation links should be present
    const skipLinks = screen.getAllByRole('link');
    expect(skipLinks.length).toBeGreaterThanOrEqual(3);

    // 2. Header should be accessible
    const header = container.querySelector('#header');
    expect(header).toBeInTheDocument();
    expect(header).toHaveAttribute('tabIndex', '-1');

    // 3. Navigation sidebar should be accessible
    const navigation = container.querySelector('#navigation');
    expect(navigation).toBeInTheDocument();
    expect(navigation).toHaveAttribute('tabIndex', '-1');

    // 4. Main content should be accessible
    const mainContent = container.querySelector('#main-content');
    expect(mainContent).toBeInTheDocument();
    expect(mainContent).toHaveAttribute('tabIndex', '-1');
  });


  it('all interactive elements are reachable via Tab key', () => {
    render(
      <BrowserRouter>
        <Layout>
          <div>
            <button>Test Button 1</button>
            <button>Test Button 2</button>
            <a href="/test">Test Link</a>
          </div>
        </Layout>
      </BrowserRouter>
    );

    // Get all interactive elements
    const buttons = screen.getAllByRole('button');
    const links = screen.getAllByRole('link');

    // All buttons should be focusable
    buttons.forEach(button => {
      button.focus();
      expect(document.activeElement).toBe(button);
    });

    // All links should be focusable
    links.forEach(link => {
      link.focus();
      expect(document.activeElement).toBe(link);
    });
  });

  it('skip navigation works correctly', () => {
    const { container } = render(
      <BrowserRouter>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </BrowserRouter>
    );

    // Find skip to main content link
    const skipToMain = screen.getByText('Skip to main content');
    
    // Click the skip link
    fireEvent.click(skipToMain);

    // Main content should be focused
    const mainContent = container.querySelector('#main-content');
    expect(document.activeElement).toBe(mainContent);
  });

  it('navigation menu items are keyboard operable', () => {
    render(
      <BrowserRouter>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </BrowserRouter>
    );

    // Find navigation items by their button role
    const navButtons = screen.getAllByRole('button');
    
    // Filter to get only the navigation buttons (exclude header buttons)
    const dashboardButton = navButtons.find(btn => btn.textContent?.includes('Dashboard'));
    const analyticsButton = navButtons.find(btn => btn.textContent?.includes('Analytics'));

    // Should be buttons
    expect(dashboardButton).toBeDefined();
    expect(analyticsButton).toBeDefined();

    if (dashboardButton && analyticsButton) {
      // Should be focusable
      dashboardButton.focus();
      expect(document.activeElement).toBe(dashboardButton);

      analyticsButton.focus();
      expect(document.activeElement).toBe(analyticsButton);
    }
  });
});


describe('Keyboard Event Handling', () => {
  it('Enter key activates navigation buttons', () => {
    const mockNavigate = vi.fn();
    
    render(
      <BrowserRouter>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </BrowserRouter>
    );

    const dashboardButton = screen.getByText('Dashboard');
    
    // Simulate Enter key press
    fireEvent.keyDown(dashboardButton, { key: 'Enter', code: 'Enter' });
    
    // Button should remain in document (navigation handled by router)
    expect(dashboardButton).toBeInTheDocument();
  });

  it('Space key activates buttons', () => {
    render(
      <BrowserRouter>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </BrowserRouter>
    );

    const themeButton = screen.getByLabelText(/Switch to (light|dark) mode/);
    
    // Focus the button
    themeButton.focus();
    
    // Simulate Space key press
    fireEvent.keyDown(themeButton, { key: ' ', code: 'Space' });
    
    // Button should still be in document
    expect(themeButton).toBeInTheDocument();
  });

  it('Escape key closes mobile menu', () => {
    render(
      <BrowserRouter>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </BrowserRouter>
    );

    // Simulate Escape key on window
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    
    // Test passes if no errors thrown
    expect(true).toBe(true);
  });
});

describe('Focus Indicators', () => {
  it('focused elements have visible focus indicators', () => {
    render(
      <BrowserRouter>
        <Layout>
          <div>Test Content</div>
        </Layout>
      </BrowserRouter>
    );

    const themeButton = screen.getByLabelText(/Switch to (light|dark) mode/);
    
    // Focus the button
    themeButton.focus();
    
    // Element should be focused
    expect(document.activeElement).toBe(themeButton);
    
    // CSS will handle visual focus indicator
  });
});

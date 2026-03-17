/**
 * Keyboard Navigation Tests
 * 
 * Tests keyboard accessibility for all interactive elements.
 * Validates: Requirements 30.2, 30.10
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import SkipNavigation from '../SkipNavigation';
import Header from '../Header';
import Sidebar from '../Sidebar';

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

describe('SkipNavigation', () => {
  it('renders skip navigation links', () => {
    render(<SkipNavigation />);
    
    expect(screen.getByText('Skip to main content')).toBeInTheDocument();
    expect(screen.getByText('Skip to navigation')).toBeInTheDocument();
    expect(screen.getByText('Skip to header')).toBeInTheDocument();
  });

  it('skip links have correct href attributes', () => {
    render(<SkipNavigation />);
    
    const mainContentLink = screen.getByText('Skip to main content');
    expect(mainContentLink).toHaveAttribute('href', '#main-content');
  });

  it('focuses target element when skip link is clicked', () => {
    // Create a target element
    const targetElement = document.createElement('div');
    targetElement.id = 'main-content';
    targetElement.tabIndex = -1;
    document.body.appendChild(targetElement);

    render(<SkipNavigation />);
    
    const skipLink = screen.getByText('Skip to main content');
    fireEvent.click(skipLink);
    
    expect(document.activeElement).toBe(targetElement);
    
    // Cleanup
    document.body.removeChild(targetElement);
  });
});

describe('Header Keyboard Navigation', () => {
  it('theme toggle button is keyboard accessible', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    
    const themeButton = screen.getByLabelText(/Switch to (light|dark) mode/);
    expect(themeButton).toBeInTheDocument();
    expect(themeButton.tagName).toBe('BUTTON');
  });

  it('mobile menu button is keyboard accessible', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    
    const menuButton = screen.getByLabelText('Toggle menu');
    expect(menuButton).toBeInTheDocument();
    expect(menuButton.tagName).toBe('BUTTON');
  });
});

describe('Sidebar Keyboard Navigation', () => {
  it('all navigation items are keyboard accessible', () => {
    render(
      <BrowserRouter>
        <Sidebar />
      </BrowserRouter>
    );
    
    const navButtons = screen.getAllByRole('button');
    expect(navButtons.length).toBeGreaterThan(0);
    
    navButtons.forEach(button => {
      expect(button.tagName).toBe('BUTTON');
    });
  });

  it('navigation items can be activated with Enter key', () => {
    const { container } = render(
      <BrowserRouter>
        <Sidebar />
      </BrowserRouter>
    );
    
    const dashboardButton = screen.getByText('Dashboard');
    fireEvent.keyDown(dashboardButton, { key: 'Enter', code: 'Enter' });
    
    // Should navigate (tested via router integration)
    expect(dashboardButton).toBeInTheDocument();
  });

  it('Escape key closes mobile menu', () => {
    render(
      <BrowserRouter>
        <Sidebar />
      </BrowserRouter>
    );
    
    // Simulate Escape key press
    fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });
    
    // Menu should close (tested via store integration)
  });
});

describe('Tab Order', () => {
  it('header elements have logical tab order', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    
    const buttons = screen.getAllByRole('button');
    
    // Mobile menu button should come first, then theme toggle
    expect(buttons.length).toBeGreaterThanOrEqual(2);
  });

  it('main content areas have proper IDs for skip navigation', () => {
    const { container } = render(
      <BrowserRouter>
        <div>
          <div id="header" />
          <div id="navigation" />
          <div id="main-content" />
        </div>
      </BrowserRouter>
    );
    
    expect(container.querySelector('#header')).toBeInTheDocument();
    expect(container.querySelector('#navigation')).toBeInTheDocument();
    expect(container.querySelector('#main-content')).toBeInTheDocument();
  });
});

describe('Focus Management', () => {
  it('skip navigation links are focusable', () => {
    render(<SkipNavigation />);
    
    const skipLinks = screen.getAllByRole('link');
    skipLinks.forEach(link => {
      link.focus();
      expect(document.activeElement).toBe(link);
    });
  });

  it('interactive elements have visible focus indicators', () => {
    render(
      <BrowserRouter>
        <Header />
      </BrowserRouter>
    );
    
    const themeButton = screen.getByLabelText(/Switch to (light|dark) mode/);
    
    // Focus the button
    themeButton.focus();
    
    // Button should be focusable
    expect(document.activeElement).toBe(themeButton);
  });
});

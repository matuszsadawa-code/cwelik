import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ReducedMotionToggle } from '../ReducedMotionToggle';
import { useDashboardStore } from '../../stores/dashboardStore';

describe('ReducedMotionToggle', () => {
  beforeEach(() => {
    // Reset store state before each test
    const store = useDashboardStore.getState();
    store.setPrefersReducedMotion(false);
    localStorage.clear();
  });

  it('should render the toggle with correct labels', () => {
    render(<ReducedMotionToggle />);
    
    expect(screen.getByText('Reduce Motion')).toBeInTheDocument();
    expect(screen.getByText(/Disable animations and transitions/i)).toBeInTheDocument();
  });

  it('should have proper ARIA attributes', () => {
    render(<ReducedMotionToggle />);
    
    const toggle = screen.getByRole('switch');
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    expect(toggle).toHaveAttribute('aria-label');
  });

  it('should toggle reduced motion when clicked', () => {
    render(<ReducedMotionToggle />);
    
    const toggle = screen.getByRole('switch');
    
    // Initially off
    expect(toggle).toHaveAttribute('aria-checked', 'false');
    
    // Click to enable
    fireEvent.click(toggle);
    
    // Should be enabled
    expect(toggle).toHaveAttribute('aria-checked', 'true');
    expect(useDashboardStore.getState().prefersReducedMotion).toBe(true);
  });

  it('should persist preference to localStorage', () => {
    render(<ReducedMotionToggle />);
    
    const toggle = screen.getByRole('switch');
    
    // Enable reduced motion
    fireEvent.click(toggle);
    
    // Check localStorage
    expect(localStorage.getItem('prefersReducedMotion')).toBe('true');
    
    // Disable reduced motion
    fireEvent.click(toggle);
    
    // Check localStorage again
    expect(localStorage.getItem('prefersReducedMotion')).toBe('false');
  });

  it('should have keyboard accessibility', () => {
    render(<ReducedMotionToggle />);
    
    const toggle = screen.getByRole('switch');
    
    // Should be focusable
    toggle.focus();
    expect(toggle).toHaveFocus();
    
    // Should have visible focus styles
    expect(toggle).toHaveClass('focus-visible:outline');
  });

  it('should update visual state when toggled', () => {
    render(<ReducedMotionToggle />);
    
    const toggle = screen.getByRole('switch');
    
    // Initially should have gray background
    expect(toggle).toHaveClass('bg-gray-600');
    
    // Click to enable
    fireEvent.click(toggle);
    
    // Should have green background when enabled
    expect(toggle).toHaveClass('bg-cta');
  });

  it('should have screen reader text', () => {
    render(<ReducedMotionToggle />);
    
    // Check for sr-only text
    const srText = screen.getAllByText(/reduced motion/i, { selector: '.sr-only' });
    expect(srText.length).toBeGreaterThan(0);
  });
});

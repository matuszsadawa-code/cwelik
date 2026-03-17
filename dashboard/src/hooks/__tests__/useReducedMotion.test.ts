import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useReducedMotion } from '../useReducedMotion';
import { useDashboardStore } from '../../stores/dashboardStore';

describe('useReducedMotion', () => {
  let matchMediaMock: any;

  beforeEach(() => {
    // Clear localStorage
    localStorage.clear();
    
    // Reset store
    const store = useDashboardStore.getState();
    store.setPrefersReducedMotion(false);
    
    // Remove any existing class
    document.documentElement.classList.remove('reduce-motion');

    // Mock matchMedia
    matchMediaMock = {
      matches: false,
      media: '(prefers-reduced-motion: reduce)',
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    };
    
    window.matchMedia = vi.fn().mockReturnValue(matchMediaMock);
  });

  afterEach(() => {
    document.documentElement.classList.remove('reduce-motion');
  });

  it('should apply reduce-motion class when preference is enabled', () => {
    const { result } = renderHook(() => useReducedMotion());
    
    // Enable reduced motion
    act(() => {
      useDashboardStore.getState().setPrefersReducedMotion(true);
    });
    
    // Check class is applied
    expect(document.documentElement.classList.contains('reduce-motion')).toBe(true);
  });

  it('should remove reduce-motion class when preference is disabled', () => {
    // Start with class applied
    document.documentElement.classList.add('reduce-motion');
    
    const { result } = renderHook(() => useReducedMotion());
    
    // Disable reduced motion
    act(() => {
      useDashboardStore.getState().setPrefersReducedMotion(false);
    });
    
    // Check class is removed
    expect(document.documentElement.classList.contains('reduce-motion')).toBe(false);
  });

  it('should listen to system prefers-reduced-motion media query', () => {
    renderHook(() => useReducedMotion());
    
    // Verify addEventListener was called
    expect(matchMediaMock.addEventListener).toHaveBeenCalledWith('change', expect.any(Function));
  });

  it('should clean up media query listener on unmount', () => {
    const { unmount } = renderHook(() => useReducedMotion());
    
    unmount();
    
    // Verify removeEventListener was called
    expect(matchMediaMock.removeEventListener).toHaveBeenCalledWith('change', expect.any(Function));
  });

  it('should respect system preference when no manual preference is set', () => {
    // Clear any manual preference
    localStorage.removeItem('prefersReducedMotion');
    
    // Set system preference to true
    matchMediaMock.matches = true;
    
    const { result } = renderHook(() => useReducedMotion());
    
    // Manually trigger the change handler to simulate system preference
    act(() => {
      const handleChange = matchMediaMock.addEventListener.mock.calls[0][1];
      handleChange(matchMediaMock);
    });
    
    // Should update the store based on system preference
    expect(useDashboardStore.getState().prefersReducedMotion).toBe(true);
    expect(document.documentElement.classList.contains('reduce-motion')).toBe(true);
  });

  it('should not override manual preference with system preference', () => {
    // Set manual preference
    localStorage.setItem('prefersReducedMotion', 'false');
    useDashboardStore.getState().setPrefersReducedMotion(false);
    
    // System preference is true
    matchMediaMock.matches = true;
    
    renderHook(() => useReducedMotion());
    
    // Should keep manual preference (false)
    expect(document.documentElement.classList.contains('reduce-motion')).toBe(false);
  });

  it('should return current reduced motion state', () => {
    const { result } = renderHook(() => useReducedMotion());
    
    // Initially false
    expect(result.current).toBe(false);
    
    // Enable reduced motion
    act(() => {
      useDashboardStore.getState().setPrefersReducedMotion(true);
    });
    
    // Should return true
    expect(useDashboardStore.getState().prefersReducedMotion).toBe(true);
  });
});

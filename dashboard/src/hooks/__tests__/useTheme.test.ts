import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTheme } from '../useTheme';
import { useDashboardStore } from '@stores/dashboardStore';

describe('useTheme Hook', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
    useDashboardStore.setState({ theme: 'dark' });
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  describe('Initial Theme Loading', () => {
    it('should load theme from localStorage if available', () => {
      localStorage.setItem('openclaw-theme', 'light');
      
      const { result } = renderHook(() => useTheme());
      
      expect(result.current.theme).toBe('light');
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('should default to dark mode if no saved theme', () => {
      const { result } = renderHook(() => useTheme());
      
      expect(result.current.theme).toBe('dark');
      expect(localStorage.getItem('openclaw-theme')).toBe('dark');
    });

    it('should apply dark class to DOM on dark mode', () => {
      localStorage.setItem('openclaw-theme', 'dark');
      
      renderHook(() => useTheme());
      
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should not apply dark class to DOM on light mode', () => {
      localStorage.setItem('openclaw-theme', 'light');
      
      renderHook(() => useTheme());
      
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('Theme Toggle', () => {
    it('should toggle from dark to light', () => {
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        result.current.toggleTheme();
      });
      
      expect(result.current.theme).toBe('light');
      expect(localStorage.getItem('openclaw-theme')).toBe('light');
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('should toggle from light to dark', () => {
      localStorage.setItem('openclaw-theme', 'light');
      useDashboardStore.setState({ theme: 'light' });
      
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        result.current.toggleTheme();
      });
      
      expect(result.current.theme).toBe('dark');
      expect(localStorage.getItem('openclaw-theme')).toBe('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should toggle multiple times correctly', () => {
      const { result } = renderHook(() => useTheme());
      
      // Toggle to light
      act(() => {
        result.current.toggleTheme();
      });
      expect(result.current.theme).toBe('light');
      
      // Toggle back to dark
      act(() => {
        result.current.toggleTheme();
      });
      expect(result.current.theme).toBe('dark');
      
      // Toggle to light again
      act(() => {
        result.current.toggleTheme();
      });
      expect(result.current.theme).toBe('light');
    });
  });

  describe('Direct Theme Setting', () => {
    it('should set theme to dark directly', () => {
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        result.current.setTheme('dark');
      });
      
      expect(result.current.theme).toBe('dark');
      expect(localStorage.getItem('openclaw-theme')).toBe('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should set theme to light directly', () => {
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        result.current.setTheme('light');
      });
      
      expect(result.current.theme).toBe('light');
      expect(localStorage.getItem('openclaw-theme')).toBe('light');
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('localStorage Persistence', () => {
    it('should persist theme changes to localStorage', () => {
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        result.current.setTheme('light');
      });
      
      expect(localStorage.getItem('openclaw-theme')).toBe('light');
    });

    it('should maintain theme across hook remounts', () => {
      const { result: result1 } = renderHook(() => useTheme());
      
      act(() => {
        result1.current.setTheme('light');
      });
      
      // Unmount and remount
      const { result: result2 } = renderHook(() => useTheme());
      
      expect(result2.current.theme).toBe('light');
    });
  });

  describe('DOM Class Management', () => {
    it('should add dark class when theme is dark', () => {
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        result.current.setTheme('dark');
      });
      
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should remove dark class when theme is light', () => {
      document.documentElement.classList.add('dark');
      
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        result.current.setTheme('light');
      });
      
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('should update DOM class when toggling theme', () => {
      const { result } = renderHook(() => useTheme());
      
      // Start in dark mode
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      
      // Toggle to light
      act(() => {
        result.current.toggleTheme();
      });
      expect(document.documentElement.classList.contains('dark')).toBe(false);
      
      // Toggle back to dark
      act(() => {
        result.current.toggleTheme();
      });
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });

  describe('Store Synchronization', () => {
    it('should update store when theme changes', () => {
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        result.current.setTheme('light');
      });
      
      expect(useDashboardStore.getState().theme).toBe('light');
    });

    it('should reflect store changes in hook', () => {
      const { result } = renderHook(() => useTheme());
      
      act(() => {
        useDashboardStore.setState({ theme: 'light' });
      });
      
      expect(result.current.theme).toBe('light');
    });
  });
});

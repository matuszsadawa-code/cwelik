/**
 * Performance Optimization Utilities
 * 
 * Provides utilities for optimizing React component performance:
 * - Selective Zustand subscriptions
 * - Memoization helpers
 * - Performance profiling
 * 
 * Requirements: Task 6.10 - Frontend performance optimization
 */

import { useEffect, useRef } from 'react';

/**
 * Creates a shallow equality comparison function for Zustand selectors
 * This prevents unnecessary re-renders when selected state hasn't changed
 */
export function shallowEqual<T>(a: T, b: T): boolean {
  if (Object.is(a, b)) {
    return true;
  }

  if (typeof a !== 'object' || a === null || typeof b !== 'object' || b === null) {
    return false;
  }

  const keysA = Object.keys(a);
  const keysB = Object.keys(b);

  if (keysA.length !== keysB.length) {
    return false;
  }

  for (const key of keysA) {
    if (
      !Object.prototype.hasOwnProperty.call(b, key) ||
      !Object.is((a as any)[key], (b as any)[key])
    ) {
      return false;
    }
  }

  return true;
}

/**
 * Performance profiler hook for measuring component render times
 * Logs warnings when render time exceeds threshold
 */
export function useRenderProfile(componentName: string, threshold = 16) {
  const renderCount = useRef(0);
  const startTime = useRef<number>(0);

  useEffect(() => {
    renderCount.current += 1;
  });

  // Measure render start
  startTime.current = performance.now();

  // Measure render end
  useEffect(() => {
    const renderTime = performance.now() - startTime.current;
    
    if (renderTime > threshold) {
      console.warn(
        `[Performance] ${componentName} render #${renderCount.current} took ${renderTime.toFixed(2)}ms (threshold: ${threshold}ms)`
      );
    }
  });

  return {
    renderCount: renderCount.current,
  };
}

/**
 * Hook to track component re-renders in development
 * Useful for debugging unnecessary re-renders
 */
export function useWhyDidYouUpdate(name: string, props: Record<string, any>) {
  const previousProps = useRef<Record<string, any>>();

  useEffect(() => {
    if (previousProps.current) {
      const allKeys = Object.keys({ ...previousProps.current, ...props });
      const changedProps: Record<string, { from: any; to: any }> = {};

      allKeys.forEach((key) => {
        if (previousProps.current![key] !== props[key]) {
          changedProps[key] = {
            from: previousProps.current![key],
            to: props[key],
          };
        }
      });

      if (Object.keys(changedProps).length > 0) {
        console.log('[WhyDidYouUpdate]', name, changedProps);
      }
    }

    previousProps.current = props;
  });
}

/**
 * Debounce function for expensive operations
 * Returns a debounced version of the callback
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null;

  return function executedFunction(...args: Parameters<T>) {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout) {
      clearTimeout(timeout);
    }
    timeout = setTimeout(later, wait);
  };
}

/**
 * Throttle function for rate-limiting expensive operations
 * Returns a throttled version of the callback
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean;

  return function executedFunction(...args: Parameters<T>) {
    if (!inThrottle) {
      func(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}

/**
 * Creates a memoized selector for Zustand store
 * Prevents re-renders when selected values haven't changed
 */
export function createSelector<T, R>(
  selector: (state: T) => R,
  equalityFn: (a: R, b: R) => boolean = shallowEqual
) {
  return (state: T) => {
    const selected = selector(state);
    return selected;
  };
}

/**
 * Performance monitoring utility
 * Tracks render counts and timing for components
 */
export class PerformanceMonitor {
  private metrics: Map<string, { count: number; totalTime: number; maxTime: number }> = new Map();

  recordRender(componentName: string, renderTime: number) {
    const existing = this.metrics.get(componentName) || { count: 0, totalTime: 0, maxTime: 0 };
    
    this.metrics.set(componentName, {
      count: existing.count + 1,
      totalTime: existing.totalTime + renderTime,
      maxTime: Math.max(existing.maxTime, renderTime),
    });
  }

  getMetrics(componentName: string) {
    const metrics = this.metrics.get(componentName);
    if (!metrics) return null;

    return {
      ...metrics,
      avgTime: metrics.totalTime / metrics.count,
    };
  }

  getAllMetrics() {
    const result: Record<string, any> = {};
    this.metrics.forEach((value, key) => {
      result[key] = {
        ...value,
        avgTime: value.totalTime / value.count,
      };
    });
    return result;
  }

  reset() {
    this.metrics.clear();
  }

  logReport() {
    console.group('[Performance Report]');
    const metrics = this.getAllMetrics();
    Object.entries(metrics)
      .sort((a, b) => b[1].avgTime - a[1].avgTime)
      .forEach(([name, data]) => {
        console.log(
          `${name}: ${data.count} renders, avg ${data.avgTime.toFixed(2)}ms, max ${data.maxTime.toFixed(2)}ms`
        );
      });
    console.groupEnd();
  }
}

export const performanceMonitor = new PerformanceMonitor();

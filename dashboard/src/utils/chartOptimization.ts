/**
 * Chart Performance Optimization Utilities
 * 
 * Provides utilities for optimizing TradingView Lightweight Charts performance:
 * - Data point limiting and downsampling
 * - Performance-optimized chart options
 * - Debounced zoom/pan handlers
 * - Lazy loading for historical data
 * - Render time measurement
 * 
 * Requirements: 29.2
 */

import type { DeepPartial, ChartOptions, Time } from 'lightweight-charts';

/**
 * Maximum number of data points to render for optimal performance
 */
export const MAX_DATA_POINTS = 1000;

/**
 * Target render time in milliseconds
 */
export const TARGET_RENDER_TIME_MS = 100;

/**
 * Debounce delay for zoom/pan operations in milliseconds
 */
export const ZOOM_PAN_DEBOUNCE_MS = 150;

/**
 * Performance-optimized chart options
 * Disables expensive features and enables hardware acceleration
 */
export const PERFORMANCE_CHART_OPTIONS: DeepPartial<ChartOptions> = {
  // Disable expensive crosshair animations
  crosshair: {
    mode: 1, // Normal mode (less expensive than magnet mode)
    vertLine: {
      labelVisible: false, // Disable label for better performance
    },
    horzLine: {
      labelVisible: false,
    },
  },
  
  // Disable price scale animations
  rightPriceScale: {
    autoScale: true,
    scaleMargins: {
      top: 0.1,
      bottom: 0.1,
    },
    borderVisible: true,
  },
  
  // Optimize time scale
  timeScale: {
    rightOffset: 5,
    barSpacing: 6,
    fixLeftEdge: false,
    fixRightEdge: false,
    lockVisibleTimeRangeOnResize: true,
    rightBarStaysOnScroll: true,
    borderVisible: true,
    visible: true,
    timeVisible: true,
    secondsVisible: false,
  },
  
  // Enable hardware acceleration
  handleScroll: {
    mouseWheel: true,
    pressedMouseMove: true,
    horzTouchDrag: true,
    vertTouchDrag: true,
  },
  
  handleScale: {
    axisPressedMouseMove: true,
    mouseWheel: true,
    pinch: true,
  },
  
  // Optimize layout
  layout: {
    attributionLogo: false, // Remove attribution logo for cleaner look
  },
  
  // Optimize grid
  grid: {
    vertLines: {
      visible: true,
    },
    horzLines: {
      visible: true,
    },
  },
};

/**
 * Downsample data points using Largest Triangle Three Buckets (LTTB) algorithm
 * Preserves visual appearance while reducing data points
 * 
 * @param data - Array of data points with time and value
 * @param threshold - Target number of data points (default: MAX_DATA_POINTS)
 * @returns Downsampled array of data points
 */
export function downsampleData<T extends { time: Time; value: number }>(
  data: T[],
  threshold: number = MAX_DATA_POINTS
): T[] {
  if (data.length <= threshold) {
    return data;
  }

  const sampled: T[] = [];
  const bucketSize = (data.length - 2) / (threshold - 2);

  // Always include first point
  sampled.push(data[0]);

  for (let i = 0; i < threshold - 2; i++) {
    const bucketStart = Math.floor(i * bucketSize) + 1;
    const bucketEnd = Math.floor((i + 1) * bucketSize) + 1;
    const bucketLength = bucketEnd - bucketStart;

    // Calculate average point in next bucket for reference
    let avgX = 0;
    let avgY = 0;
    let avgRangeStart = Math.floor((i + 1) * bucketSize) + 1;
    let avgRangeEnd = Math.floor((i + 2) * bucketSize) + 1;
    avgRangeEnd = avgRangeEnd < data.length ? avgRangeEnd : data.length;
    const avgRangeLength = avgRangeEnd - avgRangeStart;

    for (let j = avgRangeStart; j < avgRangeEnd; j++) {
      avgX += typeof data[j].time === 'number' ? data[j].time as number : 0;
      avgY += data[j].value;
    }
    avgX /= avgRangeLength;
    avgY /= avgRangeLength;

    // Find point in current bucket with largest triangle area
    let maxArea = -1;
    let maxAreaIndex = bucketStart;
    const pointAX = typeof sampled[sampled.length - 1].time === 'number' 
      ? sampled[sampled.length - 1].time as number 
      : 0;
    const pointAY = sampled[sampled.length - 1].value;

    for (let j = bucketStart; j < bucketEnd; j++) {
      const pointBX = typeof data[j].time === 'number' ? data[j].time as number : 0;
      const pointBY = data[j].value;

      // Calculate triangle area
      const area = Math.abs(
        (pointAX - avgX) * (pointBY - pointAY) -
        (pointAX - pointBX) * (avgY - pointAY)
      ) * 0.5;

      if (area > maxArea) {
        maxArea = area;
        maxAreaIndex = j;
      }
    }

    sampled.push(data[maxAreaIndex]);
  }

  // Always include last point
  sampled.push(data[data.length - 1]);

  return sampled;
}

/**
 * Create a debounced function that delays execution
 * Useful for zoom/pan operations to reduce render frequency
 * 
 * @param func - Function to debounce
 * @param delay - Delay in milliseconds
 * @returns Debounced function
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number = ZOOM_PAN_DEBOUNCE_MS
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function (this: any, ...args: Parameters<T>) {
    if (timeoutId) {
      clearTimeout(timeoutId);
    }

    timeoutId = setTimeout(() => {
      func.apply(this, args);
      timeoutId = null;
    }, delay);
  };
}

/**
 * Measure chart render time
 * Returns a function to start measurement and a function to end measurement
 * 
 * @param chartName - Name of the chart for logging
 * @returns Object with start and end functions
 */
export function createRenderTimeMeasurement(chartName: string) {
  let startTime: number | null = null;

  return {
    start: () => {
      startTime = performance.now();
    },
    end: () => {
      if (startTime === null) {
        console.warn(`[${chartName}] Render measurement not started`);
        return null;
      }

      const endTime = performance.now();
      const renderTime = endTime - startTime;
      
      // Log warning if render time exceeds target
      if (renderTime > TARGET_RENDER_TIME_MS) {
        console.warn(
          `[${chartName}] Render time ${renderTime.toFixed(2)}ms exceeds target ${TARGET_RENDER_TIME_MS}ms`
        );
      } else {
        console.log(
          `[${chartName}] Render time: ${renderTime.toFixed(2)}ms`
        );
      }

      startTime = null;
      return renderTime;
    },
  };
}

/**
 * Lazy load historical data in chunks
 * Useful for loading more data on scroll
 * 
 * @param allData - Complete dataset
 * @param chunkSize - Number of data points per chunk
 * @returns Object with methods to load chunks
 */
export function createLazyDataLoader<T>(
  allData: T[],
  chunkSize: number = MAX_DATA_POINTS
) {
  let currentIndex = 0;

  return {
    /**
     * Load next chunk of data
     * @returns Next chunk of data or null if no more data
     */
    loadNext: (): T[] | null => {
      if (currentIndex >= allData.length) {
        return null;
      }

      const chunk = allData.slice(currentIndex, currentIndex + chunkSize);
      currentIndex += chunkSize;
      return chunk;
    },

    /**
     * Check if more data is available
     * @returns True if more data can be loaded
     */
    hasMore: (): boolean => {
      return currentIndex < allData.length;
    },

    /**
     * Reset loader to start
     */
    reset: (): void => {
      currentIndex = 0;
    },

    /**
     * Get current progress
     * @returns Object with loaded count and total count
     */
    getProgress: () => {
      return {
        loaded: Math.min(currentIndex, allData.length),
        total: allData.length,
        percentage: (Math.min(currentIndex, allData.length) / allData.length) * 100,
      };
    },
  };
}

/**
 * Optimize chart data by limiting points and downsampling if needed
 * 
 * @param data - Array of data points
 * @param maxPoints - Maximum number of points (default: MAX_DATA_POINTS)
 * @returns Optimized data array
 */
export function optimizeChartData<T extends { time: Time; value: number }>(
  data: T[],
  maxPoints: number = MAX_DATA_POINTS
): T[] {
  if (data.length <= maxPoints) {
    return data;
  }

  console.log(
    `Downsampling ${data.length} data points to ${maxPoints} for optimal performance`
  );

  return downsampleData(data, maxPoints);
}

/**
 * Create performance-optimized chart options with custom overrides
 * 
 * @param customOptions - Custom options to merge with performance options
 * @returns Merged chart options
 */
export function createOptimizedChartOptions(
  customOptions: DeepPartial<ChartOptions> = {}
): DeepPartial<ChartOptions> {
  return {
    ...PERFORMANCE_CHART_OPTIONS,
    ...customOptions,
    // Deep merge nested objects
    layout: {
      ...PERFORMANCE_CHART_OPTIONS.layout,
      ...customOptions.layout,
    },
    crosshair: {
      ...PERFORMANCE_CHART_OPTIONS.crosshair,
      ...customOptions.crosshair,
    },
    rightPriceScale: {
      ...PERFORMANCE_CHART_OPTIONS.rightPriceScale,
      ...customOptions.rightPriceScale,
    },
    timeScale: {
      ...PERFORMANCE_CHART_OPTIONS.timeScale,
      ...customOptions.timeScale,
    },
    handleScroll: {
      ...PERFORMANCE_CHART_OPTIONS.handleScroll,
      ...customOptions.handleScroll,
    },
    handleScale: {
      ...PERFORMANCE_CHART_OPTIONS.handleScale,
      ...customOptions.handleScale,
    },
    grid: {
      ...PERFORMANCE_CHART_OPTIONS.grid,
      ...customOptions.grid,
    },
  };
}

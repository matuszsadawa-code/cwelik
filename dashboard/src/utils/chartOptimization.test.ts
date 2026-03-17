/**
 * Tests for Chart Performance Optimization Utilities
 * 
 * Requirements: 29.2
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  MAX_DATA_POINTS,
  TARGET_RENDER_TIME_MS,
  ZOOM_PAN_DEBOUNCE_MS,
  downsampleData,
  debounce,
  createRenderTimeMeasurement,
  createLazyDataLoader,
  optimizeChartData,
  createOptimizedChartOptions,
} from './chartOptimization';

describe('chartOptimization', () => {
  describe('downsampleData', () => {
    it('should return original data if length is below threshold', () => {
      const data = [
        { time: 1 as any, value: 10 },
        { time: 2 as any, value: 20 },
        { time: 3 as any, value: 30 },
      ];

      const result = downsampleData(data, 1000);
      expect(result).toEqual(data);
      expect(result.length).toBe(3);
    });

    it('should downsample data to target threshold', () => {
      const data = Array.from({ length: 2000 }, (_, i) => ({
        time: i as any,
        value: Math.sin(i / 100) * 100,
      }));

      const result = downsampleData(data, 1000);
      expect(result.length).toBe(1000);
      expect(result[0]).toEqual(data[0]); // First point preserved
      expect(result[result.length - 1]).toEqual(data[data.length - 1]); // Last point preserved
    });

    it('should preserve visual appearance with LTTB algorithm', () => {
      const data = Array.from({ length: 1500 }, (_, i) => ({
        time: i as any,
        value: Math.sin(i / 50) * 100 + Math.random() * 10,
      }));

      const result = downsampleData(data, 500);
      expect(result.length).toBe(500);
      
      // Check that extreme values are preserved
      const maxOriginal = Math.max(...data.map(d => d.value));
      const maxDownsampled = Math.max(...result.map(d => d.value));
      expect(Math.abs(maxOriginal - maxDownsampled)).toBeLessThan(20);
    });
  });

  describe('debounce', () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should delay function execution', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(50);
      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should reset delay on subsequent calls', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn();
      vi.advanceTimersByTime(50);
      debouncedFn(); // Reset timer
      vi.advanceTimersByTime(50);
      expect(fn).not.toHaveBeenCalled();

      vi.advanceTimersByTime(50);
      expect(fn).toHaveBeenCalledTimes(1);
    });

    it('should pass arguments correctly', () => {
      const fn = vi.fn();
      const debouncedFn = debounce(fn, 100);

      debouncedFn('arg1', 'arg2');
      vi.advanceTimersByTime(100);
      expect(fn).toHaveBeenCalledWith('arg1', 'arg2');
    });
  });

  describe('createRenderTimeMeasurement', () => {
    it('should measure render time', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      const measurement = createRenderTimeMeasurement('TestChart');

      measurement.start();
      const renderTime = measurement.end();

      expect(renderTime).toBeGreaterThanOrEqual(0);
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });

    it('should warn if render time exceeds target', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const measurement = createRenderTimeMeasurement('TestChart');

      // Mock performance.now to simulate slow render
      let startTime = 0;
      const mockNow = vi.spyOn(performance, 'now');
      mockNow.mockImplementationOnce(() => startTime);
      mockNow.mockImplementationOnce(() => startTime + TARGET_RENDER_TIME_MS + 50);

      measurement.start();
      const renderTime = measurement.end();

      expect(renderTime).toBeGreaterThan(TARGET_RENDER_TIME_MS);
      expect(consoleWarnSpy).toHaveBeenCalled();
      
      consoleWarnSpy.mockRestore();
      mockNow.mockRestore();
    });

    it('should handle end without start', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      const measurement = createRenderTimeMeasurement('TestChart');

      const renderTime = measurement.end();

      expect(renderTime).toBeNull();
      expect(consoleWarnSpy).toHaveBeenCalledWith(
        expect.stringContaining('Render measurement not started')
      );
      consoleWarnSpy.mockRestore();
    });
  });

  describe('createLazyDataLoader', () => {
    it('should load data in chunks', () => {
      const data = Array.from({ length: 2500 }, (_, i) => i);
      const loader = createLazyDataLoader(data, 1000);

      const chunk1 = loader.loadNext();
      expect(chunk1).toHaveLength(1000);
      expect(chunk1![0]).toBe(0);
      expect(chunk1![999]).toBe(999);

      const chunk2 = loader.loadNext();
      expect(chunk2).toHaveLength(1000);
      expect(chunk2![0]).toBe(1000);

      const chunk3 = loader.loadNext();
      expect(chunk3).toHaveLength(500);
      expect(chunk3![0]).toBe(2000);

      const chunk4 = loader.loadNext();
      expect(chunk4).toBeNull();
    });

    it('should track progress correctly', () => {
      const data = Array.from({ length: 2500 }, (_, i) => i);
      const loader = createLazyDataLoader(data, 1000);

      expect(loader.hasMore()).toBe(true);
      expect(loader.getProgress().loaded).toBe(0);
      expect(loader.getProgress().total).toBe(2500);

      loader.loadNext();
      expect(loader.getProgress().loaded).toBe(1000);
      expect(loader.getProgress().percentage).toBe(40);

      loader.loadNext();
      loader.loadNext();
      expect(loader.hasMore()).toBe(false);
      expect(loader.getProgress().loaded).toBe(2500);
      expect(loader.getProgress().percentage).toBe(100);
    });

    it('should reset loader', () => {
      const data = Array.from({ length: 2000 }, (_, i) => i);
      const loader = createLazyDataLoader(data, 1000);

      loader.loadNext();
      loader.loadNext();
      expect(loader.hasMore()).toBe(false);

      loader.reset();
      expect(loader.hasMore()).toBe(true);
      expect(loader.getProgress().loaded).toBe(0);

      const chunk = loader.loadNext();
      expect(chunk).toHaveLength(1000);
      expect(chunk![0]).toBe(0);
    });
  });

  describe('optimizeChartData', () => {
    it('should return original data if below max points', () => {
      const data = Array.from({ length: 500 }, (_, i) => ({
        time: i as any,
        value: i * 10,
      }));

      const result = optimizeChartData(data);
      expect(result).toEqual(data);
    });

    it('should downsample data if above max points', () => {
      const consoleSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
      const data = Array.from({ length: 2000 }, (_, i) => ({
        time: i as any,
        value: i * 10,
      }));

      const result = optimizeChartData(data);
      expect(result.length).toBe(MAX_DATA_POINTS);
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Downsampling')
      );
      consoleSpy.mockRestore();
    });

    it('should respect custom max points', () => {
      const data = Array.from({ length: 2000 }, (_, i) => ({
        time: i as any,
        value: i * 10,
      }));

      const result = optimizeChartData(data, 500);
      expect(result.length).toBe(500);
    });
  });

  describe('createOptimizedChartOptions', () => {
    it('should return performance-optimized options', () => {
      const options = createOptimizedChartOptions();

      expect(options.crosshair?.mode).toBe(1);
      expect(options.handleScroll?.mouseWheel).toBe(true);
      expect(options.handleScale?.mouseWheel).toBe(true);
      expect(options.layout?.attributionLogo).toBe(false);
    });

    it('should merge custom options', () => {
      const customOptions = {
        layout: {
          background: { color: '#000000' },
          textColor: '#FFFFFF',
        },
        timeScale: {
          timeVisible: false,
        },
      };

      const options = createOptimizedChartOptions(customOptions);

      expect(options.layout?.background).toEqual({ color: '#000000' });
      expect(options.layout?.textColor).toBe('#FFFFFF');
      expect(options.layout?.attributionLogo).toBe(false); // From performance options
      expect(options.timeScale?.timeVisible).toBe(false);
      expect(options.handleScroll?.mouseWheel).toBe(true); // From performance options
    });

    it('should preserve nested custom options', () => {
      const customOptions = {
        crosshair: {
          vertLine: {
            color: '#FF0000',
          },
        },
      };

      const options = createOptimizedChartOptions(customOptions);

      expect(options.crosshair?.mode).toBe(1); // From performance options
      expect(options.crosshair?.vertLine?.color).toBe('#FF0000'); // Custom
    });
  });

  describe('constants', () => {
    it('should have correct constant values', () => {
      expect(MAX_DATA_POINTS).toBe(1000);
      expect(TARGET_RENDER_TIME_MS).toBe(100);
      expect(ZOOM_PAN_DEBOUNCE_MS).toBe(150);
    });
  });
});

/**
 * Performance Metrics Utility Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { performanceMetrics } from '../performanceMetrics';

describe('PerformanceMetrics', () => {
  beforeEach(() => {
    performanceMetrics.reset();
  });

  describe('Chart Render Metrics', () => {
    it('should record chart render time', () => {
      performanceMetrics.recordChartRender('test-chart', 50, 100);
      
      const avgRenderTime = performanceMetrics.getAverageChartRenderTime();
      expect(avgRenderTime).toBe(50);
    });

    it('should calculate average chart render time', () => {
      performanceMetrics.recordChartRender('test-chart', 50, 100);
      performanceMetrics.recordChartRender('test-chart', 60, 100);
      performanceMetrics.recordChartRender('test-chart', 70, 100);
      
      const avgRenderTime = performanceMetrics.getAverageChartRenderTime();
      expect(avgRenderTime).toBe(60);
    });

    it('should warn when chart render time exceeds target', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      performanceMetrics.recordChartRender('slow-chart', 150, 100);
      
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Chart render time exceeded target')
      );
      
      consoleSpy.mockRestore();
    });

    it('should keep only last 100 measurements', () => {
      for (let i = 0; i < 150; i++) {
        performanceMetrics.recordChartRender('test-chart', 50, 100);
      }
      
      const report = performanceMetrics.getPerformanceReport();
      expect(report.chartMetrics.length).toBe(100);
    });
  });

  describe('WebSocket Latency Metrics', () => {
    it('should record WebSocket latency', () => {
      const sentTimestamp = Date.now() - 50;
      performanceMetrics.recordWebSocketLatency('market_data_update', sentTimestamp);
      
      const avgLatency = performanceMetrics.getAverageWebSocketLatency();
      expect(avgLatency).toBeGreaterThanOrEqual(50);
      expect(avgLatency).toBeLessThan(100);
    });

    it('should calculate average WebSocket latency', () => {
      const now = Date.now();
      performanceMetrics.recordWebSocketLatency('test', now - 30);
      performanceMetrics.recordWebSocketLatency('test', now - 40);
      performanceMetrics.recordWebSocketLatency('test', now - 50);
      
      const avgLatency = performanceMetrics.getAverageWebSocketLatency();
      expect(avgLatency).toBeGreaterThanOrEqual(30);
      expect(avgLatency).toBeLessThan(60);
    });

    it('should warn when WebSocket latency exceeds target', () => {
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      
      const sentTimestamp = Date.now() - 150;
      performanceMetrics.recordWebSocketLatency('slow_message', sentTimestamp);
      
      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('WebSocket latency exceeded target')
      );
      
      consoleSpy.mockRestore();
    });

    it('should keep only last 100 measurements', () => {
      const now = Date.now();
      for (let i = 0; i < 150; i++) {
        performanceMetrics.recordWebSocketLatency('test', now - 50);
      }
      
      const report = performanceMetrics.getPerformanceReport();
      expect(report.wsMetrics.length).toBe(100);
    });
  });

  describe('Component Render Metrics', () => {
    it('should record component render time', () => {
      performanceMetrics.recordComponentRender('TestComponent', 10);
      
      const avgRenderTime = performanceMetrics.getAverageComponentRenderTime('TestComponent');
      expect(avgRenderTime).toBe(10);
    });

    it('should calculate average component render time', () => {
      performanceMetrics.recordComponentRender('TestComponent', 10);
      performanceMetrics.recordComponentRender('TestComponent', 20);
      performanceMetrics.recordComponentRender('TestComponent', 30);
      
      const avgRenderTime = performanceMetrics.getAverageComponentRenderTime('TestComponent');
      expect(avgRenderTime).toBe(20);
    });

    it('should track multiple components separately', () => {
      performanceMetrics.recordComponentRender('ComponentA', 10);
      performanceMetrics.recordComponentRender('ComponentB', 20);
      
      expect(performanceMetrics.getAverageComponentRenderTime('ComponentA')).toBe(10);
      expect(performanceMetrics.getAverageComponentRenderTime('ComponentB')).toBe(20);
    });

    it('should keep only last 50 measurements per component', () => {
      for (let i = 0; i < 100; i++) {
        performanceMetrics.recordComponentRender('TestComponent', 10);
      }
      
      const report = performanceMetrics.getPerformanceReport();
      const componentMetrics = report.componentMetrics.get('TestComponent');
      expect(componentMetrics?.length).toBe(50);
    });
  });

  describe('Performance Report', () => {
    it('should generate comprehensive performance report', () => {
      performanceMetrics.recordChartRender('test-chart', 50, 100);
      performanceMetrics.recordWebSocketLatency('test', Date.now() - 30);
      performanceMetrics.recordComponentRender('TestComponent', 10);
      
      const report = performanceMetrics.getPerformanceReport();
      
      expect(report).toHaveProperty('summary');
      expect(report).toHaveProperty('targets');
      expect(report).toHaveProperty('chartMetrics');
      expect(report).toHaveProperty('wsMetrics');
      expect(report).toHaveProperty('componentMetrics');
    });

    it('should calculate target pass/fail correctly', () => {
      performanceMetrics.recordChartRender('fast-chart', 50, 100);
      performanceMetrics.recordChartRender('slow-chart', 150, 100);
      
      const report = performanceMetrics.getPerformanceReport();
      
      // Average is 100ms, which equals target
      expect(report.targets.chartRenderTime.value).toBe(100);
      expect(report.targets.chartRenderTime.target).toBe(100);
      expect(report.targets.chartRenderTime.passed).toBe(false); // Not less than target
    });

    it('should export metrics as JSON', () => {
      performanceMetrics.recordChartRender('test-chart', 50, 100);
      
      const json = performanceMetrics.exportMetrics();
      const parsed = JSON.parse(json);
      
      expect(parsed).toHaveProperty('summary');
      expect(parsed).toHaveProperty('targets');
    });
  });

  describe('Reset', () => {
    it('should reset all metrics', () => {
      performanceMetrics.recordChartRender('test-chart', 50, 100);
      performanceMetrics.recordWebSocketLatency('test', Date.now() - 30);
      performanceMetrics.recordComponentRender('TestComponent', 10);
      
      performanceMetrics.reset();
      
      expect(performanceMetrics.getAverageChartRenderTime()).toBe(0);
      expect(performanceMetrics.getAverageWebSocketLatency()).toBe(0);
      expect(performanceMetrics.getAverageComponentRenderTime('TestComponent')).toBe(0);
    });
  });
});

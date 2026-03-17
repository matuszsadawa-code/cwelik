/**
 * Performance Metrics Utilities
 * 
 * Utilities for measuring and tracking frontend performance metrics:
 * - Chart render time
 * - WebSocket latency
 * - Component render time
 * - Page load metrics
 */

export interface PerformanceMetrics {
  chartRenderTime: number;
  websocketLatency: number;
  componentRenderTime: number;
  pageLoadTime: number;
  timeToInteractive: number;
}

export interface ChartRenderMetric {
  chartId: string;
  renderTime: number;
  dataPoints: number;
  timestamp: number;
}

export interface WebSocketLatencyMetric {
  messageType: string;
  latency: number;
  timestamp: number;
}

export interface ComponentRenderMetric {
  componentName: string;
  renderTime: number;
  renderCount: number;
  timestamp: number;
}

/**
 * Performance Metrics Tracker
 */
class PerformanceMetricsTracker {
  private chartRenderMetrics: ChartRenderMetric[] = [];
  private wsLatencyMetrics: WebSocketLatencyMetric[] = [];
  private componentRenderMetrics: Map<string, ComponentRenderMetric[]> = new Map();
  private pageLoadMetrics: PerformanceNavigationTiming | null = null;

  /**
   * Record chart render time
   */
  recordChartRender(chartId: string, renderTime: number, dataPoints: number): void {
    this.chartRenderMetrics.push({
      chartId,
      renderTime,
      dataPoints,
      timestamp: Date.now(),
    });

    // Keep only last 100 measurements
    if (this.chartRenderMetrics.length > 100) {
      this.chartRenderMetrics.shift();
    }

    // Warn if render time exceeds target
    if (renderTime > 100) {
      console.warn(
        `⚠️ Chart render time exceeded target: ${chartId} took ${renderTime.toFixed(2)}ms (target: <100ms)`
      );
    }
  }

  /**
   * Record WebSocket message latency
   */
  recordWebSocketLatency(messageType: string, sentTimestamp: number): void {
    const latency = Date.now() - sentTimestamp;

    this.wsLatencyMetrics.push({
      messageType,
      latency,
      timestamp: Date.now(),
    });

    // Keep only last 100 measurements
    if (this.wsLatencyMetrics.length > 100) {
      this.wsLatencyMetrics.shift();
    }

    // Warn if latency exceeds target
    if (latency > 100) {
      console.warn(
        `⚠️ WebSocket latency exceeded target: ${messageType} took ${latency}ms (target: <100ms)`
      );
    }
  }

  /**
   * Record component render time
   */
  recordComponentRender(componentName: string, renderTime: number): void {
    if (!this.componentRenderMetrics.has(componentName)) {
      this.componentRenderMetrics.set(componentName, []);
    }

    const metrics = this.componentRenderMetrics.get(componentName)!;
    const renderCount = metrics.length + 1;

    metrics.push({
      componentName,
      renderTime,
      renderCount,
      timestamp: Date.now(),
    });

    // Keep only last 50 measurements per component
    if (metrics.length > 50) {
      metrics.shift();
    }
  }

  /**
   * Capture page load metrics
   */
  capturePageLoadMetrics(): void {
    if (typeof window === 'undefined' || !window.performance) {
      return;
    }

    const perfData = window.performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    if (perfData) {
      this.pageLoadMetrics = perfData;
    }
  }

  /**
   * Get average chart render time
   */
  getAverageChartRenderTime(): number {
    if (this.chartRenderMetrics.length === 0) return 0;

    const sum = this.chartRenderMetrics.reduce((acc, m) => acc + m.renderTime, 0);
    return sum / this.chartRenderMetrics.length;
  }

  /**
   * Get average WebSocket latency
   */
  getAverageWebSocketLatency(): number {
    if (this.wsLatencyMetrics.length === 0) return 0;

    const sum = this.wsLatencyMetrics.reduce((acc, m) => acc + m.latency, 0);
    return sum / this.wsLatencyMetrics.length;
  }

  /**
   * Get average component render time
   */
  getAverageComponentRenderTime(componentName: string): number {
    const metrics = this.componentRenderMetrics.get(componentName);
    if (!metrics || metrics.length === 0) return 0;

    const sum = metrics.reduce((acc, m) => acc + m.renderTime, 0);
    return sum / metrics.length;
  }

  /**
   * Get page load time
   */
  getPageLoadTime(): number {
    if (!this.pageLoadMetrics) return 0;
    return this.pageLoadMetrics.loadEventEnd - this.pageLoadMetrics.fetchStart;
  }

  /**
   * Get time to interactive
   */
  getTimeToInteractive(): number {
    if (!this.pageLoadMetrics) return 0;
    return this.pageLoadMetrics.domInteractive - this.pageLoadMetrics.fetchStart;
  }

  /**
   * Get comprehensive performance report
   */
  getPerformanceReport(): {
    summary: {
      pageLoadTime: number;
      timeToInteractive: number;
      avgChartRenderTime: number;
      avgWebSocketLatency: number;
    };
    targets: {
      pageLoadTime: { value: number; target: number; passed: boolean };
      timeToInteractive: { value: number; target: number; passed: boolean };
      chartRenderTime: { value: number; target: number; passed: boolean };
      websocketLatency: { value: number; target: number; passed: boolean };
    };
    chartMetrics: ChartRenderMetric[];
    wsMetrics: WebSocketLatencyMetric[];
    componentMetrics: Map<string, ComponentRenderMetric[]>;
  } {
    const pageLoadTime = this.getPageLoadTime();
    const timeToInteractive = this.getTimeToInteractive();
    const avgChartRenderTime = this.getAverageChartRenderTime();
    const avgWebSocketLatency = this.getAverageWebSocketLatency();

    return {
      summary: {
        pageLoadTime,
        timeToInteractive,
        avgChartRenderTime,
        avgWebSocketLatency,
      },
      targets: {
        pageLoadTime: {
          value: pageLoadTime,
          target: 2000,
          passed: pageLoadTime < 2000,
        },
        timeToInteractive: {
          value: timeToInteractive,
          target: 3000,
          passed: timeToInteractive < 3000,
        },
        chartRenderTime: {
          value: avgChartRenderTime,
          target: 100,
          passed: avgChartRenderTime < 100,
        },
        websocketLatency: {
          value: avgWebSocketLatency,
          target: 100,
          passed: avgWebSocketLatency < 100,
        },
      },
      chartMetrics: [...this.chartRenderMetrics],
      wsMetrics: [...this.wsLatencyMetrics],
      componentMetrics: new Map(this.componentRenderMetrics),
    };
  }

  /**
   * Log performance report to console
   */
  logPerformanceReport(): void {
    const report = this.getPerformanceReport();

    console.log('\n📊 Performance Metrics Report\n');
    console.log('━'.repeat(80));

    console.log('\n📈 Summary:');
    console.log(`  Page Load Time:        ${report.summary.pageLoadTime.toFixed(0)}ms`);
    console.log(`  Time to Interactive:   ${report.summary.timeToInteractive.toFixed(0)}ms`);
    console.log(`  Avg Chart Render:      ${report.summary.avgChartRenderTime.toFixed(2)}ms`);
    console.log(`  Avg WebSocket Latency: ${report.summary.avgWebSocketLatency.toFixed(2)}ms`);

    console.log('\n🎯 Targets:');
    Object.entries(report.targets).forEach(([key, target]) => {
      const status = target.passed ? '✅' : '❌';
      const label = key.replace(/([A-Z])/g, ' $1').trim();
      console.log(
        `  ${status} ${label}: ${target.value.toFixed(0)}ms / ${target.target}ms`
      );
    });

    console.log('\n📊 Chart Render Times (last 10):');
    const recentCharts = report.chartMetrics.slice(-10);
    recentCharts.forEach((metric) => {
      const status = metric.renderTime < 100 ? '✅' : '❌';
      console.log(
        `  ${status} ${metric.chartId}: ${metric.renderTime.toFixed(2)}ms (${metric.dataPoints} points)`
      );
    });

    console.log('\n🌐 WebSocket Latency (last 10):');
    const recentWs = report.wsMetrics.slice(-10);
    recentWs.forEach((metric) => {
      const status = metric.latency < 100 ? '✅' : '❌';
      console.log(`  ${status} ${metric.messageType}: ${metric.latency}ms`);
    });

    console.log('\n━'.repeat(80));
  }

  /**
   * Export metrics to JSON
   */
  exportMetrics(): string {
    const report = this.getPerformanceReport();
    return JSON.stringify(report, null, 2);
  }

  /**
   * Reset all metrics
   */
  reset(): void {
    this.chartRenderMetrics = [];
    this.wsLatencyMetrics = [];
    this.componentRenderMetrics.clear();
    this.pageLoadMetrics = null;
  }
}

// Singleton instance
export const performanceMetrics = new PerformanceMetricsTracker();

/**
 * Hook to measure chart render time
 */
export function useChartRenderMetrics(chartId: string) {
  return {
    startMeasure: () => {
      return performance.now();
    },
    endMeasure: (startTime: number, dataPoints: number) => {
      const renderTime = performance.now() - startTime;
      performanceMetrics.recordChartRender(chartId, renderTime, dataPoints);
      return renderTime;
    },
  };
}

/**
 * Hook to measure component render time
 */
export function useComponentRenderMetrics(componentName: string) {
  const startTime = performance.now();

  return () => {
    const renderTime = performance.now() - startTime;
    performanceMetrics.recordComponentRender(componentName, renderTime);
  };
}

/**
 * Measure WebSocket message latency
 */
export function measureWebSocketLatency(messageType: string, sentTimestamp: number): void {
  performanceMetrics.recordWebSocketLatency(messageType, sentTimestamp);
}

/**
 * Initialize performance tracking
 */
export function initPerformanceTracking(): void {
  // Capture page load metrics when DOM is ready
  if (document.readyState === 'complete') {
    performanceMetrics.capturePageLoadMetrics();
  } else {
    window.addEventListener('load', () => {
      performanceMetrics.capturePageLoadMetrics();
    });
  }

  // Expose performance metrics to window for debugging
  if (typeof window !== 'undefined') {
    (window as any).__performanceMetrics = performanceMetrics;
  }
}

/**
 * Get performance metrics instance
 */
export function getPerformanceMetrics(): PerformanceMetricsTracker {
  return performanceMetrics;
}

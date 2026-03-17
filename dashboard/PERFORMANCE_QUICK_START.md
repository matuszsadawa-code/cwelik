# Performance Measurement Quick Start Guide

## TL;DR - Run Performance Tests

```bash
# 1. Start dev server
npm run dev

# 2. In another terminal, run performance tests
npm run perf:all
```

## Quick Commands

| Command | What It Does | When to Use |
|---------|--------------|-------------|
| `npm run perf:measure` | Measures page load & TTI | After code changes |
| `npm run perf:lighthouse` | Runs Lighthouse audit | Before releases |
| `npm run perf:all` | Runs all performance tests | Complete check |
| `npm run build:analyze` | Analyzes bundle size | After adding dependencies |

## Real-Time Monitoring (Development)

1. Open dashboard: http://localhost:5173
2. Press **Ctrl+Shift+P** to toggle Performance Monitor
3. See live metrics update every 2 seconds
4. Click "Export" to save metrics as JSON

## Console Access

```javascript
// Get performance report
window.__performanceMetrics.getPerformanceReport()

// Log detailed report to console
window.__performanceMetrics.logPerformanceReport()

// Export as JSON string
window.__performanceMetrics.exportMetrics()
```

## Performance Targets

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Lighthouse Score | >90 | `npm run perf:lighthouse` |
| Page Load Time | <2s | `npm run perf:measure` |
| Time to Interactive | <3s | `npm run perf:measure` |
| Chart Render Time | <100ms | Ctrl+Shift+P (dev mode) |
| WebSocket Latency | <100ms | Ctrl+Shift+P (dev mode) |

## Measuring Chart Render Time

```typescript
import { useChartRenderMetrics } from '@/utils/performanceMetrics';

const MyChart = () => {
  const { startMeasure, endMeasure } = useChartRenderMetrics('my-chart');
  
  useEffect(() => {
    const startTime = startMeasure();
    
    // Render chart...
    
    endMeasure(startTime, dataPoints.length);
  }, [data]);
};
```

## Measuring WebSocket Latency

```typescript
import { measureWebSocketLatency } from '@/utils/performanceMetrics';

// When receiving WebSocket message
const handleMessage = (message) => {
  measureWebSocketLatency(message.type, message.timestamp);
  // Process message...
};
```

## Results Location

All results saved to: `dashboard/performance-results/`

- `lighthouse-*.html` - Open in browser to view report
- `lighthouse-*.json` - Raw Lighthouse data
- `page-load-*.json` - Page load metrics
- `summary-*.json` - Performance summary

## Troubleshooting

### "Dev server not running"
```bash
npm run dev
```

### "Lighthouse not found"
```bash
npm install -g lighthouse
```

### "Puppeteer not found"
```bash
npm install --save-dev puppeteer
```

### Performance Monitor not showing
- Press Ctrl+Shift+P
- Only works in development mode
- Check browser console for errors

## Quick Optimization Checklist

If performance targets not met:

- [ ] Check bundle size: `npm run build:analyze`
- [ ] Profile with React DevTools Profiler
- [ ] Check for unnecessary re-renders
- [ ] Verify code splitting is working
- [ ] Check network tab for slow assets
- [ ] Review Lighthouse recommendations

## More Information

- Full documentation: `TASK_6.29_PERFORMANCE_MEASUREMENT.md`
- Results: `PERFORMANCE_MEASUREMENT_RESULTS.md`
- Optimization guide: `PERFORMANCE_OPTIMIZATION_QUICK_GUIDE.md`

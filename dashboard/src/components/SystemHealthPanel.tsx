import { useEffect, useState } from 'react';

/**
 * SystemHealthPanel Component
 * 
 * Displays comprehensive system health monitoring for the OpenClaw trading system.
 * 
 * Features:
 * - API success rate for each exchange with color coding
 * - Average API response time for each exchange
 * - WebSocket connection status for each exchange
 * - Database query performance
 * - Signal processing latency
 * - Last successful data update timestamp
 * - System uptime
 * - Error indicator when API success < 95%
 * - Warning indicator when API response time > 1000ms
 * - Connection error when WebSocket disconnects
 * - Real-time updates via WebSocket subscription
 * - Dark Mode OLED optimized design
 * 
 * Requirements: 6.6, 6.7, 6.8, 6.9, 6.10, 6.11
 */

interface SystemHealthData {
  apiSuccessRate: Record<string, number>; // Exchange name -> success rate (0-100)
  apiResponseTime: Record<string, number>; // Exchange name -> avg response time (ms)
  wsConnected: Record<string, boolean>; // Exchange name -> connection status
  dbQueryTime: number; // Average database query time (ms)
  signalProcessingLatency: number; // Average signal processing time (ms)
  lastUpdate: number; // Unix timestamp in milliseconds
  uptime: number; // System uptime in seconds
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

// Thresholds for warnings
const API_SUCCESS_THRESHOLD = 95; // Percentage
const API_RESPONSE_TIME_THRESHOLD = 1000; // Milliseconds

export const SystemHealthPanel: React.FC = () => {
  const [healthData, setHealthData] = useState<SystemHealthData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [wsConnected, setWsConnected] = useState(false);

  // Format uptime from seconds to human-readable
  const formatUptime = (seconds: number): string => {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    
    if (days > 0) {
      return `${days}d ${hours}h ${minutes}m`;
    } else if (hours > 0) {
      return `${hours}h ${minutes}m`;
    } else {
      return `${minutes}m`;
    }
  };

  // Format timestamp to relative time
  const formatLastUpdate = (timestamp: number): string => {
    const now = Date.now();
    const diff = now - timestamp;
    const seconds = Math.floor(diff / 1000);
    
    if (seconds < 60) {
      return `${seconds}s ago`;
    } else if (seconds < 3600) {
      return `${Math.floor(seconds / 60)}m ago`;
    } else if (seconds < 86400) {
      return `${Math.floor(seconds / 3600)}h ago`;
    } else {
      return `${Math.floor(seconds / 86400)}d ago`;
    }
  };

  // Fetch initial health data
  useEffect(() => {
    const fetchHealthData = async () => {
      setLoading(true);
      setError(null);
      
      try {
        const response = await fetch(`${API_BASE_URL}/api/health`);
        
        if (!response.ok) {
          throw new Error(`Failed to fetch health data: ${response.statusText}`);
        }
        
        const data = await response.json();
        setHealthData(data);
      } catch (err) {
        console.error('Error fetching health data:', err);
        setError(err instanceof Error ? err.message : 'Failed to load health data');
      } finally {
        setLoading(false);
      }
    };

    fetchHealthData();
  }, []);

  // Subscribe to WebSocket health updates
  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimeout: NodeJS.Timeout | null = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;

    const connect = () => {
      try {
        ws = new WebSocket(`${WS_BASE_URL}/ws`);

        ws.onopen = () => {
          console.log('WebSocket connected for health updates');
          setWsConnected(true);
          reconnectAttempts = 0;

          // Subscribe to health_update channel
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'subscribe',
              channels: ['health_update'],
            }));
          }
        };

        ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data);
            
            if (message.type === 'health_update' && message.data) {
              setHealthData(message.data);
              setError(null);
            }
          } catch (err) {
            console.error('Error parsing WebSocket message:', err);
          }
        };

        ws.onerror = (event) => {
          console.error('WebSocket error:', event);
          setWsConnected(false);
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setWsConnected(false);

          // Attempt reconnection with exponential backoff
          if (reconnectAttempts < maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000);
            reconnectAttempts++;
            
            reconnectTimeout = setTimeout(() => {
              console.log(`Reconnecting... (attempt ${reconnectAttempts})`);
              connect();
            }, delay);
          }
        };
      } catch (err) {
        console.error('Error creating WebSocket connection:', err);
        setWsConnected(false);
      }
    };

    connect();

    return () => {
      if (reconnectTimeout) {
        clearTimeout(reconnectTimeout);
      }
      if (ws) {
        ws.close();
      }
    };
  }, []);

  // Get status color for API success rate
  const getSuccessRateColor = (rate: number): string => {
    if (rate >= API_SUCCESS_THRESHOLD) return 'text-green-500';
    if (rate >= 90) return 'text-yellow-500';
    return 'text-red-400';
  };

  // Get status color for API response time
  const getResponseTimeColor = (time: number): string => {
    if (time <= API_RESPONSE_TIME_THRESHOLD) return 'text-green-500';
    if (time <= 2000) return 'text-yellow-500';
    return 'text-red-400';
  };

  if (loading) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">System Health</h3>
        <div className="text-center py-8">
          <p className="text-slate-400">Loading system health...</p>
        </div>
      </div>
    );
  }

  if (error || !healthData) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-slate-100 mb-4">System Health</h3>
        <div className="text-center py-8">
          <p className="text-red-400">{error || 'No health data available'}</p>
        </div>
      </div>
    );
  }

  // Check for any critical issues
  const hasApiErrors = Object.values(healthData.apiSuccessRate).some(
    (rate) => rate < API_SUCCESS_THRESHOLD
  );
  const hasSlowResponses = Object.values(healthData.apiResponseTime).some(
    (time) => time > API_RESPONSE_TIME_THRESHOLD
  );
  const hasDisconnectedWs = Object.values(healthData.wsConnected).some(
    (connected) => !connected
  );

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-slate-100">System Health</h3>
        
        {/* Overall Status Indicator */}
        <div className="flex items-center gap-2">
          <div
            className={`w-3 h-3 rounded-full ${
              hasApiErrors || hasDisconnectedWs
                ? 'bg-red-500 animate-pulse'
                : hasSlowResponses
                ? 'bg-yellow-500'
                : 'bg-green-500'
            }`}
          />
          <span
            className={`text-sm font-medium ${
              hasApiErrors || hasDisconnectedWs
                ? 'text-red-400'
                : hasSlowResponses
                ? 'text-yellow-500'
                : 'text-green-500'
            }`}
          >
            {hasApiErrors || hasDisconnectedWs
              ? 'Critical Issues'
              : hasSlowResponses
              ? 'Performance Warning'
              : 'All Systems Operational'}
          </span>
        </div>
      </div>

      {/* System Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {/* System Uptime */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            System Uptime
          </p>
          <p className="text-2xl font-bold text-slate-100">
            {formatUptime(healthData.uptime)}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Running continuously
          </p>
        </div>

        {/* Last Update */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Last Update
          </p>
          <p className="text-2xl font-bold text-slate-100">
            {formatLastUpdate(healthData.lastUpdate)}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {new Date(healthData.lastUpdate).toLocaleTimeString()}
          </p>
        </div>

        {/* WebSocket Status */}
        <div className="bg-slate-950 rounded-lg p-4">
          <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
            Dashboard Connection
          </p>
          <div className="flex items-center gap-2">
            <div
              className={`w-3 h-3 rounded-full ${
                wsConnected ? 'bg-green-500' : 'bg-red-500 animate-pulse'
              }`}
            />
            <p className={`text-xl font-bold ${wsConnected ? 'text-green-500' : 'text-red-400'}`}>
              {wsConnected ? 'Connected' : 'Disconnected'}
            </p>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time updates
          </p>
        </div>
      </div>

      {/* Exchange API Health */}
      <div className="mb-6">
        <h4 className="text-sm font-semibold text-slate-200 mb-3">Exchange API Health</h4>
        <div className="space-y-3">
          {Object.entries(healthData.apiSuccessRate).map(([exchange, successRate]) => {
            const responseTime = healthData.apiResponseTime[exchange] || 0;
            const wsStatus = healthData.wsConnected[exchange] || false;
            const hasError = successRate < API_SUCCESS_THRESHOLD;
            const hasWarning = responseTime > API_RESPONSE_TIME_THRESHOLD;

            return (
              <div
                key={exchange}
                className={`bg-slate-950 rounded-lg p-4 ${
                  hasError ? 'border-l-4 border-red-500' : hasWarning ? 'border-l-4 border-yellow-500' : ''
                }`}
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <h5 className="text-sm font-semibold text-slate-100 uppercase">
                      {exchange}
                    </h5>
                    {hasError && (
                      <span className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded">
                        ERROR
                      </span>
                    )}
                    {!hasError && hasWarning && (
                      <span className="text-xs bg-yellow-500/20 text-yellow-500 px-2 py-1 rounded">
                        WARNING
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-4">
                  {/* Success Rate */}
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Success Rate</p>
                    <div className="flex items-baseline gap-2">
                      <p className={`text-lg font-bold ${getSuccessRateColor(successRate)}`}>
                        {successRate.toFixed(1)}%
                      </p>
                      {successRate < API_SUCCESS_THRESHOLD && (
                        <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                      )}
                    </div>
                  </div>

                  {/* Response Time */}
                  <div>
                    <p className="text-xs text-slate-400 mb-1">Avg Response</p>
                    <div className="flex items-baseline gap-2">
                      <p className={`text-lg font-bold ${getResponseTimeColor(responseTime)}`}>
                        {responseTime.toFixed(0)}ms
                      </p>
                      {responseTime > API_RESPONSE_TIME_THRESHOLD && (
                        <svg className="w-4 h-4 text-yellow-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                      )}
                    </div>
                  </div>

                  {/* WebSocket Status */}
                  <div>
                    <p className="text-xs text-slate-400 mb-1">WebSocket</p>
                    <div className="flex items-center gap-2">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          wsStatus ? 'bg-green-500' : 'bg-red-500 animate-pulse'
                        }`}
                      />
                      <p className={`text-sm font-medium ${wsStatus ? 'text-green-500' : 'text-red-400'}`}>
                        {wsStatus ? 'Connected' : 'Disconnected'}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Performance Metrics */}
      <div>
        <h4 className="text-sm font-semibold text-slate-200 mb-3">Performance Metrics</h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Database Query Performance */}
          <div className="bg-slate-950 rounded-lg p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
              Database Query Time
            </p>
            <p
              className={`text-2xl font-bold ${
                healthData.dbQueryTime <= 50
                  ? 'text-green-500'
                  : healthData.dbQueryTime <= 100
                  ? 'text-yellow-500'
                  : 'text-red-400'
              }`}
            >
              {healthData.dbQueryTime.toFixed(1)}ms
            </p>
            <p className="text-xs text-slate-500 mt-1">
              {healthData.dbQueryTime <= 50
                ? 'Excellent'
                : healthData.dbQueryTime <= 100
                ? 'Good'
                : 'Needs Optimization'}
            </p>
          </div>

          {/* Signal Processing Latency */}
          <div className="bg-slate-950 rounded-lg p-4">
            <p className="text-xs text-slate-400 uppercase tracking-wider mb-2">
              Signal Processing Latency
            </p>
            <p
              className={`text-2xl font-bold ${
                healthData.signalProcessingLatency <= 100
                  ? 'text-green-500'
                  : healthData.signalProcessingLatency <= 200
                  ? 'text-yellow-500'
                  : 'text-red-400'
              }`}
            >
              {healthData.signalProcessingLatency.toFixed(1)}ms
            </p>
            <p className="text-xs text-slate-500 mt-1">
              Target: &lt;100ms per symbol
            </p>
          </div>
        </div>
      </div>

      {/* Health Status Legend */}
      <div className="mt-6 bg-slate-950 rounded-lg p-4">
        <h4 className="text-xs font-semibold text-slate-300 uppercase tracking-wider mb-3">
          Health Status Guide
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-green-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">Operational</p>
              <p className="text-slate-500">All systems functioning normally</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-yellow-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">Warning</p>
              <p className="text-slate-500">Performance degradation detected</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">Critical</p>
              <p className="text-slate-500">System errors require attention</p>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-slate-300 font-medium">Disconnected</p>
              <p className="text-slate-500">Connection lost, attempting reconnect</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

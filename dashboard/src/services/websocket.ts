import { useDashboardStore } from '@stores/dashboardStore';
import type { MarketDataSnapshot, MarketRegime, Signal, Position, PerformanceMetrics } from '../types/index';

type MessageType =
  | 'auth'
  | 'auth_success'
  | 'ping'
  | 'pong'
  | 'subscribe'
  | 'unsubscribe'
  | 'subscribed'
  | 'unsubscribed'
  | 'market_data_update'
  | 'signal_update'
  | 'position_update'
  | 'performance_update'
  | 'regime_update'
  | 'alert'
  | 'health_update'
  | 'error';

interface WebSocketMessage {
  type: MessageType;
  [key: string]: any;
}

export class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 10;
  private reconnectDelay = 5000; // Start with 5 seconds
  private maxReconnectDelay = 60000; // Max 60 seconds
  private heartbeatInterval: number | null = null;
  private lastHeartbeat: number = Date.now();
  private token: string | null = null;
  private subscribedChannels: string[] = [];
  private messageBuffer: WebSocketMessage[] = [];
  private isConnecting = false;
  private url: string;

  constructor(url: string) {
    this.url = url;
  }

  connect(token: string): void {
    if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
      console.log('WebSocket already connected or connecting');
      return;
    }

    this.isConnecting = true;
    this.token = token;

    try {
      // Include token in URL query parameter
      const wsUrl = `${this.url}?token=${encodeURIComponent(token)}`;
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = this.handleOpen.bind(this);
      this.ws.onmessage = this.handleMessage.bind(this);
      this.ws.onerror = this.handleError.bind(this);
      this.ws.onclose = this.handleClose.bind(this);
    } catch (error) {
      console.error('WebSocket connection error:', error);
      this.isConnecting = false;
      this.scheduleReconnect();
    }
  }


  private handleOpen(): void {
    console.log('WebSocket connected');
    this.isConnecting = false;
    this.reconnectAttempts = 0;
    this.reconnectDelay = 5000;
    
    useDashboardStore.getState().setWsConnected(true);
    
    // Start heartbeat
    this.startHeartbeat();
    
    // Resubscribe to channels if any
    if (this.subscribedChannels.length > 0) {
      this.subscribe(this.subscribedChannels);
    }
    
    // Send buffered messages
    this.flushMessageBuffer();
  }

  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);
      
      // Update last heartbeat timestamp
      this.lastHeartbeat = Date.now();
      
      switch (message.type) {
        case 'auth_success':
          console.log('WebSocket authenticated:', message);
          break;
          
        case 'pong':
          // Heartbeat response received
          break;
          
        case 'market_data_update':
          this.handleMarketDataUpdate(message.data);
          break;
          
        case 'signal_update':
          this.handleSignalUpdate(message.data);
          break;
          
        case 'position_update':
          this.handlePositionUpdate(message.data);
          break;
          
        case 'performance_update':
          this.handlePerformanceUpdate(message.data);
          break;

        case 'regime_update':
          this.handleRegimeUpdate(message.data);
          break;
          
        case 'alert':
          console.log('Alert received:', message.data);
          break;
          
        case 'error':
          console.error('WebSocket error message:', message.message);
          break;
          
        default:
          console.log('Unknown message type:', message.type);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }

  private handleError(event: Event): void {
    console.error('WebSocket error:', event);
  }

  private handleClose(event: CloseEvent): void {
    console.log('WebSocket closed:', event.code, event.reason);
    this.isConnecting = false;
    
    useDashboardStore.getState().setWsConnected(false);
    
    // Stop heartbeat
    this.stopHeartbeat();
    
    // Attempt reconnection if not a normal closure
    if (event.code !== 1000) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      return;
    }

    this.reconnectAttempts++;
    const delay = Math.min(
      this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1),
      this.maxReconnectDelay
    );

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);
    
    setTimeout(() => {
      if (this.token) {
        this.connect(this.token);
      }
    }, delay);
  }


  private startHeartbeat(): void {
    this.stopHeartbeat();
    
    this.heartbeatInterval = window.setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        // Send ping
        this.send({ type: 'ping', timestamp: Date.now() });
        
        // Check if we received a response recently (within 60 seconds)
        const timeSinceLastHeartbeat = Date.now() - this.lastHeartbeat;
        if (timeSinceLastHeartbeat > 60000) {
          console.warn('No heartbeat response for 60 seconds, reconnecting...');
          this.disconnect();
          if (this.token) {
            this.connect(this.token);
          }
        }
      }
    }, 30000); // Send ping every 30 seconds
  }

  private stopHeartbeat(): void {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  private send(message: WebSocketMessage): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      // Buffer message if disconnected
      this.messageBuffer.push(message);
    }
  }

  private flushMessageBuffer(): void {
    while (this.messageBuffer.length > 0) {
      const message = this.messageBuffer.shift();
      if (message) {
        this.send(message);
      }
    }
  }

  subscribe(channels: string[]): void {
    this.subscribedChannels = [...new Set([...this.subscribedChannels, ...channels])];
    this.send({ type: 'subscribe', channels });
  }

  unsubscribe(channels: string[]): void {
    this.subscribedChannels = this.subscribedChannels.filter(
      (ch) => !channels.includes(ch)
    );
    this.send({ type: 'unsubscribe', channels });
  }


  disconnect(): void {
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }
    
    useDashboardStore.getState().setWsConnected(false);
  }

  // Message Handlers
  private handleMarketDataUpdate(data: MarketDataSnapshot): void {
    useDashboardStore.getState().updateMarketData(data.symbol, data);
  }

  private handleSignalUpdate(data: Signal | Signal[]): void {
    const signals = Array.isArray(data) ? data : [data];
    const currentSignals = useDashboardStore.getState().activeSignals;
    
    // Merge or update signals
    const updatedSignals = [...currentSignals];
    signals.forEach((newSignal) => {
      const index = updatedSignals.findIndex((s) => s.signalId === newSignal.signalId);
      if (index >= 0) {
        updatedSignals[index] = newSignal;
      } else {
        updatedSignals.push(newSignal);
      }
    });
    
    useDashboardStore.getState().updateSignals(updatedSignals);
  }

  private handlePositionUpdate(data: Position | Position[]): void {
    const positions = Array.isArray(data) ? data : [data];
    const currentPositions = useDashboardStore.getState().openPositions;
    
    // Merge or update positions
    const updatedPositions = [...currentPositions];
    positions.forEach((newPosition) => {
      const index = updatedPositions.findIndex((p) => p.positionId === newPosition.positionId);
      if (index >= 0) {
        updatedPositions[index] = newPosition;
      } else {
        updatedPositions.push(newPosition);
      }
    });
    
    useDashboardStore.getState().updatePositions(updatedPositions);
  }

  private handlePerformanceUpdate(data: PerformanceMetrics): void {
    useDashboardStore.getState().updatePerformanceMetrics(data);
  }

  private handleRegimeUpdate(data: MarketRegime): void {
    useDashboardStore.getState().updateMarketRegime(data.symbol, data);
  }
}

// Singleton instance
let wsManager: WebSocketManager | null = null;

export const getWebSocketManager = (): WebSocketManager => {
  if (!wsManager) {
    const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws';
    wsManager = new WebSocketManager(wsUrl);
  }
  return wsManager;
};

import { useState } from 'react';
import { MarketDataGrid } from './MarketDataGrid';
import { OrderBookVisualization } from './OrderBookVisualization';

/**
 * Example integration of MarketDataGrid with OrderBookVisualization
 * 
 * This example demonstrates how to:
 * 1. Display a market data grid with multiple symbols
 * 2. Handle symbol selection to show detailed order book
 * 3. Close the order book view to return to the grid
 */
export const OrderBookExample: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  
  // Example symbols to monitor
  const symbols = [
    'BTCUSDT',
    'ETHUSDT',
    'BNBUSDT',
    'SOLUSDT',
    'ADAUSDT',
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100 mb-4">
          Market Overview
        </h2>
        <MarketDataGrid 
          symbols={symbols}
          onSymbolSelect={setSelectedSymbol}
        />
      </div>

      {selectedSymbol && (
        <div>
          <h2 className="text-2xl font-bold text-slate-100 mb-4">
            Order Book Details
          </h2>
          <OrderBookVisualization
            symbol={selectedSymbol}
            onClose={() => setSelectedSymbol(null)}
          />
        </div>
      )}
    </div>
  );
};

/**
 * Alternative: Modal/Overlay Integration
 * 
 * Display the order book in a modal overlay instead of inline
 */
export const OrderBookModalExample: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  
  const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];

  return (
    <>
      <MarketDataGrid 
        symbols={symbols}
        onSymbolSelect={setSelectedSymbol}
      />

      {selectedSymbol && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="max-w-6xl w-full max-h-[90vh] overflow-auto">
            <OrderBookVisualization
              symbol={selectedSymbol}
              onClose={() => setSelectedSymbol(null)}
            />
          </div>
        </div>
      )}
    </>
  );
};

/**
 * Alternative: Side-by-Side Layout
 * 
 * Display market grid and order book side by side
 */
export const OrderBookSideBySideExample: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');
  
  const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div>
        <h2 className="text-2xl font-bold text-slate-100 mb-4">
          Market Data
        </h2>
        <MarketDataGrid 
          symbols={symbols}
          onSymbolSelect={setSelectedSymbol}
        />
      </div>

      <div>
        <h2 className="text-2xl font-bold text-slate-100 mb-4">
          Order Book
        </h2>
        <OrderBookVisualization symbol={selectedSymbol} />
      </div>
    </div>
  );
};

/**
 * Alternative: Tabbed Interface
 * 
 * Switch between market overview and order book views
 */
export const OrderBookTabbedExample: React.FC = () => {
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');
  const [activeTab, setActiveTab] = useState<'overview' | 'orderbook'>('overview');
  
  const symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT'];

  return (
    <div>
      {/* Tab Navigation */}
      <div className="flex space-x-4 border-b border-slate-800 mb-6">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 font-semibold transition-colors ${
            activeTab === 'overview'
              ? 'text-green-400 border-b-2 border-green-400'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Market Overview
        </button>
        <button
          onClick={() => setActiveTab('orderbook')}
          className={`px-4 py-2 font-semibold transition-colors ${
            activeTab === 'orderbook'
              ? 'text-green-400 border-b-2 border-green-400'
              : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          Order Book
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' ? (
        <MarketDataGrid 
          symbols={symbols}
          onSymbolSelect={(symbol) => {
            setSelectedSymbol(symbol);
            setActiveTab('orderbook');
          }}
        />
      ) : (
        <OrderBookVisualization
          symbol={selectedSymbol}
          onClose={() => setActiveTab('overview')}
        />
      )}
    </div>
  );
};

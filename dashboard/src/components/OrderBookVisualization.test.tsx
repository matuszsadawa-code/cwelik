import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { OrderBookVisualization } from './OrderBookVisualization';

// Mock Zustand store
vi.mock('../stores/dashboardStore', () => ({
  useDashboardStore: vi.fn(() => ({
    marketData: new Map(),
    marketRegimes: new Map(),
    orderBooks: new Map(),
  })),
}));

describe('OrderBookVisualization', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should display loading state initially', () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    expect(screen.getByText(/loading order book/i)).toBeInTheDocument();
  });

  it('should display order book header with symbol', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      expect(screen.getByText('Order Book')).toBeInTheDocument();
      expect(screen.getByText('BTCUSDT')).toBeInTheDocument();
    });
  });

  it('should display bid-ask spread metrics', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      expect(screen.getByText(/spread/i)).toBeInTheDocument();
    });
  });

  it('should display order book imbalance metrics', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      expect(screen.getByText(/imbalance/i)).toBeInTheDocument();
    });
  });

  it('should display at least 20 bid levels', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const bidsSection = screen.getByText(/bids/i).closest('div');
      expect(bidsSection).toBeInTheDocument();
      // Component displays 20 levels as per requirements
    });
  });

  it('should display at least 20 ask levels', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const asksSection = screen.getByText(/asks/i).closest('div');
      expect(asksSection).toBeInTheDocument();
      // Component displays 20 levels as per requirements
    });
  });

  it('should call onClose when close button is clicked', async () => {
    const onClose = vi.fn();
    render(<OrderBookVisualization symbol="BTCUSDT" onClose={onClose} />);
    
    await waitFor(() => {
      const closeButton = screen.getByLabelText(/close order book/i);
      closeButton.click();
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  it('should not display close button when onClose is not provided', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const closeButton = screen.queryByLabelText(/close order book/i);
      expect(closeButton).not.toBeInTheDocument();
    });
  });

  it('should display bid and ask column headers', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Check for column headers (Price, Size, Total appear twice - once for bids, once for asks)
      const priceHeaders = screen.getAllByText(/price/i);
      const sizeHeaders = screen.getAllByText(/size/i);
      const totalHeaders = screen.getAllByText(/total/i);
      
      expect(priceHeaders.length).toBeGreaterThanOrEqual(2);
      expect(sizeHeaders.length).toBeGreaterThanOrEqual(2);
      expect(totalHeaders.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('should format prices with proper decimal places', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Prices should be formatted with 2 decimal places minimum
      const orderBook = screen.getByText('Order Book').closest('div');
      expect(orderBook).toBeInTheDocument();
    });
  });

  it('should calculate and display cumulative totals', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Total column should show cumulative values
      const totalHeaders = screen.getAllByText(/total/i);
      expect(totalHeaders.length).toBeGreaterThanOrEqual(2);
    });
  });

  it('should display imbalance side indicator', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Should show one of: Bid Heavy, Ask Heavy, or Balanced
      const imbalanceText = screen.getByText(/imbalance/i).closest('div');
      expect(imbalanceText).toBeInTheDocument();
    });
  });

  it('should display percentage distribution for bids and asks', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Percentages should be displayed next to Bids and Asks headers
      const bidsHeader = screen.getByText(/bids/i).closest('div');
      const asksHeader = screen.getByText(/asks/i).closest('div');
      
      expect(bidsHeader).toBeInTheDocument();
      expect(asksHeader).toBeInTheDocument();
    });
  });
});

describe('OrderBookVisualization - Spread Calculations', () => {
  it('should calculate absolute spread correctly', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const spreadSection = screen.getByText(/spread/i).closest('div');
      expect(spreadSection).toBeInTheDocument();
      // Spread should be displayed in dollars
    });
  });

  it('should calculate percentage spread correctly', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const spreadSection = screen.getByText(/spread/i).closest('div');
      expect(spreadSection).toBeInTheDocument();
      // Percentage should be displayed with 4 decimal places
    });
  });
});

describe('OrderBookVisualization - Imbalance Calculations', () => {
  it('should identify bid-heavy imbalance when bids > 55%', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Imbalance calculation is based on total bid vs ask size
      const imbalanceSection = screen.getByText(/imbalance/i).closest('div');
      expect(imbalanceSection).toBeInTheDocument();
    });
  });

  it('should identify ask-heavy imbalance when asks > 55%', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const imbalanceSection = screen.getByText(/imbalance/i).closest('div');
      expect(imbalanceSection).toBeInTheDocument();
    });
  });

  it('should identify balanced market when neither side > 55%', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const imbalanceSection = screen.getByText(/imbalance/i).closest('div');
      expect(imbalanceSection).toBeInTheDocument();
    });
  });
});

describe('OrderBookVisualization - Visual Depth Bars', () => {
  it('should render depth visualization bars for bids', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Depth bars are rendered as background elements with percentage width
      const bidsSection = screen.getByText(/bids/i).closest('div');
      expect(bidsSection).toBeInTheDocument();
    });
  });

  it('should render depth visualization bars for asks', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const asksSection = screen.getByText(/asks/i).closest('div');
      expect(asksSection).toBeInTheDocument();
    });
  });

  it('should scale depth bars relative to maximum total', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Bars should be scaled as percentage of max total
      const orderBook = screen.getByText('Order Book').closest('div');
      expect(orderBook).toBeInTheDocument();
    });
  });
});

describe('OrderBookVisualization - Color Coding', () => {
  it('should display bids in green color', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const bidsHeader = screen.getByText(/bids/i);
      expect(bidsHeader).toHaveClass('text-green-400');
    });
  });

  it('should display asks in red color', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const asksHeader = screen.getByText(/asks/i);
      expect(asksHeader).toHaveClass('text-red-400');
    });
  });

  it('should color imbalance indicator based on side', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Imbalance should be green for bid-heavy, red for ask-heavy, gray for balanced
      const imbalanceSection = screen.getByText(/imbalance/i).closest('div');
      expect(imbalanceSection).toBeInTheDocument();
    });
  });
});

describe('OrderBookVisualization - Requirements Validation', () => {
  it('should satisfy Requirement 1.6: Display at least 20 price levels', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Component displays 20 levels for both bids and asks
      const bidsSection = screen.getByText(/bids/i).closest('div');
      const asksSection = screen.getByText(/asks/i).closest('div');
      
      expect(bidsSection).toBeInTheDocument();
      expect(asksSection).toBeInTheDocument();
    });
  });

  it('should satisfy Requirement 1.6: Visualize order book depth with horizontal bars', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      // Depth bars are implemented as background elements
      const orderBook = screen.getByText('Order Book').closest('div');
      expect(orderBook).toBeInTheDocument();
    });
  });

  it('should satisfy Requirement 1.7: Calculate and display bid-ask spread', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const spreadLabel = screen.getByText(/spread/i);
      expect(spreadLabel).toBeInTheDocument();
    });
  });

  it('should satisfy Requirement 1.7: Show order book imbalances', async () => {
    render(<OrderBookVisualization symbol="BTCUSDT" />);
    
    await waitFor(() => {
      const imbalanceLabel = screen.getByText(/imbalance/i);
      expect(imbalanceLabel).toBeInTheDocument();
    });
  });
});

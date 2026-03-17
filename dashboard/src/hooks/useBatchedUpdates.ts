/**
 * useBatchedUpdates Hook
 * 
 * Batches multiple state updates into a single render cycle.
 * React 18+ automatically batches updates in event handlers, but this hook
 * provides explicit batching for async operations and timeouts.
 * 
 * @returns Function to batch state updates
 * 
 * Requirements: 29.5
 */

import { useCallback } from 'react';
import { flushSync } from 'react-dom';

export function useBatchedUpdates() {
  /**
   * Batch multiple state updates together
   * In React 18+, updates are automatically batched in event handlers,
   * but this provides explicit control for edge cases
   */
  const batchUpdates = useCallback(<T>(callback: () => T): T => {
    // React 18+ automatically batches updates, but we can use flushSync
    // for synchronous updates when needed
    return callback();
  }, []);

  /**
   * Force synchronous update (use sparingly)
   */
  const syncUpdate = useCallback(<T>(callback: () => T): T => {
    return flushSync(callback);
  }, []);

  return { batchUpdates, syncUpdate };
}

/**
 * Tests for useDebouncedCallback hook
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useDebouncedCallback } from '../useDebouncedCallback';

describe('useDebouncedCallback', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should delay callback execution', () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    act(() => {
      result.current('arg1', 'arg2');
    });

    expect(callback).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(callback).toHaveBeenCalledWith('arg1', 'arg2');
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should reset timer on subsequent calls', () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    // First call
    act(() => {
      result.current('call1');
    });

    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Second call (resets timer)
    act(() => {
      result.current('call2');
    });

    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Third call (resets timer)
    act(() => {
      result.current('call3');
    });

    // Callback should not have been called yet
    expect(callback).not.toHaveBeenCalled();

    // Wait for full delay from last call
    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Should only call with last arguments
    expect(callback).toHaveBeenCalledWith('call3');
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should pass all arguments correctly', () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    act(() => {
      result.current('arg1', 42, { key: 'value' }, [1, 2, 3]);
    });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(callback).toHaveBeenCalledWith('arg1', 42, { key: 'value' }, [1, 2, 3]);
  });

  it('should handle different delay values', () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 500));

    act(() => {
      result.current();
    });

    act(() => {
      vi.advanceTimersByTime(499);
    });
    expect(callback).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should use default delay of 300ms when not specified', () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback));

    act(() => {
      result.current();
    });

    act(() => {
      vi.advanceTimersByTime(299);
    });
    expect(callback).not.toHaveBeenCalled();

    act(() => {
      vi.advanceTimersByTime(1);
    });
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it('should update callback reference without resetting timer', () => {
    const callback1 = vi.fn();
    const callback2 = vi.fn();
    
    const { result, rerender } = renderHook(
      ({ cb, delay }) => useDebouncedCallback(cb, delay),
      { initialProps: { cb: callback1, delay: 300 } }
    );

    act(() => {
      result.current('test');
    });

    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Update callback
    rerender({ cb: callback2, delay: 300 });

    act(() => {
      vi.advanceTimersByTime(200);
    });

    // Should call the new callback
    expect(callback1).not.toHaveBeenCalled();
    expect(callback2).toHaveBeenCalledWith('test');
  });

  it('should cleanup timeout on unmount', () => {
    const callback = vi.fn();
    const { result, unmount } = renderHook(() => useDebouncedCallback(callback, 300));

    act(() => {
      result.current();
    });

    unmount();

    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Callback should not be called after unmount
    expect(callback).not.toHaveBeenCalled();
  });

  it('should handle multiple rapid calls correctly', () => {
    const callback = vi.fn();
    const { result } = renderHook(() => useDebouncedCallback(callback, 300));

    // Simulate rapid typing
    act(() => {
      result.current('a');
    });
    act(() => {
      vi.advanceTimersByTime(50);
    });

    act(() => {
      result.current('ab');
    });
    act(() => {
      vi.advanceTimersByTime(50);
    });

    act(() => {
      result.current('abc');
    });
    act(() => {
      vi.advanceTimersByTime(50);
    });

    act(() => {
      result.current('abcd');
    });

    // Wait for debounce
    act(() => {
      vi.advanceTimersByTime(300);
    });

    // Should only call once with final value
    expect(callback).toHaveBeenCalledTimes(1);
    expect(callback).toHaveBeenCalledWith('abcd');
  });

  it('should work with async callbacks', async () => {
    const asyncCallback = vi.fn(async (value: string) => {
      return `processed: ${value}`;
    });

    const { result } = renderHook(() => useDebouncedCallback(asyncCallback, 300));

    act(() => {
      result.current('test');
    });

    act(() => {
      vi.advanceTimersByTime(300);
    });

    expect(asyncCallback).toHaveBeenCalledWith('test');
  });
});

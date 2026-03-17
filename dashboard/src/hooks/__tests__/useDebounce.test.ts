/**
 * Tests for useDebounce hook
 */

import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useDebounce } from '../useDebounce';

describe('useDebounce', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should return initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 300));
    expect(result.current).toBe('initial');
  });

  it('should debounce value changes', async () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 300 } }
    );

    expect(result.current).toBe('initial');

    // Change value
    rerender({ value: 'updated', delay: 300 });
    expect(result.current).toBe('initial'); // Still old value

    // Advance time by 299ms (not enough)
    act(() => {
      vi.advanceTimersByTime(299);
    });
    expect(result.current).toBe('initial');

    // Advance time by 1ms more (total 300ms)
    await act(async () => {
      vi.advanceTimersByTime(1);
      await vi.runAllTimersAsync();
    });
    
    expect(result.current).toBe('updated');
  });

  it('should reset debounce timer on rapid changes', async () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: 'initial' } }
    );

    // First change
    rerender({ value: 'change1' });
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Second change (resets timer)
    rerender({ value: 'change2' });
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Third change (resets timer)
    rerender({ value: 'change3' });
    act(() => {
      vi.advanceTimersByTime(100);
    });

    // Still showing initial value
    expect(result.current).toBe('initial');

    // Wait for full delay from last change
    await act(async () => {
      vi.advanceTimersByTime(200);
      await vi.runAllTimersAsync();
    });
    
    expect(result.current).toBe('change3');
  });

  it('should handle different delay values', async () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      { initialProps: { value: 'initial', delay: 500 } }
    );

    rerender({ value: 'updated', delay: 500 });
    
    act(() => {
      vi.advanceTimersByTime(499);
    });
    expect(result.current).toBe('initial');

    await act(async () => {
      vi.advanceTimersByTime(1);
      await vi.runAllTimersAsync();
    });
    
    expect(result.current).toBe('updated');
  });

  it('should work with different data types', async () => {
    // Number
    const { result: numberResult, rerender: numberRerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: 0 } }
    );

    numberRerender({ value: 42 });
    await act(async () => {
      vi.advanceTimersByTime(300);
      await vi.runAllTimersAsync();
    });
    expect(numberResult.current).toBe(42);

    // Object
    const { result: objectResult, rerender: objectRerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: { key: 'initial' } } }
    );

    const newObj = { key: 'updated' };
    objectRerender({ value: newObj });
    await act(async () => {
      vi.advanceTimersByTime(300);
      await vi.runAllTimersAsync();
    });
    expect(objectResult.current).toEqual(newObj);

    // Array
    const { result: arrayResult, rerender: arrayRerender } = renderHook(
      ({ value }) => useDebounce(value, 300),
      { initialProps: { value: [1, 2, 3] } }
    );

    const newArray = [4, 5, 6];
    arrayRerender({ value: newArray });
    await act(async () => {
      vi.advanceTimersByTime(300);
      await vi.runAllTimersAsync();
    });
    expect(arrayResult.current).toEqual(newArray);
  });

  it('should use default delay of 300ms when not specified', async () => {
    const { result, rerender } = renderHook(
      ({ value }) => useDebounce(value),
      { initialProps: { value: 'initial' } }
    );

    rerender({ value: 'updated' });
    
    act(() => {
      vi.advanceTimersByTime(299);
    });
    expect(result.current).toBe('initial');

    await act(async () => {
      vi.advanceTimersByTime(1);
      await vi.runAllTimersAsync();
    });
    
    expect(result.current).toBe('updated');
  });

  it('should cleanup timeout on unmount', () => {
    const { unmount } = renderHook(() => useDebounce('value', 300));
    
    // Should not throw error
    expect(() => unmount()).not.toThrow();
  });
});

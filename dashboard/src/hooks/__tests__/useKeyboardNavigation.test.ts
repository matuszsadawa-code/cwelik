/**
 * useKeyboardNavigation Hook Tests
 * 
 * Tests keyboard navigation utility hooks.
 * Validates: Requirements 30.2
 */

import { describe, it, expect, vi } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useKeyboardNavigation, useFocusTrap, useArrowNavigation } from '../useKeyboardNavigation';

describe('useKeyboardNavigation', () => {
  it('calls onActivate when Enter key is pressed', () => {
    const onActivate = vi.fn();
    const { result } = renderHook(() => useKeyboardNavigation({ onActivate }));

    const event = {
      key: 'Enter',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event);

    expect(onActivate).toHaveBeenCalledTimes(1);
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it('calls onActivate when Space key is pressed', () => {
    const onActivate = vi.fn();
    const { result } = renderHook(() => useKeyboardNavigation({ onActivate }));

    const event = {
      key: ' ',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event);

    expect(onActivate).toHaveBeenCalledTimes(1);
    expect(event.preventDefault).toHaveBeenCalled();
  });

  it('calls onEscape when Escape key is pressed', () => {
    const onEscape = vi.fn();
    const { result } = renderHook(() => useKeyboardNavigation({ onEscape }));

    const event = {
      key: 'Escape',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event);

    expect(onEscape).toHaveBeenCalledTimes(1);
    expect(event.preventDefault).toHaveBeenCalled();
  });


  it('does not call handlers when disabled', () => {
    const onActivate = vi.fn();
    const onEscape = vi.fn();
    const { result } = renderHook(() => 
      useKeyboardNavigation({ onActivate, onEscape, disabled: true })
    );

    const enterEvent = {
      key: 'Enter',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    const escapeEvent = {
      key: 'Escape',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(enterEvent);
    result.current.handleKeyDown(escapeEvent);

    expect(onActivate).not.toHaveBeenCalled();
    expect(onEscape).not.toHaveBeenCalled();
  });
});

describe('useArrowNavigation', () => {
  it('handles ArrowDown key correctly', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => useArrowNavigation(5, onSelect));

    const event = {
      key: 'ArrowDown',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event, 0);

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalledWith(1);
  });

  it('handles ArrowUp key correctly', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => useArrowNavigation(5, onSelect));

    const event = {
      key: 'ArrowUp',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event, 2);

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalledWith(1);
  });

  it('handles Home key correctly', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => useArrowNavigation(5, onSelect));

    const event = {
      key: 'Home',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event, 3);

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalledWith(0);
  });

  it('handles End key correctly', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => useArrowNavigation(5, onSelect));

    const event = {
      key: 'End',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event, 0);

    expect(event.preventDefault).toHaveBeenCalled();
    expect(onSelect).toHaveBeenCalledWith(4);
  });

  it('does not go below 0 index', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => useArrowNavigation(5, onSelect));

    const event = {
      key: 'ArrowUp',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event, 0);

    // Should not call onSelect when already at index 0
    expect(onSelect).not.toHaveBeenCalled();
  });

  it('does not go above max index', () => {
    const onSelect = vi.fn();
    const { result } = renderHook(() => useArrowNavigation(5, onSelect));

    const event = {
      key: 'ArrowDown',
      preventDefault: vi.fn(),
    } as unknown as React.KeyboardEvent;

    result.current.handleKeyDown(event, 4);

    // Should not call onSelect when already at max index
    expect(onSelect).not.toHaveBeenCalled();
  });
});

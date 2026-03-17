/**
 * useKeyboardNavigation Hook
 * 
 * Provides keyboard navigation utilities for interactive elements.
 * Handles Enter and Space key presses for button-like elements.
 * 
 * Validates: Requirements 30.2
 */

import { useCallback } from 'react';

interface UseKeyboardNavigationOptions {
  onActivate?: () => void;
  onEscape?: () => void;
  disabled?: boolean;
}

export function useKeyboardNavigation(options: UseKeyboardNavigationOptions = {}) {
  const { onActivate, onEscape, disabled = false } = options;

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (disabled) return;

      // Handle Enter and Space for activation
      if ((event.key === 'Enter' || event.key === ' ') && onActivate) {
        event.preventDefault();
        onActivate();
      }

      // Handle Escape key
      if (event.key === 'Escape' && onEscape) {
        event.preventDefault();
        onEscape();
      }
    },
    [onActivate, onEscape, disabled]
  );

  return { handleKeyDown };
}

/**
 * Hook for managing focus trap within a modal or dialog
 */
export function useFocusTrap(isActive: boolean) {
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLElement>) => {
      if (!isActive) return;

      if (event.key === 'Tab') {
        const focusableElements = event.currentTarget.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];

        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          lastElement?.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
          event.preventDefault();
          firstElement?.focus();
        }
      }
    },
    [isActive]
  );

  return { handleKeyDown };
}

/**
 * Hook for arrow key navigation in lists
 */
export function useArrowNavigation(itemCount: number, onSelect?: (index: number) => void) {
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent, currentIndex: number) => {
      let newIndex = currentIndex;

      switch (event.key) {
        case 'ArrowDown':
          event.preventDefault();
          newIndex = Math.min(currentIndex + 1, itemCount - 1);
          break;
        case 'ArrowUp':
          event.preventDefault();
          newIndex = Math.max(currentIndex - 1, 0);
          break;
        case 'Home':
          event.preventDefault();
          newIndex = 0;
          break;
        case 'End':
          event.preventDefault();
          newIndex = itemCount - 1;
          break;
        case 'Enter':
        case ' ':
          event.preventDefault();
          if (onSelect) {
            onSelect(currentIndex);
          }
          return;
        default:
          return;
      }

      if (newIndex !== currentIndex && onSelect) {
        onSelect(newIndex);
      }
    },
    [itemCount, onSelect]
  );

  return { handleKeyDown };
}

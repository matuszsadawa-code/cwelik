import { useEffect } from 'react';
import { useDashboardStore } from '../stores/dashboardStore';

/**
 * Hook to manage reduced motion preference
 * - Listens to system prefers-reduced-motion media query
 * - Applies/removes 'reduce-motion' class to document root
 * - Syncs with user's manual preference in settings
 */
export function useReducedMotion() {
  const prefersReducedMotion = useDashboardStore((state) => state.prefersReducedMotion);
  const setPrefersReducedMotion = useDashboardStore((state) => state.setPrefersReducedMotion);

  useEffect(() => {
    // Check if matchMedia is available
    if (typeof window === 'undefined' || !window.matchMedia) {
      return;
    }

    // Listen for system preference changes
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    
    const handleChange = (e: MediaQueryListEvent | MediaQueryList) => {
      // Only update if user hasn't manually set a preference
      const hasManualPreference = localStorage.getItem('prefersReducedMotion') !== null;
      if (!hasManualPreference) {
        setPrefersReducedMotion(e.matches);
      }
    };

    // Initial check
    handleChange(mediaQuery);

    // Listen for changes
    mediaQuery.addEventListener('change', handleChange);

    return () => {
      mediaQuery.removeEventListener('change', handleChange);
    };
  }, [setPrefersReducedMotion]);

  useEffect(() => {
    // Apply or remove the reduce-motion class on document root
    if (prefersReducedMotion) {
      document.documentElement.classList.add('reduce-motion');
    } else {
      document.documentElement.classList.remove('reduce-motion');
    }
  }, [prefersReducedMotion]);

  return prefersReducedMotion;
}

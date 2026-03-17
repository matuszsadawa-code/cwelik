import { useEffect } from 'react';
import { useDashboardStore } from '@stores/dashboardStore';
import type { Theme } from '@/types';

const THEME_STORAGE_KEY = 'openclaw-theme';

/**
 * Custom hook for managing theme state and persistence
 * Handles localStorage synchronization and DOM class updates
 */
export function useTheme() {
  const { theme, setTheme } = useDashboardStore();

  // Load theme from localStorage on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) as Theme | null;
    if (savedTheme && (savedTheme === 'dark' || savedTheme === 'light')) {
      setTheme(savedTheme);
      applyThemeToDOM(savedTheme);
    } else {
      // Default to dark mode (OLED optimized)
      setTheme('dark');
      applyThemeToDOM('dark');
      localStorage.setItem(THEME_STORAGE_KEY, 'dark');
    }
  }, [setTheme]);

  // Apply theme changes to DOM
  useEffect(() => {
    applyThemeToDOM(theme);
  }, [theme]);

  const toggleTheme = () => {
    const newTheme: Theme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem(THEME_STORAGE_KEY, newTheme);
    applyThemeToDOM(newTheme);
  };

  return {
    theme,
    setTheme: (newTheme: Theme) => {
      setTheme(newTheme);
      localStorage.setItem(THEME_STORAGE_KEY, newTheme);
      applyThemeToDOM(newTheme);
    },
    toggleTheme,
  };
}

/**
 * Apply theme to document element
 */
function applyThemeToDOM(theme: Theme) {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark');
  } else {
    document.documentElement.classList.remove('dark');
  }
}

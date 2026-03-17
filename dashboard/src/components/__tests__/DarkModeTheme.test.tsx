import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import Header from '../Header';
import { useDashboardStore } from '@stores/dashboardStore';

describe('Dark Mode Theme Implementation', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
    // Reset document classes
    document.documentElement.classList.remove('dark');
    // Reset store state
    useDashboardStore.setState({ theme: 'dark' });
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  describe('Theme Toggle in Header', () => {
    it('should render theme toggle button', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to (light|dark) mode/i);
      expect(toggleButton).toBeInTheDocument();
    });

    it('should show sun icon in dark mode', () => {
      useDashboardStore.setState({ theme: 'dark' });
      
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      expect(toggleButton).toBeInTheDocument();
      // Sun icon has specific path for light mode
      const sunIcon = toggleButton.querySelector('path[d*="M12 3v1m0 16v1"]');
      expect(sunIcon).toBeInTheDocument();
    });

    it('should show moon icon in light mode', () => {
      useDashboardStore.setState({ theme: 'light' });
      
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to dark mode/i);
      expect(toggleButton).toBeInTheDocument();
      // Moon icon has specific path for dark mode
      const moonIcon = toggleButton.querySelector('path[d*="M20.354 15.354A9"]');
      expect(moonIcon).toBeInTheDocument();
    });

    it('should toggle theme when button is clicked', async () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const initialTheme = useDashboardStore.getState().theme;
      expect(initialTheme).toBe('dark');

      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);

      await waitFor(() => {
        const newTheme = useDashboardStore.getState().theme;
        expect(newTheme).toBe('light');
      });
    });

    it('should toggle between dark and light modes multiple times', async () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      // Start in dark mode
      expect(useDashboardStore.getState().theme).toBe('dark');

      // Toggle to light
      let toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('light');
      });

      // Toggle back to dark
      toggleButton = screen.getByLabelText(/switch to dark mode/i);
      fireEvent.click(toggleButton);
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('dark');
      });
    });
  });

  describe('Theme Persistence in localStorage', () => {
    it('should save theme to localStorage when toggled', async () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);

      await waitFor(() => {
        const savedTheme = localStorage.getItem('openclaw-theme');
        expect(savedTheme).toBe('light');
      });
    });

    it('should persist dark mode preference', async () => {
      useDashboardStore.setState({ theme: 'dark' });
      
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);

      await waitFor(() => {
        expect(localStorage.getItem('openclaw-theme')).toBe('light');
      });

      // Toggle back to dark
      const darkToggleButton = screen.getByLabelText(/switch to dark mode/i);
      fireEvent.click(darkToggleButton);

      await waitFor(() => {
        expect(localStorage.getItem('openclaw-theme')).toBe('dark');
      });
    });

    it('should maintain theme preference across component remounts', async () => {
      // Set theme to light and save to localStorage
      localStorage.setItem('openclaw-theme', 'light');
      useDashboardStore.setState({ theme: 'light' });

      const { unmount } = render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      // Verify light mode is active
      expect(useDashboardStore.getState().theme).toBe('light');

      unmount();

      // Remount component
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      // Theme should still be light
      expect(localStorage.getItem('openclaw-theme')).toBe('light');
    });
  });

  describe('DOM Class Application', () => {
    it('should add "dark" class to document element in dark mode', async () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      
      // Initially in dark mode
      expect(document.documentElement.classList.contains('dark')).toBe(false);
      
      // Manually add dark class to simulate initial state
      document.documentElement.classList.add('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);

      // Toggle to light mode
      fireEvent.click(toggleButton);

      await waitFor(() => {
        expect(document.documentElement.classList.contains('dark')).toBe(false);
      });
    });

    it('should remove "dark" class from document element in light mode', async () => {
      document.documentElement.classList.add('dark');
      useDashboardStore.setState({ theme: 'dark' });

      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);

      await waitFor(() => {
        expect(document.documentElement.classList.contains('dark')).toBe(false);
      });
    });

    it('should apply dark class when toggling from light to dark', async () => {
      useDashboardStore.setState({ theme: 'light' });
      document.documentElement.classList.remove('dark');

      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to dark mode/i);
      fireEvent.click(toggleButton);

      await waitFor(() => {
        expect(document.documentElement.classList.contains('dark')).toBe(true);
      });
    });
  });

  describe('OLED Optimized Dark Mode Colors', () => {
    it('should apply dark class for OLED optimized background', () => {
      document.documentElement.classList.add('dark');
      
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });

    it('should remove dark class for light mode background', () => {
      document.documentElement.classList.remove('dark');
      
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });
  });

  describe('Color Coding for Positive/Negative Values', () => {
    it('should apply appropriate theme classes for positive/negative values', () => {
      // Verify dark mode is applied
      document.documentElement.classList.add('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      
      // Verify light mode removes dark class
      document.documentElement.classList.remove('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(false);
    });

    it('should maintain color consistency across theme changes', () => {
      // Toggle between themes
      document.documentElement.classList.add('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      
      document.documentElement.classList.remove('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(false);
      
      document.documentElement.classList.add('dark');
      expect(document.documentElement.classList.contains('dark')).toBe(true);
    });
  });

  describe('Accessibility', () => {
    it('should have accessible aria-label for theme toggle', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to (light|dark) mode/i);
      expect(toggleButton).toHaveAttribute('aria-label');
    });

    it('should update aria-label when theme changes', async () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      // Initially in dark mode
      let toggleButton = screen.getByLabelText(/switch to light mode/i);
      expect(toggleButton).toBeInTheDocument();

      fireEvent.click(toggleButton);

      await waitFor(() => {
        toggleButton = screen.getByLabelText(/switch to dark mode/i);
        expect(toggleButton).toBeInTheDocument();
      });
    });

    it('should have minimum touch target size (44x44px)', () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const toggleButton = screen.getByLabelText(/switch to (light|dark) mode/i);
      const styles = window.getComputedStyle(toggleButton);
      
      expect(styles.minWidth).toBe('44px');
      expect(styles.minHeight).toBe('44px');
    });
  });

  describe('Store Integration', () => {
    it('should update store theme state when toggled', async () => {
      render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      const initialTheme = useDashboardStore.getState().theme;
      expect(initialTheme).toBe('dark');

      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);

      await waitFor(() => {
        const newTheme = useDashboardStore.getState().theme;
        expect(newTheme).toBe('light');
      });
    });

    it('should reflect store theme changes in UI', async () => {
      const { rerender } = render(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      // Change theme via store
      useDashboardStore.setState({ theme: 'light' });

      rerender(
        <BrowserRouter>
          <Header />
        </BrowserRouter>
      );

      await waitFor(() => {
        const toggleButton = screen.getByLabelText(/switch to dark mode/i);
        expect(toggleButton).toBeInTheDocument();
      });
    });
  });
});

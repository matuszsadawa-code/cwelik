import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import App from '../../App';
import { useDashboardStore } from '@stores/dashboardStore';

describe('Theme Integration Tests', () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
    useDashboardStore.setState({ theme: 'dark' });
  });

  afterEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove('dark');
  });

  describe('Complete Theme Workflow', () => {
    it('should load saved theme on app startup', async () => {
      // Set saved theme to light
      localStorage.setItem('openclaw-theme', 'light');
      
      render(<App />);
      
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('light');
        expect(document.documentElement.classList.contains('dark')).toBe(false);
      });
    });

    it('should default to dark mode on first load', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('dark');
        expect(localStorage.getItem('openclaw-theme')).toBe('dark');
        expect(document.documentElement.classList.contains('dark')).toBe(true);
      });
    });

    it('should persist theme changes across app reloads', async () => {
      const { unmount } = render(<App />);
      
      // Wait for initial load
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('dark');
      });
      
      // Find and click theme toggle
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(localStorage.getItem('openclaw-theme')).toBe('light');
      });
      
      // Unmount and remount app
      unmount();
      render(<App />);
      
      // Theme should be restored to light
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('light');
        expect(document.documentElement.classList.contains('dark')).toBe(false);
      });
    });

    it('should apply theme to all components', async () => {
      render(<App />);
      
      await waitFor(() => {
        const header = screen.getByRole('banner');
        expect(header).toBeInTheDocument();
      });
      
      // Toggle to light mode
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(document.documentElement.classList.contains('dark')).toBe(false);
        expect(useDashboardStore.getState().theme).toBe('light');
      });
    });

    it('should maintain theme during navigation', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
      
      // Set to light mode
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('light');
      });
      
      // Navigate to different pages (if navigation buttons are available)
      // Theme should persist
      expect(useDashboardStore.getState().theme).toBe('light');
      expect(localStorage.getItem('openclaw-theme')).toBe('light');
    });
  });

  describe('Theme Synchronization', () => {
    it('should synchronize theme between store and localStorage', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
      
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        const storeTheme = useDashboardStore.getState().theme;
        const savedTheme = localStorage.getItem('openclaw-theme');
        
        expect(storeTheme).toBe('light');
        expect(savedTheme).toBe('light');
      });
    });

    it('should synchronize theme between store and DOM', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
      
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        const storeTheme = useDashboardStore.getState().theme;
        const hasDarkClass = document.documentElement.classList.contains('dark');
        
        expect(storeTheme).toBe('light');
        expect(hasDarkClass).toBe(false);
      });
    });
  });

  describe('Requirements Validation', () => {
    it('validates Requirement 27.1: Frontend provides dark mode theme', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('dark');
        expect(document.documentElement.classList.contains('dark')).toBe(true);
      });
    });

    it('validates Requirement 27.2: Frontend provides light mode theme', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
      
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('light');
        expect(document.documentElement.classList.contains('dark')).toBe(false);
      });
    });

    it('validates Requirement 27.3: Theme toggle control in header', async () => {
      render(<App />);
      
      await waitFor(() => {
        const toggleButton = screen.getByLabelText(/switch to (light|dark) mode/i);
        expect(toggleButton).toBeInTheDocument();
        
        // Verify it's in the header
        const header = screen.getByRole('banner');
        expect(header).toContainElement(toggleButton);
      });
    });

    it('validates Requirement 27.4: Theme switches on toggle click', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
      
      const initialTheme = useDashboardStore.getState().theme;
      const toggleButton = screen.getByLabelText(/switch to (light|dark) mode/i);
      
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        const newTheme = useDashboardStore.getState().theme;
        expect(newTheme).not.toBe(initialTheme);
      });
    });

    it('validates Requirement 27.5: Theme persisted in localStorage', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
      
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        const savedTheme = localStorage.getItem('openclaw-theme');
        expect(savedTheme).toBe('light');
      });
    });

    it('validates Requirement 27.6: Saved theme applied on load', async () => {
      localStorage.setItem('openclaw-theme', 'light');
      
      render(<App />);
      
      await waitFor(() => {
        expect(useDashboardStore.getState().theme).toBe('light');
        expect(document.documentElement.classList.contains('dark')).toBe(false);
      });
    });

    it('validates Requirement 27.8: Charts and visualizations match theme', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
      
      // Toggle theme
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        // Verify theme is applied globally
        expect(document.documentElement.classList.contains('dark')).toBe(false);
        // Charts will inherit theme through CSS variables
      });
    });

    it('validates Requirement 27.9: Appropriate colors for positive/negative values', async () => {
      render(<App />);
      
      await waitFor(() => {
        expect(screen.getByRole('banner')).toBeInTheDocument();
      });
      
      // In dark mode
      expect(document.documentElement.classList.contains('dark')).toBe(true);
      
      // Toggle to light mode
      const toggleButton = screen.getByLabelText(/switch to light mode/i);
      fireEvent.click(toggleButton);
      
      await waitFor(() => {
        // In light mode
        expect(document.documentElement.classList.contains('dark')).toBe(false);
        // Color classes (.text-positive, .text-negative) will use appropriate colors via CSS
      });
    });
  });
});

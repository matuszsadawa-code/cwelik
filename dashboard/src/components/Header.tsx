import { useDashboardStore } from '@stores/dashboardStore';

export default function Header() {
  const { wsConnected, theme, setTheme, toggleMobileMenu } = useDashboardStore();

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    
    // Persist theme preference to localStorage
    localStorage.setItem('openclaw-theme', newTheme);
    
    // Apply theme to document
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  return (
    <header
      id="header"
      tabIndex={-1}
      className="bg-background-secondary dark:bg-background-secondary border-b border-slate-200 dark:border-slate-700 sticky top-0 z-50 transition-colors duration-200"
      role="banner"
    >
      <div className="px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
        <div className="flex items-center gap-3 sm:gap-4">
          {/* Mobile Menu Button */}
          <button
            onClick={toggleMobileMenu}
            className="md:hidden p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 transition-colors touch-manipulation"
            aria-label="Toggle menu"
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          <h1 className="text-xl sm:text-2xl font-bold font-mono">OpenClaw</h1>
          <span className="text-xs sm:text-sm text-text-muted">v3.0</span>
        </div>

        <div className="flex items-center gap-3 sm:gap-6">
          {/* Connection Status */}
          <div 
            className="flex items-center gap-2"
            role="status"
            aria-live="assertive"
            aria-atomic="true"
          >
            <div
              className={`w-2 h-2 rounded-full ${
                wsConnected ? 'bg-cta animate-pulse' : 'bg-error'
              }`}
              aria-hidden="true"
            />
            <span className="hidden sm:inline text-sm text-text-secondary">
              {wsConnected ? 'Connected' : 'Disconnected'}
            </span>
            <span className="sr-only">
              WebSocket connection status: {wsConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-white/5 transition-colors touch-manipulation"
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
            style={{ minWidth: '44px', minHeight: '44px' }}
          >
            {theme === 'dark' ? (
              // Sun icon for light mode
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                />
              </svg>
            ) : (
              // Moon icon for dark mode
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                />
              </svg>
            )}
          </button>
        </div>
      </div>
    </header>
  );
}

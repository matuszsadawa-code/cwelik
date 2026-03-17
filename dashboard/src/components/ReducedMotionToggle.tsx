import { useDashboardStore } from '../stores/dashboardStore';

/**
 * ReducedMotionToggle Component
 * 
 * Provides a toggle switch to enable/disable animations for users with motion sensitivity.
 * This setting overrides the system preference and is persisted in localStorage.
 * 
 * Accessibility:
 * - WCAG 2.1 AA compliant (Requirement 30.8)
 * - Keyboard accessible with visible focus indicators
 * - ARIA labels for screen readers
 * - Clear visual state indication
 */
export function ReducedMotionToggle() {
  const prefersReducedMotion = useDashboardStore((state) => state.prefersReducedMotion);
  const toggleReducedMotion = useDashboardStore((state) => state.toggleReducedMotion);

  return (
    <div className="flex items-center justify-between p-4 bg-background-secondary rounded-lg border border-glass">
      <div className="flex-1">
        <label htmlFor="reduced-motion-toggle" className="block text-sm font-medium text-text-primary mb-1">
          Reduce Motion
        </label>
        <p className="text-xs text-text-muted">
          Disable animations and transitions for reduced motion sensitivity
        </p>
      </div>
      
      <button
        id="reduced-motion-toggle"
        role="switch"
        aria-checked={prefersReducedMotion}
        aria-label={prefersReducedMotion ? 'Disable reduced motion' : 'Enable reduced motion'}
        onClick={toggleReducedMotion}
        className={`
          relative inline-flex h-6 w-11 items-center rounded-full
          transition-colors focus-visible:outline focus-visible:outline-3 focus-visible:outline-offset-2
          ${prefersReducedMotion ? 'bg-cta' : 'bg-gray-600'}
        `}
      >
        <span className="sr-only">
          {prefersReducedMotion ? 'Disable reduced motion' : 'Enable reduced motion'}
        </span>
        <span
          className={`
            inline-block h-4 w-4 transform rounded-full bg-white transition-transform
            ${prefersReducedMotion ? 'translate-x-6' : 'translate-x-1'}
          `}
        />
      </button>
    </div>
  );
}

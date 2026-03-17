import { ReducedMotionToggle } from '../components/ReducedMotionToggle';

/**
 * Configuration Page
 * 
 * Provides interface for managing:
 * - Feature flags (20 advanced trading features)
 * - Strategy parameters
 * - Risk management settings
 * - Symbol selection
 * - Timeframe configuration
 * - Configuration profiles
 * - Accessibility settings
 */
export default function Configuration() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold mb-2">Configuration</h2>
        <p className="text-text-secondary">
          Manage trading system settings and parameters
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-glass border-glass rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">Feature Flags</h3>
          <p className="text-text-muted">Coming soon...</p>
        </div>

        <div className="bg-glass border-glass rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">Strategy Parameters</h3>
          <p className="text-text-muted">Coming soon...</p>
        </div>

        <div className="bg-glass border-glass rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">Risk Settings</h3>
          <p className="text-text-muted">Coming soon...</p>
        </div>

        <div className="bg-glass border-glass rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-4">Symbol Selection</h3>
          <p className="text-text-muted">Coming soon...</p>
        </div>
      </div>

      {/* Accessibility Settings Section */}
      <div className="bg-glass border-glass rounded-lg p-6">
        <h3 className="text-xl font-semibold mb-4">Accessibility Settings</h3>
        <p className="text-text-secondary mb-6">
          Configure accessibility preferences for improved usability
        </p>
        <div className="space-y-4">
          <ReducedMotionToggle />
        </div>
      </div>
    </div>
  );
}

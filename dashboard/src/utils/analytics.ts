/**
 * Analytics utility — Plausible Analytics wrapper
 * GDPR compliant: no cookies, no fingerprinting, no PII
 * Only fires when VITE_ENABLE_ANALYTICS === 'true'
 */

const isEnabled = import.meta.env.VITE_ENABLE_ANALYTICS === 'true'

// Extend window type for Plausible
declare global {
  interface Window {
    plausible?: (
      event: string,
      options?: { props?: Record<string, string | number>; u?: string }
    ) => void
  }
}

/**
 * Track a page view. Pass the current URL path.
 */
export function trackPageView(url: string): void {
  if (!isEnabled) return

  if (typeof window !== 'undefined' && typeof window.plausible === 'function') {
    window.plausible('pageview', { u: url })
  } else {
    console.debug('[Analytics] pageview', url)
  }
}

/**
 * Track a custom event with optional properties.
 */
export function trackEvent(name: string, props?: Record<string, string | number>): void {
  if (!isEnabled) return

  if (typeof window !== 'undefined' && typeof window.plausible === 'function') {
    window.plausible(name, props ? { props } : undefined)
  } else {
    console.debug('[Analytics] event', name, props)
  }
}

/**
 * Hook that exposes trackEvent and trackPageView.
 */
export function useAnalytics() {
  return { trackEvent, trackPageView }
}

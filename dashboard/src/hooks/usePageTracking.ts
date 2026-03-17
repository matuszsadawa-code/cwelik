import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { trackPageView } from '../utils/analytics'

/**
 * Tracks page views on every route change.
 * Must be used inside a component that is a child of BrowserRouter.
 */
export function usePageTracking(): void {
  const location = useLocation()

  useEffect(() => {
    trackPageView(location.pathname + location.search)
  }, [location])
}

import { useEffect, lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import './index.css'
import Layout from './components/Layout'
import LoadingFallback from './components/LoadingFallback'
import ErrorBoundary from './components/ErrorBoundary'
import { useDashboardStore } from './stores/dashboardStore'
import { useReducedMotion } from './hooks/useReducedMotion'
import { usePageTracking } from './hooks/usePageTracking'
import { initPerformanceTracking } from './utils/performanceMetrics'
import { PerformanceMonitor } from './components/PerformanceMonitor'

// Lazy load page components for route-based code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Configuration = lazy(() => import('./pages/Configuration'))
const TradeJournal = lazy(() => import('./pages/TradeJournal'))
const SystemHealth = lazy(() => import('./pages/SystemHealth'))

const analyticsEnabled = import.meta.env.VITE_ENABLE_ANALYTICS === 'true'
const plausibleDomain = import.meta.env.VITE_PLAUSIBLE_DOMAIN as string | undefined

/** Inner component — must live inside BrowserRouter so useLocation works */
function AppRoutes() {
  usePageTracking()

  const { theme, setTheme } = useDashboardStore()

  useEffect(() => {
    const savedTheme = localStorage.getItem('openclaw-theme') as 'dark' | 'light' | null
    if (savedTheme) {
      setTheme(savedTheme)
      if (savedTheme === 'dark') {
        document.documentElement.classList.add('dark')
      } else {
        document.documentElement.classList.remove('dark')
      }
    } else {
      document.documentElement.classList.add('dark')
      localStorage.setItem('openclaw-theme', 'dark')
    }
  }, [setTheme])

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [theme])

  return (
    <Layout>
      <Suspense fallback={<LoadingFallback />}>
        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route
            path="/dashboard"
            element={
              <ErrorBoundary section="Dashboard">
                <Dashboard />
              </ErrorBoundary>
            }
          />
          <Route
            path="/analytics"
            element={
              <ErrorBoundary section="Analytics">
                <Analytics />
              </ErrorBoundary>
            }
          />
          <Route
            path="/configuration"
            element={
              <ErrorBoundary section="Configuration">
                <Configuration />
              </ErrorBoundary>
            }
          />
          <Route
            path="/journal"
            element={
              <ErrorBoundary section="Trade Journal">
                <TradeJournal />
              </ErrorBoundary>
            }
          />
          <Route
            path="/health"
            element={
              <ErrorBoundary section="System Health">
                <SystemHealth />
              </ErrorBoundary>
            }
          />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Suspense>
    </Layout>
  )
}

function App() {
  // Initialize reduced motion support
  useReducedMotion()

  // Initialize performance tracking
  useEffect(() => {
    initPerformanceTracking()
  }, [])

  // Inject Plausible analytics script when enabled and domain is configured
  useEffect(() => {
    if (!analyticsEnabled || !plausibleDomain) return

    const existing = document.querySelector('script[data-domain]')
    if (existing) return

    const script = document.createElement('script')
    script.defer = true
    script.setAttribute('data-domain', plausibleDomain)
    script.src = 'https://plausible.io/js/script.js'
    document.head.appendChild(script)
  }, [])

  return (
    // Top-level error boundary — last resort catch-all for the entire app
    <ErrorBoundary section="Application">
      <BrowserRouter>
        <AppRoutes />
        <PerformanceMonitor />
      </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App

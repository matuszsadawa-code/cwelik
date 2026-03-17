import { Component, type ReactNode, type ErrorInfo } from 'react'

interface ErrorBoundaryProps {
  children: ReactNode
  /** Custom fallback UI to render instead of the default error card */
  fallback?: ReactNode
  /** Callback invoked when an error is caught */
  onError?: (error: Error, errorInfo: ErrorInfo) => void
  /** Section name for context in error messages */
  section?: string
}

interface ErrorBoundaryState {
  hasError: boolean
  error: Error | null
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    const { onError, section } = this.props

    // Call user-provided callback
    if (onError) {
      onError(error, errorInfo)
    }

    // Log to console in development
    if (import.meta.env.DEV) {
      console.error(
        `[ErrorBoundary]${section ? ` [${section}]` : ''} Caught error:`,
        error,
        errorInfo
      )
    }

    // Send to Sentry-style tracker if available
    if (typeof window !== 'undefined' && (window as Window & { __errorTracker?: { captureException: (err: Error, ctx?: object) => void } }).__errorTracker) {
      ;(window as Window & { __errorTracker?: { captureException: (err: Error, ctx?: object) => void } }).__errorTracker!.captureException(error, {
        componentStack: errorInfo.componentStack,
        section,
      })
    }
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null })
  }

  handleReload = (): void => {
    window.location.reload()
  }

  render(): ReactNode {
    const { hasError, error } = this.state
    const { children, fallback, section } = this.props

    if (!hasError) {
      return children
    }

    // Use custom fallback if provided
    if (fallback) {
      return fallback
    }

    return (
      <div
        role="alert"
        aria-live="assertive"
        className="flex items-center justify-center min-h-[200px] p-6"
      >
        <div className="bg-primary border border-red-500/30 rounded-xl p-6 max-w-md w-full shadow-lg">
          {/* Error icon */}
          <div className="flex items-center gap-3 mb-4">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center">
              <svg
                className="w-5 h-5 text-red-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth={2}
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
                />
              </svg>
            </div>
            <div>
              <h2 className="text-base font-semibold text-white">Something went wrong</h2>
              {section && (
                <p className="text-xs text-slate-400 mt-0.5">{section}</p>
              )}
            </div>
          </div>

          {/* Error message — dev only */}
          {import.meta.env.DEV && error && (
            <div className="mb-4 p-3 bg-background rounded-lg border border-slate-700">
              <p className="text-xs font-mono text-red-400 break-all">{error.message}</p>
            </div>
          )}

          {/* Action buttons */}
          <div className="flex gap-3">
            <button
              onClick={this.handleReset}
              className="flex-1 px-4 py-2 text-sm font-medium rounded-lg bg-accent text-black hover:bg-accent/90 transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 focus:ring-offset-primary"
            >
              Try again
            </button>
            <button
              onClick={this.handleReload}
              className="flex-1 px-4 py-2 text-sm font-medium rounded-lg bg-slate-700 text-slate-200 hover:bg-slate-600 transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-500 focus:ring-offset-2 focus:ring-offset-primary"
            >
              Reload page
            </button>
          </div>
        </div>
      </div>
    )
  }
}

export default ErrorBoundary
export type { ErrorBoundaryProps }

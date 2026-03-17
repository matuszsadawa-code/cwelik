import type { ComponentType, FC } from 'react'
import ErrorBoundary, { type ErrorBoundaryProps } from './ErrorBoundary'

/**
 * Higher-order component that wraps a component with an ErrorBoundary.
 *
 * @example
 * const SafeChart = withErrorBoundary(Chart, { section: 'Equity Curve' })
 */
export function withErrorBoundary<P extends object>(
  WrappedComponent: ComponentType<P>,
  boundaryProps?: Omit<ErrorBoundaryProps, 'children'>
): FC<P> {
  const displayName = WrappedComponent.displayName ?? WrappedComponent.name ?? 'Component'

  const WithErrorBoundary: FC<P> = (props) => (
    <ErrorBoundary {...boundaryProps}>
      <WrappedComponent {...props} />
    </ErrorBoundary>
  )

  WithErrorBoundary.displayName = `withErrorBoundary(${displayName})`
  return WithErrorBoundary
}

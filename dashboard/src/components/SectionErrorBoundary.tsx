import type { ReactNode } from 'react'
import ErrorBoundary from './ErrorBoundary'

interface SectionErrorBoundaryProps {
  children: ReactNode
  /** Label identifying the section (shown in the compact error card) */
  section: string
}

/**
 * A compact, section-level error boundary.
 * Less intrusive than a full-page error — renders a small inline error card
 * so the rest of the dashboard remains usable.
 */
export default function SectionErrorBoundary({ children, section }: SectionErrorBoundaryProps) {
  return (
    <ErrorBoundary
      section={section}
      fallback={<SectionErrorFallback section={section} />}
    >
      {children}
    </ErrorBoundary>
  )
}

function SectionErrorFallback({ section }: { section: string }) {
  const handleReload = () => window.location.reload()

  return (
    <div
      role="alert"
      aria-live="polite"
      className="flex items-center gap-3 p-3 rounded-lg bg-primary border border-red-500/20 text-sm"
    >
      <div className="flex-shrink-0 w-7 h-7 rounded-full bg-red-500/10 flex items-center justify-center">
        <svg
          className="w-4 h-4 text-red-400"
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
      <div className="flex-1 min-w-0">
        <span className="text-slate-300 font-medium">{section}</span>
        <span className="text-slate-500 ml-1">failed to load.</span>
      </div>
      <button
        onClick={handleReload}
        className="flex-shrink-0 px-3 py-1 text-xs font-medium rounded-md bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors duration-200 cursor-pointer focus:outline-none focus:ring-2 focus:ring-slate-500"
      >
        Reload
      </button>
    </div>
  )
}

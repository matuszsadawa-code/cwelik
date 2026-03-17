/**
 * Loading Fallback Component
 * 
 * Displays a loading indicator while lazy-loaded components are being fetched.
 * Used with React.Suspense boundaries for code splitting.
 */
export default function LoadingFallback() {
  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-cta"></div>
        <p className="mt-4 text-text-secondary">Loading...</p>
      </div>
    </div>
  );
}

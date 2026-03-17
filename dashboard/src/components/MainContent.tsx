import type { ReactNode } from 'react';

interface MainContentProps {
  children: ReactNode;
}

export default function MainContent({ children }: MainContentProps) {
  return (
    <main
      id="main-content"
      tabIndex={-1}
      className="flex-1 overflow-auto bg-background dark:bg-background transition-colors duration-200"
    >
      <div className="p-6">
        {children}
      </div>
    </main>
  );
}

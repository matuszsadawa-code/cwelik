import type { ReactNode } from 'react';
import Header from './Header';
import Sidebar from './Sidebar';
import MainContent from './MainContent';
import SkipNavigation from './SkipNavigation';

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  return (
    <>
      <SkipNavigation />
      <div className="min-h-screen flex flex-col bg-background dark:bg-background text-text-primary dark:text-text-primary transition-colors duration-200">
        <Header />
        <div className="flex flex-1 overflow-hidden">
          <Sidebar />
          <MainContent>{children}</MainContent>
        </div>
      </div>
    </>
  );
}

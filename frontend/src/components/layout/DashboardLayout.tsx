import { useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { TopBar } from './TopBar';

export function DashboardLayout() {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-bg-base text-text-primary antialiased font-sans relative">
      {/* Desktop Persistent Sidebar (256px wide, sticky, calm dark surface) */}
      <Sidebar className="hidden md:flex shrink-0 sticky top-0 h-screen" />

      {/* Main Workspace Area */}
      <div className="flex flex-col flex-1 min-w-0 min-h-screen">
        {/* Simplified Header */}
        <TopBar onMenuClick={() => setIsMobileMenuOpen(true)} />

        {/* Clean Page View */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto pb-16">
          <div key={location.pathname} className="animate-page-enter">
            <Outlet />
          </div>
        </main>
      </div>

      {/* Mobile Drawer */}
      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm"
            onClick={() => setIsMobileMenuOpen(false)}
          />
          <div className="relative z-10 w-64 bg-surface h-full shadow-2xl">
            <Sidebar onItemClick={() => setIsMobileMenuOpen(false)} />
          </div>
        </div>
      )}
    </div>
  );
}

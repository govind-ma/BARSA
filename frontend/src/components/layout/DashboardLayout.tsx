import { Outlet, useLocation } from 'react-router-dom';
import { IconRail } from './IconRail';
import { TopBar } from './TopBar';
import { ProjectOnboarding } from '@/components/projects/ProjectOnboarding';
import { useApp } from '@/app/AppContext';

export function DashboardLayout() {
  const { activeProject, projects } = useApp();
  const location = useLocation();

  // If no project is selected and user is on home screen, show clean onboarding state
  const isNoProjectSelected = !activeProject && (location.pathname === '/' || location.pathname.startsWith('/projects'));

  return (
    <div className="flex min-h-screen bg-bg-base bg-ice-facets text-text-primary antialiased selection:bg-lava-orange/20 selection:text-lava-orange font-sans relative">
      {/* Desktop 64px Icon Rail (Expands to 220px on hover) & Mobile Bottom Tab */}
      <IconRail />

      {/* Main Content Area */}
      <div className="flex flex-col flex-1 w-full md:pl-16 min-h-screen transition-all duration-300">
        {/* Top 56px Frosted Glass Bar */}
        <TopBar />

        {/* Page View with upward slide transition */}
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto pb-20 md:pb-8">
          {isNoProjectSelected && projects.length > 0 ? (
            <ProjectOnboarding />
          ) : (
            <div key={location.pathname} className="animate-page-enter">
              <Outlet />
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

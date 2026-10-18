import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AppProvider } from './AppContext';
import { DashboardLayout } from '@/components/layout/DashboardLayout';
import { DashboardHome } from '@/features/dashboard/DashboardHome';
import { WorkspacesPage } from '@/features/workspaces/WorkspacesPage';
import { ProjectsPage } from '@/features/projects/ProjectsPage';
import { ProjectDetailPage } from '@/features/projects/ProjectDetailPage';
import { MemoryExplorerPage } from '@/features/memory/MemoryExplorerPage';
import { VersionControlPage } from '@/features/versioning/VersionControlPage';
import { GraphExplorerPage } from '@/features/graph/GraphExplorerPage';
import { AgentsPage } from '@/features/agents/AgentsPage';
import { TasksPage } from '@/features/coordination/TasksPage';
import { SecurityPage } from '@/features/security/SecurityPage';
import { StoragePage } from '@/features/storage/StoragePage';
import { SettingsPage } from '@/features/settings/SettingsPage';
import { CheckpointsPage } from '@/features/checkpoints/CheckpointsPage';
import { StyleGuidePage } from '@/features/styleguide/StyleGuidePage';
import { ErrorBoundary } from '@/components/ui/ErrorBoundary';
import { NotFoundPage } from '@/features/notfound/NotFoundPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

export function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <AppProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/" element={<DashboardLayout />}>
                <Route index element={<DashboardHome />} />
                <Route path="workspaces" element={<WorkspacesPage />} />
                <Route path="projects" element={<ProjectsPage />} />
                <Route path="projects/:projectId" element={<ProjectDetailPage />} />
                <Route path="projects/:projectId/resume" element={<ProjectDetailPage />} />
                <Route path="memory" element={<MemoryExplorerPage />} />
                <Route path="version-control" element={<VersionControlPage />} />
                <Route path="checkpoints" element={<CheckpointsPage />} />
                <Route path="graph" element={<GraphExplorerPage />} />
                <Route path="agents" element={<AgentsPage />} />
                <Route path="tasks" element={<TasksPage />} />
                <Route path="security" element={<SecurityPage />} />
                <Route path="storage" element={<StoragePage />} />
                <Route path="settings" element={<SettingsPage />} />
                <Route path="styleguide" element={<StyleGuidePage />} />
                <Route path="*" element={<NotFoundPage />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AppProvider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;

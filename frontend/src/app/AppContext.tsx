import React, { createContext, useContext, useEffect, useState } from 'react';
import { api } from '@/lib/api';
import type { AuthenticatedPrincipal, Project, SystemInfo, Workspace } from '@/types';

interface AppContextType {
  workspaces: Workspace[];
  projects: Project[];
  activeWorkspace: Workspace | null;
  activeProject: Project | null;
  setActiveWorkspaceId: (id: string | null) => void;
  setActiveProjectId: (id: string | null) => void;
  principal: AuthenticatedPrincipal | null;
  systemInfo: SystemInfo | null;
  isBackendOnline: boolean;
  theme: 'dark' | 'light';
  toggleTheme: () => void;
  refreshWorkspaces: () => Promise<void>;
  refreshProjects: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const [principal, setPrincipal] = useState<AuthenticatedPrincipal | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);
  const [theme, setTheme] = useState<'dark' | 'light'>('dark');

  // Load theme preference
  useEffect(() => {
    const saved = localStorage.getItem('barsa_theme') as 'dark' | 'light' | null;
    if (saved) {
      setTheme(saved);
      document.documentElement.className = saved;
    } else {
      document.documentElement.className = 'dark';
    }
  }, []);

  const toggleTheme = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    localStorage.setItem('barsa_theme', next);
    document.documentElement.className = next;
  };

  const refreshWorkspaces = async () => {
    try {
      const list = await api.listWorkspaces();
      setWorkspaces(list);
      setIsBackendOnline(true);
      if (list.length > 0 && !activeWorkspaceId) {
        const firstId = list[0].workspace_id || (list[0] as any).id;
        if (firstId) setActiveWorkspaceId(firstId);
      }
    } catch {
      setIsBackendOnline(false);
    }
  };

  const refreshProjects = async () => {
    if (!activeWorkspaceId || activeWorkspaceId === 'undefined') {
      setProjects([]);
      return;
    }
    try {
      const list = await api.listProjects(activeWorkspaceId);
      setProjects(list);
      if (list.length > 0 && (!activeProjectId || !list.some((p) => (p.project_id || (p as any).id) === activeProjectId))) {
        const firstProjId = list[0].project_id || (list[0] as any).id;
        if (firstProjId) setActiveProjectId(firstProjId);
      } else if (list.length === 0) {
        setActiveProjectId(null);
      }
    } catch {
      setProjects([]);
    }
  };

  // Initial load
  useEffect(() => {
    const init = async () => {
      try {
        const info = await api.getInfo();
        setSystemInfo(info);
        setIsBackendOnline(true);
      } catch {
        setIsBackendOnline(false);
      }

      try {
        const user = await api.getCurrentPrincipal();
        setPrincipal(user);
      } catch {
        // Not authenticated or fallback
      }

      await refreshWorkspaces();
    };

    init();
  }, []);

  useEffect(() => {
    refreshProjects();
  }, [activeWorkspaceId]);

  const activeWorkspace = workspaces.find((w) => (w.workspace_id || (w as any).id) === activeWorkspaceId) || null;
  const activeProject = projects.find((p) => (p.project_id || (p as any).id) === activeProjectId) || null;

  return (
    <AppContext.Provider
      value={{
        workspaces,
        projects,
        activeWorkspace,
        activeProject,
        setActiveWorkspaceId,
        setActiveProjectId,
        principal,
        systemInfo,
        isBackendOnline,
        theme,
        toggleTheme,
        refreshWorkspaces,
        refreshProjects,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}

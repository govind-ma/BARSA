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
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<string | null>(() => {
    return localStorage.getItem('barsa_active_workspace') || null;
  });
  const [activeProjectId, setActiveProjectIdState] = useState<string | null>(() => {
    return localStorage.getItem('barsa_active_project') || null;
  });
  const [principal, setPrincipal] = useState<AuthenticatedPrincipal | null>(null);
  const [systemInfo, setSystemInfo] = useState<SystemInfo | null>(null);
  const [isBackendOnline, setIsBackendOnline] = useState<boolean>(true);
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('barsa_theme');
    return saved === 'dark' ? 'dark' : 'light';
  });

  const setActiveWorkspaceId = (id: string | null) => {
    setActiveWorkspaceIdState(id);
    if (id) {
      localStorage.setItem('barsa_active_workspace', id);
    } else {
      localStorage.removeItem('barsa_active_workspace');
    }
  };

  const setActiveProjectId = (id: string | null) => {
    setActiveProjectIdState(id);
    if (id) {
      localStorage.setItem('barsa_active_project', id);
    } else {
      localStorage.removeItem('barsa_active_project');
    }
  };

  // Sync theme with DOM and localStorage (Default: light / Ice)
  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    localStorage.setItem('barsa_theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const refreshWorkspaces = async () => {
    try {
      const list = await api.listWorkspaces();
      setWorkspaces(list);
      setIsBackendOnline(true);
      if (list.length > 0) {
        const storedId = localStorage.getItem('barsa_active_workspace');
        if (storedId && list.some((w) => (w.workspace_id || (w as any).id) === storedId)) {
          setActiveWorkspaceIdState(storedId);
        } else if (!activeWorkspaceId) {
          const firstId = list[0].workspace_id || (list[0] as any).id;
          if (firstId) setActiveWorkspaceId(firstId);
        }
      }
    } catch {
      setIsBackendOnline(false);
    }
  };

  const refreshProjects = async (_targetWsId?: string | null) => {
    try {
      // Always load all projects across all workspaces so user can switch to any project in any workspace
      const list = await api.listProjects(null);
      setProjects(list);
      if (list.length > 0) {
        const storedProjId = localStorage.getItem('barsa_active_project');
        if (storedProjId && list.some((p) => (p.project_id || (p as any).id) === storedProjId)) {
          setActiveProjectIdState(storedProjId);
        } else if (!activeProjectId || !list.some((p) => (p.project_id || (p as any).id) === activeProjectId)) {
          const currentWsId = _targetWsId || activeWorkspaceId;
          const wsProj = currentWsId ? list.find((p) => p.workspace_id === currentWsId) : null;
          const targetProj = wsProj || list[0];
          const targetId = targetProj.project_id || (targetProj as any).id;
          if (targetId) setActiveProjectId(targetId);
        }
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

      try {
        const wsList = await api.listWorkspaces();
        setWorkspaces(wsList);
        setIsBackendOnline(true);
        let selectedWsId = localStorage.getItem('barsa_active_workspace');
        if (!selectedWsId || !wsList.some((w) => (w.workspace_id || (w as any).id) === selectedWsId)) {
          selectedWsId = wsList.length > 0 ? (wsList[0].workspace_id || (wsList[0] as any).id) : null;
        }
        if (selectedWsId) {
          setActiveWorkspaceId(selectedWsId);
        }
        await refreshProjects(selectedWsId);
      } catch {
        setIsBackendOnline(false);
      }
    };

    init();
  }, []);

  useEffect(() => {
    if (activeWorkspaceId) {
      refreshProjects(activeWorkspaceId);
    }
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

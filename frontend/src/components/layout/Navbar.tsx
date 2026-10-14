import { useApp } from '@/app/AppContext';
import { Button } from '@/components/ui/Button';
import {
  FolderKanban,
  FileCode,
  Sun,
  Moon,
  Menu,
  Server,
  UserCircle2,
} from 'lucide-react';

export function Navbar({ onMenuClick }: { onMenuClick?: () => void }) {
  const {
    workspaces,
    projects,
    activeWorkspace,
    activeProject,
    setActiveWorkspaceId,
    setActiveProjectId,
    principal,
    isBackendOnline,
    theme,
    toggleTheme,
    systemInfo,
  } = useApp();

  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-border bg-card/80 px-4 md:px-6 backdrop-blur">
      <div className="flex items-center space-x-3">
        <button
          onClick={onMenuClick}
          aria-label="Open sidebar menu"
          className="md:hidden p-2 rounded-md hover:bg-accent text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Workspace Switcher */}
        <div className="flex items-center space-x-1.5 bg-muted/50 rounded-md px-2.5 py-1 border border-border">
          <FolderKanban className="h-3.5 w-3.5 text-muted-foreground" />
          <select
            value={activeWorkspace?.workspace_id || ''}
            onChange={(e) => setActiveWorkspaceId(e.target.value || null)}
            aria-label="Select active workspace"
            className="bg-transparent text-xs font-medium focus:outline-none cursor-pointer max-w-[130px] sm:max-w-[160px] truncate"
          >
            {workspaces.length === 0 ? (
              <option value="">No Workspaces</option>
            ) : (
              workspaces.map((w) => (
                <option key={w.workspace_id} value={w.workspace_id} className="bg-card text-foreground">
                  {w.name}
                </option>
              ))
            )}
          </select>
        </div>

        {/* Project Switcher */}
        <div className="flex items-center space-x-1.5 bg-muted/50 rounded-md px-2.5 py-1 border border-border">
          <FileCode className="h-3.5 w-3.5 text-muted-foreground" />
          <select
            value={activeProject?.project_id || ''}
            onChange={(e) => setActiveProjectId(e.target.value || null)}
            aria-label="Select active project"
            className="bg-transparent text-xs font-medium focus:outline-none cursor-pointer max-w-[130px] sm:max-w-[160px] truncate"
          >
            {projects.length === 0 ? (
              <option value="">No Projects</option>
            ) : (
              projects.map((p) => (
                <option key={p.project_id} value={p.project_id} className="bg-card text-foreground">
                  {p.name}
                </option>
              ))
            )}
          </select>
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center space-x-3">
        {/* Backend / Graph Status Pill */}
        <div
          title={isBackendOnline ? 'API Engine Connected (127.0.0.1:8000)' : 'Backend Engine Offline'}
          className="hidden sm:flex items-center space-x-1.5 text-xs text-muted-foreground bg-muted/40 px-2 py-1 rounded border border-border"
        >
          <span
            className={`h-2 w-2 rounded-full ${
              isBackendOnline ? 'bg-emerald-500 animate-pulse' : 'bg-destructive'
            }`}
          />
          <Server className="h-3 w-3" />
          <span className="font-mono text-[11px]">
            {isBackendOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
          {systemInfo?.falkordb_status && (
            <span
              className={`text-[10px] uppercase px-1 py-0.2 rounded font-semibold ${
                systemInfo.falkordb_status === 'connected'
                  ? 'bg-emerald-500/20 text-emerald-400'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              FalkorDB: {systemInfo.falkordb_status}
            </span>
          )}
        </div>

        {/* Identity Badge */}
        <div className="flex items-center space-x-2 text-xs border border-border rounded-md px-2.5 py-1 bg-muted/20">
          <UserCircle2 className="h-3.5 w-3.5 text-primary" />
          <span className="font-medium max-w-[100px] truncate" title={principal?.display_name || 'Local User'}>
            {principal?.display_name || 'Local User'}
          </span>
          {principal?.is_superuser && (
            <span className="text-[9px] bg-primary/20 text-primary px-1 rounded uppercase font-bold">
              ROOT
            </span>
          )}
        </div>

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleTheme}
          aria-label="Toggle theme"
          className="h-8 w-8 text-muted-foreground"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}

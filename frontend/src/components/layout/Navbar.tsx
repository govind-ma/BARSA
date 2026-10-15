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
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-border/80 bg-card/75 px-4 md:px-6 backdrop-blur-md">
      <div className="flex items-center space-x-2.5">
        <button
          onClick={onMenuClick}
          aria-label="Open sidebar menu"
          className="md:hidden p-2 rounded-lg hover:bg-accent/70 text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Workspace Switcher */}
        <div className="flex items-center space-x-1.5 bg-muted/40 hover:bg-muted/60 transition-colors rounded-lg px-2.5 py-1.5 border border-border/80">
          <FolderKanban className="h-3.5 w-3.5 text-muted-foreground" />
          <select
            value={activeWorkspace?.workspace_id || ''}
            onChange={(e) => setActiveWorkspaceId(e.target.value || null)}
            aria-label="Select active workspace"
            className="bg-transparent text-xs font-medium focus:outline-none cursor-pointer max-w-[130px] sm:max-w-[160px] truncate pr-1"
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
        <div className="flex items-center space-x-1.5 bg-muted/40 hover:bg-muted/60 transition-colors rounded-lg px-2.5 py-1.5 border border-border/80">
          <FileCode className="h-3.5 w-3.5 text-muted-foreground" />
          <select
            value={activeProject?.project_id || ''}
            onChange={(e) => setActiveProjectId(e.target.value || null)}
            aria-label="Select active project"
            className="bg-transparent text-xs font-medium focus:outline-none cursor-pointer max-w-[130px] sm:max-w-[160px] truncate pr-1"
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
      <div className="flex items-center space-x-2.5">
        {/* Backend / Graph Status Pill */}
        <div
          title={isBackendOnline ? 'API Engine Connected (127.0.0.1:8000)' : 'Backend Engine Offline'}
          className="hidden sm:flex items-center space-x-2 text-xs text-muted-foreground bg-muted/30 px-2.5 py-1 rounded-lg border border-border/70"
        >
          <span
            className={`h-2 w-2 rounded-full ${
              isBackendOnline ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-destructive'
            }`}
          />
          <Server className="h-3 w-3" />
          <span className="font-mono text-[11px] font-medium">
            {isBackendOnline ? 'ONLINE' : 'OFFLINE'}
          </span>
          {systemInfo?.falkordb_status && (
            <span
              className={`text-[9px] uppercase px-1.5 py-0.5 rounded-full font-semibold ${
                systemInfo.falkordb_status === 'connected'
                  ? 'bg-emerald-500/15 text-emerald-400 border border-emerald-500/20'
                  : 'bg-muted text-muted-foreground'
              }`}
            >
              Graph: {systemInfo.falkordb_status}
            </span>
          )}
        </div>

        {/* Identity Badge */}
        <div className="flex items-center space-x-1.5 text-xs border border-border/80 rounded-lg px-2.5 py-1.5 bg-muted/20">
          <UserCircle2 className="h-3.5 w-3.5 text-primary" />
          <span className="font-medium text-[11px] max-w-[110px] truncate" title={principal?.display_name || 'Local User'}>
            {principal?.display_name || 'Local User'}
          </span>
          {principal?.is_superuser && (
            <span className="text-[9px] bg-primary/20 text-primary px-1.5 py-0.2 rounded-full uppercase font-bold font-mono">
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
          className="h-8 w-8 text-muted-foreground hover:text-foreground rounded-lg"
        >
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}

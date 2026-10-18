import { useEffect, useRef, useState } from 'react';
import { useApp } from '@/app/AppContext';
import { NewProjectModal } from '@/components/projects/NewProjectModal';
import { ManageWorkspacesModal } from '@/components/workspaces/ManageWorkspacesModal';
import {
  ChevronDown,
  Search,
  Plus,
  FolderKanban,
  FileCode,
  Layers,
  Check,
} from 'lucide-react';

export function ProjectSwitcher() {
  const { workspaces, projects, activeWorkspace, activeProject, setActiveProjectId, setActiveWorkspaceId } = useApp();
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);
  const [isManageWorkspacesOpen, setIsManageWorkspacesOpen] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleOutsideClick = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleOutsideClick);
    }
    return () => {
      document.removeEventListener('mousedown', handleOutsideClick);
    };
  }, [isOpen]);

  // Group projects under workspaces
  const filteredProjects = projects.filter((p) =>
    p.name.toLowerCase().includes(search.toLowerCase()) ||
    (p.description && p.description.toLowerCase().includes(search.toLowerCase()))
  );

  const projectsByWorkspace: { [wsId: string]: typeof projects } = {};
  filteredProjects.forEach((p) => {
    const wsId = p.workspace_id || 'default';
    if (!projectsByWorkspace[wsId]) projectsByWorkspace[wsId] = [];
    projectsByWorkspace[wsId].push(p);
  });

  return (
    <div className="relative" ref={popoverRef}>
      {/* Central Project Switcher Button */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-secondary/40 hover:bg-secondary/70 border border-ice/20 hover:border-ice/40 transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice/50 group text-left"
        aria-expanded={isOpen}
      >
        <div className="h-2 w-2 rounded-full bg-ice shadow-[0_0_8px_rgba(56,189,248,0.8)]" />
        <div className="flex flex-col">
          <div className="flex items-center space-x-1.5">
            <span className="text-xs font-semibold text-foreground truncate max-w-[150px] sm:max-w-[200px]">
              {activeProject?.name || 'Select Project'}
            </span>
            <ChevronDown className="h-3 w-3 text-muted-foreground group-hover:text-foreground transition-transform duration-200" />
          </div>
          {activeWorkspace && (
            <span className="text-[10px] text-muted-foreground/80 font-mono truncate max-w-[150px]">
              {activeWorkspace.name}
            </span>
          )}
        </div>
      </button>

      {/* Glass Popover Dropdown */}
      {isOpen && (
        <div className="absolute left-1/2 -translate-x-1/2 top-full mt-2 w-80 sm:w-96 rounded-2xl bg-card/95 backdrop-blur-2xl border border-ice/30 shadow-[0_12px_40px_rgba(0,0,0,0.6)] z-50 p-3 space-y-3 animate-in fade-in zoom-in-95 duration-150">
          {/* Search Input */}
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search projects..."
              className="w-full bg-secondary/50 border border-ice/15 rounded-xl pl-9 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ice/60"
              autoFocus
            />
          </div>

          {/* Grouped Projects List */}
          <div className="max-h-60 overflow-y-auto space-y-3 pr-1">
            {Object.keys(projectsByWorkspace).length === 0 ? (
              <div className="py-6 text-center text-xs text-muted-foreground">
                No matching projects found
              </div>
            ) : (
              workspaces.map((ws) => {
                const wsId = ws.workspace_id || (ws as any).id;
                const wsProjects = projectsByWorkspace[wsId] || [];
                if (wsProjects.length === 0) return null;

                return (
                  <div key={wsId} className="space-y-1">
                    <div className="flex items-center space-x-1.5 px-2 py-0.5 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                      <FolderKanban className="h-3 w-3 text-ice" />
                      <span>{ws.name}</span>
                    </div>

                    <div className="space-y-0.5">
                      {wsProjects.map((proj) => {
                        const isCurrent = proj.project_id === activeProject?.project_id;
                        return (
                          <button
                            key={proj.project_id}
                            onClick={() => {
                              setActiveProjectId(proj.project_id);
                              if (proj.workspace_id) setActiveWorkspaceId(proj.workspace_id);
                              setIsOpen(false);
                            }}
                            className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs transition-colors ${
                              isCurrent
                                ? 'bg-ice/15 text-ice font-semibold border border-ice/30'
                                : 'text-muted-foreground hover:bg-secondary/70 hover:text-foreground'
                            }`}
                          >
                            <div className="flex items-center space-x-2 truncate">
                              <FileCode className={`h-3.5 w-3.5 shrink-0 ${isCurrent ? 'text-ice' : 'text-muted-foreground'}`} />
                              <span className="truncate">{proj.name}</span>
                            </div>
                            {isCurrent && <Check className="h-3.5 w-3.5 text-ice shrink-0 ml-2" />}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Footer Actions */}
          <div className="pt-2 border-t border-ice/10 flex items-center justify-between text-xs px-1">
            <button
              onClick={() => {
                setIsOpen(false);
                setIsNewProjectOpen(true);
              }}
              className="flex items-center space-x-1.5 text-chilli hover:text-chilli-hover font-semibold transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>+ New project</span>
            </button>

            <button
              onClick={() => {
                setIsOpen(false);
                setIsManageWorkspacesOpen(true);
              }}
              className="flex items-center space-x-1 text-[11px] text-muted-foreground hover:text-ice transition-colors"
            >
              <Layers className="h-3 w-3" />
              <span>Manage workspaces</span>
            </button>
          </div>
        </div>
      )}

      {/* Nested Modals */}
      <NewProjectModal
        isOpen={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
      />
      <ManageWorkspacesModal
        isOpen={isManageWorkspacesOpen}
        onClose={() => setIsManageWorkspacesOpen(false)}
      />
    </div>
  );
}

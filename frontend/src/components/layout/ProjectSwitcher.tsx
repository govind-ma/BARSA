import { useEffect, useRef, useState, useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';
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
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [popoverCoords, setPopoverCoords] = useState<{ top: number; left: number }>({ top: 60, left: 0 });

  // Compute position for portal dropdown
  useLayoutEffect(() => {
    if (isOpen && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      const popoverWidth = 360;
      // Center relative to trigger, clamping within window bounds with 16px margin
      let left = rect.left + rect.width / 2 - popoverWidth / 2;
      left = Math.max(16, Math.min(window.innerWidth - popoverWidth - 16, left));
      setPopoverCoords({
        top: rect.bottom + 8,
        left,
      });
    }
  }, [isOpen]);

  // Close on outside click and Escape key
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
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
    <>
      {/* Central Project Switcher Button */}
      <button
        ref={triggerRef}
        onClick={() => setIsOpen((prev) => !prev)}
        className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-surface hover:bg-ice-100 dark:hover:bg-bg-elevated border border-border-subtle hover:border-border-strong transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-steel-500 group text-left shadow-xs"
        aria-expanded={isOpen}
      >
        <div className="h-2 w-2 rounded-full bg-lava-orange shadow-[0_0_8px_rgba(255,122,26,0.7)]" />
        <div className="flex flex-col">
          <div className="flex items-center space-x-1.5">
            <span className="text-xs font-semibold text-text-primary truncate max-w-[150px] sm:max-w-[200px]">
              {activeProject?.name || 'Select Project'}
            </span>
            <ChevronDown className="h-3 w-3 text-text-muted group-hover:text-text-primary transition-transform duration-200" />
          </div>
          {activeWorkspace && (
            <span className="text-[10px] text-text-muted font-mono truncate max-w-[150px]">
              {activeWorkspace.name}
            </span>
          )}
        </div>
      </button>

      {/* Solid Popover Rendered via Portal at document.body */}
      {isOpen &&
        createPortal(
          <>
            {/* Scrim: dims & blurs backdrop so background content never competes */}
            <div
              className="floating-scrim"
              onClick={() => setIsOpen(false)}
            />

            {/* Solid Dropdown Popover */}
            <div
              className="fixed z-popover w-[360px] max-h-[420px] solid-floating-surface rounded-xl flex flex-col p-3 space-y-3 animate-in fade-in zoom-in-95 duration-150 text-text-primary select-none overflow-hidden"
              style={{ top: popoverCoords.top, left: popoverCoords.left }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Search Input */}
              <div className="relative shrink-0">
                <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-text-muted" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search projects..."
                  className="w-full bg-surface dark:bg-bg-elevated border border-border-subtle rounded-lg pl-9 pr-3 py-1.5 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-lava-orange"
                  autoFocus
                />
              </div>

              {/* Grouped Projects List with Internal Scroll */}
              <div className="flex-1 overflow-y-auto space-y-2 pr-1 min-h-0">
                {Object.keys(projectsByWorkspace).length === 0 ? (
                  <div className="py-8 text-center text-xs text-text-muted">
                    No matching projects found
                  </div>
                ) : (
                  workspaces.map((ws) => {
                    const wsId = ws.workspace_id || (ws as any).id;
                    const wsProjects = projectsByWorkspace[wsId] || [];
                    if (wsProjects.length === 0) return null;

                    return (
                      <div key={wsId}>
                        {/* Workspace Group Heading with 12px top spacing */}
                        <div className="flex items-center space-x-1.5 px-2 mt-3 mb-1 text-[10px] font-mono font-semibold uppercase tracking-wider text-text-muted">
                          <FolderKanban className="h-3 w-3 text-steel-500" />
                          <span>{ws.name}</span>
                        </div>

                        {/* Project Rows (44px height each, one-line with ellipsis) */}
                        <div className="space-y-1">
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
                                className={`w-full h-11 flex items-center justify-between px-3 rounded-lg text-xs transition-colors ${
                                  isCurrent
                                    ? 'bg-ice-100 dark:bg-white/[0.08] text-text-primary font-semibold border border-border-strong'
                                    : 'text-text-secondary hover:bg-ice-100/70 dark:hover:bg-white/[0.04] hover:text-text-primary'
                                }`}
                              >
                                <div className="flex items-center space-x-2.5 truncate min-w-0">
                                  <FileCode
                                    className={`h-4 w-4 shrink-0 ${isCurrent ? 'text-lava-orange' : 'text-steel-500'}`}
                                  />
                                  <span className="truncate text-left">{proj.name}</span>
                                </div>
                                {isCurrent && (
                                  <Check className="h-4 w-4 text-lava-orange shrink-0 ml-2" />
                                )}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Footer Divider with 2 Clearly Separated Rows */}
              <div className="pt-2 border-t border-border-subtle shrink-0 flex flex-col space-y-1 text-xs">
                {/* Row 1: + New project */}
                <button
                  onClick={() => {
                    setIsOpen(false);
                    setIsNewProjectOpen(true);
                  }}
                  className="w-full h-9 flex items-center space-x-2 px-3 rounded-lg text-text-primary font-semibold hover:bg-ice-100 dark:hover:bg-white/[0.06] transition-colors"
                >
                  <Plus className="h-4 w-4 text-lava-orange" />
                  <span>Create new project</span>
                </button>

                {/* Row 2: Manage workspaces */}
                <button
                  onClick={() => {
                    setIsOpen(false);
                    setIsManageWorkspacesOpen(true);
                  }}
                  className="w-full h-9 flex items-center space-x-2 px-3 rounded-lg text-text-secondary hover:text-text-primary hover:bg-ice-100 dark:hover:bg-white/[0.06] transition-colors"
                >
                  <Layers className="h-3.5 w-3.5 text-steel-500" />
                  <span>Manage workspaces</span>
                </button>
              </div>
            </div>
          </>,
          document.body
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
    </>
  );
}

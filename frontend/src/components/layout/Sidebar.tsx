import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { useApp } from '@/app/AppContext';
import {
  Home,
  CheckSquare,
  BrainCircuit,
  History,
  Bot,
  Network,
  BookmarkCheck,
  GitBranch,
  HardDrive,
  ShieldCheck,
  Settings,
  Layers,
  FolderGit2,
  Sparkles,
} from 'lucide-react';

export interface SidebarProps {
  className?: string;
  onItemClick?: () => void;
}

export function Sidebar({ className, onItemClick }: SidebarProps) {
  const { activeProject } = useApp();

  const mainProjectItems = [
    { name: 'Home', href: '/', icon: Home },
    { name: 'Tasks', href: '/tasks', icon: CheckSquare },
    { name: 'Mind Map', searchLabel: 'Knowledge Graph', href: '/graph', icon: Network },
    { name: 'Memory', searchLabel: 'Memory Explorer', href: '/memory', icon: BrainCircuit },
    { name: 'History', href: '/history', icon: History },
    { name: 'Agents', href: '/agents', icon: Bot },
  ];

  const advancedItems = [
    { name: 'Checkpoints', href: '/checkpoints', icon: BookmarkCheck },
    { name: 'Version Control', href: '/version-control', icon: GitBranch },
    { name: 'Storage', href: '/storage', icon: HardDrive },
    { name: 'Security', href: '/security', icon: ShieldCheck },
  ];

  const globalItems = [
    { name: 'Projects', href: '/projects', icon: FolderGit2 },
    { name: 'Workspaces', href: '/workspaces', icon: Layers },
    { name: 'Settings', href: '/settings', icon: Settings },
  ];

  return (
    <aside
      className={cn(
        'flex flex-col border-r border-border-subtle bg-surface/90 backdrop-blur-xl w-64 min-h-screen text-text-primary select-none transition-colors duration-200',
        className
      )}
    >
      {/* Brand Header */}
      <div className="flex h-14 items-center justify-between px-5 border-b border-border-subtle">
        <NavLink to="/" className="flex items-center space-x-2.5 group">
          <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-lava-yellow via-lava-orange to-lava-red flex items-center justify-center font-bold text-white shadow-xs">
            <Sparkles className="h-3.5 w-3.5 text-white" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center space-x-1.5">
              <span className="font-heading font-bold tracking-tight text-sm text-text-primary leading-none">
                BARSA
              </span>
              <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-lava-orange/15 text-lava-orange font-mono font-medium">
                v0.1
              </span>
            </div>
            <span className="text-[10px] text-text-muted font-medium mt-0.5">
              Universal AI Memory
            </span>
          </div>
        </NavLink>
      </div>

      {/* Nav List */}
      <nav className="flex-1 space-y-5 px-3 py-4 overflow-y-auto" aria-label="Main Navigation">
        {/* Project Navigation (Level B) */}
        <div className="space-y-1">
          <div className="px-3 pb-1.5 flex items-center justify-between text-[10px] font-semibold tracking-wider text-text-muted uppercase">
            <span>Workspace</span>
            {activeProject && (
              <span className="text-[9px] font-mono lowercase font-normal text-lava-orange truncate max-w-[90px]">
                {activeProject.name}
              </span>
            )}
          </div>
          {mainProjectItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onItemClick}
                end={item.href === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-steel-500',
                    isActive
                      ? 'bg-ice-200 dark:bg-bg-elevated text-text-primary font-semibold shadow-xs border border-border-strong'
                      : 'text-text-muted hover:bg-ice-100/60 dark:hover:bg-white/[0.04] hover:text-text-primary'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0 text-steel-500" />
                <span className="font-heading">{item.name}</span>
                {item.searchLabel && (
                  <span className="sr-only">{item.searchLabel}</span>
                )}
              </NavLink>
            );
          })}
        </div>

        {/* Advanced Navigation (Level B Secondary) */}
        <div className="space-y-1 pt-1 border-t border-border-subtle">
          <div className="px-3 pt-2 pb-1 text-[10px] font-semibold tracking-wider text-text-muted uppercase">
            Advanced
          </div>
          {advancedItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onItemClick}
                className={({ isActive }) =>
                  cn(
                    'flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-steel-500',
                    isActive
                      ? 'bg-ice-200 dark:bg-bg-elevated text-text-primary font-semibold shadow-xs border border-border-strong'
                      : 'text-text-muted hover:bg-ice-100/60 dark:hover:bg-white/[0.04] hover:text-text-primary'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0 text-steel-500" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </div>

        {/* Global Navigation (Level A) */}
        <div className="space-y-1 pt-1 border-t border-border-subtle">
          <div className="px-3 pt-2 pb-1 text-[10px] font-semibold tracking-wider text-text-muted uppercase">
            Global
          </div>
          {globalItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onItemClick}
                className={({ isActive }) =>
                  cn(
                    'flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-steel-500',
                    isActive
                      ? 'bg-ice-200 dark:bg-bg-elevated text-text-primary font-semibold shadow-xs border border-border-strong'
                      : 'text-text-muted hover:bg-ice-100/60 dark:hover:bg-white/[0.04] hover:text-text-primary'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0 text-steel-500" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Footer Info */}
      <div className="p-3.5 border-t border-border-subtle">
        <div className="rounded-xl bg-ice-100/60 dark:bg-white/[0.03] border border-border-subtle p-2.5 text-xs">
          <div className="flex items-center justify-between mb-1">
            <span className="font-heading font-medium text-text-primary text-[11px]">
              Local Engine
            </span>
            <span className="inline-flex items-center space-x-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono font-medium">
                Active
              </span>
            </span>
          </div>
          <p className="text-[10px] text-text-muted leading-relaxed">
            FalkorDB Graph + SQLite WAL. Zero cloud lock-in.
          </p>
        </div>
      </div>
    </aside>
  );
}

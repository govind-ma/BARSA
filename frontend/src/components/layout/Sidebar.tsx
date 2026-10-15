import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  Layers,
  FileCode,
  BrainCircuit,
  GitBranch,
  Network,
  Bot,
  CheckSquare,
  ShieldCheck,
  HardDrive,
  Settings,
  Sparkles,
} from 'lucide-react';

const primaryItems = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Projects', href: '/projects', icon: FileCode },
  { name: 'Memory Explorer', href: '/memory', icon: BrainCircuit },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: 'Tasks & Issues', href: '/tasks', icon: CheckSquare },
];

const secondaryItems = [
  { name: 'Workspaces', href: '/workspaces', icon: Layers },
  { name: 'Knowledge Graph', href: '/graph', icon: Network },
  { name: 'Version Control', href: '/version-control', icon: GitBranch },
  { name: 'Storage', href: '/storage', icon: HardDrive },
  { name: 'Security', href: '/security', icon: ShieldCheck },
  { name: 'Settings', href: '/settings', icon: Settings },
];

export interface SidebarProps {
  className?: string;
  onItemClick?: () => void;
}

export function Sidebar({ className, onItemClick }: SidebarProps) {
  return (
    <aside
      className={cn(
        'flex flex-col border-r border-border/80 bg-card/70 backdrop-blur-xl w-64 min-h-screen text-card-foreground select-none',
        className
      )}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center justify-between px-5 border-b border-border/70">
        <NavLink to="/" className="flex items-center space-x-2.5 group">
          <div className="h-8 w-8 rounded-xl bg-gradient-to-br from-primary/30 via-primary/20 to-primary/5 border border-primary/30 flex items-center justify-center font-bold text-primary shadow-sm group-hover:border-primary/50 transition-colors">
            <Sparkles className="h-4 w-4 text-primary" />
          </div>
          <div className="flex flex-col">
            <div className="flex items-center space-x-1.5">
              <span className="font-bold tracking-tight text-sm leading-none">BARSA</span>
              <span className="text-[9px] px-1.5 py-0.5 rounded-full bg-primary/10 text-primary font-mono font-medium">
                v0.1
              </span>
            </div>
            <span className="text-[10px] text-muted-foreground/80 font-medium tracking-tight mt-0.5">
              Universal AI Memory
            </span>
          </div>
        </NavLink>
      </div>

      {/* Nav List */}
      <nav className="flex-1 space-y-6 px-3 py-4 overflow-y-auto" aria-label="Main Navigation">
        {/* Primary Navigation */}
        <div className="space-y-1">
          <div className="px-3 pb-1 text-[10px] font-semibold tracking-wider text-muted-foreground/70 uppercase">
            Platform
          </div>
          {primaryItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onItemClick}
                className={({ isActive }) =>
                  cn(
                    'flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    isActive
                      ? 'bg-primary/10 text-primary font-semibold shadow-xs'
                      : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </div>

        {/* Secondary Navigation */}
        <div className="space-y-1">
          <div className="px-3 pb-1 text-[10px] font-semibold tracking-wider text-muted-foreground/70 uppercase">
            Workspace & Systems
          </div>
          {secondaryItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.name}
                to={item.href}
                onClick={onItemClick}
                className={({ isActive }) =>
                  cn(
                    'flex items-center space-x-3 px-3 py-2 rounded-lg text-xs font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                    isActive
                      ? 'bg-primary/10 text-primary font-semibold shadow-xs'
                      : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.name}</span>
              </NavLink>
            );
          })}
        </div>
      </nav>

      {/* Footer Info */}
      <div className="p-3.5 border-t border-border/70">
        <div className="rounded-xl bg-muted/40 border border-border/60 p-3 text-xs">
          <div className="flex items-center justify-between mb-1">
            <span className="font-medium text-foreground text-[11px]">Local-First Engine</span>
            <span className="inline-flex items-center space-x-1">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] text-emerald-500 font-mono font-medium">Ready</span>
            </span>
          </div>
          <p className="text-[10px] text-muted-foreground leading-relaxed">
            Memory persists in SQLite WAL. Zero cloud lock-in.
          </p>
        </div>
      </div>
    </aside>
  );
}

import { NavLink } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  FolderKanban,
  FileCode,
  BrainCircuit,
  GitBranch,
  Network,
  Bot,
  CheckSquare,
  ShieldAlert,
  HardDrive,
  Settings,
} from 'lucide-react';

const navigationItems = [
  { name: 'Overview', href: '/', icon: LayoutDashboard },
  { name: 'Workspaces', href: '/workspaces', icon: FolderKanban },
  { name: 'Projects', href: '/projects', icon: FileCode },
  { name: 'Memory Explorer', href: '/memory', icon: BrainCircuit },
  { name: 'Version Control', href: '/version-control', icon: GitBranch },
  { name: 'Knowledge Graph', href: '/graph', icon: Network },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: 'Tasks & Issues', href: '/tasks', icon: CheckSquare },
  { name: 'Security', href: '/security', icon: ShieldAlert },
  { name: 'Storage', href: '/storage', icon: HardDrive },
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
        'flex flex-col border-r border-border bg-card/60 backdrop-blur w-64 min-h-screen text-card-foreground',
        className
      )}
    >
      {/* Brand Header */}
      <div className="flex h-16 items-center px-6 border-b border-border">
        <NavLink to="/" className="flex items-center space-x-3">
          <div className="h-8 w-8 rounded-lg bg-primary/20 border border-primary/30 flex items-center justify-center font-bold text-primary">
            B
          </div>
          <div className="flex flex-col">
            <span className="font-bold tracking-tight text-base leading-none">BARSA</span>
            <span className="text-[10px] text-muted-foreground uppercase tracking-widest mt-0.5">
              Memory Fabric
            </span>
          </div>
        </NavLink>
      </div>

      {/* Nav List */}
      <nav className="flex-1 space-y-1 px-3 py-4 overflow-y-auto" aria-label="Main Navigation">
        {navigationItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.name}
              to={item.href}
              onClick={onItemClick}
              className={({ isActive }) =>
                cn(
                  'flex items-center space-x-3 px-3 py-2.5 rounded-md text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                  isActive
                    ? 'bg-primary/10 text-primary border border-primary/20 font-semibold'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )
              }
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.name}</span>
            </NavLink>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div className="p-4 border-t border-border">
        <div className="rounded-md bg-muted/40 p-3 text-xs text-muted-foreground">
          <div className="flex items-center justify-between mb-1">
            <span className="font-semibold text-foreground">BMS v0.1</span>
            <span className="inline-block h-2 w-2 rounded-full bg-emerald-500" />
          </div>
          <p className="text-[11px] leading-tight">Local-First AI Memory & Version Control</p>
        </div>
      </div>
    </aside>
  );
}

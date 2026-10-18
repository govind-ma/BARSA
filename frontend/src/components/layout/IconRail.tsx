import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  LayoutDashboard,
  CheckSquare,
  GitBranch,
  BrainCircuit,
  BookmarkCheck,
  Sparkles,
} from 'lucide-react';

export interface NavItem {
  id: string;
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string;
}

export const railNavItems: NavItem[] = [
  { id: 'mission-control', name: 'Mission Control', href: '/', icon: LayoutDashboard },
  { id: 'tasks', name: 'Tasks', href: '/tasks', icon: CheckSquare },
  { id: 'history', name: 'History', href: '/version-control', icon: GitBranch },
  { id: 'memory', name: 'Memory', href: '/memory', icon: BrainCircuit },
  { id: 'checkpoints', name: 'Checkpoints', href: '/checkpoints', icon: BookmarkCheck },
];

export interface IconRailProps {
  className?: string;
  onItemClick?: () => void;
}

export function IconRail({ className, onItemClick }: IconRailProps) {
  const [isHovered, setIsHovered] = useState(false);
  const location = useLocation();

  const isItemActive = (href: string) => {
    if (href === '/') {
      return location.pathname === '/' || location.pathname.startsWith('/projects');
    }
    return location.pathname.startsWith(href);
  };

  return (
    <>
      {/* Desktop / Tablet Icon Rail */}
      <aside
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        className={cn(
          'hidden md:flex flex-col fixed top-0 left-0 z-40 h-screen transition-all duration-300 ease-out',
          'bg-card/90 backdrop-blur-2xl border-r border-ice/20 shadow-[4px_0_24px_rgba(0,0,0,0.4)] select-none group',
          isHovered ? 'w-[220px]' : 'w-16',
          className
        )}
      >
        {/* Top Logo Glyph */}
        <div className="h-14 flex items-center px-4 border-b border-ice/10 shrink-0">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-ice/25 via-ice/10 to-transparent border border-ice/40 flex items-center justify-center shadow-[0_0_15px_rgba(56,189,248,0.25)] shrink-0">
            <Sparkles className="h-4 w-4 text-ice animate-pulse" />
          </div>
          <div
            className={cn(
              'ml-3 flex flex-col overflow-hidden transition-all duration-300 whitespace-nowrap',
              isHovered ? 'opacity-100 max-w-[140px]' : 'opacity-0 max-w-0'
            )}
          >
            <span className="font-bold tracking-wider text-xs bg-gradient-to-r from-ice to-foreground bg-clip-text text-transparent">
              BARSA
            </span>
            <span className="text-[9px] text-muted-foreground tracking-tight">Collective AI Brain</span>
          </div>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 py-4 flex flex-col space-y-1.5 px-2 overflow-y-auto overflow-x-hidden">
          {railNavItems.map((item) => {
            const Icon = item.icon;
            const active = isItemActive(item.href);

            return (
              <NavLink
                key={item.id}
                to={item.href}
                onClick={onItemClick}
                className={cn(
                  'relative flex items-center h-10 rounded-xl transition-all duration-200 group/btn',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ice/50',
                  active
                    ? 'text-ice bg-ice/10 shadow-[inset_0_0_12px_rgba(56,189,248,0.15)] font-semibold'
                    : 'text-muted-foreground hover:text-foreground hover:bg-secondary/60'
                )}
                title={!isHovered ? item.name : undefined}
              >
                {/* Active Ice Indicator Bar */}
                {active && (
                  <div className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-ice shadow-[0_0_10px_rgba(56,189,248,0.9)] animate-in fade-in duration-300" />
                )}

                {/* Icon Container */}
                <div className="w-12 h-10 flex items-center justify-center shrink-0">
                  <Icon
                    className={cn(
                      'h-4 w-4 transition-transform duration-200 group-hover/btn:scale-110',
                      active && 'text-ice drop-shadow-[0_0_8px_rgba(56,189,248,0.6)]'
                    )}
                  />
                </div>

                {/* Sliding Label on Hover */}
                <span
                  className={cn(
                    'text-xs tracking-tight whitespace-nowrap transition-all duration-300 overflow-hidden',
                    isHovered ? 'opacity-100 max-w-[140px] pl-1' : 'opacity-0 max-w-0 pl-0'
                  )}
                >
                  {item.name}
                </span>

                {/* Active Ambient Glow */}
                {active && (
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-r from-ice/10 to-transparent pointer-events-none" />
                )}
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom Rail Hint */}
        <div className="p-3 border-t border-ice/10 shrink-0">
          <div
            className={cn(
              'flex items-center text-[10px] text-muted-foreground/80 font-mono transition-opacity duration-200',
              isHovered ? 'justify-between px-1' : 'justify-center'
            )}
          >
            <span className={cn(isHovered ? 'inline' : 'hidden')}>Graph Hacks</span>
            <span className="px-1.5 py-0.5 rounded bg-muted/60 text-ice/80 border border-ice/10">v0.1</span>
          </div>
        </div>
      </aside>

      {/* Mobile Bottom Tab Bar */}
      <nav
        aria-label="Mobile Navigation"
        className="md:hidden fixed bottom-0 left-0 right-0 z-50 h-16 bg-card/95 backdrop-blur-2xl border-t border-ice/20 flex items-center justify-around px-2 shadow-[0_-4px_20px_rgba(0,0,0,0.5)]"
      >
        {railNavItems.map((item) => {
          const Icon = item.icon;
          const active = isItemActive(item.href);

          return (
            <NavLink
              key={item.id}
              to={item.href}
              onClick={onItemClick}
              className={cn(
                'relative flex flex-col items-center justify-center flex-1 h-full py-1 text-[10px] transition-all duration-150',
                active
                  ? 'text-ice font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {active && (
                <div className="absolute top-0 left-4 right-4 h-0.5 bg-ice shadow-[0_0_8px_rgba(56,189,248,0.9)] rounded-full" />
              )}
              <Icon
                className={cn(
                  'h-4 w-4 mb-1 transition-transform',
                  active && 'text-ice drop-shadow-[0_0_8px_rgba(56,189,248,0.6)] scale-110'
                )}
              />
              <span className="truncate max-w-[64px]">{item.name}</span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
}

import React, { useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { cn } from '@/lib/utils';
import { BarsaLogo } from '@/components/ui/BarsaLogo';
import {
  LayoutDashboard,
  CheckSquare,
  GitBranch,
  BrainCircuit,
  BookmarkCheck,
  Palette,
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
  { id: 'styleguide', name: 'Style Guide', href: '/styleguide', icon: Palette },
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
          'bg-surface/90 backdrop-blur-2xl border-r border-border-subtle shadow-lg select-none group',
          isHovered ? 'w-[220px]' : 'w-16',
          className
        )}
      >
        {/* Top Logo Glyph */}
        <div className="h-14 flex items-center px-4 border-b border-border-subtle shrink-0">
          <div className="shrink-0 flex items-center justify-center">
            <BarsaLogo size={28} />
          </div>
          <div
            className={cn(
              'ml-3 flex flex-col overflow-hidden transition-all duration-300 whitespace-nowrap',
              isHovered ? 'opacity-100 max-w-[140px]' : 'opacity-0 max-w-0'
            )}
          >
            <span className="font-heading font-semibold tracking-tight text-xs text-text-primary">
              BARSA
            </span>
            <span className="text-[10px] text-text-muted font-mono tracking-tight uppercase">
              Ice & Lava Engine
            </span>
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
                  'relative flex items-center h-10 rounded-lg transition-all duration-200 group/btn',
                  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-steel-500',
                  active
                    ? 'text-text-primary bg-ice-100 dark:bg-white/[0.08] font-semibold shadow-sm'
                    : 'text-steel-500 hover:text-text-primary hover:bg-ice-100/60 dark:hover:bg-white/[0.04]'
                )}
                title={!isHovered ? item.name : undefined}
              >
                {/* Active Magma Indicator Bar */}
                {active && (
                  <div className="absolute left-0 top-1.5 bottom-1.5 w-1 rounded-r-full bg-gradient-to-b from-lava-yellow via-lava-orange to-lava-red shadow-[0_0_8px_rgba(255,122,26,0.5)] animate-in fade-in duration-200" />
                )}

                {/* Icon Container */}
                <div className="w-12 h-10 flex items-center justify-center shrink-0">
                  <Icon
                    className={cn(
                      'h-4 w-4 transition-transform duration-200 group-hover/btn:scale-110',
                      active ? 'text-lava-orange' : 'text-steel-500'
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
              </NavLink>
            );
          })}
        </nav>

        {/* Bottom Rail Hint */}
        <div className="p-3 border-t border-border-subtle shrink-0">
          <div
            className={cn(
              'flex items-center text-[10px] text-text-muted font-mono transition-opacity duration-200',
              isHovered ? 'justify-between px-1' : 'justify-center'
            )}
          >
            <span className={cn(isHovered ? 'inline' : 'hidden')}>Ice & Lava</span>
            <span className="px-1.5 py-0.5 rounded bg-ice-100 dark:bg-white/[0.06] text-steel-700 dark:text-text-secondary border border-border-subtle">
              v0.2
            </span>
          </div>
        </div>
      </aside>

      {/* Mobile Bottom Tab Bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 h-14 bg-surface/95 backdrop-blur-xl border-t border-border-subtle flex items-center justify-around px-2 shadow-lg">
        {railNavItems.map((item) => {
          const Icon = item.icon;
          const active = isItemActive(item.href);

          return (
            <NavLink
              key={item.id}
              to={item.href}
              onClick={onItemClick}
              className={cn(
                'relative flex flex-col items-center justify-center flex-1 h-full py-1 transition-all',
                active ? 'text-lava-orange font-medium' : 'text-steel-500 hover:text-text-primary'
              )}
            >
              {active && (
                <div className="absolute top-0 left-3 right-3 h-0.5 rounded-full bg-gradient-to-r from-lava-yellow via-lava-orange to-lava-red shadow-[0_0_8px_rgba(255,122,26,0.6)]" />
              )}
              <Icon className="h-4 w-4" />
              <span className="text-[10px] tracking-tight mt-0.5 truncate max-w-[60px]">
                {item.name}
              </span>
            </NavLink>
          );
        })}
      </nav>
    </>
  );
}

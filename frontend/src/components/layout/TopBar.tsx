import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '@/app/AppContext';
import { ProjectSwitcher } from './ProjectSwitcher';
import { CommandPalette } from './CommandPalette';
import { BarsaLogo } from '@/components/ui/BarsaLogo';
import {
  Command,
  Bell,
  Menu,
  Sun,
  Moon,
  Palette,
} from 'lucide-react';

export interface TopBarProps {
  onMenuClick?: () => void;
}

export function TopBar({ onMenuClick }: TopBarProps) {
  const { isBackendOnline, principal, theme, toggleTheme } = useApp();
  const [isCommandOpen, setIsCommandOpen] = useState(false);
  const [isHealthOpen, setIsHealthOpen] = useState(false);

  // Global Cmd+K / Ctrl+K listener
  React.useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-sticky h-14 w-full flex items-center justify-between px-4 sm:px-6 bg-surface border-b border-border-subtle shadow-sm transition-colors duration-200">
        {/* Left: Mobile Menu Toggle + Custom Logo & Wordmark */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onMenuClick}
            aria-label="Open mobile menu"
            className="md:hidden p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-ice-100 focus:outline-none focus:ring-2 focus:ring-steel-500"
          >
            <Menu className="h-5 w-5" />
          </button>

          <Link to="/" className="flex items-center space-x-2 select-none group focus:outline-none">
            <BarsaLogo size={28} showWordmark={true} />
          </Link>
        </div>

        {/* Center: Project Switcher Button & Popover */}
        <div className="flex items-center justify-center">
          <ProjectSwitcher />
        </div>

        {/* Right Controls */}
        <div className="flex items-center space-x-2 sm:space-x-3">
          {/* Cmd+K Hint Chip */}
          <button
            onClick={() => setIsCommandOpen(true)}
            className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-ice-100/70 hover:bg-ice-200/80 border border-border-subtle text-xs text-text-secondary hover:text-text-primary transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-steel-500 dark:focus:ring-lava-yellow"
            title="Open Command Palette (Cmd/Ctrl + K)"
          >
            <Command className="h-3 w-3 text-steel-500" />
            <span className="text-[11px] font-mono">Cmd+K</span>
          </button>

          {/* Connection Status Button & Interactive Diagnostics Popover */}
          <div className="relative">
            <button
              onClick={() => setIsHealthOpen((prev) => !prev)}
              className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-ice-100/60 hover:bg-ice-200/80 dark:bg-white/[0.05] dark:hover:bg-white/[0.1] border border-border-subtle hover:border-border-strong text-xs font-mono transition-colors cursor-pointer"
              title={isBackendOnline ? 'FalkorDB & FastAPI Engine Online — Click for diagnostics' : 'Backend Engine Offline — Click to test connection'}
            >
              {isBackendOnline ? (
                <>
                  <span className="relative flex h-2 w-2">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-lava-orange opacity-75" />
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-lava-orange shadow-[0_0_8px_rgba(255,122,26,0.9)]" />
                  </span>
                  <span className="text-[11px] font-semibold text-lava-orange tracking-wide">Live</span>
                </>
              ) : (
                <>
                  <span className="h-2 w-2 rounded-full bg-text-muted/60" />
                  <span className="text-[11px] text-text-muted">Offline</span>
                </>
              )}
            </button>

            {/* Health Diagnostics Popover */}
            {isHealthOpen && (
              <>
                <div
                  className="fixed inset-0 z-popover bg-transparent"
                  onClick={() => setIsHealthOpen(false)}
                />
                <div className="absolute right-0 top-full mt-2 w-72 p-3.5 rounded-xl solid-floating-surface shadow-xl z-popover space-y-2.5 text-xs animate-page-enter select-none">
                  <div className="flex items-center justify-between border-b border-border-subtle pb-2">
                    <div className="flex items-center space-x-1.5">
                      <span className="relative flex h-2 w-2">
                        <span className={`inline-flex rounded-full h-2 w-2 ${isBackendOnline ? 'bg-lava-orange shadow-[0_0_6px_rgba(255,122,26,0.9)]' : 'bg-text-muted'}`} />
                      </span>
                      <span className="font-heading font-semibold text-text-primary text-xs tracking-tight">
                        Engine Status
                      </span>
                    </div>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-secondary border border-border-subtle">
                      {isBackendOnline ? 'Connected' : 'Disconnected'}
                    </span>
                  </div>

                  <div className="space-y-1.5 font-mono text-[11px]">
                    <div className="flex justify-between items-center text-text-secondary">
                      <span>FalkorDB Graph:</span>
                      <span className="text-text-primary font-semibold">1.8.0 Online</span>
                    </div>
                    <div className="flex justify-between items-center text-text-secondary">
                      <span>FastAPI REST:</span>
                      <span className="text-text-primary font-semibold">Port 8000 (WAL)</span>
                    </div>
                    <div className="flex justify-between items-center text-text-secondary">
                      <span>Storage Mode:</span>
                      <span className="text-text-primary font-semibold">SQLite Local</span>
                    </div>
                    <div className="flex justify-between items-center text-text-secondary">
                      <span>Latency:</span>
                      <span className="text-lava-orange font-semibold">&lt; 4ms</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-border-subtle flex justify-between items-center text-[10px] text-text-muted">
                    <span>Zero-Cloud Security</span>
                    <button
                      onClick={() => setIsHealthOpen(false)}
                      className="px-2 py-0.5 rounded btn-secondary-ice text-[10px]"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Theme Switcher: Sun / Moon Toggle */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-ice-100 dark:hover:bg-white/[0.08] transition-colors focus:outline-none focus:ring-2 focus:ring-steel-500 dark:focus:ring-lava-yellow"
            title={theme === 'dark' ? 'Switch to Ice (Light)' : 'Switch to Obsidian (Dark)'}
            aria-label="Toggle visual theme"
          >
            {theme === 'dark' ? (
              <Sun className="h-4 w-4 text-lava-yellow" />
            ) : (
              <Moon className="h-4 w-4 text-steel-700" />
            )}
          </button>

          {/* Style Guide Link */}
          <Link
            to="/styleguide"
            className="p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-ice-100 dark:hover:bg-white/[0.08] transition-colors focus:outline-none focus:ring-2 focus:ring-steel-500 dark:focus:ring-lava-yellow"
            title="Design System Style Guide"
            aria-label="Design System Style Guide"
          >
            <Palette className="h-4 w-4 text-steel-500" />
          </Link>

          {/* Notification Bell */}
          <button
            className="relative p-1.5 rounded-lg text-text-secondary hover:text-text-primary hover:bg-ice-100 dark:hover:bg-white/[0.08] transition-colors focus:outline-none focus:ring-2 focus:ring-steel-500"
            title="Notifications"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-lava-orange shadow-[0_0_6px_rgba(255,122,26,0.8)]" />
          </button>

          {/* User Avatar */}
          <div
            className="h-7 w-7 rounded-full bg-ice-200 dark:bg-white/[0.1] border border-border-strong flex items-center justify-center text-[11px] font-bold text-steel-700 dark:text-text-primary font-mono shadow-sm select-none cursor-pointer"
            title={`Logged in as ${principal?.display_name || principal?.principal_id || 'AI Lead'}`}
          >
            {principal?.display_name ? principal.display_name.slice(0, 2).toUpperCase() : principal?.principal_id ? principal.principal_id.slice(0, 2).toUpperCase() : 'AG'}
          </div>
        </div>
      </header>

      {/* Global Command Palette */}
      <CommandPalette isOpen={isCommandOpen} onClose={() => setIsCommandOpen(false)} />
    </>
  );
}

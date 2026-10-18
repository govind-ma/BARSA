import React, { useState } from 'react';
import { useApp } from '@/app/AppContext';
import { ProjectSwitcher } from './ProjectSwitcher';
import { CommandPalette } from './CommandPalette';
import {
  Sparkles,
  Command,
  Bell,
  Sun,
  Moon,
  Menu,
} from 'lucide-react';

export interface TopBarProps {
  onMenuClick?: () => void;
}

export function TopBar({ onMenuClick }: TopBarProps) {
  const { isBackendOnline, theme, toggleTheme, principal } = useApp();
  const [isCommandOpen, setIsCommandOpen] = useState(false);

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
      <header className="sticky top-0 z-30 h-14 w-full flex items-center justify-between px-4 sm:px-6 bg-card/80 backdrop-blur-xl border-b border-ice/20 shadow-[0_4px_20px_rgba(0,0,0,0.3)]">
        {/* Left: Mobile Menu Toggle + Wordmark */}
        <div className="flex items-center space-x-3">
          <button
            onClick={onMenuClick}
            aria-label="Open mobile menu"
            className="md:hidden p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/70 focus:outline-none focus:ring-1 focus:ring-ice"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex items-center space-x-2 select-none">
            <div className="h-7 w-7 rounded-lg bg-gradient-to-br from-ice/30 to-ice/5 border border-ice/40 flex items-center justify-center shadow-[0_0_12px_rgba(56,189,248,0.3)]">
              <Sparkles className="h-3.5 w-3.5 text-ice" />
            </div>
            <div className="flex items-baseline space-x-1.5">
              <span className="font-extrabold tracking-tight text-sm text-foreground">BARSA</span>
              <span className="hidden sm:inline-block text-[10px] uppercase font-mono tracking-wider text-ice font-semibold">
                Brain
              </span>
            </div>
          </div>
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
            className="hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-secondary/50 hover:bg-secondary/80 border border-ice/15 hover:border-ice/35 text-xs text-muted-foreground hover:text-foreground transition-all duration-150 focus:outline-none focus:ring-1 focus:ring-ice/50"
            title="Open Command Palette (Cmd/Ctrl + K)"
          >
            <Command className="h-3 w-3 text-ice" />
            <span className="text-[11px] font-mono">Cmd+K</span>
          </button>

          {/* Connection Status Badge (Pulsing Chilli Dot when Live) */}
          <div
            className="flex items-center space-x-1.5 px-2.5 py-1 rounded-full bg-secondary/40 border border-ice/10 text-xs font-mono"
            title={isBackendOnline ? 'FalkorDB & FastAPI Engine Online' : 'Backend Engine Offline'}
          >
            {isBackendOnline ? (
              <>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-chilli opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-chilli shadow-[0_0_8px_rgba(239,68,68,0.9)]" />
                </span>
                <span className="text-[11px] font-semibold text-chilli tracking-wide">Live</span>
              </>
            ) : (
              <>
                <span className="h-2 w-2 rounded-full bg-muted-foreground/60" />
                <span className="text-[11px] text-muted-foreground">Offline</span>
              </>
            )}
          </div>

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? <Sun className="h-4 w-4 text-ice" /> : <Moon className="h-4 w-4" />}
          </button>

          {/* Notification Bell */}
          <button
            className="relative p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
            title="Notifications"
          >
            <Bell className="h-4 w-4" />
            <span className="absolute top-1 right-1 h-1.5 w-1.5 rounded-full bg-chilli shadow-[0_0_6px_rgba(239,68,68,0.8)]" />
          </button>

          {/* User Avatar */}
          <div
            className="h-7 w-7 rounded-full bg-gradient-to-tr from-ice/40 to-ice/10 border border-ice/40 flex items-center justify-center text-[11px] font-bold text-ice font-mono shadow-[0_0_8px_rgba(56,189,248,0.25)] select-none cursor-pointer"
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

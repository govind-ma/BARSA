import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import { useApp } from '@/app/AppContext';
import { NewProjectModal } from '@/components/projects/NewProjectModal';
import {
  Search,
  LayoutDashboard,
  CheckSquare,
  GitBranch,
  BrainCircuit,
  BookmarkCheck,
  Plus,
  Copy,
  Check,
  GitPullRequest,
  FileCode,
  Palette,
} from 'lucide-react';

export interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
}

export function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const { projects, activeProject, setActiveProjectId } = useApp();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [isCopied, setIsCopied] = useState(false);
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  // Build items list
  const navActions = [
    { id: 'nav-mc', label: 'Go to Mission Control', icon: LayoutDashboard, category: 'Navigation', action: () => navigate('/') },
    { id: 'nav-tasks', label: 'Go to Tasks', icon: CheckSquare, category: 'Navigation', action: () => navigate('/tasks') },
    { id: 'nav-history', label: 'Go to History / Version Control', icon: GitBranch, category: 'Navigation', action: () => navigate('/version-control') },
    { id: 'nav-memory', label: 'Go to Memory Explorer', icon: BrainCircuit, category: 'Navigation', action: () => navigate('/memory') },
    { id: 'nav-checkpoints', label: 'Go to Checkpoints', icon: BookmarkCheck, category: 'Navigation', action: () => navigate('/checkpoints') },
    { id: 'nav-styleguide', label: 'Open Design System Style Guide', icon: Palette, category: 'Navigation', action: () => navigate('/styleguide') },
  ];

  const quickActions = [
    {
      id: 'act-new-project',
      label: 'Create New Project',
      icon: Plus,
      category: 'Actions',
      action: () => {
        onClose();
        setIsNewProjectOpen(true);
      },
    },
    {
      id: 'act-new-decision',
      label: 'Record Architectural Decision (ADR)',
      icon: Plus,
      category: 'Actions',
      action: () => {
        onClose();
        navigate('/memory');
      },
    },
    {
      id: 'act-create-branch',
      label: 'Create New Memory Branch',
      icon: GitPullRequest,
      category: 'Actions',
      action: () => {
        onClose();
        navigate('/version-control');
      },
    },
    {
      id: 'act-copy-prompt',
      label: 'Copy Handover Prompt for ChatGPT / Claude',
      icon: isCopied ? Check : Copy,
      category: 'Actions',
      action: () => {
        const text = `Connect to BARSA memory for project "${activeProject?.name || 'Project ATLAS'}" (${activeProject?.project_id || 'proj-atlas'}). Retrieve the latest checkpoint and identify the next task.`;
        navigator.clipboard.writeText(text);
        setIsCopied(true);
        setTimeout(() => setIsCopied(false), 2000);
      },
    },
  ];

  const projectItems = projects.map((p) => ({
    id: `proj-${p.project_id}`,
    label: `Switch to ${p.name}`,
    icon: FileCode,
    category: 'Projects',
    action: () => {
      setActiveProjectId(p.project_id);
      onClose();
      navigate('/');
    },
  }));

  const allItems = [...navActions, ...quickActions, ...projectItems];

  const filtered = allItems.filter((item) =>
    item.label.toLowerCase().includes(query.toLowerCase()) ||
    item.category.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % (filtered.length || 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + (filtered.length || 1)) % (filtered.length || 1));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
        if (filtered[selectedIndex].id !== 'act-copy-prompt') {
          onClose();
        }
      }
    } else if (e.key === 'Escape') {
      onClose();
    }
  };

  return (
    <>
      {createPortal(
        <div
          className="fixed inset-0 z-modal flex items-start justify-center pt-20 p-4 modal-scrim animate-in fade-in duration-150 select-none"
          onClick={onClose}
        >
          <div
            className="relative w-full max-w-xl rounded-xl solid-floating-surface overflow-hidden animate-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
            onKeyDown={handleKeyDown}
          >
          {/* Search Header */}
          <div className="flex items-center px-4 py-3.5 border-b border-border-subtle bg-surface">
            <Search className="h-4 w-4 text-steel-500 shrink-0 mr-3" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
              placeholder="Search projects, navigation, or run actions..."
              className="w-full bg-transparent text-sm text-text-primary placeholder:text-text-muted focus:outline-none"
            />
            <kbd className="hidden sm:inline-flex items-center px-2 py-0.5 text-[10px] font-mono text-text-muted bg-ice-100 dark:bg-white/[0.08] border border-border-subtle rounded">
              ESC
            </kbd>
          </div>

          {/* Results List */}
          <div className="max-h-80 overflow-y-auto p-2 space-y-1">
            {filtered.length === 0 ? (
              <div className="py-8 text-center text-xs text-text-muted">
                No commands or projects match "{query}"
              </div>
            ) : (
              filtered.map((item, idx) => {
                const Icon = item.icon;
                const isSelected = idx === selectedIndex;

                return (
                  <button
                    key={item.id}
                    onClick={() => {
                      item.action();
                      if (item.id !== 'act-copy-prompt') onClose();
                    }}
                    onMouseEnter={() => setSelectedIndex(idx)}
                    className={`w-full flex items-center justify-between px-3 py-2 rounded-lg text-xs transition-colors text-left ${
                      isSelected
                        ? 'bg-ice-100 dark:bg-white/[0.08] text-text-primary font-semibold border border-border-subtle'
                        : 'text-text-secondary hover:bg-ice-100/60 hover:text-text-primary border border-transparent'
                    }`}
                  >
                    <div className="flex items-center space-x-2.5 truncate">
                      <Icon className={`h-4 w-4 shrink-0 ${isSelected ? 'text-lava-orange' : 'text-steel-500'}`} />
                      <span className="truncate">{item.label}</span>
                    </div>
                    <span className="text-[10px] font-mono text-text-muted shrink-0 ml-2">
                      {item.category}
                    </span>
                  </button>
                );
              })
            )}
          </div>

          {/* Footer Guide */}
          <div className="px-4 py-2 border-t border-border-subtle bg-surface/50 flex items-center justify-between text-[11px] text-text-muted font-mono">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          </div>
        </div>,
        document.body
      )}

      <NewProjectModal
        isOpen={isNewProjectOpen}
        onClose={() => setIsNewProjectOpen(false)}
      />
    </>
  );
}

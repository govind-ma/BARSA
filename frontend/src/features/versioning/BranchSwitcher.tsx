import { useState, useRef, useEffect } from 'react';
import { GitBranch, ChevronDown, Search, Check, Plus } from 'lucide-react';
import type { Branch } from '@/types';

interface BranchSwitcherProps {
  branches: Branch[];
  activeBranch: Branch | null;
  onSelectBranch: (branch: Branch) => void;
  onCreateBranchClick: () => void;
}

export function BranchSwitcher({
  branches,
  activeBranch,
  onSelectBranch,
  onCreateBranchClick,
}: BranchSwitcherProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const popoverRef = useRef<HTMLDivElement>(null);

  // Close on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen]);

  const filteredBranches = branches.filter((b) =>
    b.name.toLowerCase().includes(search.toLowerCase())
  );

  const currentBranchName = activeBranch?.name || 'main';

  return (
    <div className="relative select-none" ref={popoverRef}>
      {/* Switcher Button */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-card/80 hover:bg-card border border-ice/25 hover:border-ice/45 text-foreground text-xs font-medium shadow-sm transition-all"
        title="Switch active branch"
      >
        <GitBranch className="h-3.5 w-3.5 text-ice" />
        <span className="font-mono font-bold text-ice truncate max-w-[140px]">
          {currentBranchName}
        </span>
        <ChevronDown
          className={`h-3 w-3 text-muted-foreground transition-transform duration-150 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Frosted Glass Dropdown Popover */}
      {isOpen && (
        <div className="absolute left-0 top-full mt-2 w-72 p-2.5 rounded-2xl bg-card/95 border border-ice/25 backdrop-blur-xl shadow-[0_12px_36px_rgba(0,0,0,0.6)] z-50 animate-page-enter">
          {/* Search Input */}
          <div className="relative mb-2">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search branches..."
              className="w-full pl-8 pr-2.5 py-1.5 bg-secondary/50 border border-ice/15 rounded-lg text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:border-ice/40"
              autoFocus
            />
          </div>

          {/* Branch List */}
          <div className="max-h-56 overflow-y-auto space-y-1 pr-1">
            {filteredBranches.length === 0 ? (
              <div className="py-4 text-center text-xs text-muted-foreground">
                No branches found
              </div>
            ) : (
              filteredBranches.map((b) => {
                const isSelected = b.name === currentBranchName;
                return (
                  <button
                    key={b.name}
                    onClick={() => {
                      onSelectBranch(b);
                      setIsOpen(false);
                    }}
                    className={`w-full flex items-center justify-between p-2 rounded-xl text-xs font-mono transition-all ${
                      isSelected
                        ? 'bg-ice/15 text-ice border border-ice/30 font-bold'
                        : 'text-foreground hover:bg-secondary/60 hover:text-ice'
                    }`}
                  >
                    <div className="flex items-center space-x-2 truncate">
                      <GitBranch
                        className={`h-3.5 w-3.5 shrink-0 ${
                          isSelected ? 'text-ice' : 'text-muted-foreground'
                        }`}
                      />
                      <span className="truncate">{b.name}</span>
                      {b.is_default && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded bg-secondary text-muted-foreground font-sans">
                          default
                        </span>
                      )}
                    </div>
                    {isSelected && <Check className="h-3.5 w-3.5 text-ice shrink-0" />}
                  </button>
                );
              })
            )}
          </div>

          {/* Quick Create Action at Bottom */}
          <div className="pt-2 mt-2 border-t border-border/60">
            <button
              onClick={() => {
                setIsOpen(false);
                onCreateBranchClick();
              }}
              className="w-full flex items-center justify-center space-x-1.5 py-1.5 rounded-lg text-xs font-medium text-ice hover:bg-ice/10 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Create new branch from HEAD</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

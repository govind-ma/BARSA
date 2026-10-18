import {
  Bot,
  User,
  Clock,
  Check,
} from 'lucide-react';
import type { Commit } from '@/types';
import { formatDate, truncate } from '@/lib/utils';

interface CommitDAGProps {
  commits: Commit[];
  selectedCommit: Commit | null;
  diffSelection: Commit[];
  onSelectCommit: (commit: Commit) => void;
  onToggleDiffSelect: (commit: Commit) => void;
}

export function CommitDAG({
  commits,
  selectedCommit,
  diffSelection,
  onSelectCommit,
  onToggleDiffSelect,
}: CommitDAGProps) {
  // Height per commit row
  const rowHeight = 90;
  const totalHeight = Math.max(400, commits.length * rowHeight + 60);

  return (
    <div className="relative w-full overflow-x-auto select-none">
      {/* SVG Container for Curved Branch Lines */}
      <svg
        className="absolute left-0 top-0 w-24 h-full pointer-events-none z-0"
        style={{ height: `${totalHeight}px` }}
      >
        <defs>
          <linearGradient id="dagLineGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#6F8FA8" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#B3CDE0" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#CFE0EC" stopOpacity="0.2" />
          </linearGradient>

          <linearGradient id="mergeLineGradient" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#FF7A1A" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#6F8FA8" stopOpacity="0.6" />
          </linearGradient>
        </defs>

        {commits.map((c, i) => {
          const curY = 44 + i * rowHeight;
          const nextY = 44 + (i + 1) * rowHeight;
          const isMerge = c.parent_hashes && c.parent_hashes.length > 1;

          return (
            <g key={`dag-line-${c.commit_hash}`}>
              {/* Vertical line to next commit */}
              {i < commits.length - 1 && (
                <path
                  d={`M 28 ${curY} C 28 ${(curY + nextY) / 2}, 28 ${(curY + nextY) / 2}, 28 ${nextY}`}
                  fill="none"
                  stroke="url(#dagLineGradient)"
                  strokeWidth="2.5"
                  className="transition-all duration-300"
                />
              )}

              {/* Converging Merge Curve if multi-parent */}
              {isMerge && (
                <path
                  d={`M 60 ${curY - 35} C 60 ${curY - 10}, 28 ${curY - 15}, 28 ${curY}`}
                  fill="none"
                  stroke="url(#mergeLineGradient)"
                  strokeWidth="2"
                  strokeDasharray="4,2"
                  className="transition-all duration-300"
                />
              )}
            </g>
          );
        })}
      </svg>

      {/* Vertical List of Commit Node Rows with 40ms Stagger */}
      <div className="relative z-10 space-y-3 pl-16 pr-2">
        {commits.map((c, idx) => {
          const isAgent = !/human|owner|developer|user|alice/i.test(c.author.name);
          const isMerge = c.parent_hashes && c.parent_hashes.length > 1;
          const isCardSelected = selectedCommit?.commit_hash === c.commit_hash;
          const isDiffSelected = diffSelection.some(
            (dc) => dc.commit_hash === c.commit_hash
          );

          return (
            <div
              key={c.commit_hash}
              style={{ animationDelay: `${idx * 40}ms` }}
              className="relative flex items-center animate-page-enter group"
            >
              {/* Node Dot positioned exactly on the SVG line at x=28 */}
              <div
                className={`absolute -left-[50px] h-5 w-5 rounded-full border-2 transition-all flex items-center justify-center bg-surface ${
                  isMerge
                    ? 'border-lava-orange shadow-[0_0_8px_rgba(255,122,26,0.7)]'
                    : isDiffSelected
                    ? 'border-lava-yellow ring-4 ring-lava-yellow/20'
                    : 'border-steel-500 shadow-sm'
                }`}
              >
                <div
                  className={`h-2 w-2 rounded-full ${
                    isMerge ? 'bg-lava-orange' : isDiffSelected ? 'bg-lava-yellow' : 'bg-steel-500'
                  }`}
                />
              </div>

              {/* Commit Card */}
              <div
                onClick={() => onSelectCommit(c)}
                className={`w-full p-3.5 rounded-lg border transition-all cursor-pointer ${
                  isCardSelected
                    ? 'bg-surface border-border-strong shadow-md ring-1 ring-steel-500/30'
                    : 'bg-surface/80 hover:bg-surface border-border-subtle hover:border-border-strong hover:-translate-y-0.5 shadow-sm'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Short SHA-256 Hash in mono */}
                    <span className="font-mono text-xs font-bold text-text-primary px-2 py-0.5 rounded bg-ice-100 dark:bg-white/[0.08] border border-border-subtle">
                      {truncate(c.commit_hash, 8)}
                    </span>

                    {/* Author Badge (Agent in ember pill, Human in ice pill) */}
                    <div
                      className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-mono font-medium ${
                        isAgent
                          ? 'bg-lava-yellow/15 text-lava-orange dark:text-lava-yellow border-lava-yellow/30'
                          : 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border-border-subtle'
                      }`}
                    >
                      {isAgent ? (
                        <Bot className="h-3 w-3 text-lava-orange" />
                      ) : (
                        <User className="h-3 w-3 text-steel-500" />
                      )}
                      <span>Author: {c.author.name}</span>
                    </div>

                    {isMerge && (
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-lava-orange/15 text-lava-orange border border-lava-orange/30 font-bold">
                        Merge
                      </span>
                    )}
                  </div>

                  {/* Diff select checkbox button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleDiffSelect(c);
                    }}
                    title={
                      isDiffSelected
                        ? 'Deselect from diff'
                        : 'Select commit for side-by-side diff'
                    }
                    className={`inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-mono transition-colors ${
                      isDiffSelected
                        ? 'bg-lava-orange text-white font-semibold'
                        : 'bg-ice-100 dark:bg-white/[0.06] text-text-muted hover:text-text-primary hover:bg-ice-200'
                    }`}
                  >
                    {isDiffSelected ? (
                      <>
                        <Check className="h-3 w-3" />
                        <span>Diff Selected</span>
                      </>
                    ) : (
                      <span>+ Select for diff</span>
                    )}
                  </button>
                </div>

                {/* Commit Message */}
                <p className="font-heading text-xs font-medium text-text-primary leading-relaxed line-clamp-2">
                  {c.message}
                </p>

                {/* Footer: Timestamp and parent hashes */}
                <div className="mt-2 pt-2 border-t border-border-subtle flex flex-wrap items-center justify-between text-[10px] text-text-muted font-mono">
                  <div className="flex items-center space-x-1">
                    <Clock className="h-3 w-3 text-steel-500" />
                    <span>{formatDate(c.timestamp)}</span>
                  </div>

                  {c.parent_hashes && c.parent_hashes.length > 0 && (
                    <div className="flex items-center space-x-1">
                      <span>parents:</span>
                      {c.parent_hashes.map((ph, pIdx) => (
                        <span key={pIdx} className="underline text-text-secondary">
                          {truncate(ph, 6)}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

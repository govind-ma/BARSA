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
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.8" />
            <stop offset="50%" stopColor="#38bdf8" stopOpacity="0.5" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.2" />
          </linearGradient>

          <linearGradient id="mergeLineGradient" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#ef4444" stopOpacity="0.7" />
            <stop offset="100%" stopColor="#38bdf8" stopOpacity="0.6" />
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
                className={`absolute -left-[50px] h-5 w-5 rounded-full border-2 transition-all flex items-center justify-center ${
                  isMerge
                    ? 'border-chilli bg-background shadow-[0_0_10px_rgba(239,68,68,0.7)]'
                    : isDiffSelected
                    ? 'border-emerald-400 bg-background ring-4 ring-emerald-400/20'
                    : 'border-ice bg-background shadow-[0_0_8px_rgba(56,189,248,0.7)]'
                }`}
              >
                <div
                  className={`h-2 w-2 rounded-full ${
                    isMerge ? 'bg-chilli' : isDiffSelected ? 'bg-emerald-400' : 'bg-ice'
                  }`}
                />
              </div>

              {/* Commit Card */}
              <div
                onClick={() => onSelectCommit(c)}
                className={`w-full p-3.5 rounded-2xl border transition-all cursor-pointer ${
                  isCardSelected
                    ? 'bg-card/95 border-ice/50 shadow-[0_0_20px_rgba(56,189,248,0.2)]'
                    : 'bg-card/65 hover:bg-card/90 border-border/70 hover:border-ice/30 shadow-sm'
                }`}
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    {/* Short SHA-256 Hash in mono */}
                    <span className="font-mono text-xs font-bold text-ice px-2 py-0.5 rounded bg-ice/10 border border-ice/25">
                      {truncate(c.commit_hash, 8)}
                    </span>

                    {/* Author Badge (Agent in ember pill, Human in ice pill) */}
                    <div
                      className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-mono font-medium ${
                        isAgent
                          ? 'bg-amber-500/15 text-amber-300 border-amber-500/35'
                          : 'bg-ice/15 text-ice border-ice/35'
                      }`}
                    >
                      {isAgent ? (
                        <Bot className="h-3 w-3 text-amber-400" />
                      ) : (
                        <User className="h-3 w-3 text-ice" />
                      )}
                      <span>Author: {c.author.name}</span>
                    </div>

                    {isMerge && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-chilli/15 border border-chilli/30 text-chilli font-bold">
                        Merge Commit
                      </span>
                    )}
                  </div>

                  {/* Right: Timestamp & Diff Selection Checkbox */}
                  <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                    <span className="flex items-center space-x-1 font-mono text-[11px]">
                      <Clock className="h-3 w-3" />
                      <span>{formatDate(c.timestamp)}</span>
                    </span>

                    {/* Diff selection checkbox */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onToggleDiffSelect(c);
                      }}
                      title={
                        isDiffSelected
                          ? 'Deselect for diff comparison'
                          : 'Select for 2-commit split diff'
                      }
                      className={`px-2 py-0.5 rounded-md font-mono text-[10px] border transition-all flex items-center space-x-1 ${
                        isDiffSelected
                          ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 font-bold'
                          : 'bg-secondary/60 text-muted-foreground border-border hover:text-ice hover:border-ice/30'
                      }`}
                    >
                      {isDiffSelected && <Check className="h-2.5 w-2.5 text-emerald-400" />}
                      <span>{isDiffSelected ? 'Diff Selected' : 'Select for Diff'}</span>
                    </button>
                  </div>
                </div>

                {/* Commit Message */}
                <p className="text-xs text-foreground font-medium leading-relaxed">
                  {c.message}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

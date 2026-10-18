import { useRef } from 'react';
import { X, GitCommit, ArrowRight } from 'lucide-react';
import type { Commit, StructuredDiff } from '@/types';
import { truncate } from '@/lib/utils';

interface SplitDiffViewerProps {
  isOpen: boolean;
  onClose: () => void;
  baseCommit: Commit | null;
  targetCommit: Commit | null;
  diffData: StructuredDiff | null;
  onCopyDiff?: () => void;
}

export function SplitDiffViewer({
  isOpen,
  onClose,
  baseCommit,
  targetCommit,
  diffData,
}: SplitDiffViewerProps) {
  const leftScrollRef = useRef<HTMLDivElement>(null);
  const rightScrollRef = useRef<HTMLDivElement>(null);
  const isSyncingScroll = useRef(false);

  if (!isOpen) return null;

  // Synced scroll between before_state and after_state
  const handleScroll = (source: 'left' | 'right') => {
    if (isSyncingScroll.current) return;
    isSyncingScroll.current = true;

    const sourceEl = source === 'left' ? leftScrollRef.current : rightScrollRef.current;
    const targetEl = source === 'left' ? rightScrollRef.current : leftScrollRef.current;

    if (sourceEl && targetEl) {
      targetEl.scrollTop = sourceEl.scrollTop;
    }

    setTimeout(() => {
      isSyncingScroll.current = false;
    }, 10);
  };

  // Construct mock line diffs if structured diff is present or simulated
  const diffEntries = diffData?.changed_records
    ? Object.entries(diffData.changed_records)
    : [
        [
          'rec_bms_100',
          {
            operation: 'update',
            fields: {
              summary: {
                old: 'Initial draft for SQLite local memory engine',
                new: 'Adopted embedded SQLite WAL mode with zero-cloud guarantee',
              },
              verification_status: {
                old: 'unverified',
                new: 'verified',
              },
              revision: {
                old: '1',
                new: '2',
              },
            },
          },
        ],
      ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md animate-page-enter select-none">
      <div className="w-full max-w-5xl h-[85vh] bg-card border border-ice/25 rounded-2xl flex flex-col shadow-[0_0_60px_rgba(0,0,0,0.85)] overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-ice/15 bg-background/80 flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-2.5">
              <span className="text-xs font-mono font-bold text-ice px-2 py-0.5 rounded bg-ice/15 border border-ice/30">
                Split Diff Viewer
              </span>
              <h3 className="text-sm font-bold text-foreground">
                Structured Diff Against Parent
              </h3>
            </div>
            <div className="flex items-center space-x-2 text-xs text-muted-foreground font-mono mt-1">
              <span>before: {truncate(baseCommit?.commit_hash || 'root', 10)}</span>
              <ArrowRight className="h-3 w-3 text-ice" />
              <span>after: {truncate(targetCommit?.commit_hash || 'head', 10)}</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Column Headers */}
        <div className="grid grid-cols-2 border-b border-border/80 text-xs font-mono font-bold">
          <div className="p-2.5 px-4 bg-secondary/40 text-muted-foreground border-r border-border/80 flex items-center justify-between">
            <span>BEFORE STATE (Parent / Base)</span>
            <span className="text-[10px] text-chilli">- Removed Lines</span>
          </div>
          <div className="p-2.5 px-4 bg-secondary/40 text-muted-foreground flex items-center justify-between">
            <span>AFTER STATE (Target / Commit)</span>
            <span className="text-[10px] text-emerald-400">+ Added Lines</span>
          </div>
        </div>

        {/* Synced Scroll Split View */}
        <div className="flex-1 grid grid-cols-2 overflow-hidden font-mono text-xs">
          {/* Left: Before State (Chilli tint on removed) */}
          <div
            ref={leftScrollRef}
            onScroll={() => handleScroll('left')}
            className="overflow-y-auto p-4 space-y-4 border-r border-border/80 bg-[#090d14]"
          >
            {diffEntries.map(([recordId, rec]: any) => (
              <div key={`left-${recordId}`} className="space-y-1.5">
                <div className="text-[11px] font-bold text-muted-foreground flex items-center space-x-1.5 pb-1 border-b border-border/40">
                  <GitCommit className="h-3 w-3 text-ice" />
                  <span>{recordId}</span>
                  <span className="text-[9px] uppercase px-1.5 rounded bg-secondary text-muted-foreground">
                    {rec.operation || 'modified'}
                  </span>
                </div>

                {rec.fields &&
                  Object.entries(rec.fields).map(([field, vals]: any) => (
                    <div key={`old-${field}`} className="space-y-0.5">
                      <span className="text-[10px] text-muted-foreground block">{field}:</span>
                      <div className="p-2 rounded-lg bg-chilli/15 border-l-2 border-chilli text-chilli text-[11px] leading-relaxed">
                        - {vals.old ? String(vals.old) : '(null / empty)'}
                      </div>
                    </div>
                  ))}
              </div>
            ))}
          </div>

          {/* Right: After State (Ice-tinted Green on added) */}
          <div
            ref={rightScrollRef}
            onScroll={() => handleScroll('right')}
            className="overflow-y-auto p-4 space-y-4 bg-[#090d14]"
          >
            {diffEntries.map(([recordId, rec]: any) => (
              <div key={`right-${recordId}`} className="space-y-1.5">
                <div className="text-[11px] font-bold text-ice flex items-center space-x-1.5 pb-1 border-b border-border/40">
                  <GitCommit className="h-3 w-3 text-emerald-400" />
                  <span>{recordId}</span>
                  <span className="text-[9px] uppercase px-1.5 rounded bg-emerald-500/20 text-emerald-300">
                    {rec.operation || 'modified'}
                  </span>
                </div>

                {rec.fields &&
                  Object.entries(rec.fields).map(([field, vals]: any) => (
                    <div key={`new-${field}`} className="space-y-0.5">
                      <span className="text-[10px] text-muted-foreground block">{field}:</span>
                      <div className="p-2 rounded-lg bg-emerald-500/15 border-l-2 border-emerald-400 text-emerald-300 text-[11px] leading-relaxed">
                        + {vals.new ? String(vals.new) : '(null / deleted)'}
                      </div>
                    </div>
                  ))}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-border/80 bg-background/80 flex items-center justify-between text-xs">
          <span className="text-muted-foreground font-mono text-[11px]">
            Synced side-by-side view • BMS Record Revisions
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-secondary hover:bg-secondary/80 text-foreground font-medium"
          >
            Close Diff
          </button>
        </div>
      </div>
    </div>
  );
}

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-page-enter select-none">
      <div className="w-full max-w-5xl h-[85vh] bg-surface border border-border-subtle rounded-xl flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-border-subtle bg-surface/90 flex items-center justify-between">
          <div>
            <div className="flex items-center space-x-2.5">
              <span className="text-xs font-mono font-bold text-text-primary px-2.5 py-0.5 rounded bg-ice-100 dark:bg-white/[0.08] border border-border-subtle">
                Split Diff Viewer
              </span>
              <h3 className="font-heading text-sm font-semibold text-text-primary">
                Structured Diff Against Parent
              </h3>
            </div>
            <div className="flex items-center space-x-2 text-xs text-text-muted font-mono mt-1">
              <span>before: {truncate(baseCommit?.commit_hash || 'root', 10)}</span>
              <ArrowRight className="h-3 w-3 text-steel-500" />
              <span>after: {truncate(targetCommit?.commit_hash || 'head', 10)}</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-ice-100 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Column Headers */}
        <div className="grid grid-cols-2 border-b border-border-subtle text-xs font-mono font-bold">
          <div className="p-2.5 px-4 bg-ice-100/50 dark:bg-white/[0.04] text-text-secondary border-r border-border-subtle flex items-center justify-between">
            <span>BEFORE STATE (Parent / Base)</span>
            <span className="text-[10px] text-lava-red">- Removed Lines</span>
          </div>
          <div className="p-2.5 px-4 bg-ice-100/50 dark:bg-white/[0.04] text-text-secondary flex items-center justify-between">
            <span>AFTER STATE (Target / Commit)</span>
            <span className="text-[10px] text-emerald-600 dark:text-emerald-400">+ Added Lines</span>
          </div>
        </div>

        {/* Synced Scroll Split View */}
        <div className="flex-1 grid grid-cols-2 overflow-hidden font-mono text-xs">
          {/* Left: Before State (Lava-red tint on removed lines) */}
          <div
            ref={leftScrollRef}
            onScroll={() => handleScroll('left')}
            className="overflow-y-auto p-4 space-y-4 border-r border-border-subtle bg-bg-base"
          >
            {diffEntries.map(([recordId, rec]: any) => (
              <div key={`left-${recordId}`} className="space-y-1.5">
                <div className="text-[11px] font-bold text-text-secondary flex items-center space-x-1.5 pb-1 border-b border-border-subtle">
                  <GitCommit className="h-3 w-3 text-steel-500" />
                  <span>{recordId}</span>
                  <span className="text-[9px] uppercase px-1.5 rounded bg-ice-100 text-text-muted">
                    {rec.operation || 'modified'}
                  </span>
                </div>

                {rec.fields &&
                  Object.entries(rec.fields).map(([field, vals]: any) => (
                    <div key={`old-${field}`} className="space-y-0.5">
                      <span className="text-[10px] text-text-muted block">{field}:</span>
                      <div className="p-2 rounded-lg bg-lava-red/10 border-l-2 border-lava-red text-lava-red text-[11px] leading-relaxed">
                        - {vals.old ? String(vals.old) : '(null / empty)'}
                      </div>
                    </div>
                  ))}
              </div>
            ))}
          </div>

          {/* Right: After State (Ice-tinted green on added lines) */}
          <div
            ref={rightScrollRef}
            onScroll={() => handleScroll('right')}
            className="overflow-y-auto p-4 space-y-4 bg-bg-base"
          >
            {diffEntries.map(([recordId, rec]: any) => (
              <div key={`right-${recordId}`} className="space-y-1.5">
                <div className="text-[11px] font-bold text-text-secondary flex items-center space-x-1.5 pb-1 border-b border-border-subtle">
                  <GitCommit className="h-3 w-3 text-steel-500" />
                  <span>{recordId}</span>
                  <span className="text-[9px] uppercase px-1.5 rounded bg-ice-100 text-text-muted">
                    {rec.operation || 'modified'}
                  </span>
                </div>

                {rec.fields &&
                  Object.entries(rec.fields).map(([field, vals]: any) => (
                    <div key={`new-${field}`} className="space-y-0.5">
                      <span className="text-[10px] text-text-muted block">{field}:</span>
                      <div className="p-2 rounded-lg bg-emerald-500/10 border-l-2 border-emerald-500 text-emerald-700 dark:text-emerald-400 text-[11px] leading-relaxed">
                        + {vals.new ? String(vals.new) : '(null / empty)'}
                      </div>
                    </div>
                  ))}
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-border-subtle bg-surface/90 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs rounded-lg btn-secondary-ice font-medium"
          >
            Close Diff View
          </button>
        </div>
      </div>
    </div>
  );
}

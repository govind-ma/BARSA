import { useState } from 'react';
import {
  CheckCircle2,
  Clock,
  ArrowRight,
  GitCommit,
  Bot,
  User,
  Copy,
  Check,
  ChevronDown,
  ChevronUp,
  RotateCcw,
  AlertCircle,
} from 'lucide-react';
import type { BMSRecord } from '@/types';
import { formatDate, truncate } from '@/lib/utils';
import { CrystalBurst } from './CrystalBurst';

interface CheckpointCardProps {
  checkpoint: BMSRecord;
  index: number;
  totalCount: number;
  isLatest: boolean;
  isActiveForResume: boolean;
  onResumeFromHere: (cp: BMSRecord) => Promise<void>;
  onCopyPrompt: (cp: BMSRecord) => void;
  isCopied: boolean;
}

export function CheckpointCard({
  checkpoint,
  index,
  totalCount,
  isLatest,
  isActiveForResume,
  onResumeFromHere,
  onCopyPrompt,
  isCopied,
}: CheckpointCardProps) {
  // Expand latest by default, others can be collapsed/expanded
  const [isExpanded, setIsExpanded] = useState(true);
  const [showConfirmPopover, setShowConfirmPopover] = useState(false);
  const [isResuming, setIsResuming] = useState(false);
  const [showBurst, setShowBurst] = useState(false);

  // Normalize ID (e.g., CP-001 format)
  const rawId = checkpoint.record_id || (checkpoint as any).id || '';
  const formattedId = rawId.startsWith('rec_')
    ? `CP-${String(totalCount - index).padStart(3, '0')}`
    : rawId.toUpperCase();

  // Extract author
  const authorName =
    checkpoint.author ||
    (checkpoint.attributes as any)?.created_by ||
    (checkpoint as any).created_by ||
    'claude-backend';

  const isAiAgent = !authorName.toLowerCase().includes('human') && !authorName.toLowerCase().includes('user');

  // Base revision / commit
  const baseRevision = String(
    (checkpoint.attributes as any)?.base_revision ||
      (checkpoint.attributes as any)?.commit_hash ||
      (checkpoint as any).base_revision ||
      'rev_root'
  );

  // Completed & Pending actions
  const completedActions: string[] = Array.isArray((checkpoint.attributes as any)?.completed_actions)
    ? (checkpoint.attributes as any).completed_actions
    : Array.isArray((checkpoint as any).completed_actions)
    ? (checkpoint as any).completed_actions
    : [];

  const pendingActions: string[] = Array.isArray((checkpoint.attributes as any)?.pending_actions)
    ? (checkpoint.attributes as any).pending_actions
    : Array.isArray((checkpoint as any).pending_actions)
    ? (checkpoint as any).pending_actions
    : [];

  // Next action
  const nextAction =
    (checkpoint.attributes as any)?.next_action ||
    (checkpoint as any).next_action ||
    (typeof checkpoint.content === 'string' && checkpoint.content.length > 0 ? checkpoint.content : null) ||
    'Verify architectural state and execute pending integration tests.';

  const handleConfirmResume = async () => {
    setIsResuming(true);
    try {
      await onResumeFromHere(checkpoint);
      setShowConfirmPopover(false);
      setShowBurst(true);
    } finally {
      setIsResuming(false);
    }
  };

  return (
    <div
      className={`relative rounded-xl border transition-all duration-300 select-none ${
        isLatest
          ? 'p-6 bg-surface border-border-strong shadow-lg ring-1 ring-steel-500/20'
          : 'p-4 bg-surface/85 hover:bg-surface border-border-subtle hover:border-border-strong shadow-sm'
      }`}
    >
      {/* Crystal Burst Animation on activation */}
      {showBurst && <CrystalBurst onComplete={() => setShowBurst(false)} />}

      {/* Timeline Dot on the left line */}
      <div
        className={`absolute -left-[31px] top-6 rounded-full bg-bg-base border-2 flex items-center justify-center transition-all ${
          isActiveForResume
            ? 'h-5 w-5 -left-[33px] border-lava-orange shadow-[0_0_12px_rgba(255,122,26,0.9)]'
            : isLatest
            ? 'h-4.5 w-4.5 -left-[32px] border-steel-500 shadow-sm'
            : 'h-3.5 w-3.5 border-steel-500/60 shadow-xs'
        }`}
      >
        <div
          className={`rounded-full ${
            isActiveForResume
              ? 'h-2 w-2 bg-lava-orange animate-ping'
              : isLatest
              ? 'h-2 w-2 bg-steel-500'
              : 'h-1.5 w-1.5 bg-steel-500/70'
          }`}
        />
      </div>

      {/* Top Card Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-border-subtle pb-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Checkpoint ID in Mono */}
          <span className="font-mono text-xs font-bold text-text-primary px-2.5 py-1 rounded-md bg-ice-100 dark:bg-white/[0.08] border border-border-subtle shadow-xs">
            {formattedId}
          </span>

          {/* Author Badge */}
          <div
            className={`inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-full border text-[11px] font-mono font-medium ${
              isAiAgent
                ? 'bg-lava-yellow/15 text-lava-orange dark:text-lava-yellow border-lava-yellow/30'
                : 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border-border-subtle'
            }`}
          >
            {isAiAgent ? <Bot className="h-3 w-3 text-lava-orange" /> : <User className="h-3 w-3 text-steel-500" />}
            <span>{authorName}</span>
          </div>

          {/* Base Commit Hash */}
          <div className="flex items-center space-x-1 font-mono text-[11px] text-text-muted px-2 py-0.5 rounded bg-surface/60 border border-border-subtle">
            <GitCommit className="h-3 w-3 text-steel-500" />
            <span>base:{truncate(baseRevision, 8)}</span>
          </div>

          {/* "Active for resume" Pill */}
          {isActiveForResume && (
            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-lava-orange/15 text-lava-orange border border-lava-orange/30 text-[10px] font-mono font-bold animate-pulse">
              Active for resume
            </span>
          )}

          {/* Latest Milestone Indicator */}
          {isLatest && !isActiveForResume && (
            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border border-border-subtle text-[10px] font-mono font-semibold">
              Latest Snapshot
            </span>
          )}
        </div>

        {/* Right side: Time & Expand/Collapse toggle */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-1 text-[11px] text-text-muted font-mono">
            <Clock className="h-3 w-3 text-steel-500" />
            <span>{formatDate(checkpoint.created_at)}</span>
          </div>

          <button
            onClick={() => setIsExpanded((prev) => !prev)}
            className="p-1 rounded-md text-text-muted hover:text-text-primary hover:bg-ice-100 transition-colors"
            title={isExpanded ? 'Collapse card' : 'Expand card'}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Expandable Body */}
      {isExpanded && (
        <div className="pt-3.5 space-y-3.5 animate-page-enter">
          {/* Title & Summary */}
          <div>
            <h3 className="font-heading text-sm font-semibold text-text-primary leading-snug">
              {checkpoint.title || 'Milestone State Snapshot'}
            </h3>
            {checkpoint.summary && (
              <p className="text-xs text-text-secondary mt-1 leading-relaxed">
                {checkpoint.summary}
              </p>
            )}
          </div>

          {/* 1. Next Action Callout (prominent left border in --magma) */}
          <div className="next-action-callout p-3.5 rounded-r-lg bg-surface border-y border-r border-border-subtle shadow-sm space-y-1">
            <div className="flex items-center space-x-1.5 text-[10px] font-mono font-bold uppercase text-lava-orange tracking-wider">
              <ArrowRight className="h-3.5 w-3.5 text-lava-orange" />
              <span>Next Continuation Action:</span>
            </div>
            <p className="font-heading text-xs font-semibold text-text-primary leading-relaxed pl-5">
              {String(nextAction)}
            </p>
          </div>

          {/* 2. Completed Actions (Ice-tinted Check Chips) */}
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-mono font-bold text-text-muted tracking-wider block">
              Completed Actions ({completedActions.length})
            </span>
            {completedActions.length === 0 ? (
              <p className="text-xs text-text-muted italic pl-1">
                No individual action items flagged as complete for this milestone.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {completedActions.map((action, aIdx) => (
                  <span
                    key={aIdx}
                    className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border border-border-subtle text-xs font-medium shadow-xs"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 text-steel-500 shrink-0" />
                    <span>{action}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 3. Pending Actions (Muted Outlined Chips) */}
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-mono font-bold text-text-muted tracking-wider block">
              Pending Actions ({pendingActions.length})
            </span>
            {pendingActions.length === 0 ? (
              <p className="text-xs text-text-muted italic pl-1">
                All scheduled tasks completed prior to snapshot.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {pendingActions.map((action, pIdx) => (
                  <span
                    key={pIdx}
                    className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-md bg-surface/60 text-text-muted hover:text-text-primary border border-border-subtle text-xs font-medium transition-colors"
                  >
                    <Clock className="h-3.5 w-3.5 text-steel-500/70 shrink-0" />
                    <span>{action}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 4. Action Buttons Bar: "Resume from here" (Primary Magma) & "Copy handover prompt" (Secondary Ice) */}
          <div className="pt-3 border-t border-border-subtle flex flex-wrap items-center justify-between gap-2.5">
            <div className="font-mono text-[10px] text-text-muted">
              Internal UID: {rawId}
            </div>

            <div className="flex items-center space-x-2 relative">
              {/* Secondary Button: "Copy handover prompt" */}
              <button
                onClick={() => onCopyPrompt(checkpoint)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg btn-secondary-ice text-xs font-medium"
                title="Copy ready-to-paste handover prompt for the next agent"
              >
                {isCopied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
                    <span className="text-emerald-600 dark:text-emerald-400 font-bold">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5 text-steel-500" />
                    <span>Copy handover prompt</span>
                  </>
                )}
              </button>

              {/* Primary Magma Button: "Resume from here" */}
              <div className="relative">
                <button
                  onClick={() => setShowConfirmPopover((prev) => !prev)}
                  disabled={isResuming || isActiveForResume}
                  className={`inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-md active:scale-[0.97] ${
                    isActiveForResume
                      ? 'bg-lava-orange/20 text-lava-orange border border-lava-orange/40 cursor-default opacity-85'
                      : 'btn-magma text-[#0C0A0B]'
                  }`}
                  title={isActiveForResume ? 'Currently active resume milestone' : 'Resume project from this checkpoint'}
                >
                  <RotateCcw className={`h-3.5 w-3.5 ${isResuming ? 'animate-spin' : ''}`} />
                  <span>{isActiveForResume ? 'Active for resume' : 'Resume from here'}</span>
                </button>

                {/* Confirm Popover */}
                {showConfirmPopover && (
                  <div className="absolute right-0 bottom-full mb-2 w-80 p-3.5 rounded-xl bg-surface border border-border-strong shadow-2xl z-40 animate-page-enter text-left">
                    <div className="flex items-start space-x-2.5">
                      <div className="p-1.5 rounded-lg bg-lava-orange/15 text-lava-orange shrink-0">
                        <AlertCircle className="h-4 w-4" />
                      </div>
                      <div>
                        <h4 className="font-heading text-xs font-bold text-text-primary">
                          Activate Milestone {formattedId}?
                        </h4>
                        <p className="text-[11px] text-text-secondary mt-1 leading-relaxed">
                          This will prepare and package this checkpoint as the primary resume state. Incoming agents will continue specifically from this milestone's pending actions.
                        </p>
                      </div>
                    </div>

                    <div className="flex justify-end space-x-2 mt-3 pt-2.5 border-t border-border-subtle">
                      <button
                        onClick={() => setShowConfirmPopover(false)}
                        className="px-2.5 py-1 rounded-md text-text-muted hover:text-text-primary text-xs font-medium"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmResume}
                        disabled={isResuming}
                        className="px-3 py-1 rounded-md btn-magma text-xs font-semibold shadow-sm"
                      >
                        {isResuming ? 'Activating...' : 'Confirm Resume'}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

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
  Sparkles,
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
      className={`relative rounded-2xl border transition-all duration-300 select-none ${
        isLatest
          ? 'p-6 bg-card/90 border-ice/45 shadow-[0_0_35px_rgba(56,189,248,0.22)] ring-1 ring-ice/30'
          : 'p-4.5 bg-card/70 hover:bg-card/90 border-ice/20 hover:border-ice/35 shadow-sm'
      }`}
    >
      {/* Crystal Burst Animation on activation */}
      {showBurst && <CrystalBurst onComplete={() => setShowBurst(false)} />}

      {/* Timeline Dot on the left line */}
      <div
        className={`absolute -left-[31px] top-6 rounded-full bg-background border-2 flex items-center justify-center transition-all ${
          isActiveForResume
            ? 'h-5 w-5 -left-[33px] border-chilli shadow-[0_0_12px_rgba(239,68,68,0.9)]'
            : isLatest
            ? 'h-4.5 w-4.5 -left-[32px] border-ice shadow-[0_0_10px_rgba(56,189,248,0.9)]'
            : 'h-3.5 w-3.5 border-ice/60 shadow-[0_0_6px_rgba(56,189,248,0.4)]'
        }`}
      >
        <div
          className={`rounded-full ${
            isActiveForResume
              ? 'h-2 w-2 bg-chilli animate-ping'
              : isLatest
              ? 'h-2 w-2 bg-ice'
              : 'h-1.5 w-1.5 bg-ice/70'
          }`}
        />
      </div>

      {/* Top Card Row */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-ice/15 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          {/* Checkpoint ID in Mono */}
          <span className="font-mono text-xs font-bold text-ice px-2.5 py-1 rounded-xl bg-ice/15 border border-ice/30 shadow-xs">
            {formattedId}
          </span>

          {/* Author Badge */}
          <span
            className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-medium border ${
              isAiAgent
                ? 'bg-amber-500/15 text-amber-300 border-amber-500/30'
                : 'bg-ice/15 text-ice border-ice/30'
            }`}
          >
            {isAiAgent ? <Bot className="h-3 w-3" /> : <User className="h-3 w-3" />}
            <span>{authorName}</span>
          </span>

          {/* Base Commit Hash in Mono */}
          <span className="inline-flex items-center space-x-1 font-mono text-[11px] text-muted-foreground px-2 py-0.5 rounded-md bg-secondary/40 border border-border">
            <GitCommit className="h-3 w-3 text-muted-foreground/70" />
            <span>base: {truncate(baseRevision, 8)}</span>
          </span>

          {/* "Active for resume" Pill */}
          {isActiveForResume && (
            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold font-mono bg-chilli/20 text-chilli border border-chilli/40 shadow-[0_0_12px_rgba(239,68,68,0.35)] animate-pulse">
              <span className="h-1.5 w-1.5 rounded-full bg-chilli" />
              <span>Active for resume</span>
            </span>
          )}

          {/* "Latest Milestone" Pill */}
          {isLatest && !isActiveForResume && (
            <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded-full text-[10px] font-bold font-mono bg-ice/15 text-ice border border-ice/30">
              <Sparkles className="h-2.5 w-2.5" />
              <span>Latest Milestone</span>
            </span>
          )}
        </div>

        {/* Right Header: Time & Expand/Collapse */}
        <div className="flex items-center space-x-3 text-xs text-muted-foreground self-end sm:self-auto">
          <div className="flex items-center space-x-1 text-[11px]">
            <Clock className="h-3 w-3 text-muted-foreground/70" />
            <span>{formatDate(checkpoint.created_at)}</span>
          </div>

          <button
            onClick={() => setIsExpanded((prev) => !prev)}
            className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
            title={isExpanded ? 'Collapse checkpoint' : 'Expand checkpoint'}
          >
            {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {/* Expandable Body */}
      {isExpanded && (
        <div className="mt-4 space-y-4 animate-page-enter">
          {/* 1. "Next Action" Callout with Bright Ice Left Border */}
          <div className="p-3.5 rounded-xl bg-ice/5 border border-ice/25 border-l-4 border-l-ice shadow-sm space-y-1">
            <div className="text-[10px] uppercase font-mono font-bold text-ice tracking-wider flex items-center space-x-1.5">
              <ArrowRight className="h-3.5 w-3.5 text-ice" />
              <span>Next Continuation Action:</span>
            </div>
            <p className="text-xs font-semibold text-foreground leading-relaxed pl-5">
              {String(nextAction)}
            </p>
          </div>

          {/* 2. Completed Actions (Ice-tinted Check Chips) */}
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-mono font-bold text-muted-foreground tracking-wider block">
              Completed Actions ({completedActions.length})
            </span>
            {completedActions.length === 0 ? (
              <p className="text-xs text-muted-foreground/70 italic pl-1">
                No individual action items flagged as complete for this milestone.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {completedActions.map((action, aIdx) => (
                  <span
                    key={aIdx}
                    className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-ice/10 text-ice border border-ice/25 text-xs font-medium shadow-2xs"
                  >
                    <CheckCircle2 className="h-3.5 w-3.5 text-ice shrink-0" />
                    <span>{action}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 3. Pending Actions (Muted Outlined Chips) */}
          <div className="space-y-1.5">
            <span className="text-[10px] uppercase font-mono font-bold text-muted-foreground tracking-wider block">
              Pending Actions ({pendingActions.length})
            </span>
            {pendingActions.length === 0 ? (
              <p className="text-xs text-muted-foreground/70 italic pl-1">
                All scheduled tasks completed prior to snapshot.
              </p>
            ) : (
              <div className="flex flex-wrap gap-1.5">
                {pendingActions.map((action, pIdx) => (
                  <span
                    key={pIdx}
                    className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg bg-secondary/30 text-muted-foreground hover:text-foreground border border-border/70 text-xs font-medium transition-colors"
                  >
                    <Clock className="h-3.5 w-3.5 text-muted-foreground/60 shrink-0" />
                    <span>{action}</span>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* 4. Action Buttons Bar: "Resume from here" (Primary Chilli) & "Copy handover prompt" (Secondary Ice) */}
          <div className="pt-3 border-t border-ice/15 flex flex-wrap items-center justify-between gap-2.5">
            <div className="font-mono text-[10px] text-muted-foreground">
              Internal UID: {rawId}
            </div>

            <div className="flex items-center space-x-2 relative">
              {/* Secondary Button: "Copy handover prompt" */}
              <button
                onClick={() => onCopyPrompt(checkpoint)}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-ice/10 hover:bg-ice/20 border border-ice/30 text-ice text-xs font-medium transition-all shadow-sm active:scale-[0.98]"
                title="Copy ready-to-paste handover prompt for the next agent"
              >
                {isCopied ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="text-emerald-400 font-bold">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3.5 w-3.5 text-ice" />
                    <span>Copy handover prompt</span>
                  </>
                )}
              </button>

              {/* Primary Chilli Button: "Resume from here" */}
              <div className="relative">
                <button
                  onClick={() => setShowConfirmPopover((prev) => !prev)}
                  disabled={isResuming || isActiveForResume}
                  className={`inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl font-bold text-xs transition-all shadow-sm active:scale-[0.98] ${
                    isActiveForResume
                      ? 'bg-chilli/20 text-chilli border border-chilli/40 cursor-default opacity-85'
                      : 'bg-chilli hover:bg-chilli/90 text-white shadow-[0_0_15px_rgba(239,68,68,0.35)]'
                  }`}
                  title={isActiveForResume ? 'Currently active resume milestone' : 'Resume project from this checkpoint'}
                >
                  <RotateCcw className={`h-3.5 w-3.5 ${isResuming ? 'animate-spin' : ''}`} />
                  <span>{isActiveForResume ? 'Active for resume' : 'Resume from here'}</span>
                </button>

                {/* Confirm Popover */}
                {showConfirmPopover && (
                  <div className="absolute right-0 bottom-full mb-2 w-80 p-3.5 rounded-2xl bg-card/95 backdrop-blur-md border border-chilli/40 shadow-[0_8px_30px_rgba(0,0,0,0.5)] z-40 animate-page-enter text-left">
                    <div className="flex items-start space-x-2.5">
                      <div className="p-1.5 rounded-lg bg-chilli/15 text-chilli shrink-0">
                        <AlertCircle className="h-4 w-4" />
                      </div>
                      <div>
                        <h4 className="text-xs font-bold text-foreground">
                          Activate Milestone {formattedId}?
                        </h4>
                        <p className="text-[11px] text-muted-foreground mt-1 leading-relaxed">
                          This will prepare and package this checkpoint as the primary resume state. Incoming agents will continue specifically from this milestone's pending actions.
                        </p>
                      </div>
                    </div>

                    <div className="flex justify-end space-x-2 mt-3 pt-2.5 border-t border-border/60">
                      <button
                        onClick={() => setShowConfirmPopover(false)}
                        className="px-2.5 py-1 rounded-lg text-muted-foreground hover:text-foreground text-xs font-medium"
                      >
                        Cancel
                      </button>
                      <button
                        onClick={handleConfirmResume}
                        disabled={isResuming}
                        className="px-3 py-1 rounded-lg bg-chilli hover:bg-chilli/90 text-white text-xs font-bold shadow-sm transition-all"
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

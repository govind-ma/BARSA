import { useEffect, useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { formatDate, truncate } from '@/lib/utils';
import type { BMSRecord } from '@/types';
import {
  BookmarkCheck,
  Clock,
  ArrowRight,
  GitCommit,
  Bot,
  Copy,
  Check,
} from 'lucide-react';

export function CheckpointsPage() {
  const { activeProject } = useApp();
  const [checkpoints, setCheckpoints] = useState<BMSRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    if (!activeProject) {
      setCheckpoints([]);
      return;
    }

    const loadCheckpoints = async () => {
      setIsLoading(true);
      try {
        const list = await api.listRecords(activeProject.project_id, 'checkpoint');
        if (isMounted) setCheckpoints(list);
      } catch {
        if (isMounted) setCheckpoints([]);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadCheckpoints();
    return () => {
      isMounted = false;
    };
  }, [activeProject]);

  const copyCheckpointPrompt = (cp: BMSRecord) => {
    const cpId = cp.record_id || (cp as any).id;
    const nextAct = (cp.attributes as any)?.next_action || (typeof cp.content === 'string' ? cp.content : 'Continue next task');
    const text = `Resume BARSA project "${activeProject?.name}" from Checkpoint ${cpId}. Next Action: ${nextAct}.`;
    navigator.clipboard.writeText(text);
    setCopiedId(cpId);
    setTimeout(() => setCopiedId(null), 2000);
  };

  if (!activeProject) {
    return (
      <div className="py-12 animate-page-enter">
        <EmptyState
          title="No Project Selected"
          description="Select a project in the top switcher to inspect saved agent checkpoints."
        />
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="py-20 flex justify-center animate-page-enter">
        <LoadingSpinner text="Retrieving verified checkpoints from BARSA storage..." />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto animate-page-enter">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-ice/15 pb-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <div className="h-8 w-8 rounded-xl bg-ice/15 border border-ice/30 flex items-center justify-center text-ice shadow-[0_0_12px_rgba(56,189,248,0.2)]">
              <BookmarkCheck className="h-4 w-4" />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-foreground">
              Audit Checkpoints
            </h1>
            <span className="text-xs px-2 py-0.5 rounded-full bg-ice/10 text-ice border border-ice/20 font-mono">
              {checkpoints.length} Saved
            </span>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Immutable milestone snapshots enabling cross-agent task continuation across Claude, ChatGPT, and Cursor.
          </p>
        </div>
      </div>

      {/* Checkpoints Timeline Cards */}
      {checkpoints.length === 0 ? (
        <EmptyState
          title="No Checkpoints Found"
          description="This project does not have any saved checkpoints yet. Instruct an agent to run barsa_save_checkpoint."
        />
      ) : (
        <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-3 before:bottom-3 before:w-0.5 before:bg-gradient-to-b before:from-ice before:via-ice/40 before:to-transparent">
          {checkpoints.map((cp, idx) => {
            const cpId = cp.record_id || (cp as any).id;
            const completedActions = (cp.attributes as any)?.completed_actions || [];
            const nextAction = (cp.attributes as any)?.next_action || (typeof cp.content === 'string' ? cp.content : 'Proceed to next task');
            const baseRevision = String((cp.attributes as any)?.base_revision || (cp.attributes as any)?.commit_hash || 'head');
            const author = cp.author || (cp.attributes as any)?.created_by || 'agent';

            return (
              <div
                key={cpId}
                className="relative p-5 rounded-2xl bg-card/85 border border-ice/20 hover:border-ice/40 shadow-[0_4px_24px_rgba(0,0,0,0.25)] transition-all group"
              >
                {/* Timeline Dot */}
                <div className="absolute -left-[30px] top-5 h-4 w-4 rounded-full bg-background border-2 border-ice shadow-[0_0_8px_rgba(56,189,248,0.8)] flex items-center justify-center">
                  <div className="h-1.5 w-1.5 rounded-full bg-ice" />
                </div>

                {/* Card Header */}
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-ice/10 pb-3 mb-3">
                  <div className="flex items-center space-x-2.5">
                    <span className="font-mono text-xs font-bold text-ice px-2.5 py-1 rounded-lg bg-ice/10 border border-ice/20">
                      {cpId}
                    </span>
                    <span className="text-xs font-semibold text-foreground">
                      {cp.title || `Milestone Checkpoint #${checkpoints.length - idx}`}
                    </span>
                  </div>

                  <div className="flex items-center space-x-3 text-xs text-muted-foreground">
                    <span className="flex items-center space-x-1 font-mono">
                      <Bot className="h-3.5 w-3.5 text-ice" />
                      <span>{author}</span>
                    </span>
                    <span className="flex items-center space-x-1">
                      <Clock className="h-3 w-3" />
                      <span>{formatDate(cp.created_at)}</span>
                    </span>
                  </div>
                </div>

                {/* Next Action Callout */}
                <div className="p-3 rounded-xl bg-secondary/50 border border-ice/15 mb-3">
                  <div className="text-[10px] uppercase font-mono font-bold text-ice tracking-wider mb-1 flex items-center space-x-1">
                    <ArrowRight className="h-3 w-3 text-ice" />
                    <span>Next Continuation Action:</span>
                  </div>
                  <p className="text-xs text-foreground font-medium">{String(nextAction)}</p>
                </div>

                {/* Completed Actions */}
                {Array.isArray(completedActions) && completedActions.length > 0 && (
                  <div className="space-y-1 mb-3">
                    <span className="text-[10px] uppercase font-mono text-muted-foreground tracking-wider">
                      Completed Actions:
                    </span>
                    <ul className="text-xs text-muted-foreground space-y-1 pl-4 list-disc marker:text-ice">
                      {completedActions.map((act: string, aIdx: number) => (
                        <li key={aIdx}>{act}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Card Footer: Revision & Copy Handover Action */}
                <div className="pt-3 border-t border-ice/10 flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-1.5 font-mono text-[11px] text-muted-foreground">
                    <GitCommit className="h-3.5 w-3.5 text-muted-foreground" />
                    <span>Revision: {truncate(baseRevision, 12)}</span>
                  </div>

                  <button
                    onClick={() => copyCheckpointPrompt(cp)}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-ice/10 hover:bg-ice/20 border border-ice/30 text-ice text-xs font-medium transition-all"
                  >
                    {copiedId === cpId ? (
                      <>
                        <Check className="h-3 w-3 text-ice" />
                        <span>Prompt Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy className="h-3 w-3 text-ice" />
                        <span>Copy Handover Prompt</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

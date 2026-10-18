import { useEffect, useState, useRef } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { CheckpointCard } from './CheckpointCard';
import type { BMSRecord } from '@/types';
import {
  BookmarkCheck,
  Check,
} from 'lucide-react';

export function CheckpointsPage() {
  const { activeProject } = useApp();
  const [checkpoints, setCheckpoints] = useState<BMSRecord[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [activeResumeCpId, setActiveResumeCpId] = useState<string | null>(null);

  // Toast feedback state
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const showToast = (msg: string) => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    setToastMessage(msg);
    toastTimeoutRef.current = setTimeout(() => setToastMessage(null), 3500);
  };

  // Load active resume checkpoint from localStorage
  useEffect(() => {
    if (!activeProject) return;
    const stored = localStorage.getItem(`barsa_active_resume_checkpoint_${activeProject.project_id}`);
    if (stored) {
      setActiveResumeCpId(stored);
    } else {
      setActiveResumeCpId(null);
    }
  }, [activeProject?.project_id]);

  // Load checkpoints list
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
        if (!isMounted) return;

        // Sort newest first
        const sorted = [...list].sort(
          (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
        );
        setCheckpoints(sorted);

        // If no active resume CP is stored, default to latest checkpoint
        const stored = localStorage.getItem(`barsa_active_resume_checkpoint_${activeProject.project_id}`);
        if (!stored && sorted.length > 0) {
          const firstId = sorted[0].record_id || (sorted[0] as any).id;
          setActiveResumeCpId(firstId);
        }
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
  }, [activeProject?.project_id]);

  const handleCopyPrompt = (cp: BMSRecord) => {
    const cpId = cp.record_id || (cp as any).id;
    const author =
      cp.author ||
      (cp.attributes as any)?.created_by ||
      (cp as any).created_by ||
      'claude-backend';
    const nextAct =
      (cp.attributes as any)?.next_action ||
      (cp as any).next_action ||
      (typeof cp.content === 'string' ? cp.content : 'Continue next task');

    const pending: string[] = Array.isArray((cp.attributes as any)?.pending_actions)
      ? (cp.attributes as any).pending_actions
      : [];

    const text = `Resume BARSA project "${activeProject?.name}" from Checkpoint ${cpId}. Author: ${author}. Next Continuation Action: ${nextAct}.${
      pending.length > 0 ? ` Pending Tasks: ${pending.join(', ')}.` : ''
    }`;

    navigator.clipboard.writeText(text);
    setCopiedId(cpId);
    showToast(`Context copied from Checkpoint ${cpId}. Paste it into your next agent.`);
    setTimeout(() => setCopiedId(null), 2500);
  };

  const handleResumeFromHere = async (cp: BMSRecord) => {
    if (!activeProject) return;
    const cpId = cp.record_id || (cp as any).id;

    try {
      // Call resume context endpoint
      await api.resumeContext(activeProject.project_id, 8000).catch(() => null);

      setActiveResumeCpId(cpId);
      localStorage.setItem(`barsa_active_resume_checkpoint_${activeProject.project_id}`, cpId);
      showToast(`Milestone activated. Context ready for incoming AI agents.`);
    } catch {
      setActiveResumeCpId(cpId);
      showToast(`Checkpoint ${cpId} activated for resume.`);
    }
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

  if (isLoading && checkpoints.length === 0) {
    return (
      <div className="py-20 flex justify-center animate-page-enter">
        <LoadingSpinner text="Retrieving verified checkpoints from BARSA storage..." />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-page-enter select-none pb-12">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed top-20 right-8 z-50 px-4 py-2.5 rounded-xl bg-card/90 backdrop-blur-md border border-ice/40 shadow-[0_0_25px_rgba(56,189,248,0.3)] text-xs text-foreground font-semibold flex items-center space-x-2 animate-bounce">
          <Check className="h-4 w-4 text-emerald-400" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Top Header Card */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 p-4 rounded-2xl bg-card/60 backdrop-blur-md border border-ice/15 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
        <div className="flex items-center space-x-3">
          <div className="h-9 w-9 rounded-xl bg-ice/15 border border-ice/30 flex items-center justify-center text-ice shadow-[0_0_15px_rgba(56,189,248,0.25)]">
            <BookmarkCheck className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-base font-bold tracking-tight text-foreground">
                Audit Checkpoints
              </h1>
              <span className="text-[10px] px-2 py-0.5 rounded-full bg-ice/15 text-ice border border-ice/30 font-mono font-bold">
                {checkpoints.length} Snapshots
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              Verified milestone checkpoints for zero-loss agent-to-agent handover.
            </p>
          </div>
        </div>

        {activeResumeCpId && (
          <div className="flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-chilli/10 border border-chilli/30 text-chilli text-xs font-mono font-bold self-start sm:self-auto">
            <span className="h-2 w-2 rounded-full bg-chilli animate-ping" />
            <span>Active Resume: {activeResumeCpId}</span>
          </div>
        )}
      </div>

      {/* Checkpoints Timeline Area */}
      {checkpoints.length === 0 ? (
        <EmptyState
          title="No Checkpoints Found"
          description="This project does not have any saved checkpoints yet. Instruct an agent to run barsa_save_checkpoint."
        />
      ) : (
        /* Vertical connected timeline with ice gradient line */
        <div className="relative pl-8 space-y-6 before:absolute before:left-3.5 before:top-4 before:bottom-4 before:w-0.5 before:bg-gradient-to-b before:from-ice before:via-ice/40 before:to-transparent">
          {checkpoints.map((cp, idx) => {
            const cpId = cp.record_id || (cp as any).id;
            const isLatest = idx === 0;
            const isActiveForResume = activeResumeCpId === cpId;

            return (
              <CheckpointCard
                key={cpId}
                checkpoint={cp}
                index={idx}
                totalCount={checkpoints.length}
                isLatest={isLatest}
                isActiveForResume={isActiveForResume}
                onResumeFromHere={handleResumeFromHere}
                onCopyPrompt={handleCopyPrompt}
                isCopied={copiedId === cpId}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

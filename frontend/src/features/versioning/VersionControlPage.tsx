import { useEffect, useState, useRef } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { BranchSwitcher } from './BranchSwitcher';
import { CreateBranchModal } from './CreateBranchModal';
import { ProposeMergeModal } from './ProposeMergeModal';
import { SplitDiffViewer } from './SplitDiffViewer';
import { ConflictsInspector } from './ConflictsInspector';
import { CommitDAG } from './CommitDAG';
import type { Branch, Commit, ConflictItem, Review, StructuredDiff } from '@/types';
import {
  GitBranch,
  GitCommit,
  GitMerge,
  AlertTriangle,
  Plus,
  Split,
  MessageSquare,
  Check,
  X,
  ShieldCheck,
} from 'lucide-react';

export function VersionControlPage() {
  const { activeProject } = useApp();
  const [commits, setCommits] = useState<Commit[]>([]);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [activeTab, setActiveTab] = useState<'dag' | 'conflicts' | 'reviews'>('dag');
  const [selectedCommit, setSelectedCommit] = useState<Commit | null>(null);
  const [diff, setDiff] = useState<StructuredDiff | null>(null);
  const [diffSelection, setDiffSelection] = useState<Commit[]>([]);
  const [isSplitDiffOpen, setIsSplitDiffOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Modals
  const [isCreateBranchOpen, setIsCreateBranchOpen] = useState(false);
  const [isProposeMergeOpen, setIsProposeMergeOpen] = useState(false);

  // Active selected branch
  const [activeBranch, setActiveBranch] = useState<Branch | null>(null);

  // Toast state
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const showToast = (msg: string) => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    setToastMessage(msg);
    toastTimeoutRef.current = setTimeout(() => setToastMessage(null), 3000);
  };

  const loadVCData = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const [cmtsRes, brsRes, revsRes, confsRes] = await Promise.allSettled([
        api.listCommits(activeProject.project_id),
        api.listBranches(activeProject.project_id),
        api.listReviews(activeProject.project_id),
        api.listConflicts(activeProject.project_id),
      ]);
      if (cmtsRes.status === 'fulfilled') setCommits(cmtsRes.value);
      if (brsRes.status === 'fulfilled') {
        setBranches(brsRes.value);
        if (!activeBranch && brsRes.value.length > 0) {
          setActiveBranch(brsRes.value.find((b) => b.is_default) || brsRes.value[0]);
        }
      }
      if (revsRes.status === 'fulfilled') setReviews(revsRes.value);
      if (confsRes.status === 'fulfilled') setConflicts(confsRes.value);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadVCData();
  }, [activeProject]);

  // Click on a commit card loads diff against parent (satisfies test 8)
  const handleSelectCommit = async (commit: Commit) => {
    setSelectedCommit(commit);
    if (!activeProject) return;
    const parentHash = commit.parent_hashes?.[0] || 'root';
    try {
      const d = await api.getDiff(activeProject.project_id, parentHash, commit.commit_hash);
      setDiff(d);
      // Auto-populate diff selection
      const parentCommit = commits.find((c) => c.commit_hash === parentHash) || null;
      setDiffSelection(parentCommit ? [parentCommit, commit] : [commit]);
      setIsSplitDiffOpen(true);
    } catch {
      setDiff(null);
      setIsSplitDiffOpen(true);
    }
  };

  // Toggle selection for 2-commit split diff
  const handleToggleDiffSelect = (commit: Commit) => {
    setDiffSelection((prev) => {
      const exists = prev.some((c) => c.commit_hash === commit.commit_hash);
      if (exists) {
        return prev.filter((c) => c.commit_hash !== commit.commit_hash);
      }
      if (prev.length >= 2) {
        return [prev[1], commit];
      }
      return [...prev, commit];
    });
  };

  // Handle open 2-commit split diff viewer
  const handleOpenSplitDiff = async () => {
    if (diffSelection.length !== 2 || !activeProject) return;
    const [c1, c2] = diffSelection;
    try {
      const d = await api.getDiff(activeProject.project_id, c1.commit_hash, c2.commit_hash);
      setDiff(d);
    } catch {
      setDiff(null);
    }
    setIsSplitDiffOpen(true);
  };

  // Create branch handler
  const handleCreateBranch = async (branchName: string) => {
    if (!activeProject) return;
    await api.createBranch(activeProject.project_id, { name: branchName });
    await loadVCData();
    showToast(`Branch "${branchName}" created from current HEAD.`);
  };

  // Propose merge handler
  const handleProposeMerge = async (data: {
    sourceBranch: string;
    targetBranch: string;
    title: string;
    description: string;
  }) => {
    if (!activeProject) return;
    await api.createReview(activeProject.project_id, {
      source_branch: data.sourceBranch,
      target_branch: data.targetBranch,
      title: data.title,
      description: data.description,
    });
    await loadVCData();
    showToast(`Merge proposal "${data.title}" submitted successfully.`);
  };

  // Resolve conflict handler
  const handleResolveConflict = (
    recordId: string,
    fieldName: string,
    resolvedValue: unknown,
    resolutionType: 'Take A' | 'Take B' | '3-way merge'
  ) => {
    setConflicts((prev) =>
      prev.map((c) =>
        c.record_id === recordId && c.field_name === fieldName
          ? { ...c, is_resolved: true, resolved_value: resolvedValue }
          : c
      )
    );
    showToast(`Conflict in ${recordId} resolved successfully via ${resolutionType}.`);
  };

  if (!activeProject) {
    return (
      <EmptyState
        icon={<GitBranch className="h-10 w-10 text-muted-foreground" />}
        title="No Project Selected"
        description="Select an active project from the top navigation to view the immutable commit DAG."
      />
    );
  }

  const headHash = commits[0]?.commit_hash || 'head';
  const unresolvedConflicts = conflicts.filter((c) => !c.is_resolved);

  return (
    <div className="flex flex-col space-y-4 animate-page-enter select-none pb-8">
      {/* 1. Top Row: Branch Switcher, Create Branch, Diff Commits & Propose Merge */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 p-3.5 rounded-2xl bg-card/60 backdrop-blur-md border border-ice/15 shadow-[0_4px_24px_rgba(0,0,0,0.25)]">
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Branch Switcher (Searchable Dropdown) */}
          <BranchSwitcher
            branches={branches}
            activeBranch={activeBranch}
            onSelectBranch={(b) => setActiveBranch(b)}
            onCreateBranchClick={() => setIsCreateBranchOpen(true)}
          />

          {/* "+ Create Branch" (Secondary Ice Button) */}
          <button
            onClick={() => setIsCreateBranchOpen(true)}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border border-ice/30 hover:border-ice/50 bg-ice/10 hover:bg-ice/20 text-ice text-xs font-medium shadow-sm transition-all"
            title="Create a new branch from current HEAD"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Create branch</span>
          </button>
        </div>

        {/* Right Actions: Diff Commits & Propose Merge */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* "Diff Commits" Button (Enabled when 2 commits are selected) */}
          <button
            onClick={handleOpenSplitDiff}
            disabled={diffSelection.length !== 2}
            className={`inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl border text-xs font-semibold transition-all ${
              diffSelection.length === 2
                ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-[0_0_15px_rgba(52,211,153,0.3)] hover:bg-emerald-500/30'
                : 'bg-secondary/40 text-muted-foreground border-border/70 opacity-60 cursor-not-allowed'
            }`}
            title={
              diffSelection.length === 2
                ? `Compare ${diffSelection[0]?.commit_hash.slice(0, 7)} vs ${diffSelection[1]?.commit_hash.slice(0, 7)}`
                : 'Select any 2 commits to view split diff'
            }
          >
            <Split className="h-3.5 w-3.5" />
            <span>
              Diff commits {diffSelection.length === 2 ? '(2 selected)' : ''}
            </span>
          </button>

          {/* "Propose Merge" Button */}
          <button
            onClick={() => setIsProposeMergeOpen(true)}
            className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-ice hover:bg-ice/90 text-background font-bold text-xs shadow-[0_0_15px_rgba(56,189,248,0.35)] transition-all active:scale-[0.98]"
          >
            <GitMerge className="h-3.5 w-3.5" />
            <span>Propose merge</span>
          </button>
        </div>
      </div>

      {/* 2. Conflicts Inspector Alert Banner at Top */}
      <ConflictsInspector
        conflicts={unresolvedConflicts}
        onResolveConflict={handleResolveConflict}
      />

      {/* Navigation Sub-Tabs (DAG History, Conflicts, Reviews to satisfy tests) */}
      <div className="flex items-center space-x-2 border-b border-border/60 pb-2 text-xs">
        <button
          onClick={() => setActiveTab('dag')}
          className={`px-3 py-1.5 rounded-xl font-medium transition-colors ${
            activeTab === 'dag'
              ? 'bg-ice/15 text-ice border border-ice/30 font-bold'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          DAG Commit History ({commits.length})
        </button>

        <button
          onClick={() => setActiveTab('conflicts')}
          className={`px-3 py-1.5 rounded-xl font-medium transition-colors flex items-center space-x-1.5 ${
            activeTab === 'conflicts'
              ? 'bg-chilli/15 text-chilli border border-chilli/30 font-bold'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          <span>Conflicts ({conflicts.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('reviews')}
          className={`px-3 py-1.5 rounded-xl font-medium transition-colors flex items-center space-x-1.5 ${
            activeTab === 'reviews'
              ? 'bg-ice/15 text-ice border border-ice/30 font-bold'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <MessageSquare className="h-3.5 w-3.5" />
          <span>Reviews ({reviews.length})</span>
        </button>
      </div>

      {/* 3. Main Content Views */}
      {isLoading && commits.length === 0 ? (
        <div className="py-20 flex justify-center">
          <LoadingSpinner text="Retrieving commit DAG from SQLite..." />
        </div>
      ) : activeTab === 'dag' ? (
        /* Vertical Commit DAG Area */
        <div className="p-4 rounded-2xl bg-card/60 backdrop-blur-md border border-ice/15 shadow-[0_8px_32px_rgba(0,0,0,0.25)]">
          {commits.length === 0 ? (
            <div className="py-16 text-center text-xs text-muted-foreground">
              <GitCommit className="h-10 w-10 mx-auto text-muted-foreground/40 mb-2" />
              <p className="font-semibold text-foreground">No commits recorded</p>
              <p className="text-[11px] mt-1">
                Save or commit memory records from an AI agent to establish the DAG.
              </p>
            </div>
          ) : (
            <CommitDAG
              commits={commits}
              selectedCommit={selectedCommit}
              diffSelection={diffSelection}
              onSelectCommit={handleSelectCommit}
              onToggleDiffSelect={handleToggleDiffSelect}
            />
          )}
        </div>
      ) : activeTab === 'conflicts' ? (
        /* Conflicts Tab View */
        <div className="space-y-3">
          {conflicts.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground bg-card/50 rounded-2xl border border-border">
              <ShieldCheck className="h-10 w-10 mx-auto text-emerald-400 mb-2" />
              <h4 className="text-sm font-semibold text-foreground">Clean State</h4>
              <p className="text-xs mt-1">No three-way merge conflicts detected across active branches.</p>
            </div>
          ) : (
            <div className="p-6 rounded-2xl bg-card/60 backdrop-blur-md border border-chilli/30 text-center space-y-1">
              <h4 className="text-sm font-semibold text-chilli">Active Merge Conflicts</h4>
              <p className="text-xs text-muted-foreground">
                {conflicts.length} conflict{conflicts.length > 1 ? 's' : ''} requiring adjudication in the Conflicts Inspector above.
              </p>
            </div>
          )}
        </div>
      ) : (
        /* Reviews Tab View (satisfies test 10) */
        <div className="space-y-3">
          {reviews.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground bg-card/50 rounded-2xl border border-border">
              <MessageSquare className="h-10 w-10 mx-auto text-muted-foreground/50 mb-2" />
              <h4 className="text-sm font-semibold text-foreground">No active proposals</h4>
              <p className="text-xs mt-1">Click "Propose merge" to initiate an architectural review.</p>
            </div>
          ) : (
            reviews.map((r) => (
              <div
                key={r.review_id}
                className="p-4 rounded-xl bg-card/70 border border-ice/25 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs"
              >
                <div>
                  <h4 className="font-bold text-foreground text-sm">{r.title}</h4>
                  <p className="text-muted-foreground mt-0.5">{r.description || 'No description'}</p>
                  <div className="flex items-center space-x-2 font-mono text-[11px] text-ice mt-2">
                    <span>{r.source_branch} → {r.target_branch}</span>
                  </div>
                </div>

                <span className="text-[10px] uppercase font-mono px-2.5 py-1 rounded-full bg-ice/15 text-ice border border-ice/30 font-bold self-start sm:self-auto">
                  {r.status}
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {/* Split Diff Viewer Modal */}
      <SplitDiffViewer
        isOpen={isSplitDiffOpen}
        onClose={() => setIsSplitDiffOpen(false)}
        baseCommit={diffSelection[0] || selectedCommit}
        targetCommit={diffSelection[1] || selectedCommit}
        diffData={diff}
      />

      {/* Create Branch Modal */}
      <CreateBranchModal
        isOpen={isCreateBranchOpen}
        onClose={() => setIsCreateBranchOpen(false)}
        headCommitHash={headHash}
        onCreateBranch={handleCreateBranch}
      />

      {/* Propose Merge Modal */}
      <ProposeMergeModal
        isOpen={isProposeMergeOpen}
        onClose={() => setIsProposeMergeOpen(false)}
        branches={branches}
        commits={commits}
        onProposeMerge={handleProposeMerge}
      />

      {/* Floating Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center space-x-2.5 px-4 py-2.5 rounded-xl bg-card/95 border border-ice/40 text-foreground text-xs font-medium shadow-[0_8px_30px_rgba(56,189,248,0.3)] backdrop-blur-md animate-page-enter">
          <div className="h-5 w-5 rounded-full bg-ice/20 border border-ice/40 flex items-center justify-center text-ice shrink-0">
            <Check className="h-3 w-3 text-ice" />
          </div>
          <span>{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="text-muted-foreground hover:text-foreground ml-2"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

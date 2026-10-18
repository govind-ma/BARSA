import React, { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input, Textarea } from '@/components/ui/Input';
import { GitMerge, ArrowRight, GitCommit, Loader2 } from 'lucide-react';
import type { Branch, Commit } from '@/types';
import { truncate } from '@/lib/utils';

interface ProposeMergeModalProps {
  isOpen: boolean;
  onClose: () => void;
  branches: Branch[];
  commits: Commit[];
  onProposeMerge: (data: {
    sourceBranch: string;
    targetBranch: string;
    title: string;
    description: string;
  }) => Promise<void>;
}

export function ProposeMergeModal({
  isOpen,
  onClose,
  branches,
  commits,
  onProposeMerge,
}: ProposeMergeModalProps) {
  const [sourceBranch, setSourceBranch] = useState(
    branches.find((b) => !b.is_default)?.name || branches[1]?.name || 'feature-branch'
  );
  const [targetBranch, setTargetBranch] = useState(
    branches.find((b) => b.is_default)?.name || 'main'
  );
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !sourceBranch || !targetBranch) return;
    if (sourceBranch === targetBranch) {
      setError('Source and target branches cannot be the same.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      await onProposeMerge({
        sourceBranch,
        targetBranch,
        title: title.trim(),
        description: description.trim(),
      });
      setTitle('');
      setDescription('');
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to propose merge');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Preview of recent commits to merge
  const previewCommits = commits.slice(0, 3);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Propose Branch Merge"
      className="max-w-lg"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-1 text-xs">
        {error && (
          <div className="p-2.5 rounded-lg bg-destructive/15 border border-destructive/30 text-destructive">
            {error}
          </div>
        )}

        {/* Source -> Target Selectors */}
        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2 p-3 rounded-xl bg-secondary/30 border border-ice/15 font-mono">
          <div>
            <label className="text-[10px] uppercase text-muted-foreground block mb-1">
              Source Branch (from)
            </label>
            <select
              value={sourceBranch}
              onChange={(e) => setSourceBranch(e.target.value)}
              className="w-full h-8 rounded-lg bg-card border border-border px-2 text-xs text-foreground focus:outline-none"
            >
              {branches.map((b) => (
                <option key={b.name} value={b.name}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>

          <ArrowRight className="h-4 w-4 text-ice mt-4 shrink-0" />

          <div>
            <label className="text-[10px] uppercase text-muted-foreground block mb-1">
              Target Branch (into)
            </label>
            <select
              value={targetBranch}
              onChange={(e) => setTargetBranch(e.target.value)}
              className="w-full h-8 rounded-lg bg-card border border-border px-2 text-xs text-foreground focus:outline-none"
            >
              {branches.map((b) => (
                <option key={b.name} value={b.name}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Proposal Title */}
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
            Proposal Title
          </label>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Merge BMS v0.1 schema modifications"
            required
            className="text-xs bg-secondary/40 border-ice/20 focus-visible:ring-ice/50"
          />
        </div>

        {/* Description */}
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1">
            Summary & Rationale
          </label>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the architectural impact, agent decisions, and testing notes..."
            rows={2}
            className="text-xs bg-secondary/40 border-ice/20 focus-visible:ring-ice/50"
          />
        </div>

        {/* Preview of commits to merge */}
        <div>
          <span className="text-[10px] uppercase font-mono font-bold text-muted-foreground tracking-wider block mb-1.5">
            Commits to Merge Preview ({previewCommits.length})
          </span>
          <div className="space-y-1.5 max-h-28 overflow-y-auto pr-1">
            {previewCommits.map((c) => (
              <div
                key={c.commit_hash}
                className="flex items-center justify-between p-2 rounded-lg bg-secondary/20 border border-border/50 text-[11px]"
              >
                <div className="flex items-center space-x-2 truncate">
                  <GitCommit className="h-3 w-3 text-ice shrink-0" />
                  <span className="font-mono text-ice">{truncate(c.commit_hash, 7)}</span>
                  <span className="text-foreground truncate">{c.message}</span>
                </div>
                <span className="text-[10px] text-muted-foreground shrink-0">
                  {c.author.name}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Submit Actions */}
        <div className="pt-2 flex justify-end space-x-2 border-t border-border/60">
          <button
            type="button"
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-xl border border-border hover:bg-secondary text-foreground text-xs"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !title.trim() || sourceBranch === targetBranch}
            className="px-4 py-1.5 rounded-xl bg-ice hover:bg-ice/90 text-background font-bold text-xs shadow-[0_0_15px_rgba(56,189,248,0.35)] transition-all flex items-center space-x-1.5 disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <GitMerge className="h-3.5 w-3.5" />
            )}
            <span>Propose Merge</span>
          </button>
        </div>
      </form>
    </Modal>
  );
}

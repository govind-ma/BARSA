import React, { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input } from '@/components/ui/Input';
import { GitBranch, GitCommit, Loader2 } from 'lucide-react';
import { truncate } from '@/lib/utils';

interface CreateBranchModalProps {
  isOpen: boolean;
  onClose: () => void;
  headCommitHash: string;
  onCreateBranch: (branchName: string) => Promise<void>;
}

export function CreateBranchModal({
  isOpen,
  onClose,
  headCommitHash,
  onCreateBranch,
}: CreateBranchModalProps) {
  const [branchName, setBranchName] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!branchName.trim()) return;
    setIsSubmitting(true);
    setError(null);
    try {
      await onCreateBranch(branchName.trim());
      setBranchName('');
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create branch');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Create New Branch"
      className="max-w-md"
    >
      <form onSubmit={handleSubmit} className="space-y-4 pt-1 text-xs">
        {error && (
          <div className="p-2.5 rounded-lg bg-destructive/15 border border-destructive/30 text-destructive">
            {error}
          </div>
        )}

        <div className="p-3 rounded-xl bg-secondary/30 border border-ice/15 flex items-center justify-between text-muted-foreground font-mono">
          <span className="flex items-center space-x-1.5">
            <GitCommit className="h-3.5 w-3.5 text-ice" />
            <span>Forking from HEAD:</span>
          </span>
          <span className="font-bold text-ice">{truncate(headCommitHash, 12)}</span>
        </div>

        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block mb-1.5">
            Branch Name
          </label>
          <div className="relative">
            <GitBranch className="absolute left-3 top-2.5 h-4 w-4 text-ice" />
            <Input
              value={branchName}
              onChange={(e) => setBranchName(e.target.value)}
              placeholder="e.g. feature-smart-context-v2"
              required
              className="pl-9 font-mono text-xs bg-secondary/40 border-ice/20 focus-visible:ring-ice/50"
              autoFocus
            />
          </div>
        </div>

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
            disabled={isSubmitting || !branchName.trim()}
            className="px-4 py-1.5 rounded-xl bg-ice hover:bg-ice/90 text-background font-bold text-xs shadow-[0_0_15px_rgba(56,189,248,0.35)] transition-all flex items-center space-x-1.5 disabled:opacity-50"
          >
            {isSubmitting ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <GitBranch className="h-3.5 w-3.5" />
            )}
            <span>Create Branch</span>
          </button>
        </div>
      </form>
    </Modal>
  );
}

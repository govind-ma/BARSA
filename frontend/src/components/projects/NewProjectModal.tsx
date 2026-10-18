import React, { useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Flame, Check, Loader2 } from 'lucide-react';

export interface NewProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (projectId: string) => void;
}

export function NewProjectModal({ isOpen, onClose, onSuccess }: NewProjectModalProps) {
  const { activeWorkspace, workspaces, refreshProjects, setActiveProjectId } = useApp();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [goals, setGoals] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }

    const targetWsId = activeWorkspace?.workspace_id || (workspaces[0]?.workspace_id) || 'ws-atlas';

    setIsSubmitting(true);
    setError(null);

    try {
      const goalsList = goals
        .split('\n')
        .map((g) => g.trim())
        .filter(Boolean);

      const created = await api.createProject(targetWsId, {
        name: name.trim(),
        description: description.trim() || undefined,
        ...(goalsList.length > 0 ? { goals: goalsList } : {}),
      } as any);

      // Trigger success state and crystal burst animation
      setIsSuccess(true);
      await refreshProjects();
      setActiveProjectId(created.project_id);

      setTimeout(() => {
        setIsSuccess(false);
        setName('');
        setDescription('');
        setGoals('');
        onClose();
        if (onSuccess) {
          onSuccess(created.project_id);
        }
      }, 1200);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Create New Project" className="max-w-lg">
      <form onSubmit={handleSubmit} className="space-y-4 pt-1">
        {error && (
          <div className="p-3 text-xs bg-lava-red/10 border border-lava-red/30 text-lava-red rounded-lg">
            {error}
          </div>
        )}

        {isSuccess && (
          <div className="relative overflow-hidden p-4 rounded-xl bg-ice-100 dark:bg-bg-elevated border border-border-strong text-text-primary flex items-center space-x-3 shadow-[0_4px_20px_rgba(60,100,130,0.12)]">
            <div className="h-8 w-8 rounded-full bg-lava-orange/20 flex items-center justify-center shrink-0">
              <Check className="h-5 w-5 text-lava-orange" />
            </div>
            <div>
              <div className="font-semibold text-sm font-display text-text-primary">Project Created Successfully</div>
              <div className="text-xs text-text-muted">Connecting memory standard & FalkorDB graph...</div>
            </div>
          </div>
        )}

        <div>
          <label className="block text-xs font-medium text-text-muted uppercase tracking-wider mb-1.5">
            Project Name <span className="text-lava-red">*</span>
          </label>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Project NEXUS"
            required
            disabled={isSubmitting || isSuccess}
            className="border-border-subtle focus-visible:ring-lava-orange/40 bg-surface dark:bg-bg-elevated text-text-primary"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-text-muted uppercase tracking-wider mb-1.5">
            Description
          </label>
          <Textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="High-level architectural scope, purpose, and domain..."
            rows={2}
            disabled={isSubmitting || isSuccess}
            className="border-border-subtle focus-visible:ring-lava-orange/40 bg-surface dark:bg-bg-elevated text-text-primary"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-text-muted uppercase tracking-wider mb-1.5">
            Project Goals <span className="text-[10px] text-text-muted/70 normal-case">(one per line)</span>
          </label>
          <Textarea
            value={goals}
            onChange={(e) => setGoals(e.target.value)}
            placeholder="Sub-millisecond cascade graph traversal&#10;Dynamic incident severity routing&#10;Cross-AI state persistence"
            rows={3}
            disabled={isSubmitting || isSuccess}
            className="border-border-subtle focus-visible:ring-lava-orange/40 bg-surface dark:bg-bg-elevated text-text-primary text-xs font-mono"
          />
        </div>

        <div className="flex items-center justify-end space-x-2 pt-3 border-t border-border-subtle">
          <Button
            type="button"
            variant="ghost"
            onClick={onClose}
            disabled={isSubmitting || isSuccess}
            className="btn-secondary-ice text-xs"
          >
            Cancel
          </Button>
          <button
            type="submit"
            disabled={isSubmitting || isSuccess || !name.trim()}
            className="btn-magma inline-flex items-center justify-center px-4 py-2 rounded-lg text-xs font-semibold text-white shadow-sm disabled:opacity-50 disabled:pointer-events-none"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                Creating Project...
              </>
            ) : isSuccess ? (
              <>
                <Check className="mr-1.5 h-3.5 w-3.5" />
                Initialized!
              </>
            ) : (
              <>
                <Flame className="mr-1.5 h-3.5 w-3.5 text-lava-yellow" />
                Create Project
              </>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}

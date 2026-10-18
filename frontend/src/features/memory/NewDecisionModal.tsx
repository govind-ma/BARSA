import { useState } from 'react';
import { Modal } from '@/components/ui/Modal';
import { Input, Textarea } from '@/components/ui/Input';
import { api } from '@/lib/api';
import { Check, AlertCircle } from 'lucide-react';
import type { BMSRecord } from '@/types';

interface NewDecisionModalProps {
  isOpen: boolean;
  onClose: () => void;
  projectId: string;
  onSuccess: (newRecord: BMSRecord) => void;
}

export function NewDecisionModal({
  isOpen,
  onClose,
  projectId,
  onSuccess,
}: NewDecisionModalProps) {
  const [title, setTitle] = useState('');
  const [decision, setDecision] = useState('');
  const [rationale, setRationale] = useState('');
  const [alternatives, setAlternatives] = useState('');
  const [affectedTasks, setAffectedTasks] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errors, setErrors] = useState<{ [key: string]: string }>({});

  const validate = () => {
    const errs: { [key: string]: string } = {};
    if (!title.trim()) errs.title = 'Title is required';
    if (!decision.trim()) errs.decision = 'Decision statement is required';
    if (!rationale.trim()) errs.rationale = 'Rationale explaining the trade-offs is required';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setIsSubmitting(true);
    const recId = `dec_${Date.now()}`;
    const nowIso = new Date().toISOString();

    const parsedAlternatives = alternatives
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);

    const parsedTasks = affectedTasks
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    const payload: Partial<BMSRecord> = {
      record_id: recId,
      schema_version: '0.2',
      record_type: 'decision',
      project_id: projectId,
      title: title.trim(),
      summary: decision.trim(),
      content: rationale.trim(),
      author: 'dashboard-user',
      verification_status: 'verified',
      revision: 1,
      tags: ['decision', 'adr', ...parsedTasks],
      attributes: {
        decision: decision.trim(),
        rationale: rationale.trim(),
        alternatives: parsedAlternatives,
        affected_tasks: parsedTasks,
        status: 'approved',
        created_at: nowIso,
      },
      created_at: nowIso,
      updated_at: nowIso,
    };

    try {
      const created = await api.createRecord(projectId, payload);
      onSuccess(created);
      handleClose();
    } catch (err: unknown) {
      setErrors({ form: err instanceof Error ? err.message : 'Failed to create decision' });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setTitle('');
    setDecision('');
    setRationale('');
    setAlternatives('');
    setAffectedTasks('');
    setErrors({});
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="+ Record New Architectural Decision (ADR)"
      description="Record an immutable decision record with trade-offs, alternatives, and impacted tasks."
    >
      <form onSubmit={handleSubmit} className="space-y-4 text-xs">
        {errors.form && (
          <div className="p-3 rounded-lg bg-lava-red/10 border border-lava-red/30 text-lava-red flex items-center space-x-2">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{errors.form}</span>
          </div>
        )}

        <div>
          <label className="block text-xs font-semibold text-text-primary mb-1.5">
            Decision Title <span className="text-lava-red">*</span>
          </label>
          <Input
            placeholder="e.g. SQLite WAL Mode for High-Concurrency Memory"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (errors.title) setErrors((prev) => ({ ...prev, title: '' }));
            }}
            className={errors.title ? 'border-lava-red focus:border-lava-red' : ''}
          />
          {errors.title && (
            <p className="text-[11px] text-lava-red mt-1 flex items-center space-x-1">
              <AlertCircle className="h-3 w-3 inline" />
              <span>{errors.title}</span>
            </p>
          )}
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-primary mb-1.5">
            Decision Statement <span className="text-lava-red">*</span>
          </label>
          <Textarea
            placeholder="State clearly what architectural choice has been made..."
            rows={3}
            value={decision}
            onChange={(e) => {
              setDecision(e.target.value);
              if (errors.decision) setErrors((prev) => ({ ...prev, decision: '' }));
            }}
            className={errors.decision ? 'border-lava-red focus:border-lava-red' : ''}
          />
          {errors.decision && (
            <p className="text-[11px] text-lava-red mt-1 flex items-center space-x-1">
              <AlertCircle className="h-3 w-3 inline" />
              <span>{errors.decision}</span>
            </p>
          )}
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-primary mb-1.5">
            Rationale & Trade-Offs <span className="text-lava-red">*</span>
          </label>
          <Textarea
            placeholder="Why was this chosen? Include performance, security, and complexity trade-offs..."
            rows={3}
            value={rationale}
            onChange={(e) => {
              setRationale(e.target.value);
              if (errors.rationale) setErrors((prev) => ({ ...prev, rationale: '' }));
            }}
            className={errors.rationale ? 'border-lava-red focus:border-lava-red' : ''}
          />
          {errors.rationale && (
            <p className="text-[11px] text-lava-red mt-1 flex items-center space-x-1">
              <AlertCircle className="h-3 w-3 inline" />
              <span>{errors.rationale}</span>
            </p>
          )}
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-primary mb-1.5">
            Alternatives Considered (one per line)
          </label>
          <Textarea
            placeholder="e.g.&#10;PostgreSQL - rejected due to local zero-config requirement&#10;DuckDB - rejected due to concurrency write lock"
            rows={2}
            value={alternatives}
            onChange={(e) => setAlternatives(e.target.value)}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-text-primary mb-1.5">
            Affected Tasks (comma-separated IDs)
          </label>
          <Input
            placeholder="e.g. TASK-001, TASK-017, TASK-022"
            value={affectedTasks}
            onChange={(e) => setAffectedTasks(e.target.value)}
          />
        </div>

        <div className="flex justify-end space-x-2 pt-3 border-t border-border-subtle">
          <button
            type="button"
            onClick={handleClose}
            disabled={isSubmitting}
            className="px-3 py-1.5 rounded-lg btn-secondary-ice text-xs"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-lg btn-magma text-xs font-semibold shadow-md active:scale-[0.97] disabled:opacity-50"
          >
            {isSubmitting ? (
              <span className="flex items-center space-x-1.5">
                <span className="h-3 w-3 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                <span>Saving ADR...</span>
              </span>
            ) : (
              <>
                <Check className="h-3.5 w-3.5" />
                <span>Save Decision</span>
              </>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}

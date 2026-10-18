import { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import {
  X,
  Bot,
  Link2,
  ArrowRight,
  ShieldAlert,
} from 'lucide-react';
import type { CoordinationTask, AgentProfile } from '@/types';
import { formatDate } from '@/lib/utils';

interface TaskDetailDrawerProps {
  task: CoordinationTask | null;
  onClose: () => void;
  agents: AgentProfile[];
  onClaimTask: (taskId: string, agentId: string) => Promise<void>;
  onSelectRelatedTask: (taskId: string) => void;
}

export function TaskDetailDrawer({
  task,
  onClose,
  agents,
  onClaimTask,
  onSelectRelatedTask,
}: TaskDetailDrawerProps) {
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');
  const [isClaiming, setIsClaiming] = useState(false);
  const [claimSuccess, setClaimSuccess] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && task) {
        onClose();
      }
    };
    if (task) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [task, onClose]);

  if (!task) return null;

  const handleClaim = async () => {
    if (!selectedAgentId) return;
    setIsClaiming(true);
    try {
      await onClaimTask(task.task_id, selectedAgentId);
      setClaimSuccess(true);
      setTimeout(() => setClaimSuccess(false), 2000);
    } finally {
      setIsClaiming(false);
    }
  };

  return createPortal(
    <div
      className="fixed inset-0 z-drawer flex justify-end floating-scrim animate-page-enter select-none"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md h-full solid-floating-surface p-6 flex flex-col justify-between shadow-2xl overflow-y-auto relative"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-border-subtle">
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-bold text-text-primary px-2.5 py-1 rounded-lg bg-ice-100 dark:bg-white/[0.08] border border-border-subtle">
                {task.task_id}
              </span>
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-ice-100 dark:bg-white/[0.08] text-text-secondary border border-border-subtle">
                {task.status}
              </span>
            </div>

            <button
              onClick={onClose}
              className="p-1 rounded-lg text-text-muted hover:text-text-primary hover:bg-ice-100 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Title & Description */}
          <div>
            <h3 className="font-heading text-base font-semibold text-text-primary leading-snug">
              {task.title}
            </h3>
            {task.description ? (
              <p className="text-xs text-text-secondary mt-2 leading-relaxed whitespace-pre-wrap">
                {task.description}
              </p>
            ) : (
              <p className="text-xs text-text-muted italic mt-2">
                No description provided.
              </p>
            )}
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg bg-surface/80 border border-border-subtle">
              <span className="text-[10px] uppercase font-mono text-text-muted block mb-1">
                Priority
              </span>
              <span className="font-semibold text-text-primary capitalize font-mono">
                {task.priority}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-surface/80 border border-border-subtle">
              <span className="text-[10px] uppercase font-mono text-text-muted block mb-1">
                Created
              </span>
              <span className="text-text-primary">
                {formatDate(task.created_at)}
              </span>
            </div>
          </div>

          {/* Dependencies as clickable chips */}
          <div>
            <h4 className="text-[10px] font-mono uppercase font-bold text-text-muted tracking-wider mb-2 flex items-center space-x-1">
              <Link2 className="h-3 w-3 text-steel-500" />
              <span>Inbound Dependencies ({task.dependencies?.length || 0})</span>
            </h4>
            {task.dependencies && task.dependencies.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {task.dependencies.map((depId) => (
                  <button
                    key={depId}
                    onClick={() => onSelectRelatedTask(depId)}
                    title={`Jump to dependency ${depId}`}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-ice-100 hover:bg-ice-200 dark:bg-white/[0.08] dark:hover:bg-white/[0.12] border border-border-subtle text-text-primary font-mono text-xs transition-colors group"
                  >
                    <span>{depId}</span>
                    <ArrowRight className="h-2.5 w-2.5 opacity-60 group-hover:opacity-100" />
                  </button>
                ))}
              </div>
            ) : (
              <span className="text-xs text-text-muted italic">
                No dependencies required.
              </span>
            )}
          </div>

          {/* Blockers as clickable lava-red chips */}
          <div>
            <h4 className="text-[10px] font-mono uppercase font-bold text-lava-red tracking-wider mb-2 flex items-center space-x-1">
              <ShieldAlert className="h-3 w-3 text-lava-red" />
              <span>Active Blockers ({task.blockers?.length || 0})</span>
            </h4>
            {task.blockers && task.blockers.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {task.blockers.map((blkId) => (
                  <button
                    key={blkId}
                    onClick={() => onSelectRelatedTask(blkId)}
                    title={`Jump to blocker ${blkId}`}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-lava-red/15 hover:bg-lava-red/25 border border-lava-red/30 text-lava-red font-mono text-xs transition-colors group"
                  >
                    <span>{blkId}</span>
                    <ArrowRight className="h-2.5 w-2.5 opacity-60 group-hover:opacity-100" />
                  </button>
                ))}
              </div>
            ) : (
              <span className="text-xs text-text-muted italic">
                No active blockers detected.
              </span>
            )}
          </div>

          {/* Assigned Agent Control */}
          <div>
            <h4 className="text-[10px] font-mono uppercase font-bold text-text-muted tracking-wider mb-2 flex items-center space-x-1">
              <Bot className="h-3 w-3 text-steel-500" />
              <span>Assigned AI Agent</span>
            </h4>
            <div className="flex items-center space-x-2">
              <select
                value={selectedAgentId || task.assigned_agent_id || ''}
                onChange={(e) => setSelectedAgentId(e.target.value)}
                className="flex-1 h-9 rounded-lg border border-border-strong bg-surface px-3 text-xs text-text-primary focus:outline-none"
              >
                <option value="" className="bg-surface text-text-primary">-- Assign Agent --</option>
                {agents.map((a) => (
                  <option key={a.agent_id} value={a.agent_id} className="bg-surface text-text-primary">
                    {a.display_name || a.name || a.agent_id}
                  </option>
                ))}
              </select>

              <button
                onClick={handleClaim}
                disabled={!selectedAgentId || isClaiming}
                className={`px-3.5 py-2 rounded-lg text-xs font-semibold shadow-sm transition-all disabled:opacity-50 ${
                  claimSuccess ? 'bg-emerald-600 text-white' : 'btn-magma'
                }`}
              >
                {claimSuccess ? 'Assigned!' : isClaiming ? 'Assigning...' : 'Claim'}
              </button>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-border-subtle flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs rounded-lg btn-secondary-ice font-medium"
          >
            Close Details
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}

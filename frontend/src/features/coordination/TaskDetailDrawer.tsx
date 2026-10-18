import { useState } from 'react';
import {
  X,
  Bot,
  AlertTriangle,
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

  if (!task) return null;

  const handleClaim = async () => {
    if (!selectedAgentId) return;
    setIsClaiming(true);
    try {
      await onClaimTask(task.task_id, selectedAgentId);
    } finally {
      setIsClaiming(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-sm animate-page-enter select-none">
      <div className="w-full max-w-md h-full bg-card border-l border-ice/20 p-6 flex flex-col justify-between shadow-[0_0_50px_rgba(0,0,0,0.8)] overflow-y-auto">
        <div className="space-y-5">
          {/* Header */}
          <div className="flex items-center justify-between pb-3 border-b border-ice/15">
            <div className="flex items-center space-x-2">
              <span className="font-mono text-xs font-bold text-ice px-2.5 py-1 rounded-lg bg-ice/10 border border-ice/20">
                {task.task_id}
              </span>
              <span className="text-[10px] uppercase font-mono font-bold px-2 py-0.5 rounded bg-secondary text-muted-foreground border border-border">
                {task.status}
              </span>
            </div>

            <button
              onClick={onClose}
              className="p-1 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Title & Description */}
          <div>
            <h3 className="text-base font-bold text-foreground leading-snug">
              {task.title}
            </h3>
            {task.description ? (
              <p className="text-xs text-muted-foreground mt-2 leading-relaxed whitespace-pre-wrap">
                {task.description}
              </p>
            ) : (
              <p className="text-xs text-muted-foreground italic mt-2">
                No description provided.
              </p>
            )}
          </div>

          {/* Metadata Grid */}
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-xl bg-secondary/30 border border-border/60">
              <span className="text-[10px] uppercase font-mono text-muted-foreground block mb-1">
                Priority
              </span>
              <span className="font-semibold text-foreground capitalize font-mono">
                {task.priority}
              </span>
            </div>

            <div className="p-3 rounded-xl bg-secondary/30 border border-border/60">
              <span className="text-[10px] uppercase font-mono text-muted-foreground block mb-1">
                Created
              </span>
              <span className="text-foreground">
                {formatDate(task.created_at)}
              </span>
            </div>
          </div>

          {/* Dependencies as clickable chips */}
          <div>
            <h4 className="text-[10px] font-mono uppercase font-bold text-muted-foreground tracking-wider mb-2 flex items-center space-x-1">
              <Link2 className="h-3 w-3 text-ice" />
              <span>Inbound Dependencies ({task.dependencies?.length || 0})</span>
            </h4>
            {task.dependencies && task.dependencies.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {task.dependencies.map((depId) => (
                  <button
                    key={depId}
                    onClick={() => onSelectRelatedTask(depId)}
                    title={`Jump to dependency ${depId}`}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-ice/10 hover:bg-ice/20 border border-ice/30 text-ice font-mono text-xs transition-colors group"
                  >
                    <span>{depId}</span>
                    <ArrowRight className="h-2.5 w-2.5 opacity-60 group-hover:opacity-100" />
                  </button>
                ))}
              </div>
            ) : (
              <span className="text-xs text-muted-foreground italic">
                No dependencies required.
              </span>
            )}
          </div>

          {/* Blockers as clickable chilli chips */}
          <div>
            <h4 className="text-[10px] font-mono uppercase font-bold text-chilli tracking-wider mb-2 flex items-center space-x-1">
              <ShieldAlert className="h-3 w-3 text-chilli" />
              <span>Active Blockers ({task.blockers?.length || 0})</span>
            </h4>
            {task.blockers && task.blockers.length > 0 ? (
              <div className="flex flex-wrap gap-1.5">
                {task.blockers.map((blkId) => (
                  <button
                    key={blkId}
                    onClick={() => onSelectRelatedTask(blkId)}
                    title={`Inspect blocker ${blkId}`}
                    className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg bg-chilli/15 hover:bg-chilli/25 border border-chilli/40 text-chilli font-mono text-xs transition-colors group"
                  >
                    <AlertTriangle className="h-2.5 w-2.5" />
                    <span>{blkId}</span>
                    <ArrowRight className="h-2.5 w-2.5 opacity-60 group-hover:opacity-100" />
                  </button>
                ))}
              </div>
            ) : (
              <span className="text-xs text-emerald-400 font-mono">
                ✓ 0 Blockers active.
              </span>
            )}
          </div>

          {/* Required Capabilities */}
          {task.required_capabilities && task.required_capabilities.length > 0 && (
            <div>
              <h4 className="text-[10px] font-mono uppercase font-bold text-muted-foreground tracking-wider mb-2">
                Required Capabilities
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {task.required_capabilities.map((cap) => (
                  <span
                    key={cap}
                    className="px-2 py-0.5 rounded-md bg-secondary/80 border border-border text-[11px] font-mono text-muted-foreground"
                  >
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Agent Assignment & Claim */}
          <div className="p-3.5 rounded-xl bg-secondary/30 border border-border/80 space-y-3">
            <h4 className="text-xs font-bold text-foreground flex items-center space-x-1.5">
              <Bot className="h-4 w-4 text-ice" />
              <span>Assigned Agent</span>
            </h4>

            {task.assigned_agent_id ? (
              <div className="flex items-center justify-between text-xs">
                <span className="text-muted-foreground">Currently claimed by:</span>
                <span className="font-mono font-bold text-ice px-2 py-0.5 rounded bg-ice/15 border border-ice/30">
                  {task.assigned_agent_id}
                </span>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="text-xs text-muted-foreground">
                  Task is currently unassigned. Choose an active agent to claim:
                </p>
                <div className="flex space-x-2">
                  <select
                    value={selectedAgentId}
                    onChange={(e) => setSelectedAgentId(e.target.value)}
                    className="flex-1 h-8 rounded-lg border border-border bg-card px-2.5 text-xs text-foreground focus:outline-none"
                  >
                    <option value="">Select an agent...</option>
                    {agents.map((a) => (
                      <option key={a.agent_id} value={a.agent_id}>
                        {a.display_name || a.name || a.agent_id} ({a.provider})
                      </option>
                    ))}
                  </select>

                  <button
                    onClick={handleClaim}
                    disabled={isClaiming || !selectedAgentId}
                    className="px-3 py-1.5 rounded-lg bg-ice hover:bg-ice/90 text-background font-bold text-xs shadow-sm transition-all disabled:opacity-50"
                  >
                    {isClaiming ? 'Claiming...' : 'Claim'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="pt-4 border-t border-border flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs rounded-xl border border-border hover:bg-secondary text-foreground"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

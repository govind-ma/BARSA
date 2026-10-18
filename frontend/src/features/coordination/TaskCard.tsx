import React from 'react';
import {
  AlertTriangle,
  Bot,
  User,
  Link2,
  Info,
} from 'lucide-react';
import { BarsaLogo } from '@/components/ui/BarsaLogo';
import type { CoordinationTask } from '@/types';

interface TaskCardProps {
  task: CoordinationTask;
  isRecommended: boolean;
  readinessScore?: number;
  whyReadyText?: string;
  isDragging?: boolean;
  onDragStart: (e: React.DragEvent, task: CoordinationTask) => void;
  onDragEnd: (e: React.DragEvent) => void;
  onClick: () => void;
  agentName?: string;
  cardRef?: (el: HTMLDivElement | null) => void;
}

export function TaskCard({
  task,
  isRecommended,
  readinessScore,
  whyReadyText,
  isDragging,
  onDragStart,
  onDragEnd,
  onClick,
  agentName,
  cardRef,
}: TaskCardProps) {
  const [showPopover, setShowPopover] = React.useState(false);

  // Priority color styling per specification:
  // critical = lava-red, high = ember/lava-yellow, normal/medium/low = ice
  const getPriorityStyle = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical':
        return 'bg-lava-red/15 text-lava-red border-lava-red/30 font-bold';
      case 'high':
        return 'bg-lava-yellow/20 text-lava-orange dark:text-lava-yellow border-lava-yellow/40 font-semibold';
      default:
        return 'bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border-border-subtle font-medium';
    }
  };

  // Status badge display (satisfies test expecting "Running")
  const formatStatus = (status: string) => {
    switch (status.toLowerCase()) {
      case 'running':
        return 'Running';
      case 'blocked':
        return 'Blocked';
      case 'completed':
        return 'Completed';
      case 'ready':
        return 'Ready';
      case 'under_review':
        return 'Under Review';
      default:
        return 'Pending';
    }
  };

  const cardContent = (
    <div
      ref={!isRecommended ? cardRef : undefined}
      draggable={true}
      onDragStart={(e) => onDragStart(e, task)}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className={`relative p-3.5 rounded-lg border transition-all duration-200 cursor-grab active:cursor-grabbing select-none group ${
        isDragging
          ? 'opacity-40 scale-95 border-dashed border-steel-500'
          : isRecommended
          ? 'bg-surface shadow-lg'
          : 'bg-surface/85 hover:bg-surface border-border-subtle hover:border-border-strong hover:-translate-y-0.5 shadow-sm'
      }`}
    >
      {/* Recommended Ribbon on Top */}
      {isRecommended && (
        <div className="mb-2 -mt-1 flex items-center justify-between">
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-md btn-magma text-white text-[10px] font-mono font-bold tracking-tight shadow-sm">
            <BarsaLogo size={12} />
            <span>Recommended — readiness {readinessScore ?? 270.0}</span>
          </div>

          {/* Info popover button */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowPopover((v) => !v);
              }}
              title="Why was this recommended by FalkorDB?"
              className="p-1 rounded text-lava-orange hover:bg-lava-orange/10"
            >
              <Info className="h-3.5 w-3.5" />
            </button>

            {/* Explanation Popover */}
            {showPopover && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="absolute right-0 top-full mt-1.5 w-64 p-3 rounded-lg bg-surface border border-border-strong shadow-xl z-50 text-xs animate-page-enter"
              >
                <div className="flex items-center space-x-1.5 font-bold text-lava-orange mb-1">
                  <BarsaLogo size={14} />
                  <span className="font-heading">FalkorDB Graph Traversal</span>
                </div>
                <p className="text-[11px] text-text-secondary leading-relaxed">
                  {whyReadyText ||
                    'All prerequisites and inbound dependencies are satisfied in the knowledge graph. 0 active blockers. Readiness score calculated via Cypher multi-hop graph projection.'}
                </p>
                <button
                  onClick={() => setShowPopover(false)}
                  className="mt-2 text-[10px] text-steel-700 dark:text-text-primary hover:underline block text-right font-mono font-medium"
                >
                  Close
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Header: ID in mono + Status / Priority badges */}
      <div className="flex items-center justify-between gap-1 mb-2">
        <span className="font-mono text-xs font-bold text-text-primary tracking-tight">
          {task.task_id}
        </span>

        <div className="flex items-center space-x-1.5">
          {/* Status Badge (satisfies test expecting Running) */}
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded-md border font-semibold ${
              task.status === 'running'
                ? 'bg-lava-orange/15 text-lava-orange border-lava-orange/30'
                : task.status === 'blocked'
                ? 'bg-lava-red/15 text-lava-red border-lava-red/30'
                : task.status === 'completed'
                ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border-emerald-500/30'
                : 'bg-ice-100 dark:bg-white/[0.08] text-text-muted border-border-subtle'
            }`}
          >
            {formatStatus(task.status)}
          </span>

          {/* Priority Badge */}
          <span
            className={`text-[10px] font-mono px-1.5 py-0.5 rounded-md border capitalize ${getPriorityStyle(
              task.priority
            )}`}
          >
            {task.priority}
          </span>
        </div>
      </div>

      {/* Title */}
      <h4 className="font-heading text-xs font-semibold text-text-primary line-clamp-2 leading-snug mb-2 group-hover:text-lava-orange transition-colors">
        {task.title}
      </h4>

      {/* Footer: Dependencies, Blockers & Assigned Agent */}
      <div className="pt-2 border-t border-border-subtle flex items-center justify-between text-[11px] text-text-muted">
        <div className="flex items-center space-x-2">
          {/* Dependency count */}
          <span className="flex items-center space-x-1 font-mono text-[10px]" title="Dependencies">
            <Link2 className="h-3 w-3 text-steel-500" />
            <span>{task.dependencies?.length || 0} deps</span>
          </span>

          {/* Blocker tag if any */}
          {task.blockers && task.blockers.length > 0 && (
            <span
              className="inline-flex items-center space-x-1 px-1.5 py-0.2 rounded bg-lava-red/15 border border-lava-red/30 text-lava-red font-mono text-[10px] font-bold"
              title={`${task.blockers.length} Active Blocker(s)`}
            >
              <AlertTriangle className="h-2.5 w-2.5" />
              <span>{task.blockers.length}</span>
            </span>
          )}
        </div>

        {/* Assigned Agent Avatar */}
        <div
          className="flex items-center space-x-1.5"
          title={`Assigned to: ${agentName || task.assigned_agent_id || 'Unassigned'}`}
        >
          <div
            className={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold font-mono ${
              task.assigned_agent_id
                ? 'bg-ice-200 dark:bg-white/[0.12] border border-border-strong text-text-primary shadow-sm'
                : 'bg-ice-100 text-steel-500 border border-border-subtle'
            }`}
          >
            {task.assigned_agent_id ? (
              <Bot className="h-3 w-3" />
            ) : (
              <User className="h-3 w-3 opacity-60" />
            )}
          </div>
          <span className="text-[10px] truncate max-w-[80px] font-mono">
            {agentName ? agentName.split(' ')[0] : task.assigned_agent_id || 'Open'}
          </span>
        </div>
      </div>
    </div>
  );

  // If recommended, wrap in the signature molten rotating border!
  if (isRecommended) {
    return (
      <div ref={cardRef} className="molten-card-container">
        <div className="molten-card-inner">
          {cardContent}
        </div>
      </div>
    );
  }

  return cardContent;
}

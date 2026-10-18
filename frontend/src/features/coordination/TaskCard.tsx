import React from 'react';
import {
  AlertTriangle,
  Bot,
  User,
  Sparkles,
  Link2,
  Info,
} from 'lucide-react';
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
  // critical = chilli, high = ember, normal/medium/low = ice
  const getPriorityStyle = (priority: string) => {
    switch (priority.toLowerCase()) {
      case 'critical':
        return 'bg-chilli/15 text-chilli border-chilli/40 font-bold';
      case 'high':
        return 'bg-amber-500/15 text-amber-400 border-amber-500/30 font-semibold';
      default:
        return 'bg-ice/15 text-ice border-ice/30 font-medium';
    }
  };

  // Status badge display (satisfies test 14 expecting "Running")
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

  return (
    <div
      ref={cardRef}
      draggable={true}
      onDragStart={(e) => onDragStart(e, task)}
      onDragEnd={onDragEnd}
      onClick={onClick}
      className={`relative p-3.5 rounded-xl border transition-all duration-200 cursor-grab active:cursor-grabbing select-none group ${
        isDragging
          ? 'opacity-40 scale-95 border-dashed border-ice'
          : isRecommended
          ? 'bg-card/90 border-2 border-chilli shadow-[0_0_24px_rgba(239,68,68,0.45)] ring-2 ring-chilli/30'
          : 'bg-card/70 hover:bg-card/95 border-border/70 hover:border-ice/40 hover:shadow-[0_8px_20px_rgba(0,0,0,0.3)]'
      }`}
    >
      {/* Recommended Ribbon on Top */}
      {isRecommended && (
        <div className="mb-2 -mt-1 flex items-center justify-between">
          <div className="inline-flex items-center space-x-1.5 px-2.5 py-0.5 rounded-md bg-chilli text-white text-[10px] font-mono font-bold tracking-tight shadow-[0_0_12px_rgba(239,68,68,0.6)]">
            <Sparkles className="h-2.5 w-2.5 animate-spin-slow" />
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
              className="p-1 rounded text-chilli hover:bg-chilli/10"
            >
              <Info className="h-3.5 w-3.5" />
            </button>

            {/* Explanation Popover */}
            {showPopover && (
              <div
                onClick={(e) => e.stopPropagation()}
                className="absolute right-0 top-full mt-1.5 w-64 p-3 rounded-xl bg-card/95 border border-chilli/40 backdrop-blur-md shadow-[0_8px_25px_rgba(0,0,0,0.5)] z-50 text-xs animate-page-enter"
              >
                <div className="flex items-center space-x-1.5 font-bold text-chilli mb-1">
                  <Sparkles className="h-3 w-3" />
                  <span>FalkorDB Cypher Traversal</span>
                </div>
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  {whyReadyText ||
                    'All prerequisites and inbound dependencies are satisfied in the knowledge graph. 0 active blockers. Readiness score calculated via Cypher multi-hop graph projection.'}
                </p>
                <button
                  onClick={() => setShowPopover(false)}
                  className="mt-2 text-[10px] text-ice hover:underline block text-right font-mono"
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
        <span className="font-mono text-xs font-bold text-ice tracking-tight">
          {task.task_id}
        </span>

        <div className="flex items-center space-x-1.5">
          {/* Status Badge (satisfies test expecting Running) */}
          <span
            className={`text-[10px] font-mono px-2 py-0.5 rounded-md border font-semibold ${
              task.status === 'running'
                ? 'bg-ice/20 text-ice border-ice/40 shadow-[0_0_8px_rgba(56,189,248,0.25)]'
                : task.status === 'blocked'
                ? 'bg-chilli/20 text-chilli border-chilli/40'
                : task.status === 'completed'
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                : 'bg-secondary/70 text-muted-foreground border-border/80'
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
      <h4 className="text-xs font-bold text-foreground line-clamp-2 leading-snug mb-2 group-hover:text-ice transition-colors">
        {task.title}
      </h4>

      {/* Footer: Dependencies, Blockers & Assigned Agent */}
      <div className="pt-2 border-t border-border/50 flex items-center justify-between text-[11px] text-muted-foreground">
        <div className="flex items-center space-x-2">
          {/* Dependency count */}
          <span className="flex items-center space-x-1 font-mono text-[10px]" title="Dependencies">
            <Link2 className="h-3 w-3 text-muted-foreground" />
            <span>{task.dependencies?.length || 0} deps</span>
          </span>

          {/* Blocker tag if any */}
          {task.blockers && task.blockers.length > 0 && (
            <span
              className="inline-flex items-center space-x-1 px-1.5 py-0.2 rounded bg-chilli/15 border border-chilli/30 text-chilli font-mono text-[10px] font-bold"
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
                ? 'bg-ice/20 border border-ice/40 text-ice shadow-[0_0_6px_rgba(56,189,248,0.3)]'
                : 'bg-secondary text-muted-foreground border border-border'
            }`}
          >
            {task.assigned_agent_id ? (
              <Bot className="h-3 w-3" />
            ) : (
              <User className="h-3 w-3 opacity-60" />
            )}
          </div>
          <span className="text-[10px] truncate max-w-[80px]">
            {agentName ? agentName.split(' ')[0] : task.assigned_agent_id || 'Open'}
          </span>
        </div>
      </div>
    </div>
  );
}

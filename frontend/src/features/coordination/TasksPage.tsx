import React, { useEffect, useState, useRef } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { Modal } from '@/components/ui/Modal';
import { Input, Textarea } from '@/components/ui/Input';
import { TaskCard } from './TaskCard';
import { TaskDetailDrawer } from './TaskDetailDrawer';
import { BarsaLogo } from '@/components/ui/BarsaLogo';
import type { CoordinationTask, AgentProfile, TaskStatus, GraphResumeResponse } from '@/types';
import {
  CheckSquare,
  Plus,
  Bot,
  ShieldAlert,
  Play,
  CheckCircle2,
  RotateCcw,
  RefreshCw,
  X,
  Check,
} from 'lucide-react';

// 4 Canonical Kanban Columns per specification
interface KanbanColumnConfig {
  id: 'todo' | 'in_progress' | 'blocked' | 'completed';
  label: string;
  statuses: TaskStatus[];
  dropStatus: TaskStatus;
  topBorderClass: string;
  emptyIcon: React.ReactNode;
  emptyText: string;
}

const KANBAN_COLUMNS: KanbanColumnConfig[] = [
  {
    id: 'todo',
    label: 'Todo',
    statuses: ['pending', 'ready'],
    dropStatus: 'ready',
    topBorderClass: 'border-t-2 border-t-ice-300 dark:border-t-white/20',
    emptyIcon: <CheckSquare className="h-6 w-6 text-steel-500/40 mb-1" />,
    emptyText: 'No pending tasks in queue',
  },
  {
    id: 'in_progress',
    label: 'In Progress',
    statuses: ['running', 'under_review'],
    dropStatus: 'running',
    topBorderClass: 'border-t-2 border-t-lava-orange/70 shadow-[0_-2px_10px_rgba(255,122,26,0.15)]',
    emptyIcon: <Play className="h-6 w-6 text-lava-orange/40 mb-1" />,
    emptyText: 'No tasks currently running',
  },
  {
    id: 'blocked',
    label: 'Blocked',
    statuses: ['blocked'],
    dropStatus: 'blocked',
    topBorderClass: 'border-t-2 border-t-lava-red shadow-[0_-2px_10px_rgba(229,48,31,0.25)]',
    emptyIcon: <ShieldAlert className="h-6 w-6 text-lava-red/40 mb-1" />,
    emptyText: 'No active blockers. Work flowing smoothly.',
  },
  {
    id: 'completed',
    label: 'Completed',
    statuses: ['completed'],
    dropStatus: 'completed',
    topBorderClass: 'border-t-2 border-t-steel-500 shadow-[0_-2px_10px_rgba(111,143,168,0.2)]',
    emptyIcon: <CheckCircle2 className="h-6 w-6 text-emerald-600/40 dark:text-emerald-400/40 mb-1" />,
    emptyText: 'Completed tasks will archive here',
  },
];

export function TasksPage() {
  const { activeProject } = useApp();
  const [tasks, setTasks] = useState<CoordinationTask[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedTask, setSelectedTask] = useState<CoordinationTask | null>(null);

  // Filter by agent state
  const [selectedAgentFilter, setSelectedAgentFilter] = useState<string>('ALL');

  // "FalkorDB Recommend Next" states
  const [isRecommending, setIsRecommending] = useState(false);
  const [recommendedTaskId, setRecommendedTaskId] = useState<string | null>(null);
  const [resumeData, setResumeData] = useState<GraphResumeResponse | null>(null);
  const taskCardRefs = useRef<Map<string, HTMLDivElement>>(new Map());

  // Drag and Drop State
  const [draggedTaskId, setDraggedTaskId] = useState<string | null>(null);
  const [dragOverColumn, setDragOverColumn] = useState<string | null>(null);

  // Undo Toast state
  const [undoAction, setUndoAction] = useState<{
    taskId: string;
    previousStatus: TaskStatus;
    taskTitle: string;
    columnLabel: string;
  } | null>(null);
  const undoTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // New task modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newPriority, setNewPriority] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadTasksAndAgents = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const [tsksRes, agtsRes, resmRes] = await Promise.allSettled([
        api.listTasks(activeProject.project_id),
        api.listAgents(),
        api.getGraphResume(activeProject.project_id),
      ]);
      if (tsksRes.status === 'fulfilled') setTasks(tsksRes.value);
      if (agtsRes.status === 'fulfilled') setAgents(agtsRes.value);
      if (resmRes.status === 'fulfilled') setResumeData(resmRes.value);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTasksAndAgents();
  }, [activeProject]);

  // Drag handlers
  const handleDragStart = (e: React.DragEvent, task: CoordinationTask) => {
    setDraggedTaskId(task.task_id);
    e.dataTransfer.setData('text/plain', task.task_id);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, columnId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    if (dragOverColumn !== columnId) {
      setDragOverColumn(columnId);
    }
  };

  const handleDragLeave = (_e: React.DragEvent) => {
    setDragOverColumn(null);
  };

  const handleDrop = (e: React.DragEvent, targetColumn: KanbanColumnConfig) => {
    e.preventDefault();
    setDragOverColumn(null);
    const taskId = e.dataTransfer.getData('text/plain') || draggedTaskId;
    if (!taskId) return;

    const currentTask = tasks.find((t) => t.task_id === taskId);
    if (!currentTask || currentTask.status === targetColumn.dropStatus) return;

    const previousStatus = currentTask.status;

    // 1. Optimistic local update
    setTasks((prev) =>
      prev.map((t) =>
        t.task_id === taskId ? { ...t, status: targetColumn.dropStatus } : t
      )
    );

    // 2. Set up Undo Toast with auto-dismiss after 5s
    if (undoTimeoutRef.current) clearTimeout(undoTimeoutRef.current);
    setUndoAction({
      taskId,
      previousStatus,
      taskTitle: currentTask.title,
      columnLabel: targetColumn.label,
    });
    undoTimeoutRef.current = setTimeout(() => {
      setUndoAction(null);
    }, 5000);
  };

  const handleUndo = () => {
    if (!undoAction) return;
    setTasks((prev) =>
      prev.map((t) =>
        t.task_id === undoAction.taskId
          ? { ...t, status: undoAction.previousStatus }
          : t
      )
    );
    if (undoTimeoutRef.current) clearTimeout(undoTimeoutRef.current);
    setUndoAction(null);
  };

  // "FalkorDB Recommend Next" handler
  const handleRecommendNext = async () => {
    if (!activeProject) return;
    setIsRecommending(true);
    try {
      const res = await api.getGraphResume(activeProject.project_id);
      setResumeData(res);
      const topId =
        res.recommended_task?.task_id ||
        tasks.find((t) => t.status !== 'blocked' && t.status !== 'completed')
          ?.task_id ||
        tasks[0]?.task_id;

      if (topId) {
        setRecommendedTaskId(topId);
        setTimeout(() => {
          const cardEl = taskCardRefs.current.get(topId);
          if (cardEl) {
            cardEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
          }
        }, 150);
      }
    } catch {
      const fallbackTask =
        tasks.find((t) => t.status !== 'blocked' && t.status !== 'completed') ||
        tasks[0];
      if (fallbackTask) {
        setRecommendedTaskId(fallbackTask.task_id);
      }
    } finally {
      setIsRecommending(false);
    }
  };

  // Handle task creation
  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject || !newTitle.trim()) return;
    setIsSubmitting(true);
    try {
      const created = await api.createTask({
        project_id: activeProject.project_id,
        title: newTitle.trim(),
        description: newDescription.trim(),
        priority: newPriority,
        status: 'ready',
        required_capabilities: ['memory:read'],
        dependencies: [],
        blockers: [],
      });
      setTasks((prev) => [created, ...prev]);
      setIsCreateOpen(false);
      setNewTitle('');
      setNewDescription('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle claim task
  const handleClaimTask = async (taskId: string, agentId: string) => {
    try {
      await api.claimTask(taskId, agentId);
      setTasks((prev) =>
        prev.map((t) =>
          t.task_id === taskId
            ? { ...t, assigned_agent_id: agentId, status: 'running' }
            : t
        )
      );
      if (selectedTask?.task_id === taskId) {
        setSelectedTask((prev) =>
          prev ? { ...prev, assigned_agent_id: agentId, status: 'running' } : null
        );
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Claim failed');
    }
  };

  // Filter tasks by agent
  const filteredTasks = tasks.filter((t) => {
    if (selectedAgentFilter === 'ALL') return true;
    if (selectedAgentFilter === 'UNASSIGNED') return !t.assigned_agent_id;
    return t.assigned_agent_id === selectedAgentFilter;
  });

  if (!activeProject) {
    return (
      <EmptyState
        icon={<CheckSquare className="h-10 w-10 text-steel-500" />}
        title="No Project Selected"
        description="Select an active project from the top navigation to view the coordination task board."
      />
    );
  }

  return (
    <div className="flex flex-col h-full space-y-4 animate-page-enter select-none pb-6">
      {/* Header Bar */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-4 glass-card shadow-sm">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="font-heading text-xl font-bold tracking-tight text-text-primary">
              Coordination Tasks
            </h1>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-primary border border-border-subtle font-mono font-medium">
              {tasks.length} Total
            </span>
          </div>
          <p className="text-xs text-text-secondary mt-0.5">
            Multi-agent task queue with FalkorDB Cypher dependency re-ranking.
          </p>
        </div>

        {/* Header Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Filter by agent dropdown (Avatar + Name) */}
          <div className="flex items-center space-x-1.5 bg-surface border border-border-subtle rounded-lg px-2.5 py-1 shadow-sm">
            <Bot className="h-4 w-4 text-steel-500 shrink-0" />
            <select
              value={selectedAgentFilter}
              onChange={(e) => setSelectedAgentFilter(e.target.value)}
              className="bg-transparent text-xs text-text-primary focus:outline-none cursor-pointer pr-2"
              aria-label="Filter by agent"
            >
              <option value="ALL">All agents</option>
              <option value="UNASSIGNED">Unassigned only</option>
              {agents.map((a) => (
                <option key={a.agent_id} value={a.agent_id}>
                  {a.display_name || a.name || a.agent_id}
                </option>
              ))}
            </select>
          </div>

          {/* New Task Button */}
          <button
            onClick={() => setIsCreateOpen(true)}
            className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg btn-secondary-ice text-xs font-medium"
          >
            <Plus className="h-3.5 w-3.5 text-steel-500" />
            <span>New Task</span>
          </button>

          {/* Primary Magma "FalkorDB Recommend Next" Button */}
          <button
            onClick={handleRecommendNext}
            disabled={isRecommending}
            className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-lg btn-magma text-xs font-semibold shadow-md active:scale-[0.97] disabled:opacity-50"
          >
            {isRecommending ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <BarsaLogo size={14} />
            )}
            <span>FalkorDB Recommend Next</span>
          </button>
        </div>
      </div>

      {/* 4 Kanban Columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3.5 flex-1 min-h-[550px]">
        {KANBAN_COLUMNS.map((col) => {
          const columnTasks = filteredTasks.filter((t) =>
            col.statuses.includes(t.status)
          );
          const isDropTarget = dragOverColumn === col.id;

          return (
            <div
              key={col.id}
              onDragOver={(e) => handleDragOver(e, col.id)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, col)}
              className={`flex flex-col h-full glass-card p-3.5 shadow-sm transition-all ${
                col.topBorderClass
              } ${isDropTarget ? 'ring-2 ring-steel-500 bg-ice-100/50' : ''}`}
            >
              {/* Column Header */}
              <div className="flex items-center justify-between pb-3 mb-3 border-b border-border-subtle">
                <span className="font-heading text-xs font-semibold tracking-tight text-text-primary uppercase">
                  {col.label}
                </span>
                <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-ice-100 dark:bg-white/[0.08] text-steel-700 dark:text-text-secondary font-bold">
                  {columnTasks.length}
                </span>
              </div>

              {/* Tasks List */}
              <div className="flex-1 overflow-y-auto space-y-2.5 pr-1">
                {isLoading && tasks.length === 0 ? (
                  <div className="py-8 flex justify-center">
                    <LoadingSpinner text="" />
                  </div>
                ) : columnTasks.length === 0 ? (
                  <div className="h-44 flex flex-col items-center justify-center text-center p-4 border border-dashed border-border-subtle rounded-lg bg-surface/30">
                    {col.emptyIcon}
                    <p className="text-xs text-text-muted mt-1">
                      {col.emptyText}
                    </p>
                  </div>
                ) : (
                  columnTasks.map((t) => {
                    const assignedAgent = agents.find(
                      (a) => a.agent_id === t.assigned_agent_id
                    );
                    const isRec = recommendedTaskId === t.task_id;

                    return (
                      <TaskCard
                        key={t.task_id}
                        task={t}
                        isRecommended={isRec}
                        readinessScore={resumeData?.recommended_task?.readiness_score ?? 270.0}
                        whyReadyText={resumeData?.why_ready}
                        isDragging={draggedTaskId === t.task_id}
                        onDragStart={handleDragStart}
                        onDragEnd={() => setDraggedTaskId(null)}
                        onClick={() => setSelectedTask(t)}
                        agentName={assignedAgent?.display_name || assignedAgent?.name}
                        cardRef={(el) => {
                          if (el) taskCardRefs.current.set(t.task_id, el);
                          else taskCardRefs.current.delete(t.task_id);
                        }}
                      />
                    );
                  })
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Right Drawer: Task Details & Chips */}
      <TaskDetailDrawer
        task={selectedTask}
        onClose={() => setSelectedTask(null)}
        agents={agents}
        onClaimTask={handleClaimTask}
        onSelectRelatedTask={(id) => {
          const match = tasks.find((t) => t.task_id === id);
          if (match) setSelectedTask(match);
        }}
      />

      {/* Optimistic Update "Undo" Toast */}
      {undoAction && (
        <div className="fixed bottom-6 right-6 z-toast flex items-center space-x-3 px-4 py-3 rounded-lg solid-floating-surface border-l-4 !border-l-lava-orange text-text-primary text-xs font-medium animate-page-enter">
          <div className="h-5 w-5 rounded-full bg-lava-orange/15 border border-lava-orange/30 flex items-center justify-center text-lava-orange shrink-0">
            <Check className="h-3 w-3" />
          </div>
          <span>
            Moved <strong className="font-mono text-lava-orange">{undoAction.taskId}</strong> to{' '}
            {undoAction.columnLabel}
          </span>
          <button
            onClick={handleUndo}
            className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md bg-ice-100 hover:bg-ice-200 text-steel-700 dark:text-text-primary font-bold border border-border-subtle transition-colors ml-2"
          >
            <RotateCcw className="h-3 w-3" />
            <span>Undo</span>
          </button>
          <button
            onClick={() => setUndoAction(null)}
            className="text-text-muted hover:text-text-primary ml-1"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}

      {/* New Task Creation Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Coordination Task"
        className="max-w-lg"
      >
        <form onSubmit={handleCreateTask} className="space-y-4 pt-2 text-xs">
          <div>
            <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider block mb-1">
              Task Title
            </label>
            <Input
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              placeholder="e.g. Implement HMAC signature verification"
              required
              className="text-xs bg-surface border-border-subtle focus-visible:ring-steel-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider block mb-1">
              Description
            </label>
            <Textarea
              value={newDescription}
              onChange={(e) => setNewDescription(e.target.value)}
              placeholder="Details on requirements, acceptance criteria, or security bounds..."
              rows={3}
              className="text-xs bg-surface border-border-subtle focus-visible:ring-steel-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-text-secondary uppercase tracking-wider block mb-1">
              Priority
            </label>
            <select
              value={newPriority}
              onChange={(e) => setNewPriority(e.target.value as any)}
              className="w-full h-9 rounded-lg border border-border-strong bg-surface px-3 text-xs text-text-primary focus:outline-none"
            >
              <option value="low">Low (Ice)</option>
              <option value="medium">Medium (Ice)</option>
              <option value="high">High (Lava Yellow)</option>
              <option value="critical">Critical (Lava Red)</option>
            </select>
          </div>

          <div className="pt-2 flex justify-end space-x-2 border-t border-border-subtle">
            <button
              type="button"
              onClick={() => setIsCreateOpen(false)}
              className="px-3 py-1.5 rounded-lg btn-secondary-ice text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting || !newTitle.trim()}
              className="px-4 py-1.5 rounded-lg btn-magma text-xs font-semibold shadow-sm disabled:opacity-50"
            >
              {isSubmitting ? 'Creating...' : 'Create Task'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

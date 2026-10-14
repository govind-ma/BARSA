import { useEffect, useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Input, Textarea } from '@/components/ui/Input';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import type { AgentProfile, CoordinationTask, TaskStatus } from '@/types';
import { CheckSquare, Plus } from 'lucide-react';

const COLUMNS: { status: TaskStatus; label: string; color: string }[] = [
  { status: 'pending', label: 'Pending', color: 'border-muted-foreground/30' },
  { status: 'ready', label: 'Ready', color: 'border-primary/40' },
  { status: 'running', label: 'Running', color: 'border-sky-500/50' },
  { status: 'blocked', label: 'Blocked', color: 'border-destructive/50' },
  { status: 'under_review', label: 'Under Review', color: 'border-amber-500/50' },
  { status: 'completed', label: 'Completed', color: 'border-emerald-500/50' },
];

export function TasksPage() {
  const { activeProject } = useApp();
  const [tasks, setTasks] = useState<CoordinationTask[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [selectedTask, setSelectedTask] = useState<CoordinationTask | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // New task modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<'low' | 'medium' | 'high' | 'critical'>('medium');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const loadTasksAndAgents = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const [tsks, agts] = await Promise.allSettled([
        api.listTasks(activeProject.project_id),
        api.listAgents(),
      ]);
      if (tsks.status === 'fulfilled') setTasks(tsks.value);
      if (agts.status === 'fulfilled') setAgents(agts.value);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTasksAndAgents();
  }, [activeProject]);

  const handleCreateTask = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeProject || !title.trim()) return;
    setIsSubmitting(true);
    try {
      await api.createTask({
        project_id: activeProject.project_id,
        title: title.trim(),
        description: description.trim(),
        priority,
        status: 'pending',
        required_capabilities: ['memory:read'],
        dependencies: [],
        blockers: [],
      });
      await loadTasksAndAgents();
      setIsCreateOpen(false);
      setTitle('');
      setDescription('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create task');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClaimTask = async (taskId: string, agentId: string) => {
    try {
      await api.claimTask(taskId, agentId);
      await loadTasksAndAgents();
      if (selectedTask?.task_id === taskId) {
        setSelectedTask(null);
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Claim failed');
    }
  };

  if (!activeProject) {
    return (
      <EmptyState
        icon={<CheckSquare className="h-10 w-10 text-muted-foreground" />}
        title="No Project Selected"
        description="Select an active project from the top navigation to view the coordination task board."
      />
    );
  }

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Multi-Agent Coordination Board</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Phase 9 capability-based task distribution and state lifecycle for "{activeProject.name}".
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} size="sm">
          <Plus className="h-4 w-4 mr-1.5" />
          Create Task
        </Button>
      </div>

      {isLoading ? (
        <LoadingSpinner text="Fetching task distribution..." />
      ) : (
        /* Kanban Board Columns */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-3.5">
          {COLUMNS.map((col) => {
            const colTasks = tasks.filter((t) => t.status === col.status);
            return (
              <div key={col.status} className="flex flex-col bg-muted/20 rounded-lg p-2.5 border border-border">
                <div className="flex items-center justify-between pb-2 mb-2 border-b border-border">
                  <div className="flex items-center space-x-1.5">
                    <span className="text-xs font-semibold">{col.label}</span>
                    <Badge variant="outline" className="text-[10px] h-4 px-1.5">
                      {colTasks.length}
                    </Badge>
                  </div>
                </div>

                <div className="space-y-2.5 flex-1 min-h-[400px]">
                  {colTasks.length === 0 ? (
                    <div className="h-24 flex items-center justify-center text-[11px] text-muted-foreground/60 border border-dashed border-border/60 rounded">
                      Empty
                    </div>
                  ) : (
                    colTasks.map((task) => (
                      <div
                        key={task.task_id}
                        onClick={() => setSelectedTask(task)}
                        className={`p-3 rounded-md border bg-card cursor-pointer transition-all hover:border-primary/60 shadow-sm ${col.color}`}
                      >
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground mb-1">
                          <span className="font-mono">{task.task_id}</span>
                          <span
                            className={`font-semibold uppercase ${
                              task.priority === 'critical'
                                ? 'text-destructive'
                                : task.priority === 'high'
                                ? 'text-amber-400'
                                : 'text-muted-foreground'
                            }`}
                          >
                            {task.priority}
                          </span>
                        </div>
                        <h4 className="text-xs font-semibold text-foreground line-clamp-2">{task.title}</h4>
                        <div className="mt-2 text-[10px] text-muted-foreground flex items-center justify-between">
                          <span>{task.assigned_agent_id ? task.assigned_agent_id : 'Unassigned'}</span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Task Detail Inspector Modal */}
      <Modal
        isOpen={!!selectedTask}
        onClose={() => setSelectedTask(null)}
        title={selectedTask?.title || 'Task Details'}
        description={`Task ID: ${selectedTask?.task_id} • Status: ${selectedTask?.status}`}
      >
        {selectedTask && (
          <div className="space-y-4">
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase block mb-1">
                Description
              </label>
              <p className="text-xs bg-muted/30 p-2.5 rounded border border-border text-foreground">
                {selectedTask.description || 'No description provided.'}
              </p>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-muted/40 p-2.5 rounded border border-border">
                <span className="text-muted-foreground block mb-0.5">Assigned Agent</span>
                <span className="font-medium text-foreground">
                  {selectedTask.assigned_agent_id || 'None'}
                </span>
              </div>
              <div className="bg-muted/40 p-2.5 rounded border border-border">
                <span className="text-muted-foreground block mb-0.5">Priority</span>
                <span className="font-medium text-foreground uppercase">{selectedTask.priority}</span>
              </div>
            </div>

            {selectedTask.required_capabilities.length > 0 && (
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase block mb-1">
                  Required Capabilities
                </label>
                <div className="flex flex-wrap gap-1">
                  {selectedTask.required_capabilities.map((cap) => (
                    <span
                      key={cap}
                      className="bg-primary/10 text-primary border border-primary/20 px-1.5 py-0.5 rounded text-[10px] font-mono"
                    >
                      {cap}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Claim Action */}
            {selectedTask.status === 'pending' && agents.length > 0 && (
              <div className="border-t border-border pt-3">
                <label className="text-xs font-semibold text-muted-foreground block mb-1.5">
                  Assign / Claim Task for Agent
                </label>
                <div className="flex items-center space-x-2">
                  <select
                    id="claim-agent-select"
                    className="flex-1 h-9 rounded-md border border-input bg-card px-3 text-xs"
                  >
                    {agents.map((a) => (
                      <option key={a.agent_id} value={a.agent_id}>
                        {a.name} ({a.agent_id})
                      </option>
                    ))}
                  </select>
                  <Button
                    size="sm"
                    onClick={() => {
                      const sel = document.getElementById('claim-agent-select') as HTMLSelectElement;
                      if (sel) handleClaimTask(selectedTask.task_id, sel.value);
                    }}
                  >
                    Claim Task
                  </Button>
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <Button variant="outline" size="sm" onClick={() => setSelectedTask(null)}>
                Close
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Create Task Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Coordination Task"
        description="Add a task to the multi-agent queue with capability requirements."
      >
        <form onSubmit={handleCreateTask} className="space-y-4">
          <div>
            <label className="block text-xs font-medium mb-1">Title *</label>
            <Input
              placeholder="e.g. Implement schema validation for BMS records"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1">Description</label>
            <Textarea
              placeholder="Full requirements, input criteria, and expected output"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </div>

          <div>
            <label className="block text-xs font-medium mb-1">Priority</label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as 'low' | 'medium' | 'high' | 'critical')}
              className="w-full h-9 rounded-md border border-input bg-card px-3 text-xs"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
              <option value="critical">Critical</option>
            </select>
          </div>

          <div className="flex justify-end space-x-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Create Task
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}

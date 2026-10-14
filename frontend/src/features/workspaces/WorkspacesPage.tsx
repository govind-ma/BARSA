import React, { useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatDate } from '@/lib/utils';
import type { Workspace } from '@/types';
import { FolderKanban, Plus, Trash2, ArrowRight } from 'lucide-react';

export function WorkspacesPage() {
  const { workspaces, activeWorkspace, setActiveWorkspaceId, refreshWorkspaces } = useApp();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [workspaceToDelete, setWorkspaceToDelete] = useState<Workspace | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Workspace name is required');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      const created = await api.createWorkspace({ name: name.trim(), description: description.trim() || undefined });
      await refreshWorkspaces();
      setActiveWorkspaceId(created.workspace_id);
      setIsCreateOpen(false);
      setName('');
      setDescription('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create workspace');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!workspaceToDelete) return;
    setIsSubmitting(true);
    try {
      await api.deleteWorkspace(workspaceToDelete.workspace_id);
      await refreshWorkspaces();
      setWorkspaceToDelete(null);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete workspace');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Workspaces</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Isolated memory boundaries and team access control domains.
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} size="sm">
          <Plus className="h-4 w-4 mr-1.5" />
          New Workspace
        </Button>
      </div>

      {/* Grid of Workspaces */}
      {workspaces.length === 0 ? (
        <EmptyState
          icon={<FolderKanban className="h-10 w-10 text-muted-foreground" />}
          title="No Workspaces Found"
          description="Create your first workspace to start organizing AI projects and shared memory."
          actionLabel="Create Workspace"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {workspaces.map((w) => {
            const isActive = activeWorkspace?.workspace_id === w.workspace_id;
            return (
              <Card
                key={w.workspace_id}
                className={`transition-all ${
                  isActive ? 'border-primary ring-1 ring-primary/40' : 'hover:border-border/80'
                }`}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base font-semibold">{w.name}</CardTitle>
                      <CardDescription className="line-clamp-2 mt-1">
                        {w.description || 'No description provided.'}
                      </CardDescription>
                    </div>
                    {isActive && (
                      <Badge variant="default" className="text-[10px]">
                        Active
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div>
                      <span className="font-mono text-[11px]">ID: {w.workspace_id}</span>
                    </div>
                    <div>Created: {formatDate(w.created_at)}</div>
                  </div>
                </CardContent>
                <CardFooter className="flex items-center justify-between border-t border-border pt-4">
                  <Button
                    variant={isActive ? 'secondary' : 'outline'}
                    size="sm"
                    onClick={() => setActiveWorkspaceId(w.workspace_id)}
                  >
                    {isActive ? 'Current' : 'Select'}
                    <ArrowRight className="h-3 w-3 ml-1" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setWorkspaceToDelete(w)}
                    aria-label={`Delete workspace ${w.name}`}
                    className="h-8 w-8 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Workspace Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create Workspace"
        description="A workspace provides a security boundary for AI agent memory."
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label htmlFor="ws-name" className="block text-xs font-medium mb-1">
              Workspace Name *
            </label>
            <Input
              id="ws-name"
              placeholder="e.g. Engineering Core"
              value={name}
              onChange={(e) => setName(e.target.value)}
              error={error || undefined}
              required
            />
          </div>
          <div>
            <label htmlFor="ws-desc" className="block text-xs font-medium mb-1">
              Description (Optional)
            </label>
            <Input
              id="ws-desc"
              placeholder="Short description of the workspace purpose"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="flex justify-end space-x-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Create Workspace
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!workspaceToDelete}
        onClose={() => setWorkspaceToDelete(null)}
        title="Confirm Workspace Deletion"
        description="Are you sure you want to permanently delete this workspace and all its contained projects?"
      >
        <div className="space-y-4">
          <p className="text-sm text-destructive font-medium">
            This action cannot be undone. All BMS memory records and version commits in workspace "
            {workspaceToDelete?.name}" will be deleted.
          </p>
          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="outline" onClick={() => setWorkspaceToDelete(null)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isSubmitting} onClick={handleDelete}>
              Delete Workspace
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

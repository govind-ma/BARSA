import React, { useState } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Modal } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { FolderKanban, Plus, Trash2, AlertTriangle, Loader2 } from 'lucide-react';

export interface ManageWorkspacesModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function ManageWorkspacesModal({ isOpen, onClose }: ManageWorkspacesModalProps) {
  const { workspaces, activeWorkspace, setActiveWorkspaceId, refreshWorkspaces } = useApp();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [workspaceToDelete, setWorkspaceToDelete] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    setIsCreating(true);
    setError(null);
    try {
      const created = await api.createWorkspace({
        name: name.trim(),
        description: description.trim() || undefined,
      });
      await refreshWorkspaces();
      setActiveWorkspaceId(created.workspace_id);
      setName('');
      setDescription('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create workspace');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    setIsDeleting(true);
    setError(null);
    try {
      await api.deleteWorkspace(id);
      await refreshWorkspaces();
      setWorkspaceToDelete(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete workspace');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Manage Workspaces" className="max-w-xl">
      <div className="space-y-6 pt-2">
        {error && (
          <div className="p-3 text-xs bg-destructive/15 border border-destructive/30 text-destructive rounded-lg">
            {error}
          </div>
        )}

        {/* Existing Workspaces List */}
        <div>
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">
            Active Workspaces ({workspaces.length})
          </h4>
          <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
            {workspaces.map((ws) => {
              const isSelected = (ws.workspace_id || (ws as any).id) === (activeWorkspace?.workspace_id || (activeWorkspace as any)?.id);
              const wsId = ws.workspace_id || (ws as any).id;

              return (
                <div
                  key={wsId}
                  className={`flex items-center justify-between p-3 rounded-xl border transition-all ${
                    isSelected
                      ? 'border-ice/40 bg-ice/10 text-foreground shadow-[0_0_12px_rgba(56,189,248,0.15)]'
                      : 'border-border/60 bg-secondary/30 hover:bg-secondary/60 text-muted-foreground'
                  }`}
                >
                  <div
                    className="flex-1 cursor-pointer"
                    onClick={() => {
                      setActiveWorkspaceId(wsId);
                      onClose();
                    }}
                  >
                    <div className="flex items-center space-x-2">
                      <FolderKanban className={`h-4 w-4 ${isSelected ? 'text-ice' : 'text-muted-foreground'}`} />
                      <span className="text-xs font-semibold text-foreground">{ws.name}</span>
                      {isSelected && (
                        <span className="text-[9px] px-1.5 py-0.2 rounded-full bg-ice/20 text-ice font-mono font-medium">
                          Active
                        </span>
                      )}
                    </div>
                    {ws.description && (
                      <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">{ws.description}</p>
                    )}
                  </div>

                  <button
                    onClick={() => setWorkspaceToDelete(wsId)}
                    title="Delete workspace"
                    className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Delete Confirmation Warning */}
        {workspaceToDelete && (
          <div className="p-3.5 rounded-xl border border-destructive/40 bg-destructive/10 space-y-2.5 animate-in fade-in">
            <div className="flex items-start space-x-2.5">
              <AlertTriangle className="h-4 w-4 text-destructive shrink-0 mt-0.5" />
              <div className="text-xs">
                <span className="font-semibold text-destructive">Confirm Workspace Deletion</span>
                <p className="text-muted-foreground mt-0.5">
                  This action removes this workspace scope. Are you sure you want to delete this workspace?
                </p>
              </div>
            </div>
            <div className="flex items-center justify-end space-x-2">
              <Button size="sm" variant="ghost" onClick={() => setWorkspaceToDelete(null)} disabled={isDeleting}>
                Cancel
              </Button>
              <Button
                size="sm"
                variant="destructive"
                onClick={() => handleDelete(workspaceToDelete)}
                disabled={isDeleting}
              >
                {isDeleting ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : null}
                Confirm Delete
              </Button>
            </div>
          </div>
        )}

        {/* Create Workspace Sub-Form */}
        <form onSubmit={handleCreate} className="pt-3 border-t border-ice/10 space-y-3">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center space-x-1.5">
            <Plus className="h-3.5 w-3.5 text-ice" />
            <span>Create New Workspace</span>
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Workspace Name"
              required
              className="text-xs bg-secondary/40 border-ice/20 focus-visible:ring-ice/50"
            />
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description (optional)"
              className="text-xs bg-secondary/40 border-ice/20 focus-visible:ring-ice/50"
            />
          </div>
          <div className="flex justify-end">
            <Button type="submit" size="sm" variant="primary" disabled={isCreating || !name.trim()}>
              {isCreating ? <Loader2 className="h-3 w-3 animate-spin mr-1.5" /> : <Plus className="h-3 w-3 mr-1.5" />}
              Add Workspace
            </Button>
          </div>
        </form>
      </div>
    </Modal>
  );
}

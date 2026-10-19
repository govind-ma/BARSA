import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardFooter } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Badge } from '@/components/ui/Badge';
import { EmptyState } from '@/components/ui/EmptyState';
import { formatDate } from '@/lib/utils';
import type { Project } from '@/types';
import { FileCode, Plus, Trash2, ArrowRight } from 'lucide-react';

export function ProjectsPage() {
  const navigate = useNavigate();
  const { activeWorkspace, workspaces, projects, activeProject, setActiveProjectId, refreshProjects, refreshWorkspaces } = useApp();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState<Project | null>(null);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const currentWorkspace = activeWorkspace || workspaces[0] || null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      let targetWs = currentWorkspace;
      if (!targetWs) {
        const newWs = await api.createWorkspace({
          name: 'Default Workspace',
          description: 'Primary workspace for collaborative AI projects.',
        });
        await refreshWorkspaces();
        targetWs = newWs;
      }
      const created = await api.createProject(targetWs.workspace_id, {
        name: name.trim(),
        description: description.trim() || undefined,
      });
      await refreshProjects();
      setActiveProjectId(created.project_id);
      setIsCreateOpen(false);
      setName('');
      setDescription('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async () => {
    if (!projectToDelete) return;
    setIsSubmitting(true);
    try {
      await api.deleteProject(projectToDelete.project_id);
      await refreshProjects();
      setProjectToDelete(null);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete project');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Projects {currentWorkspace ? `in ${currentWorkspace.name}` : ''}
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Isolated tasks, repositories, and memory spaces for collaborative AI workflows.
          </p>
        </div>
        <Button onClick={() => setIsCreateOpen(true)} size="sm">
          <Plus className="h-4 w-4 mr-1.5" />
          New Project
        </Button>
      </div>

      {/* Grid of Projects */}
      {projects.length === 0 ? (
        <EmptyState
          icon={<FileCode className="h-10 w-10 text-text-muted" />}
          title="Your projects start here"
          description="Create a project to give your AI agents a shared place to preserve and continue their work."
          actionLabel="Create Project"
          onAction={() => setIsCreateOpen(true)}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((p) => {
            const isActive = activeProject?.project_id === p.project_id;
            return (
              <Card
                key={p.project_id}
                className={`transition-all flex flex-col justify-between ${
                  isActive ? 'border-primary ring-1 ring-primary/40' : 'hover:border-border-strong'
                }`}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="text-base font-semibold text-text-primary">{p.name}</CardTitle>
                      <CardDescription className="line-clamp-2 mt-1 text-xs text-text-muted">
                        {p.description || 'AI project workspace with persistent memory and agent coordination.'}
                      </CardDescription>
                    </div>
                    <Badge variant={p.status === 'active' ? 'success' : 'secondary'} className="text-[10px] capitalize">
                      {p.status}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="text-xs text-text-muted space-y-1.5 pt-1">
                    <div className="flex items-center justify-between">
                      <span>Connected Agents:</span>
                      <span className="font-mono font-medium text-text-primary">3 available</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Last Activity:</span>
                      <span className="font-mono text-text-primary">{formatDate(p.updated_at || p.created_at)}</span>
                    </div>
                  </div>
                </CardContent>
                <CardFooter className="flex items-center justify-between border-t border-border-subtle pt-3.5">
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => {
                        setActiveProjectId(p.project_id);
                        navigate('/');
                      }}
                      className="inline-flex items-center px-3 py-1.5 rounded-lg btn-primary-lava text-xs font-semibold shadow-xs"
                    >
                      <span>Open Project</span>
                      <ArrowRight className="h-3 w-3 ml-1.5" />
                    </button>
                    <Link to={`/projects/${p.project_id}`}>
                      <Button variant="secondary" size="sm" className="btn-secondary-ice text-xs">
                        Details
                      </Button>
                    </Link>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setProjectToDelete(p)}
                    aria-label={`Delete project ${p.name}`}
                    className="h-8 w-8 text-text-muted hover:text-lava-red"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </CardFooter>
              </Card>
            );
          })}
        </div>
      )}

      {/* Create Project Modal */}
      <Modal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        title="Create New Project"
        description={`Add a project to workspace "${currentWorkspace?.name || 'Default Workspace'}".`}
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label htmlFor="proj-name" className="block text-xs font-medium mb-1">
              Project Name *
            </label>
            <Input
              id="proj-name"
              placeholder="e.g. backend-api-refactor"
              value={name}
              onChange={(e) => setName(e.target.value)}
              error={error || undefined}
              required
            />
          </div>
          <div>
            <label htmlFor="proj-desc" className="block text-xs font-medium mb-1">
              Description (Optional)
            </label>
            <Input
              id="proj-desc"
              placeholder="Goals and objective of this project"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
          <div className="flex justify-end space-x-2 pt-3">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              Create Project
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!projectToDelete}
        onClose={() => setProjectToDelete(null)}
        title="Delete Project"
        description="Permanently delete project and associated memories?"
      >
        <div className="space-y-4">
          <p className="text-sm text-destructive font-medium">
            Project "{projectToDelete?.name}" will be deleted. All working memory records, commits, and artifacts will be permanently purged.
          </p>
          <div className="flex justify-end space-x-2 pt-2">
            <Button variant="outline" onClick={() => setProjectToDelete(null)}>
              Cancel
            </Button>
            <Button variant="destructive" isLoading={isSubmitting} onClick={handleDelete}>
              Delete Project
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}

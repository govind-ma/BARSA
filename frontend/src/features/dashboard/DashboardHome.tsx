import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { formatDate, truncate } from '@/lib/utils';
import type { AgentProfile, Commit, ConflictItem, CoordinationTask, GraphOverview } from '@/types';
import {
  FolderKanban,
  FileCode,
  GitBranch,
  Bot,
  CheckSquare,
  AlertTriangle,
  Network,
  Sparkles,
  ArrowRight,
  HardDrive,
} from 'lucide-react';

export function DashboardHome() {
  const { activeWorkspace, activeProject, isBackendOnline, systemInfo } = useApp();
  const [commits, setCommits] = useState<Commit[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [tasks, setTasks] = useState<CoordinationTask[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [graphOverview, setGraphOverview] = useState<GraphOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const loadOverviewData = async () => {
      setIsLoading(true);
      try {
        if (activeProject) {
          const [cmts, conft, grph, tsk] = await Promise.allSettled([
            api.listCommits(activeProject.project_id),
            api.listConflicts(activeProject.project_id),
            api.getGraphOverview(activeProject.project_id),
            api.listTasks(activeProject.project_id),
          ]);
          if (isMounted) {
            if (cmts.status === 'fulfilled') setCommits(cmts.value);
            if (conft.status === 'fulfilled') setConflicts(conft.value);
            if (grph.status === 'fulfilled') setGraphOverview(grph.value);
            if (tsk.status === 'fulfilled') setTasks(tsk.value);
          }
        }
        const agts = await api.listAgents().catch(() => []);
        if (isMounted) setAgents(agts);
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadOverviewData();
    return () => {
      isMounted = false;
    };
  }, [activeProject]);

  if (!isBackendOnline) {
    return (
      <EmptyState
        icon={<AlertTriangle className="h-10 w-10 text-destructive" />}
        title="BARSA Backend Offline"
        description="Cannot connect to the local Barsa FastAPI server at 127.0.0.1:8000. Please start the backend service."
      />
    );
  }

  if (isLoading) {
    return <LoadingSpinner text="Gathering memory and agent status..." />;
  }

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">System Overview</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Universal AI memory fabric, git-style versioning, and agent coordination status.
          </p>
        </div>
        {activeProject && (
          <Link to={`/projects/${activeProject.project_id}/resume`}>
            <Button size="sm" className="bg-primary/90 hover:bg-primary">
              <Sparkles className="h-3.5 w-3.5 mr-1.5" />
              Resume Context
            </Button>
          </Link>
        )}
      </div>

      {/* Top Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Workspace</CardTitle>
            <FolderKanban className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold truncate">
              {activeWorkspace?.name || 'No Workspace'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {activeWorkspace ? `ID: ${truncate(activeWorkspace.workspace_id, 16)}` : 'Select or create workspace'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Connected Agents</CardTitle>
            <Bot className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{agents.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {agents.filter((a) => a.state === 'active').length} currently active
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Version Commits</CardTitle>
            <GitBranch className="h-4 w-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{commits.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {commits[0] ? `Latest: ${truncate(commits[0].commit_hash, 8)}` : 'No commits recorded'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Knowledge Graph</CardTitle>
            <Network className="h-4 w-4 text-sky-400" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">
              {graphOverview ? `${graphOverview.total_nodes} nodes` : 'Not available'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {graphOverview ? `${graphOverview.total_edges} relations` : (systemInfo?.falkordb_status || 'Disabled')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Grid: Tasks & Recent Commits */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Coordination Tasks */}
        <Card className="flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold">Active Coordination Tasks</CardTitle>
              <CardDescription>Running and pending agent assignments</CardDescription>
            </div>
            <Link to="/tasks" className="text-xs text-primary hover:underline flex items-center">
              View board <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </CardHeader>
          <CardContent className="flex-1">
            {tasks.length === 0 ? (
              <EmptyState
                icon={<CheckSquare className="h-8 w-8 text-muted-foreground" />}
                title="No active tasks"
                description="Agents have not claimed or created any tasks for this project."
              />
            ) : (
              <div className="divide-y divide-border">
                {tasks.slice(0, 5).map((t) => (
                  <div key={t.task_id} className="py-2.5 flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">{t.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {t.assigned_agent_id ? `Assigned to ${t.assigned_agent_id}` : 'Unassigned'}
                      </div>
                    </div>
                    <Badge
                      variant={
                        t.status === 'completed'
                          ? 'success'
                          : t.status === 'blocked'
                          ? 'destructive'
                          : t.status === 'running'
                          ? 'default'
                          : 'secondary'
                      }
                    >
                      {t.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Version Commits */}
        <Card className="flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold">Recent Memory Commits</CardTitle>
              <CardDescription>Immutable commit DAG history</CardDescription>
            </div>
            <Link to="/version-control" className="text-xs text-primary hover:underline flex items-center">
              Inspect DAG <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </CardHeader>
          <CardContent className="flex-1">
            {commits.length === 0 ? (
              <EmptyState
                icon={<GitBranch className="h-8 w-8 text-muted-foreground" />}
                title="No commits yet"
                description="Save or commit BMS memory records to begin version tracking."
              />
            ) : (
              <div className="divide-y divide-border">
                {commits.slice(0, 5).map((c) => (
                  <div key={c.commit_hash} className="py-2.5 flex items-start justify-between">
                    <div>
                      <div className="text-sm font-medium font-mono text-primary">
                        {truncate(c.commit_hash, 10)}
                      </div>
                      <p className="text-xs text-foreground/90 mt-0.5">{truncate(c.message, 45)}</p>
                      <span className="text-[11px] text-muted-foreground">
                        by {c.author.name} • {formatDate(c.timestamp)}
                      </span>
                    </div>
                    {c.parent_hashes.length > 1 && (
                      <Badge variant="outline" className="text-[10px]">
                        Merge
                      </Badge>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Unresolved Conflicts Warning Banner if any */}
      {conflicts.length > 0 && (
        <Card className="border-amber-500/40 bg-amber-500/10">
          <CardHeader className="flex flex-row items-center space-x-3 pb-2">
            <AlertTriangle className="h-5 w-5 text-amber-400" />
            <div>
              <CardTitle className="text-sm font-semibold text-amber-300">
                {conflicts.length} Unresolved Merge Conflicts Detected
              </CardTitle>
              <CardDescription className="text-xs text-amber-200/80">
                Concurrent agent commits have divergent field values that require review.
              </CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <Link to="/version-control">
              <Button size="sm" variant="outline" className="border-amber-500/40 text-amber-300 hover:bg-amber-500/20">
                Resolve Conflicts Now
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Storage and System Info */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase flex items-center">
              <HardDrive className="h-3.5 w-3.5 mr-1.5 text-primary" /> Storage Engine
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Provider:</span>
              <span className="font-mono font-medium">{systemInfo?.storage_provider || 'SQLite'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Mode:</span>
              <span>Local-First (zero-cloud)</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase flex items-center">
              <Network className="h-3.5 w-3.5 mr-1.5 text-primary" /> Graph Projection
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">FalkorDB:</span>
              <span className="capitalize font-medium">{systemInfo?.falkordb_status || 'Disabled'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Sync State:</span>
              <span>{graphOverview?.is_stale ? 'Stale' : 'Up to Date'}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-semibold text-muted-foreground uppercase flex items-center">
              <FileCode className="h-3.5 w-3.5 mr-1.5 text-primary" /> Standard
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Memory Standard:</span>
              <span className="font-medium">BMS v0.1</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">App Version:</span>
              <span className="font-mono">{systemInfo?.version || '0.1.0'}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

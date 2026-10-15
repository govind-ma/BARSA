import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { LoadingSpinner, EmptyState } from '@/components/ui/EmptyState';
import { formatDate, formatBytes, truncate } from '@/lib/utils';
import type {
  Artifact,
  BMSRecord,
  Commit,
  ContextPackage,
  CoordinationTask,
  Project,
} from '@/types';
import {
  Sparkles,
  GitBranch,
  Copy,
  Check,
  Download,
  AlertCircle,
  FileCheck,
  CheckSquare,
  ArrowRight,
  Network,
} from 'lucide-react';

export function ProjectDetailPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [records, setRecords] = useState<BMSRecord[]>([]);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [tasks, setTasks] = useState<CoordinationTask[]>([]);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [contextPackage, setContextPackage] = useState<ContextPackage | null>(null);
  const [isGeneratingContext, setIsGeneratingContext] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'memory' | 'tasks' | 'history' | 'graph' | 'settings'>('overview');

  useEffect(() => {
    let isMounted = true;
    if (!projectId) return;

    const loadData = async () => {
      setIsLoading(true);
      try {
        const [proj, recs, cmts, tsks, arts] = await Promise.allSettled([
          api.getProject(projectId),
          api.listRecords(projectId),
          api.listCommits(projectId),
          api.listTasks(projectId),
          api.listArtifacts(projectId),
        ]);

        if (isMounted) {
          if (proj.status === 'fulfilled') setProject(proj.value);
          if (recs.status === 'fulfilled') setRecords(recs.value);
          if (cmts.status === 'fulfilled') setCommits(cmts.value);
          if (tsks.status === 'fulfilled') setTasks(tsks.value);
          if (arts.status === 'fulfilled') setArtifacts(arts.value);
        }
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    loadData();
    return () => {
      isMounted = false;
    };
  }, [projectId]);

  const handleResumeContext = async () => {
    if (!projectId) return;
    setIsGeneratingContext(true);
    try {
      const pkg = await api.resumeContext(projectId, 8000);
      setContextPackage(pkg);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to generate context package');
    } finally {
      setIsGeneratingContext(false);
    }
  };

  const handleCopyContext = () => {
    if (!contextPackage) return;
    navigator.clipboard.writeText(contextPackage.rendered_context);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  const handleExportPackage = async () => {
    if (!projectId) return;
    try {
      const data = await api.exportProject(projectId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `barsa-project-${projectId}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to export project');
    }
  };

  if (isLoading) {
    return <LoadingSpinner text="Loading project details..." />;
  }

  if (!project) {
    return (
      <EmptyState
        icon={<AlertCircle className="h-10 w-10 text-destructive" />}
        title="Project Not Found"
        description="The requested project does not exist or has been removed."
      />
    );
  }

  const latestCommit = commits[0];
  const pendingTasks = tasks.filter((t) => t.status === 'pending' || t.status === 'ready' || t.status === 'running');
  const decisions = records.filter((r) => r.record_type === 'decision');

  return (
    <div className="space-y-6 animate-in fade-in pb-12">
      {/* Top Project Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border/80 pb-5">
        <div>
          <div className="flex items-center space-x-2.5">
            <h1 className="text-2xl font-bold tracking-tight text-foreground">{project.name}</h1>
            <Badge variant={project.status === 'active' ? 'success' : 'secondary'} className="capitalize text-[10px]">
              {project.status}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {project.description || 'FastAPI memory backend overhaul'}
          </p>
          <div className="flex items-center space-x-3 text-xs text-muted-foreground mt-2">
            <span className="font-mono text-[11px]">ID: {project.project_id}</span>
            <span>•</span>
            <span>Created {formatDate(project.created_at)}</span>
            <span>•</span>
            <span className="text-emerald-500 font-medium">BMS v0.1 Standard</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            onClick={handleResumeContext}
            isLoading={isGeneratingContext}
            className="bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm"
          >
            <Sparkles className="h-4 w-4 mr-1.5" />
            Resume Context
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportPackage} className="border-border/80">
            <Download className="h-4 w-4 mr-1.5" />
            Export BMS Package
          </Button>
        </div>
      </div>

      {/* Hero Feature: Resume Project Context Panel */}
      {contextPackage && (
        <Card className="border-primary/40 bg-gradient-to-br from-primary/5 via-card to-card rounded-2xl shadow-sm animate-in fade-in overflow-hidden">
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/60">
            <div>
              <CardTitle className="text-sm font-semibold flex items-center text-foreground">
                <Sparkles className="h-4 w-4 text-primary mr-2" />
                Optimized Resume Context Package
              </CardTitle>
              <CardDescription className="text-xs">
                Generated by Smart Context Engine • {contextPackage.total_tokens} tokens ({contextPackage.counting_method})
              </CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Button size="sm" variant="secondary" onClick={handleCopyContext} className="bg-primary/10 hover:bg-primary/20 text-primary">
                {isCopied ? <Check className="h-3.5 w-3.5 mr-1 text-emerald-500" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                {isCopied ? 'Copied to Clipboard!' : 'Copy Prompt'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4 pt-4">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs bg-muted/40 p-3 rounded-xl border border-border/70">
              <div>
                <span className="text-muted-foreground block text-[11px]">Records Included</span>
                <span className="font-semibold text-foreground text-sm">{contextPackage.records_included}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Records Omitted</span>
                <span className="font-semibold text-foreground text-sm">{contextPackage.records_omitted}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Token Budget</span>
                <span className="font-semibold text-foreground text-sm">{contextPackage.token_budget}</span>
              </div>
              <div>
                <span className="text-muted-foreground block text-[11px]">Graph Freshness</span>
                <span className="font-semibold text-emerald-500 text-sm">{contextPackage.graph_freshness || 'Verified'}</span>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="text-xs font-medium text-muted-foreground">
                  Rendered Continuity Prompt (Paste into Claude, ChatGPT, or Cursor):
                </label>
              </div>
              <pre className="p-3.5 bg-card rounded-xl border border-border/80 text-xs font-mono max-h-56 overflow-y-auto whitespace-pre-wrap text-foreground selection:bg-primary/20">
                {contextPackage.rendered_context}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Navigation Tabs: Overview | Memory | Tasks | History | Graph | Settings */}
      <div className="flex items-center space-x-1 border-b border-border/80 overflow-x-auto pb-px">
        {[
          { id: 'overview', label: 'Overview' },
          { id: 'memory', label: `Memory (${records.length})` },
          { id: 'tasks', label: `Tasks (${tasks.length})` },
          { id: 'history', label: `History (${commits.length})` },
          { id: 'graph', label: 'Graph' },
          { id: 'settings', label: 'Settings' },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-3.5 py-2 text-xs font-medium border-b-2 transition-all whitespace-nowrap ${
              activeTab === tab.id
                ? 'border-primary text-primary font-semibold'
                : 'border-transparent text-muted-foreground hover:text-foreground hover:border-border'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {/* Latest Approved Commit */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center">
                  <GitBranch className="h-4 w-4 mr-1.5 text-primary" />
                  Latest Approved Commit
                </CardTitle>
              </CardHeader>
              <CardContent>
                {latestCommit ? (
                  <div className="space-y-1.5 text-xs">
                    <div className="font-mono text-primary font-semibold">
                      {truncate(latestCommit.commit_hash, 12)}
                    </div>
                    <p className="text-foreground font-medium">{latestCommit.message}</p>
                    <p className="text-muted-foreground">
                      By {latestCommit.author.name} • {formatDate(latestCommit.timestamp)}
                    </p>
                  </div>
                ) : (
                  <p className="text-xs text-muted-foreground">No commits committed to this project.</p>
                )}
              </CardContent>
            </Card>

            {/* Pending Tasks & Blockers */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center">
                  <CheckSquare className="h-4 w-4 mr-1.5 text-emerald-400" />
                  Pending Tasks
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">{pendingTasks.length}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {tasks.filter((t) => t.status === 'blocked').length} currently blocked
                </p>
                <div className="mt-3">
                  <button onClick={() => setActiveTab('tasks')} className="text-xs text-primary hover:underline font-medium">
                    View task board →
                  </button>
                </div>
              </CardContent>
            </Card>

            {/* BMS Memory Records */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-semibold flex items-center">
                  <FileCheck className="h-4 w-4 mr-1.5 text-sky-400" />
                  BMS Memory Records
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-xl font-bold">{records.length}</div>
                <p className="text-xs text-muted-foreground mt-1">
                  {records.filter((r) => r.verification_status === 'verified').length} verified records
                </p>
                <div className="mt-3">
                  <button onClick={() => setActiveTab('memory')} className="text-xs text-primary hover:underline font-medium">
                    Explore structured memory →
                  </button>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Important Decisions & Related Artifacts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Important Decisions */}
            <Card>
              <CardHeader className="pb-3 border-b border-border/60">
                <CardTitle className="text-sm font-semibold">Important Decisions</CardTitle>
                <CardDescription className="text-xs">Historical architectural decisions recorded by agents</CardDescription>
              </CardHeader>
              <CardContent className="pt-3">
                {decisions.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-4 text-center">
                    No decision records logged yet.
                  </p>
                ) : (
                  <div className="divide-y divide-border/60">
                    {decisions.slice(0, 5).map((d) => (
                      <div key={d.record_id} className="py-2.5">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-foreground">{d.title}</span>
                          <Badge variant="outline" className="text-[10px]">
                            {d.verification_status}
                          </Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{d.summary}</p>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Related Artifacts */}
            <Card>
              <CardHeader className="pb-3 border-b border-border/60">
                <CardTitle className="text-sm font-semibold">Related Artifacts</CardTitle>
                <CardDescription className="text-xs">Code patches, design documents, and attachments</CardDescription>
              </CardHeader>
              <CardContent className="pt-3">
                {artifacts.length === 0 ? (
                  <p className="text-xs text-muted-foreground py-4 text-center">
                    No artifacts uploaded to this project.
                  </p>
                ) : (
                  <div className="divide-y divide-border/60">
                    {artifacts.slice(0, 5).map((a) => (
                      <div key={a.artifact_id} className="py-2.5 flex items-center justify-between text-xs">
                        <div>
                          <div className="font-medium text-foreground">{a.filename}</div>
                          <div className="text-muted-foreground font-mono text-[11px]">
                            {formatBytes(a.byte_size)} • {truncate(a.sha256_hash, 10)}
                          </div>
                        </div>
                        <span className="text-muted-foreground">{formatDate(a.created_at)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Tab 2: Memory */}
      {activeTab === 'memory' && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/70">
            <div>
              <CardTitle className="text-sm font-semibold">Project Memory Records</CardTitle>
              <CardDescription className="text-xs">Structured knowledge, decisions, and checkpoints</CardDescription>
            </div>
            <Link to="/memory">
              <Button size="sm" variant="outline" className="text-xs">
                Open Full Memory Explorer <ArrowRight className="h-3.5 w-3.5 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="pt-3">
            {records.length === 0 ? (
              <EmptyState title="No records" description="This project has no BMS memory records yet." />
            ) : (
              <div className="divide-y divide-border/60">
                {records.map((r) => (
                  <div key={r.record_id} className="py-3 flex items-start justify-between text-xs">
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-foreground">{r.title}</span>
                        <Badge variant="outline" className="text-[9px] uppercase font-mono">
                          {r.record_type}
                        </Badge>
                      </div>
                      <p className="text-muted-foreground mt-1">{r.summary}</p>
                      <span className="text-[11px] text-muted-foreground mt-1 block">
                        Author: {r.author} • Updated {formatDate(r.updated_at)}
                      </span>
                    </div>
                    <Badge variant={r.verification_status === 'verified' ? 'success' : 'secondary'}>
                      {r.verification_status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab 3: Tasks */}
      {activeTab === 'tasks' && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/70">
            <div>
              <CardTitle className="text-sm font-semibold">Active Coordination Tasks</CardTitle>
              <CardDescription className="text-xs">Tasks assigned to collaborative AI workers</CardDescription>
            </div>
            <Link to="/tasks">
              <Button size="sm" variant="outline" className="text-xs">
                Open Kanban Board <ArrowRight className="h-3.5 w-3.5 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="pt-3">
            {tasks.length === 0 ? (
              <EmptyState title="No tasks" description="No coordination tasks recorded for this project." />
            ) : (
              <div className="divide-y divide-border/60">
                {tasks.map((t) => (
                  <div key={t.task_id} className="py-3 flex items-center justify-between text-xs">
                    <div>
                      <div className="font-semibold text-foreground">{t.title}</div>
                      <div className="text-muted-foreground mt-0.5">{t.description}</div>
                      <div className="text-[11px] text-muted-foreground mt-1 font-mono">
                        {t.assigned_agent_id ? `Assigned to: ${t.assigned_agent_id}` : 'Unassigned'} • Priority: {t.priority}
                      </div>
                    </div>
                    <Badge variant={t.status === 'completed' ? 'success' : t.status === 'running' ? 'default' : 'secondary'}>
                      {t.status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab 4: History */}
      {activeTab === 'history' && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/70">
            <div>
              <CardTitle className="text-sm font-semibold">Commit History</CardTitle>
              <CardDescription className="text-xs">Immutable Git-style commit DAG</CardDescription>
            </div>
            <Link to="/version-control">
              <Button size="sm" variant="outline" className="text-xs">
                Open Version Control <ArrowRight className="h-3.5 w-3.5 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="pt-3">
            {commits.length === 0 ? (
              <EmptyState title="No commits" description="No commits recorded for this project." />
            ) : (
              <div className="divide-y divide-border/60">
                {commits.map((c) => (
                  <div key={c.commit_hash} className="py-3 flex items-start justify-between text-xs">
                    <div>
                      <div className="font-mono text-primary font-semibold">{c.commit_hash}</div>
                      <p className="font-medium text-foreground mt-0.5">{c.message}</p>
                      <span className="text-[11px] text-muted-foreground">
                        {c.author.name} • {formatDate(c.timestamp)}
                      </span>
                    </div>
                    <Badge variant="outline" className="text-[10px] font-mono">
                      {c.parent_hashes.length} parents
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Tab 5: Graph */}
      {activeTab === 'graph' && (
        <Card>
          <CardHeader className="pb-3 border-b border-border/70">
            <CardTitle className="text-sm font-semibold">Knowledge Graph</CardTitle>
            <CardDescription className="text-xs">Entity relationships and dependency projection</CardDescription>
          </CardHeader>
          <CardContent className="pt-4 text-center py-8">
            <Network className="h-10 w-10 text-primary mx-auto mb-2 opacity-80" />
            <p className="text-xs text-muted-foreground max-w-sm mx-auto mb-4">
              Explore interconnected requirements, decisions, and tasks visually in the Knowledge Graph Explorer.
            </p>
            <Link to="/graph">
              <Button size="sm" className="bg-primary text-primary-foreground">
                Launch Graph Canvas
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}

      {/* Tab 6: Settings */}
      {activeTab === 'settings' && (
        <Card>
          <CardHeader className="pb-3 border-b border-border/70">
            <CardTitle className="text-sm font-semibold">Project Configuration</CardTitle>
            <CardDescription className="text-xs">Manage workspace parameters and storage targets</CardDescription>
          </CardHeader>
          <CardContent className="pt-4 space-y-4 text-xs">
            <div>
              <label className="block text-muted-foreground font-medium mb-1">Project Identifier</label>
              <input
                readOnly
                value={project.project_id}
                className="w-full bg-muted/40 font-mono text-xs p-2 rounded-lg border border-input text-foreground"
              />
            </div>
            <div>
              <label className="block text-muted-foreground font-medium mb-1">Parent Workspace</label>
              <input
                readOnly
                value={project.workspace_id}
                className="w-full bg-muted/40 font-mono text-xs p-2 rounded-lg border border-input text-foreground"
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

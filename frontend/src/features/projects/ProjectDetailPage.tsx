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
  const pendingTasks = tasks.filter((t) => t.status === 'pending' || t.status === 'ready');
  const decisions = records.filter((r) => r.record_type === 'decision');

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-2xl font-bold tracking-tight">{project.name}</h1>
            <Badge variant={project.status === 'active' ? 'success' : 'secondary'} className="capitalize">
              {project.status}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            {project.description || 'No description set for this project.'}
          </p>
          <div className="flex items-center space-x-3 text-xs text-muted-foreground mt-2">
            <span className="font-mono">ID: {project.project_id}</span>
            <span>•</span>
            <span>Created {formatDate(project.created_at)}</span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={handleResumeContext} isLoading={isGeneratingContext} className="bg-primary hover:bg-primary/90">
            <Sparkles className="h-4 w-4 mr-1.5" />
            Resume Context
          </Button>
          <Button variant="outline" size="sm" onClick={handleExportPackage}>
            <Download className="h-4 w-4 mr-1.5" />
            Export BMS Package
          </Button>
        </div>
      </div>

      {/* Generated Context Package Panel */}
      {contextPackage && (
        <Card className="border-primary/40 bg-primary/5 animate-in fade-in">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <div>
              <CardTitle className="text-base font-semibold flex items-center">
                <Sparkles className="h-4 w-4 text-primary mr-2" />
                Optimized Resume Context Package
              </CardTitle>
              <CardDescription>
                Generated by Smart Context Engine • {contextPackage.total_tokens} tokens ({contextPackage.counting_method})
              </CardDescription>
            </div>
            <div className="flex items-center space-x-2">
              <Button size="sm" variant="secondary" onClick={handleCopyContext}>
                {isCopied ? <Check className="h-3.5 w-3.5 mr-1 text-emerald-400" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                {isCopied ? 'Copied!' : 'Copy Prompt'}
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap gap-4 text-xs bg-card p-3 rounded border border-border">
              <div>
                <span className="text-muted-foreground">Records Included: </span>
                <span className="font-semibold text-foreground">{contextPackage.records_included}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Records Omitted: </span>
                <span className="font-semibold text-foreground">{contextPackage.records_omitted}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Token Budget: </span>
                <span className="font-semibold text-foreground">{contextPackage.token_budget}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Freshness: </span>
                <span className="font-semibold text-foreground">{contextPackage.graph_freshness || 'Verified'}</span>
              </div>
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                Context Rendered for AI Agent:
              </label>
              <pre className="p-3 bg-muted/50 rounded border border-border text-xs font-mono max-h-48 overflow-y-auto whitespace-pre-wrap">
                {contextPackage.rendered_context}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Latest Commit */}
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
                <p className="text-foreground/90 font-medium">{latestCommit.message}</p>
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
              <Link to="/tasks" className="text-xs text-primary hover:underline">
                View task board →
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Memory Records Count */}
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
              <Link to="/memory" className="text-xs text-primary hover:underline">
                Explore structured memory →
              </Link>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Decisions & Artifacts Lists */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Important Decisions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Important Decisions</CardTitle>
            <CardDescription>Historical architectural decisions recorded by agents</CardDescription>
          </CardHeader>
          <CardContent>
            {decisions.length === 0 ? (
              <p className="text-xs text-muted-foreground py-4 text-center">
                No decision records logged yet.
              </p>
            ) : (
              <div className="divide-y divide-border">
                {decisions.slice(0, 5).map((d) => (
                  <div key={d.record_id} className="py-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{d.title}</span>
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
          <CardHeader>
            <CardTitle className="text-base font-semibold">Related Artifacts</CardTitle>
            <CardDescription>Code patches, design documents, and attachments</CardDescription>
          </CardHeader>
          <CardContent>
            {artifacts.length === 0 ? (
              <p className="text-xs text-muted-foreground py-4 text-center">
                No artifacts uploaded to this project.
              </p>
            ) : (
              <div className="divide-y divide-border">
                {artifacts.slice(0, 5).map((a) => (
                  <div key={a.artifact_id} className="py-2.5 flex items-center justify-between">
                    <div>
                      <div className="text-sm font-medium">{a.filename}</div>
                      <div className="text-xs text-muted-foreground font-mono">
                        {formatBytes(a.byte_size)} • {truncate(a.sha256_hash, 10)}
                      </div>
                    </div>
                    <span className="text-xs text-muted-foreground">{formatDate(a.created_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

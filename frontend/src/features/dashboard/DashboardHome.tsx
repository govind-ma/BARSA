import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import { formatDate, truncate } from '@/lib/utils';
import type { AgentProfile, BMSRecord, Commit, ConflictItem, GraphOverview } from '@/types';
import {
  FolderKanban,
  FileCode,
  GitBranch,
  Bot,
  AlertTriangle,
  Network,
  Sparkles,
  ArrowRight,
  HardDrive,
  Plus,
  Terminal,
  Copy,
  Check,
  BrainCircuit,
  Activity,
} from 'lucide-react';

export function DashboardHome() {
  const { activeWorkspace, activeProject, projects, isBackendOnline, systemInfo, refreshProjects } = useApp();
  const [commits, setCommits] = useState<Commit[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [records, setRecords] = useState<BMSRecord[]>([]);
  const [conflicts, setConflicts] = useState<ConflictItem[]>([]);
  const [graphOverview, setGraphOverview] = useState<GraphOverview | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [isConnectAiOpen, setIsConnectAiOpen] = useState(false);
  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [isCreatingProject, setIsCreatingProject] = useState(false);

  // Resume Quick Drawer / Modal
  const [isResumeModalOpen, setIsResumeModalOpen] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  useEffect(() => {
    let isMounted = true;
    const loadOverviewData = async () => {
      setIsLoading(true);
      try {
        if (activeProject) {
          const [cmts, conft, grph, recs] = await Promise.allSettled([
            api.listCommits(activeProject.project_id),
            api.listConflicts(activeProject.project_id),
            api.getGraphOverview(activeProject.project_id),
            api.listRecords(activeProject.project_id),
          ]);
          if (isMounted) {
            if (cmts.status === 'fulfilled') setCommits(cmts.value);
            if (conft.status === 'fulfilled') setConflicts(conft.value);
            if (grph.status === 'fulfilled') setGraphOverview(grph.value);
            if (recs.status === 'fulfilled') setRecords(recs.value);
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

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activeWorkspace || !newProjectName.trim()) return;
    setIsCreatingProject(true);
    try {
      await api.createProject(activeWorkspace.workspace_id, {
        name: newProjectName.trim(),
        description: newProjectDesc.trim() || undefined,
      });
      await refreshProjects();
      setIsCreateProjectOpen(false);
      setNewProjectName('');
      setNewProjectDesc('');
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsCreatingProject(false);
    }
  };

  const copyConfigSnippet = (text: string) => {
    navigator.clipboard.writeText(text);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

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

  const latestCheckpoint = records.find((r) => r.record_type === 'checkpoint');

  return (
    <div className="space-y-8 animate-in fade-in pb-12">
      {/* Hero Introduction Section (EvoMap Inspiration) */}
      <div className="relative overflow-hidden rounded-2xl border border-border/80 bg-gradient-to-b from-card via-card/90 to-card/60 p-6 md:p-8 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="max-w-2xl space-y-2">
            <div className="inline-flex items-center space-x-2 px-2.5 py-0.5 rounded-full bg-primary/10 border border-primary/20 text-primary text-xs font-medium">
              <Sparkles className="h-3 w-3" />
              <span>System Overview</span>
            </div>
            <h1 className="text-2xl md:text-3xl font-bold tracking-tight text-foreground">
              Your AI memory, everywhere.
            </h1>
            <p className="text-sm md:text-base text-muted-foreground leading-relaxed">
              Continue your work across AI agents, accounts, and devices. Barsa preserves your decisions, checkpoints, and versioned progress in a decentralized, user-owned knowledge standard.
            </p>
          </div>

          {/* Prominent Quick Actions */}
          <div className="flex flex-wrap items-center gap-2.5 shrink-0">
            <Button
              size="sm"
              onClick={() => setIsCreateProjectOpen(true)}
              className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-sm"
            >
              <Plus className="h-3.5 w-3.5 mr-1.5" />
              Create Project
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsConnectAiOpen(true)}
              className="border-border/80 hover:bg-accent/80"
            >
              <Terminal className="h-3.5 w-3.5 mr-1.5 text-primary" />
              Connect AI
            </Button>
            {activeProject && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsResumeModalOpen(true)}
                className="bg-accent/60 hover:bg-accent text-accent-foreground font-medium"
              >
                <Sparkles className="h-3.5 w-3.5 mr-1.5 text-primary" />
                Resume Project
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Top Stat Metrics Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="hover:border-primary/40 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Active Workspace
            </CardTitle>
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

        <Card className="hover:border-emerald-500/40 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Connected Agents
            </CardTitle>
            <Bot className="h-4 w-4 text-emerald-400" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{agents.length}</div>
            <p className="text-xs text-muted-foreground mt-1 flex items-center">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
              {agents.filter((a) => a.state === 'active').length} currently active
            </p>
          </CardContent>
        </Card>

        <Card className="hover:border-indigo-500/40 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Version Commits
            </CardTitle>
            <GitBranch className="h-4 w-4 text-indigo-400" />
          </CardHeader>
          <CardContent>
            <div className="text-xl font-bold">{commits.length}</div>
            <p className="text-xs text-muted-foreground mt-1">
              {commits[0] ? `Latest: ${truncate(commits[0].commit_hash, 8)}` : 'No commits recorded'}
            </p>
          </CardContent>
        </Card>

        <Card className="hover:border-sky-500/40 transition-colors">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Knowledge Graph
            </CardTitle>
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

      {/* Recent Projects Section */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold tracking-tight text-foreground">Recent Projects</h2>
            <p className="text-xs text-muted-foreground">Active memory workspaces and continuity targets</p>
          </div>
          <Link to="/projects" className="text-xs text-primary hover:underline font-medium flex items-center">
            View all projects <ArrowRight className="h-3 w-3 ml-1" />
          </Link>
        </div>

        {projects.length === 0 ? (
          <EmptyState
            icon={<FileCode className="h-8 w-8 text-muted-foreground" />}
            title="No projects yet"
            description="Create your first project and give your AI a memory that lasts across platforms."
            actionLabel="Create First Project"
            onAction={() => setIsCreateProjectOpen(true)}
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {projects.slice(0, 3).map((proj) => (
              <Card
                key={proj.project_id}
                className={`relative flex flex-col justify-between hover:border-primary/50 transition-all ${
                  activeProject?.project_id === proj.project_id ? 'border-primary/40 bg-card/90' : 'bg-card/50'
                }`}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <CardTitle className="text-sm font-semibold truncate max-w-[180px]">{proj.name}</CardTitle>
                    <Badge variant={proj.status === 'active' ? 'success' : 'secondary'} className="text-[10px]">
                      {proj.status}
                    </Badge>
                  </div>
                  <CardDescription className="text-xs line-clamp-2 mt-1">
                    {proj.description || 'No description provided.'}
                  </CardDescription>
                </CardHeader>
                <CardContent className="pt-2">
                  <div className="flex items-center justify-between pt-2 border-t border-border/70 text-xs">
                    <span className="text-[11px] text-muted-foreground font-mono">{truncate(proj.project_id, 10)}</span>
                    <Link
                      to={`/projects/${proj.project_id}`}
                      className="inline-flex items-center text-primary font-medium hover:underline text-xs"
                    >
                      Open Project <ArrowRight className="h-3 w-3 ml-1" />
                    </Link>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Main Grid: Recently Updated Memories & Recent Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recently Updated Memories */}
        <Card className="flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/60">
            <div>
              <CardTitle className="text-sm font-semibold flex items-center">
                <BrainCircuit className="h-4 w-4 mr-2 text-primary" />
                Recently Updated Memories
              </CardTitle>
              <CardDescription className="text-xs">BMS records for active project</CardDescription>
            </div>
            <Link to="/memory" className="text-xs text-primary hover:underline font-medium flex items-center">
              Explore all <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </CardHeader>
          <CardContent className="flex-1 pt-3">
            {records.length === 0 ? (
              <EmptyState
                icon={<BrainCircuit className="h-8 w-8 text-muted-foreground" />}
                title="No saved memory records"
                description="Save architecture decisions, knowledge, or checkpoints from your AI agent."
              />
            ) : (
              <div className="divide-y divide-border/60">
                {records.slice(0, 5).map((r) => (
                  <div key={r.record_id} className="py-2.5 flex items-start justify-between">
                    <div className="space-y-0.5">
                      <div className="text-xs font-semibold text-foreground flex items-center space-x-2">
                        <span>{r.title}</span>
                        <Badge variant="outline" className="text-[9px] uppercase px-1.5 py-0 font-mono">
                          {r.record_type}
                        </Badge>
                      </div>
                      <p className="text-xs text-muted-foreground line-clamp-1">{r.summary}</p>
                    </div>
                    <Badge
                      variant={r.verification_status === 'verified' ? 'success' : 'secondary'}
                      className="text-[9px] shrink-0 ml-2"
                    >
                      {r.verification_status}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Version Commits / Activity */}
        <Card className="flex flex-col">
          <CardHeader className="flex flex-row items-center justify-between pb-3 border-b border-border/60">
            <div>
              <CardTitle className="text-sm font-semibold flex items-center">
                <Activity className="h-4 w-4 mr-2 text-indigo-400" />
                Recent Activity & Commits
              </CardTitle>
              <CardDescription className="text-xs">Immutable commit DAG timeline</CardDescription>
            </div>
            <Link to="/version-control" className="text-xs text-primary hover:underline font-medium flex items-center">
              Inspect DAG <ArrowRight className="h-3 w-3 ml-1" />
            </Link>
          </CardHeader>
          <CardContent className="flex-1 pt-3">
            {commits.length === 0 ? (
              <EmptyState
                icon={<GitBranch className="h-8 w-8 text-muted-foreground" />}
                title="No commits yet"
                description="Save or commit BMS memory records to begin version tracking."
              />
            ) : (
              <div className="divide-y divide-border/60">
                {commits.slice(0, 5).map((c) => (
                  <div key={c.commit_hash} className="py-2.5 flex items-start justify-between">
                    <div>
                      <div className="text-xs font-mono font-medium text-primary">
                        {truncate(c.commit_hash, 10)}
                      </div>
                      <p className="text-xs text-foreground/90 mt-0.5 font-medium">{truncate(c.message, 45)}</p>
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

      {/* Connect AI Assistant Modal */}
      <Modal
        isOpen={isConnectAiOpen}
        onClose={() => setIsConnectAiOpen(false)}
        title="Connect AI Assistant via FastMCP"
        description="Plug BARSA into your favorite AI tool with standard Model Context Protocol."
      >
        <div className="space-y-4 text-xs">
          <div>
            <span className="font-semibold text-foreground block mb-1">Option 1: Claude Desktop</span>
            <p className="text-muted-foreground mb-2">
              Add this block into your <code className="font-mono text-primary">%APPDATA%\Claude\claude_desktop_config.json</code>:
            </p>
            <div className="relative bg-muted/60 p-3 rounded-lg font-mono text-[11px] border border-border/80">
              <pre className="overflow-x-auto text-foreground">
{`{
  "mcpServers": {
    "barsa": {
      "command": "D:\\\\projects\\\\BARSA\\\\.venv\\\\Scripts\\\\python.exe",
      "args": ["-m", "barsa.mcp.server"]
    }
  }
}`}
              </pre>
              <Button
                size="sm"
                variant="ghost"
                className="absolute top-2 right-2 h-7 px-2 text-[10px]"
                onClick={() =>
                  copyConfigSnippet(`{\n  "mcpServers": {\n    "barsa": {\n      "command": "D:\\\\projects\\\\BARSA\\\\.venv\\\\Scripts\\\\python.exe",\n      "args": ["-m", "barsa.mcp.server"]\n    }\n  }\n}`)
                }
              >
                {isCopied ? <Check className="h-3.5 w-3.5 text-emerald-500 mr-1" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                {isCopied ? 'Copied' : 'Copy'}
              </Button>
            </div>
          </div>

          <div>
            <span className="font-semibold text-foreground block mb-1">Option 2: Cursor / Windsurf</span>
            <p className="text-muted-foreground mb-1">
              Add MCP Server: <strong>Type:</strong> Command | <strong>Command:</strong>{' '}
              <code className="font-mono text-primary">D:\projects\BARSA\.venv\Scripts\python.exe -m barsa.mcp.server</code>
            </p>
          </div>

          <div className="pt-2 border-t border-border/70 flex justify-end">
            <Button size="sm" onClick={() => setIsConnectAiOpen(false)}>
              Done
            </Button>
          </div>
        </div>
      </Modal>

      {/* Create Project Modal */}
      <Modal
        isOpen={isCreateProjectOpen}
        onClose={() => setIsCreateProjectOpen(false)}
        title="Create New Project"
        description={`Add a new memory project inside workspace "${activeWorkspace?.name || 'Selected Workspace'}".`}
      >
        <form onSubmit={handleCreateProject} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-foreground mb-1">Project Name *</label>
            <input
              type="text"
              required
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="e.g. Authentication Service"
              className="w-full text-xs bg-muted/30 border border-input rounded-lg px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-foreground mb-1">Description (Optional)</label>
            <textarea
              rows={3}
              value={newProjectDesc}
              onChange={(e) => setNewProjectDesc(e.target.value)}
              placeholder="Primary goals and scope of this project"
              className="w-full text-xs bg-muted/30 border border-input rounded-lg px-3 py-2 text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="pt-3 border-t border-border/70 flex justify-end space-x-2">
            <Button variant="outline" size="sm" type="button" onClick={() => setIsCreateProjectOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" type="submit" disabled={isCreatingProject || !newProjectName.trim()}>
              {isCreatingProject ? 'Creating...' : 'Create Project'}
            </Button>
          </div>
        </form>
      </Modal>

      {/* Resume Project Prompt Modal */}
      <Modal
        isOpen={isResumeModalOpen}
        onClose={() => setIsResumeModalOpen(false)}
        title="Resume Project Context"
        description="Copy this prompt into any AI agent (Claude, ChatGPT, Cursor) to resume where you stopped."
      >
        <div className="space-y-4 text-xs">
          <div className="p-3 bg-muted/40 rounded-xl border border-border/80 space-y-2">
            <div className="flex items-center justify-between">
              <span className="font-semibold text-foreground text-xs">Formatted Continuity Prompt</span>
              <Button
                size="sm"
                variant="ghost"
                onClick={() =>
                  copyConfigSnippet(
                    `Connect to Barsa. Retrieve project "${activeProject?.name}" (ID: ${activeProject?.project_id}) and latest checkpoint. Continue from the active next action.`
                  )
                }
                className="h-7 text-[10px]"
              >
                {isCopied ? <Check className="h-3.5 w-3.5 text-emerald-500 mr-1" /> : <Copy className="h-3.5 w-3.5 mr-1" />}
                {isCopied ? 'Copied' : 'Copy Prompt'}
              </Button>
            </div>
            <p className="font-mono text-[11px] text-primary bg-background/80 p-2.5 rounded-lg border border-border/60">
              {`Connect to Barsa. Retrieve project "${activeProject?.name || 'Selected'}" (ID: ${
                activeProject?.project_id || ''
              }) and latest checkpoint. Continue from the active next action.`}
            </p>
          </div>

          {latestCheckpoint && (
            <div className="space-y-1 text-xs">
              <span className="font-semibold text-foreground">Latest Stored Checkpoint:</span>
              <p className="text-muted-foreground">{latestCheckpoint.summary}</p>
            </div>
          )}

          <div className="pt-2 border-t border-border/70 flex justify-end">
            <Link to={`/projects/${activeProject?.project_id}/resume`}>
              <Button size="sm" className="bg-primary text-primary-foreground">
                <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                View Detailed Token Budget & Slices
              </Button>
            </Link>
          </div>
        </div>
      </Modal>
    </div>
  );
}

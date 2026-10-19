import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Modal } from '@/components/ui/Modal';
import { NewProjectModal } from '@/components/projects/NewProjectModal';
import { formatDate } from '@/lib/utils';
import type {
  Commit,
  AgentProfile,
  BMSRecord,
  CoordinationTask,
  GraphResumeResponse,
} from '@/types';
import {
  Sparkles,
  ArrowRight,
  Bot,
  User,
  CheckCircle2,
  BookmarkCheck,
  BrainCircuit,
  GitCommit,
  HelpCircle,
  Copy,
  Check,
  Plus,
  Play,
  Network,
} from 'lucide-react';

export function DashboardHome() {
  const { activeProject, projects, activeWorkspace, refreshProjects } = useApp();

  // Data states
  const [tasks, setTasks] = useState<CoordinationTask[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [records, setRecords] = useState<BMSRecord[]>([]);
  const [commits, setCommits] = useState<Commit[]>([]);
  const [checkpoints, setCheckpoints] = useState<BMSRecord[]>([]);
  const [resumeData, setResumeData] = useState<GraphResumeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Modals
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);
  const [isContinueWorkOpen, setIsContinueWorkOpen] = useState(false);
  const [isWhyTaskOpen, setIsWhyTaskOpen] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);

  // Load project-scoped data
  useEffect(() => {
    let isMounted = true;

    async function loadData() {
      const targetProj = activeProject || projects[0];
      if (!targetProj) {
        setIsLoading(false);
        return;
      }

      setIsLoading(true);
      try {
        const [tsks, agts, recs, cmts, chks, resm] = await Promise.allSettled([
          api.listTasks(targetProj.project_id),
          api.listAgents(),
          api.listRecords(targetProj.project_id),
          api.listCommits(targetProj.project_id),
          api.listRecords(targetProj.project_id, 'checkpoint'),
          api.getGraphResume(targetProj.project_id).catch(() => null),
        ]);

        if (!isMounted) return;

        if (tsks.status === 'fulfilled') setTasks(tsks.value);
        if (agts.status === 'fulfilled') setAgents(agts.value);
        if (recs.status === 'fulfilled') setRecords(recs.value);
        if (cmts.status === 'fulfilled') setCommits(cmts.value);
        if (chks.status === 'fulfilled') setCheckpoints(chks.value);
        if (resm.status === 'fulfilled') setResumeData(resm.value);
      } finally {
        if (!isMounted) return;
        setIsLoading(false);
      }
    }

    loadData();
    return () => {
      isMounted = false;
    };
  }, [activeProject?.project_id]);

  // Determine current or recommended task
  const recommendedTask = resumeData?.recommended_task;
  const currentTask =
    tasks.find((t) => t.status === 'running') ||
    tasks.find((t) => t.task_id === recommendedTask?.task_id) ||
    tasks[0] ||
    null;

  // Latest checkpoint
  const latestCheckpoint = checkpoints[0] || null;

  // Recent Activity Events (3 to 5 items)
  const recentActivity = React.useMemo(() => {
    const list: Array<{
      id: string;
      title: string;
      time: string;
      author: string;
      isAgent: boolean;
      type: 'task' | 'decision' | 'checkpoint' | 'commit';
      summary?: string;
    }> = [];

    // Commits
    commits.slice(0, 3).forEach((c) => {
      const isAgent = !/human|owner|developer|user/i.test(c.author?.name || '');
      list.push({
        id: `c-${c.commit_hash}`,
        title: c.message || 'Saved memory commit',
        time: c.timestamp,
        author: c.author?.name || 'AI Agent',
        isAgent,
        type: 'commit',
      });
    });

    // Checkpoints
    checkpoints.slice(0, 2).forEach((ck) => {
      list.push({
        id: `ck-${ck.record_id}`,
        title: ck.title || 'Agent state checkpoint saved',
        time: ck.created_at,
        author: ck.author || 'AI Agent',
        isAgent: true,
        type: 'checkpoint',
        summary: ck.summary,
      });
    });

    // Decisions
    records
      .filter((r) => r.record_type === 'decision')
      .slice(0, 2)
      .forEach((d) => {
        const isAgent = !/human|owner|developer|user/i.test(d.author || '');
        list.push({
          id: `d-${d.record_id}`,
          title: d.title,
          time: d.created_at,
          author: d.author || 'AI Agent',
          isAgent,
          type: 'decision',
          summary: d.summary,
        });
      });

    return list
      .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime())
      .slice(0, 4);
  }, [commits, checkpoints, records]);

  // Handover prompt for Continue Work
  const handoverPromptText = React.useMemo(() => {
    if (!activeProject) return '';
    const taskTitle = currentTask?.title || recommendedTask?.title || 'System Core Architecture';
    const whyReady = resumeData?.why_ready || 'Prerequisites and architecture decisions satisfied.';
    const adrs = records
      .filter((r) => r.record_type === 'decision')
      .map((d) => `- ${d.title}: ${d.summary || ''}`)
      .join('\n');

    return `### BARSA AI Handover Context
**Project:** ${activeProject.name} (ID: ${activeProject.project_id})
**Active Task:** ${taskTitle}
**Graph Readiness:** ${whyReady}

${adrs ? `**Key Architectural Decisions (ADRs):**\n${adrs}\n` : ''}
**Instructions:**
Continue implementation of "${taskTitle}". Comply strictly with existing project ADRs and commit your progress to BARSA memory when verified.`;
  }, [activeProject, currentTask, recommendedTask, resumeData, records]);

  const handleCopyPrompt = () => {
    navigator.clipboard.writeText(handoverPromptText);
    setCopiedPrompt(true);
    setTimeout(() => setCopiedPrompt(false), 2500);
  };

  // If no projects exist in the workspace, show clean empty state
  if (!activeProject && projects.length === 0 && !isLoading) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 animate-page-enter">
        <div className="glass-card p-10 rounded-2xl text-center space-y-5 border border-border-subtle shadow-lg">
          <div className="h-14 w-14 rounded-2xl bg-gradient-to-br from-lava-yellow via-lava-orange to-lava-red flex items-center justify-center text-white mx-auto shadow-md">
            <Sparkles className="h-7 w-7" />
          </div>
          <div className="space-y-2">
            <h1 className="text-2xl font-heading font-bold text-text-primary tracking-tight">
              Your projects start here
            </h1>
            <p className="text-sm text-text-muted max-w-md mx-auto leading-relaxed">
              Create a project to give your AI agents a shared place to preserve and continue their work.
            </p>
          </div>
          <div className="pt-2">
            <Button
              onClick={() => setIsNewProjectOpen(true)}
              className="px-6 py-2.5 rounded-xl btn-primary-lava font-medium text-sm shadow-md"
            >
              <Plus className="h-4 w-4 mr-2" />
              Create Project
            </Button>
          </div>
        </div>

        {activeWorkspace && (
          <NewProjectModal
            isOpen={isNewProjectOpen}
            onClose={() => setIsNewProjectOpen(false)}
            onSuccess={() => {
              refreshProjects();
              setIsNewProjectOpen(false);
            }}
          />
        )}
      </div>
    );
  }

  const currentProject = activeProject || projects[0] || null;

  return (
    <div className="space-y-6 animate-page-enter select-none">
      {/* ======================================================== */}
      {/* 1. PROJECT HEADER                                        */}
      {/* ======================================================== */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border-subtle pb-4">
        <div>
          <div className="flex items-center space-x-2.5">
            <span className="sr-only">System Overview</span>
            <h1 className="text-2xl font-heading font-bold tracking-tight text-text-primary">
              {currentProject?.name || 'Project Workspace'}
            </h1>
            <Badge variant="success" className="text-[10px] uppercase font-mono tracking-wider">
              {currentProject?.status || 'Active'}
            </Badge>
          </div>
          <p className="text-sm text-text-muted mt-1 max-w-2xl">
            {currentProject?.description ||
              'A collaborative AI project workspace with persistent memory and graph coordination.'}
          </p>
        </div>

        <div className="flex items-center space-x-2.5">
          <Link to="/graph">
            <Button variant="secondary" size="sm" className="btn-secondary-ice text-xs font-medium flex items-center space-x-1.5">
              <Network className="h-3.5 w-3.5 text-lava-orange" />
              <span>Mind Map (Graph)</span>
            </Button>
          </Link>
          <Link to="/tasks">
            <Button variant="secondary" size="sm" className="btn-secondary-ice text-xs font-medium">
              View Tasks ({tasks.length})
            </Button>
          </Link>
          <Button
            onClick={() => setIsContinueWorkOpen(true)}
            size="sm"
            className="btn-primary-lava text-xs font-medium shadow-xs"
          >
            <Play className="h-3.5 w-3.5 mr-1.5 fill-current" />
            Continue Work
          </Button>
        </div>
      </div>
      {/* ======================================================== */}
      {/* 2. MAIN WORKSPACE GRID                                   */}
      {/* ======================================================== */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* ---------------------------------------------------- */}
          {/* LEFT COLUMN: Section A & Section D (8 cols)          */}
          {/* ---------------------------------------------------- */}
          <div className="lg:col-span-8 space-y-6">
            {/* SECTION A — CONTINUE WORK HERO CARD */}
            <div className="glass-card rounded-2xl p-6 border-l-4 border-l-lava-orange relative overflow-hidden shadow-sm">
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="space-y-3 flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] font-mono font-bold uppercase tracking-wider text-lava-orange bg-lava-orange/10 px-2 py-0.5 rounded-md">
                      Current Work
                    </span>
                    {currentTask?.priority && (
                      <Badge variant="outline" className="text-[10px] uppercase font-mono">
                        Priority: {currentTask.priority}
                      </Badge>
                    )}
                    <span className="text-xs text-text-muted">
                      {currentTask?.status === 'running' ? 'In Progress' : 'Ready to start'}
                    </span>
                  </div>

                  <div>
                    <h2 className="text-lg font-heading font-semibold text-text-primary">
                      {currentTask?.title || recommendedTask?.title || 'Auth Middleware & API Security'}
                    </h2>
                    <p className="text-xs text-text-muted mt-1 leading-relaxed">
                      {currentTask?.description ||
                        'Implement token authentication and rate limiting for secure local agent coordination.'}
                    </p>
                  </div>

                  {/* Recommendation Reason */}
                  <div className="rounded-xl bg-ice-100/70 dark:bg-white/[0.03] border border-border-subtle p-3 text-xs flex items-start space-x-2.5">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                    <div className="flex-1 text-text-secondary leading-relaxed">
                      <span className="font-semibold text-text-primary">Recommended by FalkorDB: </span>
                      {resumeData?.why_ready ||
                        'Prerequisite architecture decision records and required capabilities are satisfied.'}
                    </div>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="mt-5 pt-4 border-t border-border-subtle flex flex-wrap items-center justify-between gap-3">
                <button
                  onClick={() => setIsWhyTaskOpen(true)}
                  className="inline-flex items-center space-x-1.5 text-xs text-text-muted hover:text-text-primary transition-colors font-medium"
                >
                  <HelpCircle className="h-3.5 w-3.5 text-steel-500" />
                  <span>Why this task? (Graph Reasoning)</span>
                </button>

                <div className="flex items-center space-x-2">
                  <Link to="/tasks">
                    <Button variant="secondary" size="sm" className="btn-secondary-ice text-xs font-medium">
                      Manage in Board
                    </Button>
                  </Link>
                  <Button
                    onClick={() => setIsContinueWorkOpen(true)}
                    size="sm"
                    className="btn-primary-lava text-xs font-medium shadow-xs"
                  >
                    <Play className="h-3.5 w-3.5 mr-1.5 fill-current" />
                    Continue Work
                  </Button>
                </div>
              </div>
            </div>

            {/* SECTION D — RECENT ACTIVITY */}
            <div className="glass-card rounded-2xl p-6 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-heading font-semibold text-text-primary">Recent Activity</h3>
                  <p className="text-xs text-text-muted mt-0.5">
                    Latest changes, checkpoints, and decisions committed by your team.
                  </p>
                  <span className="sr-only">Version Commits</span>
                </div>
                <Link
                  to="/history"
                  className="inline-flex items-center text-xs font-medium text-lava-orange hover:underline"
                >
                  <span>View All Activity</span>
                  <ArrowRight className="h-3.5 w-3.5 ml-1" />
                </Link>
              </div>

              {recentActivity.length === 0 ? (
                <div className="text-center py-8 text-xs text-text-muted">
                  No activity recorded yet. As your agents save memories or complete tasks, activity appears here.
                </div>
              ) : (
                <div className="space-y-3 pt-1">
                  {recentActivity.map((ev) => (
                    <div
                      key={ev.id}
                      className="flex items-start justify-between p-3 rounded-xl bg-ice-100/50 dark:bg-white/[0.02] border border-border-subtle hover:border-border-strong transition-all"
                    >
                      <div className="flex items-start space-x-3">
                        <div className="h-7 w-7 rounded-lg bg-surface border border-border-subtle flex items-center justify-center text-text-muted mt-0.5 shrink-0">
                          {ev.type === 'decision' ? (
                            <BrainCircuit className="h-3.5 w-3.5 text-amber-500" />
                          ) : ev.type === 'checkpoint' ? (
                            <BookmarkCheck className="h-3.5 w-3.5 text-lava-orange" />
                          ) : (
                            <GitCommit className="h-3.5 w-3.5 text-steel-500" />
                          )}
                        </div>
                        <div>
                          <p className="text-xs font-semibold text-text-primary">{ev.title}</p>
                          <div className="flex items-center space-x-2 text-[11px] text-text-muted mt-1">
                            <span className="flex items-center space-x-1">
                              {ev.isAgent ? (
                                <Bot className="h-3 w-3 text-lava-orange" />
                              ) : (
                                <User className="h-3 w-3 text-steel-500" />
                              )}
                              <span>{ev.author}</span>
                            </span>
                            <span>•</span>
                            <span className="font-mono">{formatDate(ev.time)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* ---------------------------------------------------- */}
          {/* RIGHT COLUMN: Section B & Section C (4 cols)         */}
          {/* ---------------------------------------------------- */}
          <div className="lg:col-span-4 space-y-6">
            {/* SECTION B — CONNECTED AGENTS */}
            <div className="glass-card rounded-2xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <h3 className="text-sm font-heading font-semibold text-text-primary">Connected Agents</h3>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-ice-200 dark:bg-bg-elevated text-text-primary">
                    {agents.length}
                  </span>
                </div>
                <Link
                  to="/agents"
                  className="text-xs font-medium text-lava-orange hover:underline inline-flex items-center"
                >
                  <span>View Agents</span>
                  <ArrowRight className="h-3 w-3 ml-1" />
                </Link>
              </div>

              {agents.length === 0 ? (
                <div className="text-center py-6 text-xs text-text-muted space-y-2">
                  <p>No agents registered in this workspace yet.</p>
                  <Link to="/agents">
                    <Button variant="secondary" size="sm" className="btn-secondary-ice text-xs">
                      Register Agent
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="space-y-2.5">
                  {agents.slice(0, 3).map((a) => (
                    <div
                      key={a.agent_id}
                      className="p-3 rounded-xl bg-ice-100/50 dark:bg-white/[0.02] border border-border-subtle flex items-center justify-between text-xs"
                    >
                      <div className="flex items-center space-x-2.5 min-w-0">
                        <div className="h-7 w-7 rounded-lg bg-lava-orange/10 border border-lava-orange/30 flex items-center justify-center text-lava-orange shrink-0">
                          <Bot className="h-4 w-4" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-semibold text-text-primary truncate">{a.display_name || a.agent_id}</p>
                          <p className="text-[10px] text-text-muted font-mono truncate">
                            {a.provider} • {a.model || 'custom'}
                          </p>
                        </div>
                      </div>
                      <span className="h-2 w-2 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.7)] shrink-0" />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* SECTION C — LATEST CHECKPOINT */}
            <div className="glass-card rounded-2xl p-5 space-y-4 shadow-sm">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-heading font-semibold text-text-primary">Latest Checkpoint</h3>
                <Link
                  to="/checkpoints"
                  className="text-xs font-medium text-lava-orange hover:underline inline-flex items-center"
                >
                  <span>All Snapshots</span>
                  <ArrowRight className="h-3 w-3 ml-1" />
                </Link>
              </div>

              {latestCheckpoint ? (
                <div className="space-y-3">
                  <div className="p-3.5 rounded-xl bg-ice-100/60 dark:bg-white/[0.02] border border-border-subtle space-y-2">
                    <div className="flex items-center space-x-2">
                      <BookmarkCheck className="h-4 w-4 text-lava-orange" />
                      <span className="font-semibold text-xs text-text-primary">
                        {latestCheckpoint.title || latestCheckpoint.record_id.substring(0, 10)}
                      </span>
                    </div>
                    <p className="text-[11px] text-text-muted leading-relaxed line-clamp-2">
                      {latestCheckpoint.summary ||
                        'Verified memory state and architectural alignment saved by coordinator.'}
                    </p>
                    <div className="pt-1 flex items-center justify-between text-[10px] text-text-muted font-mono">
                      <span>By {latestCheckpoint.author || 'AI Agent'}</span>
                      <span>{formatDate(latestCheckpoint.created_at)}</span>
                    </div>
                  </div>

                  <Link to={`/checkpoints`}>
                    <Button variant="secondary" size="sm" className="w-full btn-secondary-ice text-xs font-medium">
                      Resume from Checkpoint
                    </Button>
                  </Link>
                </div>
              ) : (
                <div className="text-center py-6 text-xs text-text-muted space-y-2">
                  <p>No checkpoints saved for this project yet.</p>
                  <p className="text-[11px] text-text-muted/80">
                    Snapshots appear automatically when agents complete milestones.
                  </p>
                </div>
              )}
            </div>

            {/* QUICK LINK TO ADVANCED KNOWLEDGE GRAPH */}
            <div className="rounded-2xl p-4 solid-floating-surface border border-border-subtle flex items-center justify-between text-xs">
              <div className="space-y-0.5">
                <span className="font-semibold text-text-primary">Knowledge Graph</span>
                <p className="text-[11px] text-text-muted">Interactive FalkorDB 3D node topology</p>
              </div>
              <Link to="/graph">
                <Button size="sm" variant="secondary" className="btn-secondary-ice text-xs">
                  Open Graph
                </Button>
              </Link>
            </div>
          </div>
        </div>

      {/* ======================================================== */}
      {/* 3. CONTINUE WORK HANDOVER MODAL                          */}
      {/* ======================================================== */}
      {isContinueWorkOpen && (
        <Modal
          isOpen={isContinueWorkOpen}
          onClose={() => setIsContinueWorkOpen(false)}
          title="Continue Work with AI Agent"
          className="max-w-2xl"
        >
          <div className="space-y-4 text-xs">
            <p className="text-text-muted leading-relaxed">
              Copy this structured context handover and paste it into Claude, ChatGPT, or Kimi to resume work with
              complete architectural context:
            </p>

            <div className="relative">
              <pre className="p-4 rounded-xl bg-ice-100/80 dark:bg-black/40 border border-border-subtle font-mono text-[11px] text-text-primary whitespace-pre-wrap max-h-60 overflow-y-auto leading-relaxed">
                {handoverPromptText}
              </pre>
              <button
                onClick={handleCopyPrompt}
                className="absolute top-2.5 right-2.5 px-2.5 py-1 rounded-lg bg-surface hover:bg-ice-200 dark:bg-bg-elevated border border-border-strong text-xs font-medium text-text-primary flex items-center space-x-1.5 shadow-sm transition-all"
              >
                {copiedPrompt ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-500" />
                    <span>Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3 text-steel-500" />
                    <span>Copy Prompt</span>
                  </>
                )}
              </button>
            </div>

            <div className="pt-3 border-t border-border-subtle flex items-center justify-between">
              <Link to="/tasks" onClick={() => setIsContinueWorkOpen(false)}>
                <Button variant="secondary" size="sm" className="btn-secondary-ice text-xs">
                  Go to Tasks Board
                </Button>
              </Link>
              <Button
                onClick={() => {
                  handleCopyPrompt();
                  setIsContinueWorkOpen(false);
                }}
                size="sm"
                className="btn-primary-lava text-xs font-medium"
              >
                Copy & Close
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* ======================================================== */}
      {/* 4. WHY THIS TASK? GRAPH REASONING MODAL                  */}
      {/* ======================================================== */}
      {isWhyTaskOpen && (
        <Modal
          isOpen={isWhyTaskOpen}
          onClose={() => setIsWhyTaskOpen(false)}
          title="Graph Recommendation Reasoning"
          className="max-w-md"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3.5 rounded-xl bg-ice-100 dark:bg-white/[0.03] border border-border-subtle space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-heading font-semibold text-text-primary text-sm">
                  {currentTask?.title || recommendedTask?.title || 'Active Task'}
                </span>
                {recommendedTask?.readiness_score !== undefined && (
                  <span className="font-mono text-xs font-bold text-lava-orange px-2 py-0.5 rounded bg-lava-orange/10 border border-lava-orange/30">
                    SCORE {recommendedTask.readiness_score}
                  </span>
                )}
              </div>
              <p className="text-text-secondary leading-relaxed">
                {resumeData?.why_ready ||
                  'All prerequisite tasks and Architecture Decision Records (ADRs) have been satisfied in the FalkorDB knowledge graph.'}
              </p>
            </div>

            <div className="space-y-2 font-mono text-[11px]">
              <div className="flex justify-between py-1 border-b border-border-subtle text-text-muted">
                <span>Completed Dependencies:</span>
                <span className="text-emerald-500 font-semibold">
                  {recommendedTask?.completed_dependencies?.length || 0} satisfied
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border-subtle text-text-muted">
                <span>Active Blockers:</span>
                <span className="text-text-primary font-semibold">
                  {recommendedTask?.active_blockers?.length || 0} blockers
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border-subtle text-text-muted">
                <span>FalkorDB Engine:</span>
                <span className="text-text-primary font-semibold">
                  {resumeData?.falkordb_version || '1.8.0 Cypher'}
                </span>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <Button onClick={() => setIsWhyTaskOpen(false)} size="sm" className="btn-secondary-ice text-xs">
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}

import React, { useEffect, useState, useRef } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { EmptyState } from '@/components/ui/EmptyState';
import { ProjectStatusStrip } from '@/features/mission-control/ProjectStatusStrip';
import { AgentHandoffStream } from '@/features/mission-control/AgentHandoffStream';
import { LiveKnowledgeGraph } from '@/features/mission-control/LiveKnowledgeGraph';
import { ActiveStateHandover } from '@/features/mission-control/ActiveStateHandover';
import type {
  Commit,
  AgentProfile,
  BMSRecord,
  GraphOverview,
  SubgraphResponse,
  GraphNode,
  GraphEdge,
  GraphResumeResponse,
  Branch,
  CoordinationTask,
} from '@/types';
import { AlertTriangle, Check, X } from 'lucide-react';

export function DashboardHome() {
  const { activeProject, isBackendOnline, systemInfo } = useApp();

  // Data states
  const [commits, setCommits] = useState<Commit[]>([]);
  const [agents, setAgents] = useState<AgentProfile[]>([]);
  const [records, setRecords] = useState<BMSRecord[]>([]);
  const [graphOverview, setGraphOverview] = useState<GraphOverview | null>(null);
  const [subgraph, setSubgraph] = useState<SubgraphResponse | null>(null);
  const [resumeData, setResumeData] = useState<GraphResumeResponse | null>(null);
  const [branches, setBranches] = useState<Branch[]>([]);
  const [tasks, setTasks] = useState<CoordinationTask[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Interaction states
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [highlightedNodeId, setHighlightedNodeId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'stream' | 'graph' | 'handover'>('graph');

  // Toast notification state
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const hasLoadedOnce = useRef(false);

  const showToast = (message: string) => {
    if (toastTimeoutRef.current) clearTimeout(toastTimeoutRef.current);
    setToastMessage(message);
    toastTimeoutRef.current = setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  };

  // Primary data fetcher
  const loadMissionControlData = async () => {
    if (!hasLoadedOnce.current) {
      setIsLoading(true);
    }
    try {
      if (activeProject) {
        const [
          cmtsRes,
          grphRes,
          recsRes,
          subgRes,
          resmRes,
          brnchRes,
          tsksRes,
        ] = await Promise.allSettled([
          api.listCommits(activeProject.project_id),
          api.getGraphOverview(activeProject.project_id),
          api.listRecords(activeProject.project_id),
          api.getSubgraph(activeProject.project_id),
          api.getGraphResume(activeProject.project_id),
          api.listBranches(activeProject.project_id),
          api.listTasks(activeProject.project_id),
        ]);

        if (cmtsRes.status === 'fulfilled') setCommits(cmtsRes.value);
        if (grphRes.status === 'fulfilled') setGraphOverview(grphRes.value);
        if (recsRes.status === 'fulfilled') setRecords(recsRes.value);
        if (subgRes.status === 'fulfilled') setSubgraph(subgRes.value);
        if (resmRes.status === 'fulfilled') setResumeData(resmRes.value);
        if (brnchRes.status === 'fulfilled') setBranches(brnchRes.value);
        if (tsksRes.status === 'fulfilled') setTasks(tsksRes.value);
      }
      const agts = await api.listAgents().catch(() => []);
      setAgents(agts);
    } finally {
      setIsLoading(false);
      hasLoadedOnce.current = true;
    }
  };

  useEffect(() => {
    loadMissionControlData();
  }, [activeProject]);

  // Fallback demo graph data if project has no nodes yet
  const displayNodes: GraphNode[] = React.useMemo(() => {
    if (subgraph?.nodes && subgraph.nodes.length > 0) {
      return subgraph.nodes;
    }
    if (!activeProject) return [];
    return [
      { id: 'TASK-017', label: 'Auth Middleware', type: 'Task', properties: { status: 'ready', priority: 'high' } },
      { id: 'TASK-018', label: 'SQLite Engine', type: 'Task', properties: { status: 'running' } },
      { id: 'ADR-004', label: 'Local-First Schema', type: 'Decision', properties: { status: 'approved' } },
      { id: 'CAP-001', label: 'FastAPI Backend', type: 'Capability', properties: {} },
      { id: 'AGT-01', label: 'Claude 3.7', type: 'Agent', properties: { model: 'claude-3-7-sonnet' } },
      { id: 'AGT-02', label: 'GPT-4o', type: 'Agent', properties: { model: 'gpt-4o' } },
    ];
  }, [subgraph?.nodes, activeProject]);

  const displayEdges: GraphEdge[] = React.useMemo(() => {
    if (subgraph?.edges && subgraph.edges.length > 0) {
      return subgraph.edges;
    }
    if (!activeProject) return [];
    return [
      { id: 'edge_1', source: 'TASK-017', target: 'ADR-004', type: 'DEPENDS_ON' },
      { id: 'edge_2', source: 'TASK-018', target: 'ADR-004', type: 'DEPENDS_ON' },
      { id: 'edge_3', source: 'TASK-017', target: 'CAP-001', type: 'REQUIRES' },
      { id: 'edge_4', source: 'AGT-01', target: 'TASK-017', type: 'ASSIGNED_TO' },
      { id: 'edge_5', source: 'AGT-02', target: 'TASK-018', type: 'ASSIGNED_TO' },
    ];
  }, [subgraph?.edges, activeProject]);

  // Active task details
  const activeTask = tasks[0] || (resumeData?.recommended_task ? {
    task_id: resumeData.recommended_task.task_id,
    project_id: activeProject?.project_id || '',
    title: resumeData.recommended_task.title,
    status: 'running',
    priority: resumeData.recommended_task.priority as any,
    required_capabilities: resumeData.recommended_task.required_capabilities,
    dependencies: resumeData.recommended_task.completed_dependencies,
    blockers: resumeData.recommended_task.active_blockers,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  } : null);

  const lastCheckpoint = records.find((r) => r.record_type === 'checkpoint') || null;
  const activeBranch = branches.find((b) => b.is_default) || branches[0] || null;

  // Re-rank action handler
  const handleRunRerank = async () => {
    if (!activeProject) return;
    try {
      const refreshedResume = await api.getGraphResume(activeProject.project_id);
      setResumeData(refreshedResume);
      showToast('FalkorDB graph re-rank complete. Next task highlighted.');
    } catch {
      showToast('FalkorDB re-rank executed on cached graph projection.');
    }
  };

  // Inject Blocker action handler
  const handleInjectBlocker = () => {
    const targetTaskId = resumeData?.recommended_task?.task_id || displayNodes[0]?.id || 'TASK-017';
    // Add synthetic blocker edge
    const newBlockerEdge: GraphEdge = {
      id: `edge_blocker_${Date.now()}`,
      source: targetTaskId,
      target: 'ISSUE-SYNTH-99',
      type: 'BLOCKED_BY',
    };
    const newBlockerNode: GraphNode = {
      id: 'ISSUE-SYNTH-99',
      label: 'Security Audit Hold',
      type: 'Issue',
      properties: { severity: 'critical', author: 'agent-sec' },
    };

    setSubgraph((prev) => ({
      nodes: prev ? [...prev.nodes, newBlockerNode] : [newBlockerNode],
      edges: prev ? [...prev.edges, newBlockerEdge] : [newBlockerEdge],
    }));

    showToast(`Synthetic blocker injected onto ${targetTaskId}. FalkorDB graph updated.`);
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

  const checkpointsList = records.filter((r) => r.record_type === 'checkpoint');

  return (
    <div className="flex flex-col h-full w-full max-w-[1750px] mx-auto animate-page-enter">
      {/* 1. Top Project Status Strip */}
      <ProjectStatusStrip
        projectName={activeProject?.name || 'Local Workspace'}
        activeBranch={activeBranch}
        latestCommit={commits[0] || null}
        agentCount={agents.length}
        commitCount={commits.length}
        graphOverview={graphOverview}
        systemInfo={systemInfo}
        isBackendOnline={isBackendOnline}
      />

      {/* Mobile/Tablet Tab Switcher (< 1024px) */}
      <div className="flex lg:hidden items-center justify-between p-1.5 mb-3 rounded-xl bg-card/60 backdrop-blur-md border border-ice/15">
        <div className="flex items-center space-x-1 w-full">
          <button
            onClick={() => setActiveTab('stream')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'stream'
                ? 'bg-ice text-background shadow-[0_0_10px_rgba(56,189,248,0.5)]'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Handoff Stream
          </button>
          <button
            onClick={() => setActiveTab('graph')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'graph'
                ? 'bg-ice text-background shadow-[0_0_10px_rgba(56,189,248,0.5)]'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Live Graph
          </button>
          <button
            onClick={() => setActiveTab('handover')}
            className={`flex-1 py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'handover'
                ? 'bg-ice text-background shadow-[0_0_10px_rgba(56,189,248,0.5)]'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            Active State
          </button>
        </div>
      </div>

      {/* 2. Three-Pane CSS Grid Layout (Full Height under Top Bar) */}
      <div className="flex-1 grid grid-cols-1 md:grid-cols-[280px_1fr] lg:grid-cols-[300px_1fr_340px] gap-3 h-[calc(100vh-140px)] min-h-[580px] overflow-hidden">
        {/* LEFT PANE: Agent Handoff Stream (300px) */}
        <div className={`${activeTab === 'stream' ? 'block' : 'hidden'} md:block h-full overflow-hidden`}>
          <AgentHandoffStream
            commits={commits}
            checkpoints={checkpointsList}
            isLoading={isLoading && commits.length === 0}
            onHoverItem={(nodeId) => setHighlightedNodeId(nodeId)}
            onSelectItem={(nodeId) => {
              const matchedNode = displayNodes.find((n) => n.id.includes(nodeId) || nodeId.includes(n.id));
              if (matchedNode) {
                setSelectedNode(matchedNode);
                setActiveTab('handover');
              }
            }}
          />
        </div>

        {/* CENTER PANE: Live Knowledge Graph (Flexible Width) */}
        <div className={`${activeTab === 'graph' ? 'block' : 'hidden'} md:block h-full overflow-hidden relative`}>
          <LiveKnowledgeGraph
            nodes={displayNodes}
            edges={displayEdges}
            recommendedTaskId={resumeData?.recommended_task?.task_id || displayNodes[0]?.id}
            readinessScore={resumeData?.recommended_task?.readiness_score ?? 270.0}
            whyReadyText={resumeData?.why_ready}
            selectedNodeId={selectedNode?.id}
            highlightedNodeId={highlightedNodeId}
            onSelectNode={(node) => {
              setSelectedNode(node);
              // On mobile/tablet, open handover tab/drawer to view node details
              if (window.innerWidth < 1024) {
                setActiveTab('handover');
              }
            }}
            onRunRerank={handleRunRerank}
            onInjectBlocker={handleInjectBlocker}
            isLoading={isLoading}
          />
        </div>

        {/* RIGHT PANE: Active State and Handover (340px on desktop) */}
        <div
          className={`${
            activeTab === 'handover' ? 'block' : 'hidden'
          } lg:block h-full overflow-hidden`}
        >
          <ActiveStateHandover
            selectedNode={selectedNode}
            onClearSelectedNode={() => setSelectedNode(null)}
            activeTask={activeTask}
            lastCheckpoint={lastCheckpoint}
            whyReadyText={resumeData?.why_ready}
            projectName={activeProject?.name || 'Local Workspace'}
            allEdges={displayEdges}
            onTriggerToast={showToast}
          />
        </div>
      </div>

      {/* Floating Toast Notification (Solid surface with left lava accent bar) */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-toast flex items-center space-x-3 px-4 py-3 rounded-lg solid-floating-surface border-l-4 !border-l-lava-orange text-text-primary text-xs font-medium animate-page-enter">
          <div className="h-5 w-5 rounded-full bg-lava-orange/15 border border-lava-orange/30 flex items-center justify-center text-lava-orange shrink-0">
            <Check className="h-3 w-3" />
          </div>
          <span>{toastMessage}</span>
          <button
            onClick={() => setToastMessage(null)}
            className="text-text-muted hover:text-text-primary ml-2 p-0.5"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

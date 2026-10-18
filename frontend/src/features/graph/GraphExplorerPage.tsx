import { useEffect, useState, useMemo } from 'react';
import { useApp } from '@/app/AppContext';
import { api } from '@/lib/api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Badge } from '@/components/ui/Badge';
import { Input } from '@/components/ui/Input';
import { EmptyState, LoadingSpinner } from '@/components/ui/EmptyState';
import type { GraphNode, GraphOverview, SubgraphResponse, GraphResumeResponse } from '@/types';
import {
  Network,
  RefreshCw,
  Search,
  Filter,
  Table as TableIcon,
  Layers,
  Info,
  AlertTriangle,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  Play,
  ArrowRight,
  UserCheck,
} from 'lucide-react';

const NODE_COLORS: Record<string, string> = {
  Project: 'fill-primary stroke-primary/80',
  Task: 'fill-amber-500 stroke-amber-600',
  Requirement: 'fill-emerald-500 stroke-emerald-600',
  Decision: 'fill-indigo-500 stroke-indigo-600',
  Knowledge: 'fill-sky-400 stroke-sky-500',
  Checkpoint: 'fill-purple-500 stroke-purple-600',
  Agent: 'fill-pink-500 stroke-pink-600',
  Artifact: 'fill-teal-500 stroke-teal-600',
  Capability: 'fill-cyan-500 stroke-cyan-600',
  Issue: 'fill-rose-500 stroke-rose-600',
};

export function GraphExplorerPage() {
  const { activeProject, systemInfo } = useApp();
  const [subgraph, setSubgraph] = useState<SubgraphResponse | null>(null);
  const [overview, setOverview] = useState<GraphOverview | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRebuilding, setIsRebuilding] = useState(false);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [viewMode, setViewMode] = useState<'canvas' | 'table'>('canvas');

  // FalkorDB Project Continuation State
  const [resumeData, setResumeData] = useState<GraphResumeResponse | null>(null);
  const [isResuming, setIsResuming] = useState(false);
  const [resumeError, setResumeError] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('');

  // Zoom & Pan state for SVG Canvas
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  const loadResumeData = async (agentId?: string) => {
    if (!activeProject) return;
    setIsResuming(true);
    setResumeError(null);
    try {
      const data = await api.getGraphResume(activeProject.project_id, agentId ?? (selectedAgentId || undefined));
      setResumeData(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'FalkorDB graph continuation failed';
      setResumeError(msg);
      setResumeData(null);
    } finally {
      setIsResuming(false);
    }
  };

  const loadGraph = async () => {
    if (!activeProject) return;
    setIsLoading(true);
    try {
      const [ov, sg] = await Promise.allSettled([
        api.getGraphOverview(activeProject.project_id),
        api.getSubgraph(activeProject.project_id),
      ]);
      if (ov.status === 'fulfilled') setOverview(ov.value);
      if (sg.status === 'fulfilled') setSubgraph(sg.value);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
    loadResumeData();
  }, [activeProject]);

  const handleRebuild = async () => {
    if (!activeProject) return;
    setIsRebuilding(true);
    try {
      await api.rebuildGraph(activeProject.project_id);
      await loadGraph();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Rebuild failed');
    } finally {
      setIsRebuilding(false);
    }
  };

  // Filtered nodes
  const filteredNodes = useMemo(() => {
    if (!subgraph) return [];
    return subgraph.nodes.filter((node) => {
      const matchesSearch =
        node.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
        node.id.toLowerCase().includes(searchQuery.toLowerCase());
      const matchesType = selectedType === 'all' || node.type === selectedType;
      return matchesSearch && matchesType;
    });
  }, [subgraph, searchQuery, selectedType]);

  // Node positions computed deterministically in a circular/force layout
  const nodePositions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    const n = filteredNodes.length;
    if (n === 0) return map;

    const centerX = 400;
    const centerY = 280;
    const radius = Math.min(240, 60 + n * 20);

    filteredNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / n;
      map.set(node.id, {
        x: centerX + radius * Math.cos(angle),
        y: centerY + radius * Math.sin(angle),
      });
    });
    return map;
  }, [filteredNodes]);

  // Mouse handlers for pan
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => setIsDragging(false);

  if (!activeProject) {
    return (
      <EmptyState
        icon={<Network className="h-10 w-10 text-muted-foreground" />}
        title="No Project Selected"
        description="Select an active project from the top navigation to visualize the knowledge graph."
      />
    );
  }

  const isFalkorDbAvailable = systemInfo?.falkordb_status === 'connected';

  return (
    <div className="space-y-6 animate-in fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">FalkorDB Knowledge Graph</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Interconnected entities, task dependencies, and decision lineage for "{activeProject.name}".
          </p>
        </div>

        <div className="flex items-center space-x-2">
          {/* View toggle (Canvas vs Table for accessibility) */}
          <Button
            variant={viewMode === 'canvas' ? 'secondary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('canvas')}
            aria-label="View graph canvas"
          >
            <Layers className="h-4 w-4 mr-1.5" />
            Canvas
          </Button>
          <Button
            variant={viewMode === 'table' ? 'secondary' : 'outline'}
            size="sm"
            onClick={() => setViewMode('table')}
            aria-label="View accessible table list"
          >
            <TableIcon className="h-4 w-4 mr-1.5" />
            Accessible Table
          </Button>

          <Button size="sm" variant="outline" onClick={handleRebuild} isLoading={isRebuilding}>
            <RefreshCw className="h-4 w-4 mr-1.5" />
            Rebuild Projection
          </Button>
        </div>
      </div>

      {/* Freshness & Status Banner */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-card p-3 rounded-lg border border-border text-xs">
        <div className="flex items-center space-x-3">
          <Badge variant={isFalkorDbAvailable ? 'success' : 'secondary'} className="text-[11px]">
            {isFalkorDbAvailable ? 'FalkorDB Connected' : 'FalkorDB Disabled / Inactive'}
          </Badge>
          <span className="text-muted-foreground">
            Revision: <strong className="text-foreground">{overview?.projection_revision || 0}</strong>
          </span>
          <span className="text-muted-foreground">
            Total Entities: <strong className="text-foreground">{overview?.total_nodes || 0}</strong>
          </span>
          <span className="text-muted-foreground">
            Total Relations: <strong className="text-foreground">{overview?.total_edges || 0}</strong>
          </span>
        </div>

        {overview?.is_stale && (
          <div className="flex items-center text-amber-400 font-medium space-x-1">
            <AlertTriangle className="h-3.5 w-3.5" />
            <span>Projection is stale. Click "Rebuild Projection" to resync.</span>
          </div>
        )}
      </div>

      {/* FalkorDB Continuation Engine (Section 7) */}
      <Card className="border-border bg-card/60 backdrop-blur-sm overflow-hidden">
        <CardHeader className="pb-3 border-b border-border/50 bg-muted/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 rounded-md bg-primary/10 text-primary">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  Graph-Powered Continuation Engine
                  <Badge variant="outline" className="text-[10px] font-mono border-primary/30 text-primary">
                    barsa_graph_resume
                  </Badge>
                </CardTitle>
                <CardDescription className="text-xs">
                  FalkorDB Cypher multi-hop traversal, dependency analysis, blocker detection, and agent capability matching
                </CardDescription>
              </div>
            </div>

            {/* Agent Selector & Execution Control */}
            <div className="flex items-center space-x-2">
              <select
                value={selectedAgentId}
                onChange={(e) => {
                  setSelectedAgentId(e.target.value);
                  loadResumeData(e.target.value);
                }}
                className="h-8 rounded-md border border-input bg-card px-2.5 text-xs text-foreground focus:outline-none"
                aria-label="Filter continuation by agent"
              >
                <option value="">Any / Unassigned Agent</option>
                <option value="agent-backend-claude">Claude (Backend / Auth / DB)</option>
                <option value="agent-frontend-gpt4o">GPT-4o (Frontend / React / UI)</option>
                <option value="agent-tester">QA / Test Engineer</option>
              </select>

              <Button
                size="sm"
                variant="secondary"
                onClick={() => loadResumeData()}
                isLoading={isResuming}
                className="h-8 text-xs font-medium"
              >
                <Play className="h-3.5 w-3.5 mr-1" />
                Compute Next Task
              </Button>
            </div>
          </div>
        </CardHeader>

        <CardContent className="pt-4 space-y-4">
          {resumeError ? (
            /* Explicit Failure Banner when FalkorDB is offline */
            <div className="p-4 rounded-lg border border-destructive/40 bg-destructive/10 text-destructive flex items-start space-x-3">
              <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" />
              <div>
                <h4 className="text-sm font-semibold">FalkorDB Required — Graph Reasoning Offline</h4>
                <p className="text-xs mt-1 text-destructive/90">
                  {resumeError}
                </p>
                <p className="text-[11px] mt-2 text-muted-foreground">
                  Rule 3 Compliance: Non-graph storage and ordinary dashboard views remain functional, but authoritative next-task reasoning requires an active FalkorDB graph engine.
                </p>
              </div>
            </div>
          ) : isResuming ? (
            <div className="py-8 text-center text-muted-foreground text-xs">
              <LoadingSpinner text="Executing Cypher multi-hop traversals in FalkorDB..." />
            </div>
          ) : resumeData?.recommended_task ? (
            <div className="space-y-4">
              {/* Recommended Task Banner */}
              <div className="p-4 rounded-lg border border-primary/20 bg-primary/5 space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <Badge variant="default" className="text-xs bg-primary text-primary-foreground font-medium">
                      Recommended Next Task
                    </Badge>
                    <Badge variant="outline" className="font-mono text-xs">
                      {resumeData.recommended_task.task_id}
                    </Badge>
                    <Badge variant="secondary" className="capitalize text-[11px]">
                      Priority: {resumeData.recommended_task.priority}
                    </Badge>
                    <Badge variant="outline" className="text-[11px] text-emerald-500 border-emerald-500/30">
                      Readiness Score: {resumeData.recommended_task.readiness_score}
                    </Badge>
                  </div>

                  <span className="text-[11px] text-muted-foreground font-mono">
                    FalkorDB v{resumeData.falkordb_version} • {resumeData.total_tasks_evaluated} Tasks Evaluated
                  </span>
                </div>

                <h3 className="text-base font-semibold text-foreground">
                  {resumeData.recommended_task.title}
                </h3>

                {/* Why Ready Box */}
                <div className="p-3 rounded-md bg-background/80 border border-border text-xs text-foreground/90 leading-relaxed flex items-start space-x-2.5">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0 mt-0.5" />
                  <div>
                    <span className="font-semibold text-foreground">Graph Traversal Explanation: </span>
                    {resumeData.why_ready}
                  </div>
                </div>
              </div>

              {/* 3-Column Diagnostic Details */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                {/* Column 1: Dependencies & Blockers */}
                <div className="p-3 rounded-lg border border-border bg-card/40 space-y-2">
                  <span className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider block">
                    Dependencies & Blockers
                  </span>
                  <div>
                    <span className="text-[11px] text-muted-foreground">Completed Prerequisites:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {resumeData.recommended_task.completed_dependencies.length > 0 ? (
                        resumeData.recommended_task.completed_dependencies.map((dep) => (
                          <Badge key={dep} variant="outline" className="text-[10px] text-emerald-400 border-emerald-500/20 bg-emerald-500/5">
                            ✓ {dep}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-muted-foreground italic text-[11px]">None required</span>
                      )}
                    </div>
                  </div>

                  <div className="pt-1">
                    <span className="text-[11px] text-muted-foreground">Active Blockers:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {resumeData.recommended_task.active_blockers.length > 0 ? (
                        resumeData.recommended_task.active_blockers.map((b) => (
                          <Badge key={b} variant="destructive" className="text-[10px]">
                            ✕ {b}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-emerald-500 text-[11px] flex items-center gap-1">
                          <CheckCircle2 className="h-3 w-3" /> Unblocked
                        </span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Column 2: Capabilities & Agent Match */}
                <div className="p-3 rounded-lg border border-border bg-card/40 space-y-2">
                  <span className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider block">
                    Capabilities & Agent Match
                  </span>
                  <div>
                    <span className="text-[11px] text-muted-foreground">Required Capabilities:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {resumeData.recommended_task.required_capabilities.map((cap) => (
                        <Badge key={cap} variant="secondary" className="text-[10px]">
                          {cap}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div className="pt-1">
                    <span className="text-[11px] text-muted-foreground">Suitable AI Agents:</span>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {resumeData.suitable_agents.length > 0 ? (
                        resumeData.suitable_agents.map((ag) => (
                          <Badge key={ag.agent_id} variant="outline" className="text-[10px] text-primary border-primary/30">
                            <UserCheck className="h-2.5 w-2.5 mr-1" />
                            {ag.display_name || ag.agent_id}
                          </Badge>
                        ))
                      ) : (
                        <span className="text-muted-foreground italic text-[11px]">Any agent</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Column 3: Decisions & Domain Knowledge */}
                <div className="p-3 rounded-lg border border-border bg-card/40 space-y-2">
                  <span className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider block">
                    ADR Lineage & Knowledge
                  </span>
                  <div>
                    <span className="text-[11px] text-muted-foreground">Connected Decisions:</span>
                    <div className="mt-1 space-y-1">
                      {resumeData.recommended_task.related_decisions.length > 0 ? (
                        resumeData.recommended_task.related_decisions.map((d: any, idx: number) => (
                          <div key={idx} className="text-[11px] text-foreground truncate">
                            • <strong className="text-primary">{d.decision_id || d.id}:</strong> {d.title || d.label}
                          </div>
                        ))
                      ) : (
                        <span className="text-muted-foreground italic text-[11px]">None linked</span>
                      )}
                    </div>
                  </div>

                  <div className="pt-1">
                    <span className="text-[11px] text-muted-foreground">Linked Knowledge:</span>
                    <div className="mt-1 space-y-1">
                      {resumeData.recommended_task.related_knowledge.length > 0 ? (
                        resumeData.recommended_task.related_knowledge.map((k: any, idx: number) => (
                          <div key={idx} className="text-[11px] text-foreground truncate">
                            • {k.title || k.label || k.id}
                          </div>
                        ))
                      ) : (
                        <span className="text-muted-foreground italic text-[11px]">None linked</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Supporting Graph Paths */}
              {resumeData.supporting_graph_paths.length > 0 && (
                <div className="p-3 rounded-lg border border-border bg-muted/20">
                  <span className="font-semibold text-muted-foreground uppercase text-[10px] tracking-wider block mb-2">
                    Verified FalkorDB Graph Paths ({resumeData.supporting_graph_paths.length})
                  </span>
                  <div className="space-y-1 font-mono text-[11px] text-muted-foreground max-h-32 overflow-y-auto pr-2">
                    {resumeData.supporting_graph_paths.map((path, idx) => (
                      <div key={idx} className="bg-background/60 px-2 py-1 rounded border border-border/50 text-foreground/80 flex items-center space-x-1">
                        <ArrowRight className="h-3 w-3 text-primary shrink-0" />
                        <span className="truncate">{path}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="py-6 text-center text-muted-foreground text-xs">
              <p>No continuation data available. Select a project and click "Compute Next Task" to query FalkorDB.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Search & Filter Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-card p-3 rounded-lg border border-border">
        <div className="relative w-full sm:w-80">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search graph entities..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9 h-9 text-xs"
          />
        </div>

        <div className="flex items-center space-x-2 w-full sm:w-auto">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <select
            value={selectedType}
            onChange={(e) => setSelectedType(e.target.value)}
            className="h-9 rounded-md border border-input bg-card px-3 text-xs focus:outline-none"
          >
            <option value="all">All Entity Types</option>
            <option value="Project">Project</option>
            <option value="Task">Task</option>
            <option value="Requirement">Requirement</option>
            <option value="Decision">Decision</option>
            <option value="Knowledge">Knowledge</option>
            <option value="Checkpoint">Checkpoint</option>
            <option value="Agent">Agent</option>
            <option value="Artifact">Artifact</option>
          </select>
        </div>
      </div>

      {/* Main View Area */}
      {isLoading ? (
        <LoadingSpinner text="Retrieving graph projection from backend..." />
      ) : viewMode === 'canvas' ? (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Interactive SVG Canvas */}
          <div className="lg:col-span-3 border border-border rounded-lg bg-card/60 relative overflow-hidden h-[600px] select-none">
            {/* Zoom Controls */}
            <div className="absolute bottom-4 left-4 z-10 flex space-x-1 bg-background/90 p-1 rounded-md border border-border">
              <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setZoom((z) => Math.min(2, z + 0.2))}>
                +
              </Button>
              <Button size="sm" variant="ghost" className="h-7 w-7 p-0" onClick={() => setZoom((z) => Math.max(0.4, z - 0.2))}>
                -
              </Button>
              <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}>
                Reset
              </Button>
            </div>

            <svg
              className="w-full h-full cursor-grab active:cursor-grabbing"
              onMouseDown={handleMouseDown}
              onMouseMove={handleMouseMove}
              onMouseUp={handleMouseUp}
              onMouseLeave={handleMouseUp}
            >
              <g transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}>
                {/* Edges */}
                {subgraph?.edges.map((edge) => {
                  const s = nodePositions.get(edge.source);
                  const t = nodePositions.get(edge.target);
                  if (!s || !t) return null;
                  return (
                    <g key={edge.id}>
                      <line
                        x1={s.x}
                        y1={s.y}
                        x2={t.x}
                        y2={t.y}
                        stroke="hsl(var(--muted-foreground) / 0.3)"
                        strokeWidth="2"
                        strokeDasharray={edge.type === 'DEPENDS_ON' ? '4 2' : undefined}
                      />
                      <text
                        x={(s.x + t.x) / 2}
                        y={(s.y + t.y) / 2 - 4}
                        fill="hsl(var(--muted-foreground))"
                        fontSize="9"
                        textAnchor="middle"
                        className="font-mono pointer-events-none"
                      >
                        {edge.type}
                      </text>
                    </g>
                  );
                })}

                {/* Nodes */}
                {filteredNodes.map((node) => {
                  const pos = nodePositions.get(node.id);
                  if (!pos) return null;
                  const isSelected = selectedNode?.id === node.id;
                  const colorClass = NODE_COLORS[node.type] || 'fill-muted stroke-border';

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${pos.x}, ${pos.y})`}
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedNode(node);
                      }}
                      className="cursor-pointer group"
                    >
                      <circle
                        r={isSelected ? 24 : 18}
                        className={`transition-all duration-200 ${colorClass} ${
                          isSelected ? 'ring-4 ring-primary' : 'group-hover:opacity-90'
                        }`}
                        strokeWidth="2"
                      />
                      <text
                        y="30"
                        fill="hsl(var(--foreground))"
                        fontSize="11"
                        textAnchor="middle"
                        className="font-medium pointer-events-none"
                      >
                        {node.label.length > 16 ? node.label.substring(0, 14) + '...' : node.label}
                      </text>
                      <text
                        y="42"
                        fill="hsl(var(--muted-foreground))"
                        fontSize="9"
                        textAnchor="middle"
                        className="font-mono pointer-events-none capitalize"
                      >
                        {node.type}
                      </text>
                    </g>
                  );
                })}
              </g>
            </svg>
          </div>

          {/* Node Inspector Panel */}
          <div className="lg:col-span-1">
            {selectedNode ? (
              <Card className="h-full">
                <CardHeader>
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline" className="capitalize text-xs">
                      {selectedNode.type}
                    </Badge>
                  </div>
                  <CardTitle className="text-base font-bold mt-2">{selectedNode.label}</CardTitle>
                  <CardDescription className="font-mono text-xs mt-1">ID: {selectedNode.id}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h5 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                      Entity Properties
                    </h5>
                    <div className="space-y-2 text-xs bg-muted/40 p-3 rounded border border-border">
                      {Object.entries(selectedNode.properties).map(([k, v]) => (
                        <div key={k} className="flex justify-between">
                          <span className="text-muted-foreground font-mono">{k}:</span>
                          <span className="font-medium text-foreground truncate max-w-[150px]">
                            {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h5 className="text-xs font-semibold text-muted-foreground uppercase mb-2">
                      Connected Relationships
                    </h5>
                    <div className="space-y-1.5 text-xs max-h-48 overflow-y-auto">
                      {subgraph?.edges
                        .filter((e) => e.source === selectedNode.id || e.target === selectedNode.id)
                        .map((e) => (
                          <div key={e.id} className="p-2 rounded bg-card border border-border text-[11px]">
                            <span className="font-semibold text-primary">{e.type}</span>
                            <div className="text-muted-foreground mt-0.5 truncate">
                              {e.source === selectedNode.id ? `→ ${e.target}` : `← ${e.source}`}
                            </div>
                          </div>
                        ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ) : (
              <Card className="h-full flex items-center justify-center p-8 text-center text-muted-foreground">
                <div>
                  <Info className="h-8 w-8 mx-auto text-muted-foreground/60 mb-2" />
                  <p className="text-xs">Click any node on the graph canvas to inspect properties and lineage.</p>
                </div>
              </Card>
            )}
          </div>
        </div>
      ) : (
        /* Accessible Table Alternative View (Section 18) */
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-semibold">Accessible Graph Entity List</CardTitle>
            <CardDescription>
              Screen-reader accessible table of knowledge graph entities and properties
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs" aria-label="Knowledge Graph Entities">
                <thead className="border-b border-border bg-muted/50 text-muted-foreground">
                  <tr>
                    <th className="p-3">ID</th>
                    <th className="p-3">Type</th>
                    <th className="p-3">Label</th>
                    <th className="p-3">Properties</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {filteredNodes.map((n) => (
                    <tr key={n.id} className="hover:bg-accent/40">
                      <td className="p-3 font-mono text-[11px] text-primary">{n.id}</td>
                      <td className="p-3">
                        <Badge variant="outline" className="capitalize text-[10px]">
                          {n.type}
                        </Badge>
                      </td>
                      <td className="p-3 font-medium">{n.label}</td>
                      <td className="p-3 font-mono text-[11px] text-muted-foreground max-w-xs truncate">
                        {JSON.stringify(n.properties)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
